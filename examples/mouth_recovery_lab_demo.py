"""Capture the isolated, deterministic mouth-state prototype."""

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
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
FPS = 30
STATES = ["closed", "slight", "moderate", "open", "smile"]


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def _capture(output: Path, port: int, timeout: float, overwrite: bool) -> dict:
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"capture already exists: {output}; pass --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["FABULOOM_CAPTURE_DIR"] = str(output.parent)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None
    profile = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/mouth-recovery-lab.html", timeout=1):
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise TimeoutError("mouth recovery lab server did not start")
        profile = Path(tempfile.mkdtemp(prefix=".mouth-lab-edge-", dir=output.parent))
        url = f"http://127.0.0.1:{port}/mouth-recovery-lab.html?session={output.name}&capture=1"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", "--window-size=900,900", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = output / "complete.json"
        deadline = time.monotonic() + timeout
        while not complete.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"capture timed out after {timeout:.0f}s")
            if edge.poll() is not None:
                error = output / "error.json"
                raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before completion")
            time.sleep(0.15)
        result = json.loads(complete.read_text(encoding="utf-8"))
        frames = sorted(path for path in output.glob("*.png") if path.stem.isdigit())
        if len(frames) != result["frame_count"] or any(path.stat().st_size < 1000 for path in frames):
            raise ValueError("prototype capture frames are incomplete")
        return result
    finally:
        if edge is not None and edge.poll() is None:
            edge.terminate()
            try:
                edge.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"], check=False, capture_output=True)
        if profile is not None:
            shutil.rmtree(profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


def _board(frames: Path, output: Path, overwrite: bool) -> None:
    inputs: list[str] = []
    filters: list[str] = []
    for index, state in enumerate(STATES):
        inputs.extend(["-i", str(frames / f"{index * 12:06d}.png")])
        filters.append(f"[{index}:v]scale=320:360,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{state}':fontcolor=white:fontsize=22:x=16:y=16:box=1:boxcolor=0x07142A@.85[n{index}]")
    filters.append("[n0][n1][n2][n3][n4]hstack=inputs=5[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _video(frames: Path, output: Path, overwrite: bool) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8798)
    parser.add_argument("--capture-timeout", type=float, default=120)
    args = parser.parse_args()
    root = args.export_dir.resolve() / "videos" / "facial-system-recovery-v1"
    root.mkdir(parents=True, exist_ok=True)
    frames = root / ".mouth-recovery-prototype-frames"
    board = root / "mouth-recovery-prototype-states.png"
    video = root / "mouth-recovery-prototype.mp4"
    report = root / "mouth-recovery-prototype-report.json"
    result = _capture(frames, args.port, args.capture_timeout, args.overwrite)
    _board(frames, board, args.overwrite)
    _video(frames, video, args.overwrite)
    report.write_text(json.dumps({
        "format": "fabuloom.mouth-recovery-prototype-report/0.1",
        "states": STATES,
        "renderer": "LayeredCharacterRenderer",
        "capture": result,
        "board": str(board),
        "video": str(video),
        "strategy": "neutral-cartoon-head-with-explicit-state-plates",
        "human_review_required": True,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"board={board}")
    print(f"video={video}")
    print(f"report={report}")
    print(f"frame_count={result['frame_count']}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
