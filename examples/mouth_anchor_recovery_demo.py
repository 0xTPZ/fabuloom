"""Render Mission 023.4.3 mouth-anchor recovery from existing local audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import time
from time import monotonic, sleep
from urllib.parse import quote
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ROOT = EXPORT_ROOT / "videos" / "official-narrators-v1"
OUTPUT_ROOT = EXPORT_ROOT / "videos" / "mouth-anchor-recovery-v1"
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
from facial_system_recovery_demo import _capture, _facial_closeups, _frame_board, _probe_export, _render_mp4, _comparison

NARRATORS = {
    "dora": ("pf_dora", "Dora mouth anchor V1"),
    "alex": ("pm_alex", "Alex mouth anchor V1"),
    "santa": ("pm_santa", "Santa V5 reference"),
}


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _stack(paths: list[Path], output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n"]
    args.extend(item for path in paths for item in ("-i", str(path)))
    filters = [f"[{index}:v]scale=760:-1[v{index}]" for index in range(len(paths))]
    filters.append("".join(f"[v{index}]" for index in range(len(paths))) + f"vstack=inputs={len(paths)}[out]")
    _run_ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _trio(videos: list[Path], audio: Path, output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n", *[item for path in videos for item in ("-i", str(path))], "-i", str(audio)]
    filters = [f"[{index}:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1[v{index}]" for index in range(3)]
    filters.append("[v0][v1][v2]vstack=inputs=3[outv]")
    _run_ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "3:a:0", "-shortest", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(output)], output.parent)


def _capture_calibration_board(output_root: Path, port: int, timeout: float, overwrite: bool) -> tuple[Path, dict]:
    session = output_root / ".mouth-anchor-calibration-capture"
    target = output_root / "mouth-anchor-calibration-board.png"
    if session.exists():
        if not overwrite:
            raise FileExistsError(f"capture exists: {session}; pass --overwrite")
        shutil.rmtree(session)
    if target.exists() and not overwrite:
        raise FileExistsError(f"board exists: {target}; pass --overwrite")
    session.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["FABULOOM_CAPTURE_DIR"] = str(output_root)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None
    profile = None
    try:
        deadline = monotonic() + 20
        while monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/mouth-anchor-calibration-lab.html", timeout=1):
                    break
            except Exception:
                sleep(0.2)
        else:
            raise TimeoutError("mouth anchor calibration server did not start")
        profile = Path(tempfile.mkdtemp(prefix=".mouth-anchor-edge-", dir=output_root))
        url = f"http://127.0.0.1:{port}/mouth-anchor-calibration-lab.html?session={quote(session.name)}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", "--window-size=1900,1250", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session / "complete.json"
        deadline = monotonic() + timeout
        while not complete.is_file():
            if monotonic() >= deadline:
                raise TimeoutError("mouth anchor calibration capture timed out")
            if edge.poll() is not None:
                error = session / "error.json"
                raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before calibration completion")
            sleep(0.2)
        payload = json.loads(complete.read_text(encoding="utf-8"))
        shutil.copy2(session / "board.png", target)
        payload.update({"board": str(target), "human_review_required": True})
        report = output_root / "mouth-anchor-calibration-board-report.json"
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target, payload
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8820)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()
    export_root = args.export_dir.resolve()
    source_root = export_root / "videos" / "official-narrators-v1"
    output_root = export_root / "videos" / "mouth-anchor-recovery-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: list[dict] = []
    videos: list[Path] = []

    for character_id, (voice_id, name) in NARRATORS.items():
        source_id = f"fabuloom-official-narrator-{character_id}-v1"
        manifest_path = export_root / f"{source_id}.json"
        audio_path = source_root / f"{source_id}.wav"
        video_path = output_root / f"fabuloom-{character_id}-mouth-anchor-v1.mp4"
        board_path = output_root / f"{character_id}-mouth-anchor-v1-frames.png"
        closeup_path = output_root / f"{character_id}-mouth-anchor-v1-facial-closeups.png"
        frames_path = output_root / f".fabuloom-{character_id}-mouth-anchor-v1-frames"
        for path in (manifest_path, audio_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        if frames_path.exists():
            if not args.overwrite:
                raise FileExistsError(f"frames exist: {frames_path}; pass --overwrite")
            shutil.rmtree(frames_path)
        frames_path.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capture = _capture(STUDIO_ROOT, frames_path, manifest_path, args.port, args.capture_timeout, character_id=character_id)
        _render_mp4(frames_path, audio_path, video_path, int(manifest["duration_ms"]), args.overwrite)
        _frame_board(frames_path, board_path, int(manifest["duration_ms"]))
        _facial_closeups(frames_path, closeup_path, args.overwrite)
        videos.append(video_path)
        results.append({"character_id": character_id, "name": name, "voice_id": voice_id, "language": "pt-BR", "manifest": str(manifest_path), "audio_reused": str(audio_path), "video": str(video_path), "frame_board": str(board_path), "facial_closeups": str(closeup_path), "duration_ms": manifest["duration_ms"], "frame_count": capture["frame_count"], "probe": _probe_export(video_path)})

    comparisons: dict[str, str] = {}
    for character_id in ("dora", "alex"):
        old = output_root.parent / "facial-mouth-polish-v1" / f"{character_id}-mouth-polish-v1-facial-closeups.png"
        new = output_root / f"{character_id}-mouth-anchor-v1-facial-closeups.png"
        target = output_root / f"{character_id}-mouth-anchor-before-after.png"
        if old.is_file() and new.is_file():
            _comparison(old, new, target, args.overwrite)
            comparisons[character_id] = str(target)
    before_after = output_root / "mouth-anchor-before-after-board.png"
    if len(comparisons) == 2:
        _stack([Path(comparisons["dora"]), Path(comparisons["alex"])], before_after, args.overwrite)

    trio_path = output_root / "fabuloom-narrators-mouth-anchor-trio-v1.mp4"
    _trio(videos, source_root / "fabuloom-official-narrator-dora-v1.wav", trio_path, args.overwrite)
    calibration_board, calibration_payload = _capture_calibration_board(output_root, args.port + 1, args.capture_timeout, args.overwrite)
    report_path = output_root / "mouth-anchor-recovery-v1-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.mouth-anchor-recovery-report/0.1",
        "mission": "023.4.3",
        "diagnosis": {
            "evidence": "real frames extracted from Mission 023.4.2 Dora, Alex, Santa and trio MP4s",
            "previous_behavior": "Dora and Alex shared the geometric mouth position [0.5, 0.5] and centered their mouth layer by the transparent canvas rather than identity-specific facial landmarks",
            "observed": ["mouth center sat too close to the nose in the reduced avatar", "closed/open states remained centered but inherited the same incorrect facial anchor", "Santa V5 reference remained visually stable"],
            "global_renderer_changed": False,
            "crop_changed": False,
            "santa_changed": False,
        },
        "calibration": {
            "contract": "fabuloom.narrator-mouth-anchor/0.1",
            "source_size": [1254, 1254],
            "previous": {"dora": {"mouth_anchor": [0.5, 0.5], "mouth_position": [0.5, 0.5], "mouth_offset": [0, 0], "mouth_scale": [1, 1]}, "alex": {"mouth_anchor": [0.5, 0.5], "mouth_position": [0.5, 0.5], "mouth_offset": [0, 0], "mouth_scale": [1, 1]}},
            "corrected": {"dora": {"mouth_anchor": [0.5, 0.5], "mouth_position": [0.5, 0.5], "mouth_offset": [0, 0.04], "effective_position": [0.5, 0.54], "mouth_scale": [1, 1]}, "alex": {"mouth_anchor": [0.5, 0.5], "mouth_position": [0.5, 0.5], "mouth_offset": [0, 0.036], "effective_position": [0.5, 0.536], "mouth_scale": [1, 1]}},
            "landmarks_local": {"dora": {"head_center": [627, 627], "nose_center": [627, 565], "mouth_center": [627, 665], "mouth_left": [552, 665], "mouth_right": [702, 665], "chin_upper_limit": [627, 775]}, "alex": {"head_center": [627, 627], "nose_center": [627, 580], "mouth_center": [627, 666], "mouth_left": [548, 666], "mouth_right": [706, 666], "chin_upper_limit": [627, 810]}},
            "resolved_landmark_projection_at_neutral": {"canvas": [1920, 1080], "avatar_bounds": [74, 676, 330], "dora": {"previous_canvas_px": [239, 888.522], "corrected_canvas_px": [239, 904.953], "delta_px": [0, 16.431]}, "alex": {"previous_canvas_px": [239, 888.837], "corrected_canvas_px": [239, 903.624], "delta_px": [0, 14.787]}},
            "state_selection": "unchanged PCM16 RMS thresholds; no phoneme or viseme timing added",
        },
        "results": results,
        "trio_video": str(trio_path),
        "comparisons": comparisons,
        "before_after_board": str(before_after),
        "calibration_board": str(calibration_board),
        "calibration_board_report": calibration_payload,
        "real_frame_evidence": str(output_root / "reference-frames"),
        "art_gate": "AWAITING_ART_APPROVAL",
        "processing_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}")
    for result in results:
        print(f"{result['character_id']}: video={result['video']} duration_ms={result['duration_ms']} frames={result['frame_count']}")
    print(f"trio={trio_path}")
    print(f"calibration_board={calibration_board}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
