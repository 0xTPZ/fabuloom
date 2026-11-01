"""Render the first vertical Fabuloom story video from a Kokoro manifest."""

from __future__ import annotations

import argparse
from array import array
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import textwrap
from urllib.parse import urlparse
import wave
import zlib

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


STORY_ID = "fabuloom-first-video-dora"
VOICE_ID = "pf_dora"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
STORY_TEXT = """Quando a última estrela desapareceu, o mundo acreditou que a escuridão havia vencido.

Mas, nas profundezas do antigo templo, uma pequena chama ainda resistia.

Não era o fogo dos reis, nem a magia dos grandes guardiões.

Era a esperança de alguém que se recusava a desistir.

E, naquela noite, uma única luz foi suficiente para despertar um novo amanhecer."""


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _write_rgba_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = b"".join(b"\x00" + bytes(pixels[row * width * 4 : (row + 1) * width * 4]) for row in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(rows, 6))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def _set_pixel(pixels: bytearray, width: int, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if 0 <= x < width and 0 <= y < len(pixels) // (width * 4):
        index = (y * width + x) * 4
        pixels[index : index + 4] = bytes(color)


def _ellipse(
    pixels: bytearray,
    width: int,
    height: int,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    color: tuple[int, int, int, int],
) -> None:
    for y in range(max(0, int(center_y - radius_y - 1)), min(height, int(center_y + radius_y + 2))):
        for x in range(max(0, int(center_x - radius_x - 1)), min(width, int(center_x + radius_x + 2))):
            dx = (x - center_x) / max(1.0, radius_x)
            dy = (y - center_y) / max(1.0, radius_y)
            if dx * dx + dy * dy <= 1.0:
                _set_pixel(pixels, width, x, y, color)


def _line(pixels: bytearray, width: int, height: int, x1: int, y1: int, x2: int, y2: int, thickness: int, color: tuple[int, int, int, int]) -> None:
    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
    for step in range(steps + 1):
        progress = step / steps
        x = round(x1 + (x2 - x1) * progress)
        y = round(y1 + (y2 - y1) * progress)
        for offset_y in range(-thickness, thickness + 1):
            for offset_x in range(-thickness, thickness + 1):
                _set_pixel(pixels, width, x + offset_x, y + offset_y, color)


def _write_face_sprites(directory: Path, frame_count: int, amplitudes: list[float], fps: int) -> tuple[Path, Path]:
    mouth_directory = directory / "mouth"
    eyes_directory = directory / "eyes"
    mouth_directory.mkdir()
    eyes_directory.mkdir()
    for frame_index in range(frame_count):
        timestamp = frame_index / fps
        amplitude = amplitudes[frame_index]
        mouth_width, mouth_height = 140, 70
        mouth_pixels = bytearray(mouth_width * mouth_height * 4)
        opening = max(0.0, min(1.0, amplitude))
        if opening > 0.18:
            _ellipse(mouth_pixels, mouth_width, mouth_height, 70, 34, 16 + 22 * opening, 2 + 12 * opening, (46, 12, 29, 110))
        if opening > 0.28:
            _ellipse(mouth_pixels, mouth_width, mouth_height, 70, 31 + 5 * opening, 8 + 13 * opening, 1.5 + 4 * opening, (244, 157, 164, 90))
        _write_rgba_png(mouth_directory / f"{frame_index:06d}.png", mouth_width, mouth_height, mouth_pixels)

        eye_width, eye_height = 190, 90
        eye_pixels = bytearray(eye_width * eye_height * 4)
        blink_phase = timestamp % 4.8
        blink = 0.0 if blink_phase < 0.14 else 1.0
        if blink < 0.5:
            _line(eye_pixels, eye_width, eye_height, 18, 45, 70, 45, 3, (50, 25, 31, 125))
            _line(eye_pixels, eye_width, eye_height, 120, 45, 172, 45, 3, (50, 25, 31, 125))
        _write_rgba_png(eyes_directory / f"{frame_index:06d}.png", eye_width, eye_height, eye_pixels)
    return mouth_directory / "%06d.png", eyes_directory / "%06d.png"


def _wav_path(audio_uri: str) -> Path:
    parsed = urlparse(audio_uri)
    if parsed.scheme != "file":
        raise ValueError(f"expected a local file URI, got {audio_uri!r}")
    return Path(parsed.path.lstrip("/"))


def _compose_audio(manifest: dict, output_path: Path) -> tuple[int, array]:
    first_path = _wav_path(manifest["segments"][0]["audio_uri"])
    with wave.open(str(first_path), "rb") as first_wav:
        params = first_wav.getparams()
        if params.nchannels != 1 or params.sampwidth != 2:
            raise ValueError("demo requires mono PCM-16 source WAVs")
        sample_rate = params.framerate
    combined = array("h")
    written_frames = 0
    for segment in manifest["segments"]:
        segment_path = _wav_path(segment["audio_uri"])
        with wave.open(str(segment_path), "rb") as segment_wav:
            if segment_wav.getframerate() != sample_rate or segment_wav.getnchannels() != 1 or segment_wav.getsampwidth() != 2:
                raise ValueError(f"inconsistent WAV format in {segment_path}")
            target_start = round(segment["start_ms"] * sample_rate / 1000)
            combined.extend([0] * max(0, target_start - written_frames))
            frames = segment_wav.readframes(segment_wav.getnframes())
            combined.frombytes(frames)
            written_frames = target_start + segment_wav.getnframes()
    target_end = round(manifest["duration_ms"] * sample_rate / 1000)
    combined.extend([0] * max(0, target_end - written_frames))
    with wave.open(str(output_path), "wb") as output_wav:
        output_wav.setnchannels(1)
        output_wav.setsampwidth(2)
        output_wav.setframerate(sample_rate)
        output_wav.writeframes(combined.tobytes())
    return sample_rate, combined


def _rms_envelope(samples: array, sample_rate: int, duration_ms: int, fps: int) -> list[float]:
    frame_count = math.ceil(duration_ms / 1000 * fps)
    envelope: list[float] = []
    half_window = max(1, round(sample_rate * 0.018))
    for frame_index in range(frame_count):
        center = round(frame_index / fps * sample_rate)
        window = samples[max(0, center - half_window) : min(len(samples), center + half_window)]
        if not window:
            envelope.append(0.0)
            continue
        rms = math.sqrt(sum(sample * sample for sample in window) / len(window)) / 32768
        envelope.append(max(0.0, min(1.0, (rms - 0.012) * 7.0)))
    return envelope


def _srt_time(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _write_srt(manifest: dict, path: Path) -> None:
    blocks = []
    for index, segment in enumerate(manifest["segments"], start=1):
        lines = "\n".join(textwrap.wrap(segment["text"], width=54, break_long_words=False))
        blocks.append(f"{index}\n{_srt_time(segment['start_ms'])} --> {_srt_time(segment['end_ms'])}\n{lines}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _run_ffmpeg(background: Path, character: Path, mouth_pattern: Path, eyes_pattern: Path, audio: Path, captions: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    title_end = min(duration, 3.8)
    outro_start = max(0.0, duration - 3.2)
    subtitle_path = captions.name.replace("'", r"\'")
    filter_graph = ";".join([
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg]",
        "[1:v]format=rgba,scale=w='trunc(900*(1+0.008*sin(2*PI*t/4))/2)*2':h=-1:eval=frame[character]",
        "[bg][character]overlay=x='(W-w)/2+6*sin(2*PI*t/5)':y='360+4*sin(2*PI*t/4)':eof_action=pass[stage]",
        "[stage][2:v]overlay=x='(W-w)/2-30+6*sin(2*PI*t/5)':y='648+4*sin(2*PI*t/4)':eof_action=pass[face]",
        "[face][3:v]overlay=x='(W-w)/2+6*sin(2*PI*t/5)':y='555+4*sin(2*PI*t/4)':eof_action=pass[face_animated]",
        f"[face_animated]drawbox=x=70:y=70:w=940:h=150:color=0x07142A@0.62:t=fill:enable='between(t,0,{title_end:.3f})',drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='A Última Luz':fontcolor=0xF7D27A:fontsize=54:x=(w-text_w)/2:y=108:enable='between(t,0,{title_end:.3f})',drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='FABULOOM STUDIO  ·  DORA':fontcolor=0xDCEBFF:fontsize=24:x=(w-text_w)/2:y=180:enable='between(t,0,{title_end:.3f})',subtitles='{subtitle_path}':force_style='FontName=Segoe UI,FontSize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=150',drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='FABULOOM  ·  TOPAZIOVERSE':fontcolor=0xF7D27A:fontsize=25:x=(w-text_w)/2:y=h-110:enable='between(t,{outro_start:.3f},{duration:.3f})'[v]",
    ])
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-loop", "1", "-i", str(background),
        "-loop", "1", "-i", str(character),
        "-framerate", str(FPS), "-i", str(mouth_pattern),
        "-framerate", str(FPS), "-i", str(eyes_pattern),
        "-i", str(audio),
        "-filter_complex", filter_graph,
        "-map", "[v]", "-map", "4:a",
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1",
        "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True, cwd=str(captions.parent))


def _probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=index,codec_name,codec_type,width,height,sample_rate,channels", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _write_manifest(path: Path, payload: str, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise TTSError("OUTPUT_EXISTS", "manifest already exists; pass --overwrite explicitly")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _generate_manifest(export_dir: Path, *, overwrite: bool) -> Path:
    manifest_path = export_dir / f"{STORY_ID}.json"
    provider = KokoroTTSProvider(output_dir=export_dir, allow_overwrite=overwrite)
    try:
        run = synthesize_narration(
            provider,
            STORY_TEXT,
            narration_id=STORY_ID,
            manifest_id=STORY_ID,
            voice_id=VOICE_ID,
            language=LANGUAGE,
            output_dir=export_dir,
            max_chars=360,
        )
        _write_manifest(manifest_path, serialize_manifest(run.manifest), overwrite=overwrite)
        print(f"tts_provider={provider.provider_id}")
        print(f"tts_model={provider.model_id}")
        print(f"tts_model_revision={provider.model_revision}")
        print(f"tts_model_load_count={provider.model_load_count}")
        print(f"tts_voice={VOICE_ID}")
        print(f"tts_duration_ms={run.manifest.duration_ms}")
        print(f"tts_segments={len(run.manifest.segments)}")
        return manifest_path
    finally:
        provider.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).resolve().parents[2] / "workspace" / "exports")
    parser.add_argument("--background", type=Path)
    parser.add_argument("--character", type=Path, default=Path(__file__).resolve().parents[1] / "frontend" / "assets" / "characters" / "topazio-narrators" / "dora.png")
    parser.add_argument("--reuse-manifest", action="store_true", help="reuse the already generated manifest for this exact demo text")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    export_dir = args.export_dir.resolve()
    video_dir = export_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    background = (args.background or video_dir / "fabuloom-first-video-background.png").resolve()
    if not background.is_file():
        raise FileNotFoundError(f"background not found: {background}")
    if not args.character.is_file():
        raise FileNotFoundError(f"character asset not found: {args.character}")

    manifest_path = export_dir / f"{STORY_ID}.json"
    if args.reuse_manifest and manifest_path.is_file():
        print(f"tts_manifest_reused={manifest_path}")
    else:
        manifest_path = _generate_manifest(export_dir, overwrite=args.overwrite)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_path = video_dir / f"{STORY_ID}.wav"
    captions_path = video_dir / f"{STORY_ID}.srt"
    output_path = video_dir / f"{STORY_ID}.mp4"
    sample_rate, samples = _compose_audio(manifest, audio_path)
    _write_srt(manifest, captions_path)

    with tempfile.TemporaryDirectory(prefix=".first-video-", dir=video_dir) as temporary_name:
        temporary_dir = Path(temporary_name)
        amplitudes = _rms_envelope(samples, sample_rate, manifest["duration_ms"], FPS)
        mouth_pattern, eyes_pattern = _write_face_sprites(temporary_dir, len(amplitudes), amplitudes, FPS)
        _run_ffmpeg(
            background,
            args.character.resolve(),
            mouth_pattern,
            eyes_pattern,
            audio_path,
            captions_path,
            output_path,
            manifest["duration_ms"],
            overwrite=args.overwrite,
        )
    probe = _probe(output_path)
    print(f"manifest={manifest_path}")
    print(f"audio={audio_path}")
    print(f"captions={captions_path}")
    print(f"video={output_path}")
    print(f"video_size_bytes={output_path.stat().st_size}")
    print(f"video_probe={json.dumps(probe, ensure_ascii=False, sort_keys=True)}")
    print("timing_source=measured_wav_segments")
    print("mouth_source=audio_rms_envelope")
    print("word_phoneme_viseme_timing=unavailable")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
