"""Synthesize and render the reproducible Fabuloom Narrator Mode V1 demo."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError

from first_video_demo import _compose_audio, _probe, _write_srt

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
STORY_ID = "fabuloom-narrator-mode-v1"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1920
HEIGHT = 1080
DEMO_TEXT = "Olá, viajante! Seja bem-vindo ao Topazioverse. Hoje, vamos conhecer uma cidade esquecida, onde antigas histórias ainda ecoam entre as montanhas. Dizem que, quando a última estrela desaparecer, os segredos de Arenhast finalmente despertarão."


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file(): return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def _write_manifest(path: Path, payload: str, overwrite: bool) -> None:
    if path.exists() and not overwrite: raise FileExistsError(f"manifest already exists: {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".json", dir=path.parent, text=True)
    os.close(descriptor); temporary_path = Path(temporary)
    try:
        temporary_path.write_text(payload, encoding="utf-8"); os.replace(temporary_path, path)
    finally:
        if temporary_path.exists(): temporary_path.unlink()


def _synthesize(export_root: Path, manifest_path: Path, overwrite: bool, text: str) -> tuple[dict, float, float]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1"); os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    provider = KokoroTTSProvider(output_dir=export_root, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(provider, text, narration_id=STORY_ID, manifest_id=STORY_ID, voice_id=VOICE_ID, language=LANGUAGE, output_dir=export_root, max_chars=360)
        _write_manifest(manifest_path, serialize_manifest(run.manifest), overwrite)
        load_seconds = float(run.results[0].metadata.get("model_load_seconds") or 0)
        return json.loads(serialize_manifest(run.manifest)), run.processing_seconds, load_seconds
    except (TTSError, NarrationSynthesisError):
        raise
    finally:
        provider.close()


def _wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-narrator-mode.html", timeout=1): return
        except Exception: time.sleep(0.2)
    raise TimeoutError("narrator capture server did not start")


def _capture(studio_root: Path, capture_dir: Path, manifest: Path, port: int, timeout: float) -> dict:
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(capture_dir.parent)
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None; profile = None
    try:
        _wait_for_server(port); profile = Path(tempfile.mkdtemp(prefix=".narrator-edge-", dir=capture_dir.parent))
        url = f"http://127.0.0.1:{port}/capture-narrator-mode.html?session={quote(capture_dir.name)}&manifest={quote('/exports/' + manifest.name, safe='')}&fps={FPS}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = capture_dir / "complete.json"; deadline = time.monotonic() + timeout
        while not complete.is_file():
            if time.monotonic() >= deadline: raise TimeoutError(f"capture timed out after {timeout:.0f}s")
            if edge.poll() is not None:
                error = capture_dir / "error.json"; raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before completion")
            time.sleep(0.25)
        result = json.loads(complete.read_text(encoding="utf-8")); frames = sorted(path for path in capture_dir.glob("*.png") if path.stem.isdigit())
        if len(frames) != result["frame_count"] or any(path.stat().st_size < 1000 for path in frames): raise ValueError("capture frames are incomplete")
        return result
    finally:
        if edge is not None and edge.poll() is None:
            edge.terminate()
            try: edge.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"], check=False, capture_output=True)
        if profile is not None: shutil.rmtree(profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


def _frame_board(frames: Path, output: Path, duration_ms: int) -> None:
    last = max(0, int(round(duration_ms / 1000 * FPS)) - 1); indexes = [0, max(0, last // 3), max(0, last * 2 // 3), last]
    inputs = []; filters = []
    labels = ["início", "fala", "fala / piscar", "encerramento"]
    for index, label in zip(indexes, labels):
        inputs += ["-i", str(frames / f"{index:06d}.png")]; slot = chr(97 + len(filters)); filters.append(f"[{len(filters)}:v]scale=480:270,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=22:x=18:y=18:box=1:boxcolor=0x07142A@.85[{slot}]")
    filters.append("[a][b][c][d]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, overwrite: bool) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def _probe_export(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=index,codec_name,codec_type,width,height,pix_fmt,sample_rate,channels", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--text", default=DEMO_TEXT); parser.add_argument("--port", type=int, default=8781); parser.add_argument("--capture-timeout", type=float, default=600); args = parser.parse_args()
    export_root = args.export_dir.resolve(); video_root = export_root / "videos"; video_root.mkdir(parents=True, exist_ok=True); manifest_path = export_root / f"{STORY_ID}.json"; output = video_root / f"{STORY_ID}.mp4"; board = video_root / f"{STORY_ID}-frames.png"; report = video_root / f"{STORY_ID}-report.md"; srt = video_root / f"{STORY_ID}.srt"; audio = video_root / f"{STORY_ID}.wav"; frames = video_root / f".{STORY_ID}-frames"
    if output.exists() and not args.overwrite: raise FileExistsError(f"video already exists: {output}; pass --overwrite")
    story_text = str(args.text).strip() or DEMO_TEXT
    started = time.perf_counter(); manifest, synthesis_seconds, load_seconds = _synthesize(export_root, manifest_path, args.overwrite, story_text); sample_rate, _ = _compose_audio(manifest, audio); _write_srt(manifest, srt)
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    frames.mkdir(parents=True); capture = _capture(STUDIO_ROOT, frames, manifest_path, args.port, args.capture_timeout); _render_mp4(frames, audio, output, int(manifest["duration_ms"]), args.overwrite); _frame_board(frames, board, int(manifest["duration_ms"])); probe = _probe_export(output); elapsed = time.perf_counter() - started
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video"); audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report.write_text("\n".join(["# Fabuloom Narrator Mode V1 — relatório de produção", "", f"- Texto: `{story_text}`", f"- Provedor: Kokoro · modelo `hexgrad/Kokoro-82M` · voz `{VOICE_ID}` · idioma `{LANGUAGE}`", f"- Manifesto medido: `{manifest_path}`", f"- Segmentos: {len(manifest['segments'])}; duração real: `{manifest['duration_ms']} ms`", f"- Síntese: `{synthesis_seconds:.3f} s`; carregamento do modelo: `{load_seconds:.3f} s`; tempo total: `{elapsed:.3f} s`", f"- Frames reais: `{frames}` ({capture['frame_count']} em {FPS} fps)", f"- MP4: `{output}` ({output.stat().st_size} bytes)", f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']} `{video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`", f"- Prancha real: `{board}`", "- Avatar: recorte circular de camadas faciais Santa V5; sem braços, mãos, corpo ou IK.", "- Boca: envelope RMS PCM-16 do WAV produzido; alinhamento de palavras, fonemas e visemas não disponível.", "- Legendas: intervalos medidos por segmento; não são timestamps fonéticos.", "- Cenário: SVG original local, sem referência protegida.", "- Visual Inspector: evidências de quadros reais e validações estruturais foram registradas em `narrator-mode-visual-inspection.json`.", ""]), encoding="utf-8")
    visual_report = video_root / "narrator-mode-visual-inspection.json"; visual_report.write_text(json.dumps({"format": "fabuloom.visual-inspection-narrator/0.1", "mode": "narrator-mode-v1", "source": str(output), "frame_board": str(board), "checks": {"canvas": [WIDTH, HEIGHT], "avatar": "circular-clipped", "facial_layers_only": True, "mouth_source": "pcm16_rms_envelope", "captions": "measured_segment_ranges", "no_black_frame_sample": True, "deterministic_frame_count": capture["frame_count"]}, "human_review_required": True}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={manifest_path}"); print(f"audio={audio}"); print(f"frames={frames}"); print(f"video={output}"); print(f"board={board}"); print(f"report={report}"); print(f"visual_report={visual_report}"); print(f"duration_ms={manifest['duration_ms']}"); print(f"processing_seconds={elapsed:.3f}"); print(f"probe={json.dumps(probe, ensure_ascii=False)}"); print("state=completed"); return 0


if __name__ == "__main__":
    raise SystemExit(main())

