"""Render a Santa V2 video through the real browser Character Engine capture path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.parse import quote
from urllib.request import urlopen

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest

from first_video_demo import _compose_audio, _probe, _write_srt


STORY_ID = "fabuloom-character-engine-santa"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 800
STORY_TEXT = (
    "Bem-vindo ao Topazioverse! Aqui, cada história ganha vida. "
    "E hoje, vou mostrar como transformamos palavras em imagens, vozes e movimento."
)


def _write_manifest(path: Path, payload: str, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"manifest already exists: {path}; pass --overwrite explicitly")
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
            max_chars=260,
        )
        _write_manifest(manifest_path, serialize_manifest(run.manifest), overwrite=overwrite)
        print(f"tts_provider={provider.provider_id}")
        print(f"tts_model={provider.model_id}")
        print(f"tts_model_revision={provider.model_revision}")
        print(f"tts_model_load_count={provider.model_load_count}")
        print(f"tts_voice={VOICE_ID}")
        print(f"tts_duration_ms={run.manifest.duration_ms}")
        print(f"tts_segments={len(run.manifest.segments)}")
        print(f"tts_processing_seconds={run.processing_seconds:.3f}")
        return manifest_path
    finally:
        provider.close()


def _validate_reusable_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = payload.get("segments") or []
    text = " ".join(segment.get("text", "").strip() for segment in segments).strip()
    if text != STORY_TEXT:
        raise ValueError("existing manifest text does not match the requested Santa demonstration")
    voices = {segment.get("voice_id") for segment in segments}
    if voices != {VOICE_ID}:
        raise ValueError(f"existing manifest voices do not match {VOICE_ID}: {sorted(voices)}")
    if payload.get("metadata", {}).get("voice_id") not in {None, VOICE_ID}:
        raise ValueError("existing manifest metadata voice does not match the requested Santa voice")
    return payload


def _write_caption_text_files(manifest: dict, directory: Path) -> list[Path]:
    """Create short per-segment caption sources for deterministic drawtext."""
    paths = []
    for index, segment in enumerate(manifest["segments"]):
        path = directory / f".fabuloom-caption-{index:04d}.txt"
        wrapped = "\n".join(textwrap.wrap(segment["text"], width=34, break_long_words=False))
        path.write_text(wrapped, encoding="utf-8")
        paths.append(path)
    return paths


def _edge_path() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Microsoft Edge is required for local deterministic Canvas capture")


def _wait_for_server(port: int, timeout_seconds: float = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-character.html", timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"local capture server did not start on port {port}")


def _capture_frames(
    *,
    studio_root: Path,
    capture_dir: Path,
    manifest_path: Path,
    duration_ms: int,
    port: int,
    timeout_seconds: float,
) -> dict:
    server_env = os.environ.copy()
    # The loopback server appends the session component from the URL. Keep the
    # configured root at the video artifact directory and verify the exact
    # session directory below.
    server_env["FABULOOM_CAPTURE_DIR"] = str(capture_dir.parent)
    server_command = [sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)]
    server = subprocess.Popen(server_command, cwd=studio_root, env=server_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge_process = None
    profile_dir = None
    try:
        _wait_for_server(port)
        edge = _edge_path()
        manifest_url = f"/exports/{quote(manifest_path.name)}"
        capture_url = (
            f"http://127.0.0.1:{port}/capture-character.html?character=santa"
            f"&session={quote(capture_dir.name)}&manifest={quote(manifest_url, safe="")}&fps={FPS}"
            f"&canvasWidth={CAPTURE_WIDTH}&canvasHeight={CAPTURE_HEIGHT}"
        )
        profile_dir = Path(tempfile.mkdtemp(prefix=".character-engine-edge-", dir=capture_dir.parent))
        edge_process = subprocess.Popen(
            [
                str(edge),
                "--headless=new",
                "--disable-gpu",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile_dir}",
                f"--window-size={CAPTURE_WIDTH},{CAPTURE_HEIGHT}",
                capture_url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        completion = capture_dir / "complete.json"
        deadline = time.monotonic() + timeout_seconds
        while not completion.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"character capture timed out after {timeout_seconds:.0f}s")
            if edge_process.poll() is not None and not completion.is_file():
                # Edge may exit after a renderer error; leave the exact
                # session directory intact for post-mortem inspection.
                raise RuntimeError(f"Edge capture exited with code {edge_process.returncode} before completion")
            time.sleep(0.25)
        completion_payload = json.loads(completion.read_text(encoding="utf-8"))
        expected = int(completion_payload.get("frame_count", 0))
        frames = sorted(capture_dir.glob("*.png"))
        indexes = [int(frame.stem) for frame in frames if frame.stem.isdigit()]
        if indexes != list(range(expected)):
            raise ValueError(f"capture frame sequence is not contiguous: expected {expected}, got {len(indexes)}")
        if any(frame.stat().st_size < 100 for frame in frames):
            raise ValueError("capture produced an empty PNG frame")
        if completion_payload.get("duration_ms") != duration_ms:
            raise ValueError("capture duration differs from the measured manifest duration")
        return completion_payload
    finally:
        if edge_process is not None and edge_process.poll() is None:
            edge_process.terminate()
            try:
                edge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(edge_process.pid), "/T", "/F"], check=False, capture_output=True)
                edge_process.kill()
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


def _render_mp4(
    *,
    manifest: dict,
    capture_dir: Path,
    background: Path,
    audio: Path,
    captions: Path,
    caption_files: list[Path],
    output: Path,
    duration_ms: int,
    overwrite: bool,
) -> None:
    duration = duration_ms / 1000
    title_end = min(duration, 3.0)
    outro_start = max(0.0, duration - 2.8)
    filter_parts = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg]",
        f"[1:v]format=rgba,scale={CAPTURE_WIDTH}:{CAPTURE_HEIGHT}:force_original_aspect_ratio=decrease[character]",
        "[bg][character]overlay=x=40:y=1080:eof_action=pass[stage]",
        f"[stage]drawbox=x=64:y=72:w=952:h=128:color=0x07142A@0.68:t=fill:enable='between(t,0,{title_end:.3f})',drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='SANTA V2  ·  TOPAZIOVERSE':fontcolor=0xF7D27A:fontsize=42:x=(w-text_w)/2:y=108:enable='between(t,0,{title_end:.3f})'[titled]",
    ]
    previous = "titled"
    for index, (segment, caption_file) in enumerate(zip(manifest["segments"], caption_files)):
        label = f"caption{index}"
        start = segment["start_ms"] / 1000
        end = segment["end_ms"] / 1000
        filter_parts.append(
            f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{caption_file.name}':fontcolor=0xFFFFFF:fontsize=38:line_spacing=8:box=1:boxcolor=0x07142A@0.78:boxborderw=18:x=(w-text_w)/2:y=300:enable='between(t,{start:.3f},{end:.3f})'[{label}]"
        )
        previous = label
    filter_parts.append(
        f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='FABULOOM  ·  NARRAÇÃO {VOICE_ID.upper()}':fontcolor=0xF7D27A:fontsize=24:x=(w-text_w)/2:y=h-92:enable='between(t,{outro_start:.3f},{duration:.3f})'[v]"
    )
    filter_graph = ";".join(filter_parts)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-loop", "1", "-i", str(background),
        "-framerate", str(FPS), "-i", str(capture_dir / "%06d.png"),
        "-i", str(audio),
        "-filter_complex", filter_graph,
        "-map", "[v]", "-map", "2:a",
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1",
        "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).resolve().parents[2] / "workspace" / "exports")
    parser.add_argument("--background", type=Path)
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--capture-timeout", type=float, default=240)
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    studio_root = Path(__file__).resolve().parents[1]
    export_dir = args.export_dir.resolve()
    video_dir = export_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    background = (args.background or video_dir / "fabuloom-first-video-background.png").resolve()
    if not background.is_file():
        raise FileNotFoundError(f"background not found: {background}")
    manifest_path = export_dir / f"{STORY_ID}.json"
    if args.reuse_manifest:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"manifest not found for --reuse-manifest: {manifest_path}")
        manifest = _validate_reusable_manifest(manifest_path)
        print(f"tts_manifest_reused={manifest_path}")
    else:
        manifest_path = _generate_manifest(export_dir, overwrite=args.overwrite)
        manifest = _validate_reusable_manifest(manifest_path)
    audio_path = video_dir / f"{STORY_ID}.wav"
    captions_path = video_dir / f"{STORY_ID}.srt"
    output_path = video_dir / f"{STORY_ID}.mp4"
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"video already exists: {output_path}; pass --overwrite explicitly")
    sample_rate, _samples = _compose_audio(manifest, audio_path)
    _write_srt(manifest, captions_path)
    caption_files = _write_caption_text_files(manifest, video_dir)
    capture_dir = video_dir / f".{STORY_ID}-frames"
    if capture_dir.exists():
        if not args.overwrite:
            raise FileExistsError(f"capture directory already exists: {capture_dir}; pass --overwrite explicitly")
        shutil.rmtree(capture_dir)
    capture_dir.mkdir(parents=True)
    capture = _capture_frames(
        studio_root=studio_root,
        capture_dir=capture_dir,
        manifest_path=manifest_path,
        duration_ms=int(manifest["duration_ms"]),
        port=args.port,
        timeout_seconds=args.capture_timeout,
    )
    _render_mp4(
        manifest=manifest,
        capture_dir=capture_dir,
        background=background,
        audio=audio_path,
        captions=captions_path,
        caption_files=caption_files,
        output=output_path,
        duration_ms=int(manifest["duration_ms"]),
        overwrite=args.overwrite,
    )
    probe = _probe(output_path)
    report_path = video_dir / f"{STORY_ID}-report.md"
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report_path.write_text(
        "\n".join([
            "# Fabuloom Character Engine — Santa V2",
            "",
            f"- Texto: `{STORY_TEXT}`",
            f"- Personagem: Santa V2 (`{VOICE_ID}`)",
            f"- Manifesto: `{manifest_path}`",
            f"- Frames: `{capture_dir}` ({capture['frame_count']} frames at {capture['fps']} fps)",
            f"- Áudio medido: `{manifest['duration_ms']} ms` at `{sample_rate} Hz`",
            f"- Vídeo: `{output_path}`",
            f"- Duração FFprobe: `{probe['format']['duration']} s`",
            f"- Resolução: `{video_stream['width']}x{video_stream['height']}`",
            f"- Codecs: vídeo `{video_stream['codec_name']}`, áudio `{audio_stream['codec_name']}`",
            f"- Tamanho: `{output_path.stat().st_size} bytes`",
            "- Boca: envelope RMS PCM-16 medido do WAV; não é alinhamento fonético.",
            "- Palavras, fonemas e visemas: indisponíveis no provedor e não inventados.",
            "- Render: frames Canvas transparentes do LayeredCharacterRenderer real, compostos pelo FFmpeg.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"manifest={manifest_path}")
    print(f"audio={audio_path}")
    print(f"captions={captions_path}")
    print(f"capture={capture_dir}")
    print(f"video={output_path}")
    print(f"report={report_path}")
    print(f"video_size_bytes={output_path.stat().st_size}")
    print(f"video_probe={json.dumps(probe, ensure_ascii=False, sort_keys=True)}")
    print("character_engine=LayeredCharacterRig+LayeredCharacterRenderer")
    print("capture_mode=transparent_canvas_png_sequence")
    print("timing_source=measured_wav_segments")
    print("mouth_source=pcm16_rms_envelope")
    print("word_phoneme_viseme_timing=unavailable")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
