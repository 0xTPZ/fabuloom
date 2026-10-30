"""Capture and encode the deterministic Santa V5 POINT_AT demo."""

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


FPS = 30
WIDTH = 1080
HEIGHT = 1920
DURATION_MS = 8500


def edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-santa-v5-point-at.html", timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError("local POINT_AT capture server did not start")


def capture_frames(studio_root: Path, capture_dir: Path, port: int, timeout: float) -> dict:
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(capture_dir.parent)
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None; profile_dir = None
    try:
        wait_for_server(port)
        profile_dir = Path(tempfile.mkdtemp(prefix=".santa-v5-point-edge-", dir=capture_dir.parent))
        url = f"http://127.0.0.1:{port}/capture-santa-v5-point-at.html?session={quote(capture_dir.name)}&fps={FPS}"
        browser = subprocess.Popen([str(edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile_dir}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        completion = capture_dir / "complete.json"; deadline = time.monotonic() + timeout
        while not completion.is_file():
            if time.monotonic() >= deadline:
                error = capture_dir / "error.json"; detail = error.read_text(encoding="utf-8") if error.is_file() else "no browser error record"; raise TimeoutError(f"capture timed out: {detail}")
            if browser.poll() is not None:
                error = capture_dir / "error.json"; detail = error.read_text(encoding="utf-8") if error.is_file() else "no browser error record"; raise RuntimeError(f"Edge exited before completion: {detail}")
            time.sleep(0.25)
        result = json.loads(completion.read_text(encoding="utf-8")); frames = sorted(path for path in capture_dir.glob("*.png") if path.stem.isdigit())
        indexes = [int(path.stem) for path in frames]
        if indexes != list(range(int(result["frame_count"]))): raise ValueError("capture frame sequence is not contiguous")
        if int(result["duration_ms"]) != DURATION_MS: raise ValueError("capture duration is not 8.5 seconds")
        return result
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try: browser.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(browser.pid), "/T", "/F"], check=False, capture_output=True)
        if profile_dir is not None: shutil.rmtree(profile_dir, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


def render_video(frames: Path, output: Path, overwrite: bool) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-t", f"{DURATION_MS / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).resolve().parents[2] / "workspace" / "exports")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8783)
    parser.add_argument("--capture-timeout", type=float, default=240)
    args = parser.parse_args()
    studio_root = Path(__file__).resolve().parents[1]; export_dir = args.export_dir.resolve(); video_dir = export_dir / "videos"; video_dir.mkdir(parents=True, exist_ok=True)
    frames = video_dir / ".fabuloom-santa-v5-point-at-frames"; output = video_dir / "fabuloom-santa-v5-point-at.mp4"; report = video_dir / "fabuloom-santa-v5-point-at-report.md"
    if (frames.exists() or output.exists()) and not args.overwrite: raise FileExistsError("POINT_AT artifacts already exist; pass --overwrite explicitly")
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir(parents=True)
    started = time.perf_counter(); result = capture_frames(studio_root, frames, args.port, args.capture_timeout); processing_seconds = time.perf_counter() - started
    render_video(frames, output, args.overwrite); metadata = probe(output); video_stream = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    report.write_text("\n".join([
        "# Santa V5 — relatório POINT_AT", "", "- Objetivo: demonstrar o mesmo `SantaV5Rig` + `LayeredCharacterRenderer` apontando para dois alvos de apresentação.", "- Alvos: Livro à direita e Símbolo à esquerda; a mão para antes do objeto e o indicador mantém a direção visual.", f"- Frames: `{frames}` ({result['frame_count']} frames, {FPS} fps)", f"- Tempo de captura: `{processing_seconds:.2f} s`", f"- MP4: `{output}`", f"- FFprobe: `{metadata['format']['duration']} s`, `{video_stream['width']}x{video_stream['height']}`, vídeo `{video_stream['codec_name']}`, `{output.stat().st_size} bytes`", "- Fases: repouso, atenção, antecipação, elevação, sustentação, retorno e troca de alvo.", "- Determinismo: cada frame usa tempo absoluto do clipe e o alvo é resolvido pelo contrato `fabuloom.presentation-target/0.1`.", "- Segurança: alvos fora do alcance são aproximados pelo limite do IK; o gesto não força articulações impossíveis.", "- Limitação: os dois braços possuem calibração explícita, mas o rig ainda usa camadas rígidas 2.5D; não há deformação de malha, física ou espelhamento geométrico automático.", "", ]), encoding="utf-8")
    print(f"frames={frames}"); print(f"video={output}"); print(f"report={report}"); print(f"processing_seconds={processing_seconds:.2f}"); print(json.dumps(metadata, ensure_ascii=False, sort_keys=True)); print("state=completed")
    return 0


if __name__ == "__main__": raise SystemExit(main())
