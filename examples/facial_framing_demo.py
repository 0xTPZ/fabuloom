"""Render Mission 023.4.1 framing videos from existing local audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

STUDIO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ROOT = EXPORT_ROOT / "videos" / "official-narrators-v1"
OUTPUT_ROOT = EXPORT_ROOT / "videos" / "facial-framing-v1"
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
from facial_system_recovery_demo import _capture, _facial_closeups, _frame_board, _probe_export, _render_mp4, _comparison

NARRATORS = {
    "dora": ("pf_dora", "Dora Cartoon V1"),
    "alex": ("pm_alex", "Alex Cartoon V1"),
    "santa": ("pm_santa", "Santa V5 reference"),
}


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _stack_images(paths: list[Path], output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n"]
    args.extend(item for path in paths for item in ("-i", str(path)))
    labels = [f"v{index}" for index in range(len(paths))]
    filters = [f"[{index}:v]scale=760:-1[{label}]" for index, label in enumerate(labels)]
    filters.append("".join(f"[{label}]" for label in labels) + f"vstack=inputs={len(labels)}[out]")
    _run_ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _trio_video(videos: list[Path], audio: Path, output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n", *[item for path in videos for item in ("-i", str(path))], "-i", str(audio)]
    filters = []
    for index in range(3):
        filters.append(f"[{index}:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1[v{index}]")
    filters.append("[v0][v1][v2]vstack=inputs=3[outv]")
    _run_ffmpeg([
        *args,
        "-filter_complex", ";".join(filters),
        "-map", "[outv]", "-map", "3:a:0", "-shortest",
        "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        str(output),
    ], output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8815)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()
    export_root = args.export_dir.resolve()
    source_root = export_root / "videos" / "official-narrators-v1"
    output_root = export_root / "videos" / "facial-framing-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: list[dict] = []
    videos: list[Path] = []
    for character_id, (voice_id, name) in NARRATORS.items():
        source_id = f"fabuloom-official-narrator-{character_id}-v1"
        manifest_path = export_root / f"{source_id}.json"
        audio_path = source_root / f"{source_id}.wav"
        video_path = output_root / f"fabuloom-{character_id}-framing-v1.mp4"
        board_path = output_root / f"{character_id}-framing-v1-frames.png"
        closeup_path = output_root / f"{character_id}-framing-v1-facial-closeups.png"
        frames_path = output_root / f".fabuloom-{character_id}-framing-v1-frames"
        for path in (manifest_path, audio_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        if frames_path.exists():
            if not args.overwrite:
                raise FileExistsError(f"frames exist: {frames_path}; pass --overwrite")
            import shutil
            shutil.rmtree(frames_path)
        frames_path.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capture = _capture(STUDIO_ROOT, frames_path, manifest_path, args.port, args.capture_timeout, character_id=character_id)
        _render_mp4(frames_path, audio_path, video_path, int(manifest["duration_ms"]), args.overwrite)
        _frame_board(frames_path, board_path, int(manifest["duration_ms"]))
        _facial_closeups(frames_path, closeup_path, args.overwrite)
        videos.append(video_path)
        results.append({
            "character_id": character_id,
            "name": name,
            "voice_id": voice_id,
            "language": "pt-BR",
            "manifest": str(manifest_path),
            "audio_reused": str(audio_path),
            "video": str(video_path),
            "frame_board": str(board_path),
            "facial_closeups": str(closeup_path),
            "duration_ms": manifest["duration_ms"],
            "frame_count": capture["frame_count"],
            "probe": _probe_export(video_path),
        })

    comparisons: dict[str, str] = {}
    for character_id in ("dora", "alex"):
        old = EXPORT_ROOT / "videos" / "facial-art-consistency-v1" / f"{character_id}-cartoon-v1-facial-closeups.png"
        new = output_root / f"{character_id}-framing-v1-facial-closeups.png"
        target = output_root / f"{character_id}-before-after-framing.png"
        if old.is_file() and new.is_file():
            _comparison(old, new, target, args.overwrite)
            comparisons[character_id] = str(target)
    before_after = output_root / "before-after-framing-board.png"
    if len(comparisons) == 2:
        _stack_images([Path(comparisons["dora"]), Path(comparisons["alex"])], before_after, args.overwrite)

    trio_video = output_root / "fabuloom-narrators-framing-trio-v1.mp4"
    _trio_video(videos, source_root / "fabuloom-official-narrator-dora-v1.wav", trio_video, args.overwrite)
    report_path = output_root / "facial-framing-v1-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.facial-framing-report/0.1",
        "mission": "023.4.1",
        "diagnosis": {
            "observed": ["cartoon heads were vertically stretched by normalized root size on a 1080x1920 source canvas", "hair and chin approached the circular crop boundary", "mouth states were children of the head but inherited the visually compressed framing"],
            "evidence": "real MP4-derived frames and facial closeups from facial-art-consistency-v1",
            "global_renderer_changed": False,
            "assets_changed": False,
        },
        "calibration": {
            "source_canvas": [1080, 1920],
            "cartoon_asset_size": [1254, 1254],
            "old_base_size": [0.68, 0.68],
            "new_base_size": [0.68, 0.3825],
            "old_base_position": [0.5, 0.32],
            "new_base_position": [0.5, 0.205],
            "mouth_scale_old": [0.9, 0.9],
            "mouth_scale_new": [1, 1],
            "head_and_mouth_transform": "mouth remains a child of head; state selection and RMS thresholds unchanged",
        },
        "results": results,
        "trio_video": str(trio_video),
        "comparisons": comparisons,
        "before_after_board": str(before_after),
        "mouth_timing": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "art_gate": "AWAITING_ART_APPROVAL",
        "processing_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}")
    for result in results:
        print(f"{result['character_id']}: video={result['video']} duration_ms={result['duration_ms']} frames={result['frame_count']}")
    print(f"trio={trio_video}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
