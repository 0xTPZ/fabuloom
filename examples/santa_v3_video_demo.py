"""Render the Santa V3 continuous-shot demonstration through the real engine."""

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


STORY_ID = "fabuloom-santa-v3"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
STORY_TEXT = """Seja bem-vindo ao Topazioverse.

Sabe, meu jovem, toda grande história começa com uma pequena ideia.

Às vezes, tudo o que precisamos é de um bom livro e uma xícara de café.

Mas hoje, quero mostrar algo especial.

Aqui, nossas histórias não são apenas contadas.

Elas ganham vida."""


def _write_manifest(path: Path, payload: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"manifest already exists: {path}; pass --overwrite explicitly")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _generate_manifest(export_dir: Path, overwrite: bool) -> Path:
    path = export_dir / f"{STORY_ID}.json"
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
            max_chars=180,
        )
        _write_manifest(path, serialize_manifest(run.manifest), overwrite)
        print(f"tts_provider={provider.provider_id}")
        print(f"tts_model={provider.model_id}")
        print(f"tts_model_revision={provider.model_revision}")
        print(f"tts_voice={VOICE_ID}")
        print(f"tts_duration_ms={run.manifest.duration_ms}")
        print(f"tts_segments={len(run.manifest.segments)}")
        print(f"tts_processing_seconds={run.processing_seconds:.3f}")
        return path
    finally:
        provider.close()


def _validate_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = "\n\n".join(segment.get("text", "").strip() for segment in payload.get("segments", []))
    if text != STORY_TEXT:
        raise ValueError("existing manifest text does not match the Santa V3 demonstration")
    voices = {segment.get("voice_id") for segment in payload.get("segments", [])}
    if voices != {VOICE_ID}:
        raise ValueError(f"existing manifest voices do not match {VOICE_ID}: {sorted(voices)}")
    return payload


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def _wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-santa-v3.html", timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"local capture server did not start on port {port}")


def _capture_frames(studio_root: Path, capture_dir: Path, manifest_path: Path, duration_ms: int, port: int, timeout: float) -> dict:
    env = os.environ.copy()
    env["FABULOOM_CAPTURE_DIR"] = str(capture_dir.parent)
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge_process = None
    profile_dir = None
    try:
        _wait_for_server(port)
        profile_dir = Path(tempfile.mkdtemp(prefix=".santa-v3-edge-", dir=capture_dir.parent))
        url = f"http://127.0.0.1:{port}/capture-santa-v3.html?session={quote(capture_dir.name)}&manifest={quote('/exports/' + manifest_path.name, safe='')}&fps={FPS}"
        edge_process = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile_dir}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        completion = capture_dir / "complete.json"
        deadline = time.monotonic() + timeout
        while not completion.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Santa V3 capture timed out after {timeout:.0f}s")
            if edge_process.poll() is not None:
                error = capture_dir / "error.json"
                detail = error.read_text(encoding="utf-8") if error.is_file() else "no browser error record"
                raise RuntimeError(f"Edge exited before completion: {detail}")
            time.sleep(0.25)
        result = json.loads(completion.read_text(encoding="utf-8"))
        frames = sorted(path for path in capture_dir.glob("*.png") if path.stem.isdigit())
        indexes = [int(path.stem) for path in frames]
        expected = int(result["frame_count"])
        if indexes != list(range(expected)):
            raise ValueError(f"frame sequence is not contiguous: expected {expected}, got {len(indexes)}")
        if any(path.stat().st_size < 1000 for path in frames):
            raise ValueError("capture contains an unexpectedly small PNG")
        if int(result["duration_ms"]) != duration_ms:
            raise ValueError("capture duration differs from measured manifest duration")
        return result
    finally:
        if edge_process is not None and edge_process.poll() is None:
            edge_process.terminate()
            try:
                edge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(edge_process.pid), "/T", "/F"], check=False, capture_output=True)
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


def _caption_files(manifest: dict, directory: Path) -> list[Path]:
    paths = []
    for index, segment in enumerate(manifest["segments"]):
        path = directory / f".santa-v3-caption-{index:04d}.txt"
        path.write_text("\n".join(textwrap.wrap(segment["text"], width=34, break_long_words=False)), encoding="utf-8")
        paths.append(path)
    return paths


def _render_mp4(manifest: dict, frames: Path, audio: Path, caption_files: list[Path], output: Path, overwrite: bool) -> None:
    duration = int(manifest["duration_ms"]) / 1000
    parts = ["[0:v]setsar=1[stage]"]
    previous = "stage"
    for index, (segment, caption_file) in enumerate(zip(manifest["segments"], caption_files)):
        label = f"caption{index}"
        start = segment["start_ms"] / 1000
        end = segment["end_ms"] / 1000
        parts.append(f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{caption_file.name}':fontcolor=0xFFFFFF:fontsize=38:line_spacing=8:box=1:boxcolor=0x07142A@0.80:boxborderw=18:x=(w-text_w)/2:y=300:enable='between(t,{start:.3f},{end:.3f})'[{label}]")
        previous = label
    parts.append(f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='FABULOOM  ·  SANTA V3':fontcolor=0xF7D27A:fontsize=26:x=(w-text_w)/2:y=h-84:enable='gte(t,{max(0, duration - 2.8):.3f})'[v]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio), "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "1:a", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def _comparison(video: Path, output: Path, duration_ms: int) -> None:
    last = max(1, round(duration_ms / 1000 * FPS) - 1)
    middle = max(1, last // 2)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vf", f"select='eq(n,0)+eq(n,{middle})+eq(n,{last})',scale=360:-1,tile=3x1:padding=8:margin=8", "-frames:v", "1", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).resolve().parents[2] / "workspace" / "exports")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8773)
    parser.add_argument("--capture-timeout", type=float, default=360)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    studio_root = Path(__file__).resolve().parents[1]
    export_dir = args.export_dir.resolve(); video_dir = export_dir / "videos"; video_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = export_dir / f"{STORY_ID}.json"
    if args.reuse_manifest:
        if not manifest_path.is_file(): raise FileNotFoundError(f"manifest not found: {manifest_path}")
        manifest = _validate_manifest(manifest_path)
    else:
        manifest_path = _generate_manifest(export_dir, args.overwrite); manifest = _validate_manifest(manifest_path)
    audio_path = video_dir / f"{STORY_ID}.wav"; srt_path = video_dir / f"{STORY_ID}.srt"; output = video_dir / f"{STORY_ID}.mp4"; comparison = video_dir / f"{STORY_ID}-frames-comparison.png"
    if output.exists() and not args.overwrite: raise FileExistsError(f"video already exists: {output}; pass --overwrite explicitly")
    sample_rate, _ = _compose_audio(manifest, audio_path); _write_srt(manifest, srt_path); caption_files = _caption_files(manifest, video_dir)
    frames = video_dir / f".{STORY_ID}-frames"
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"capture directory already exists: {frames}; pass --overwrite explicitly")
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    capture = _capture_frames(studio_root, frames, manifest_path, int(manifest["duration_ms"]), args.port, args.capture_timeout)
    _render_mp4(manifest, frames, audio_path, caption_files, output, args.overwrite); _comparison(output, comparison, int(manifest["duration_ms"]))
    probe = _probe(output); video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video"); audio_stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    report = video_dir / f"{STORY_ID}-report.md"
    report.write_text("\n".join([
        "# Fabuloom Santa V3 — relatório de demonstração", "", f"- Personagem: Santa V3 (`{VOICE_ID}`), português brasileiro.", f"- Texto: `{STORY_TEXT}`", f"- Manifesto: `{manifest_path}`", f"- Frames: `{frames}` ({capture['frame_count']} frames at {FPS} fps)", f"- Áudio medido: `{manifest['duration_ms']} ms` at `{sample_rate} Hz`", f"- MP4: `{output}`", f"- FFprobe: `{probe['format']['duration']} s`, `{video_stream['width']}x{video_stream['height']}`, vídeo `{video_stream['codec_name']}`, áudio `{audio_stream['codec_name']}`, `{output.stat().st_size} bytes`", f"- Comparativo: `{comparison}`", "- Animação: LayeredCharacterRig + LayeredCharacterRenderer + SantaV3SceneRenderer; não há segunda implementação de movimento no FFmpeg.", "- Boca: envelope RMS do WAV medido; alinhamento fonético/visemas não disponível e não inventado.", "- Sequência: caminhada, sentar, alcançar, beber, devolver a xícara, ler e explicar em uma tomada contínua.", "" ]), encoding="utf-8")
    print(f"manifest={manifest_path}"); print(f"audio={audio_path}"); print(f"frames={frames}"); print(f"video={output}"); print(f"comparison={comparison}"); print(f"report={report}"); print(f"probe={json.dumps(probe, ensure_ascii=False, sort_keys=True)}"); print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
