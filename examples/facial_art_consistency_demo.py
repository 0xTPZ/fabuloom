"""Render the Mission 023.4 cartoon-face validation using existing Kokoro audio."""

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
OUTPUT_ROOT = EXPORT_ROOT / "videos" / "facial-art-consistency-v1"
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
from facial_system_recovery_demo import _capture, _facial_closeups, _frame_board, _probe_export, _render_mp4, _comparison

NARRATORS = {
    "dora": ("pf_dora", "Dora Cartoon V1"),
    "alex": ("pm_alex", "Alex Cartoon V1"),
    "santa": ("pm_santa", "Santa V5 reference"),
}


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _trio_board(paths: list[Path], output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n"]
    args.extend(item for path in paths for item in ("-i", str(path)))
    args.extend([
        "-filter_complex",
        "[0:v]scale=560:-1[d];[1:v]scale=560:-1[a];[2:v]scale=560:-1[s];[d][a][s]vstack=inputs=3[out]",
        "-map", "[out]", "-frames:v", "1", str(output),
    ])
    _run_ffmpeg(args, output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8813)
    parser.add_argument("--capture-timeout", type=float, default=600)
    parser.add_argument("--character", choices=["dora", "alex", "santa", "all"], default="all")
    args = parser.parse_args()
    export_root = args.export_dir.resolve()
    output_root = export_root / "videos" / "facial-art-consistency-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    selected = list(NARRATORS) if args.character == "all" else [args.character]
    started = time.perf_counter()
    results: list[dict] = []
    for character_id in selected:
        voice_id, name = NARRATORS[character_id]
        source_id = f"fabuloom-official-narrator-{character_id}-v1"
        manifest_path = export_root / f"{source_id}.json"
        audio_path = SOURCE_ROOT / f"{source_id}.wav"
        video_path = output_root / f"fabuloom-official-narrator-{character_id}-cartoon-v1.mp4"
        board_path = output_root / f"{character_id}-cartoon-v1-frames.png"
        closeup_path = output_root / f"{character_id}-cartoon-v1-facial-closeups.png"
        frames_path = output_root / f".fabuloom-official-narrator-{character_id}-cartoon-v1-frames"
        for path in (manifest_path, audio_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        if frames_path.exists() and not args.overwrite:
            raise FileExistsError(f"frames exist: {frames_path}; pass --overwrite")
        if frames_path.exists():
            import shutil
            shutil.rmtree(frames_path)
        frames_path.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capture = _capture(STUDIO_ROOT, frames_path, manifest_path, args.port, args.capture_timeout, character_id=character_id)
        _render_mp4(frames_path, audio_path, video_path, int(manifest["duration_ms"]), args.overwrite)
        _frame_board(frames_path, board_path, int(manifest["duration_ms"]))
        _facial_closeups(frames_path, closeup_path, args.overwrite)
        results.append({
            "character_id": character_id,
            "name": name,
            "voice_id": voice_id,
            "language": "pt-BR",
            "manifest": str(manifest_path),
            "audio": str(audio_path),
            "video": str(video_path),
            "frame_board": str(board_path),
            "facial_closeups": str(closeup_path),
            "duration_ms": manifest["duration_ms"],
            "frame_count": capture["frame_count"],
            "probe": _probe_export(video_path),
        })

    if args.character == "all":
        for character_id in ("dora", "alex"):
            previous = EXPORT_ROOT / "videos" / "facial-system-recovery-v1" / f"{character_id}-recovery-v1-facial-closeups.png"
            current = output_root / f"{character_id}-cartoon-v1-facial-closeups.png"
            if previous.is_file() and current.is_file():
                _comparison(previous, current, output_root / f"{character_id}-recovery-to-cartoon-comparison.png", args.overwrite)
        _trio_board([output_root / f"{item}-cartoon-v1-facial-closeups.png" for item in ("dora", "alex", "santa")], output_root / "trio-cartoon-v1-comparison.png", args.overwrite)

    report_path = output_root / "facial-art-consistency-v1-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.facial-art-consistency-report/0.1",
        "mission": "023.4",
        "diagnosis": {
            "previous_defect": "V4 semi-realistic heads were paired with oversized purple vector bands; the state-loading fix made the mismatch visible but did not solve the art direction.",
            "evidence": "real MP4-derived closeups from Mission 023.3 were inspected before replacement",
            "preserved": ["Santa V5", "Mission 023.3 recovery packs", "V2/V3/V4 narrator assets"],
        },
        "strategy": {
            "base": "one original mouthless cartoon identity canvas per narrator",
            "mouth_states": ["closed", "slight", "moderate", "open"],
            "mouth_geometry": "compact same-canvas painted states; no full-width strip, no lower-face plate",
            "renderer": "NarratorAvatarRenderer + LayeredCharacterRenderer",
            "timing": "pcm16_rms_envelope; no phoneme or viseme timing invented",
        },
        "results": results,
        "art_gate": "AWAITING_ART_APPROVAL",
        "processing_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}")
    for result in results:
        print(f"{result['character_id']}: video={result['video']} duration_ms={result['duration_ms']} frames={result['frame_count']}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
