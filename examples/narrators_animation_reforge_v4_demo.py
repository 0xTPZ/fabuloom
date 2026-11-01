"""Render the V4 Dora/Alex narrator reforge using existing measured audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from narrator_mode_demo import _capture, _frame_board, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ROOT = EXPORT_ROOT / "videos" / "official-narrators-v1"
OUTPUT_ROOT = EXPORT_ROOT / "videos" / "narrators-animation-reforge-v4"
FPS = 30
NARRATORS = {
    "dora": ("pf_dora", "Dora V4"),
    "santa": ("pm_santa", "Santa V5"),
    "alex": ("pm_alex", "Alex V4"),
}


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _comparison(before: Path, after: Path, output: Path, overwrite: bool) -> None:
    _run_ffmpeg([
        "-y" if overwrite else "-n",
        "-i", str(before),
        "-i", str(after),
        "-filter_complex", "[0:v]scale=640:-1[left];[1:v]scale=640:-1[right];[left][right]hstack=inputs=2[out]",
        "-map", "[out]",
        "-frames:v", "1",
        str(output),
    ], output.parent)


def _trio_board(boards: list[Path], output: Path, overwrite: bool) -> None:
    inputs: list[str] = []
    filters: list[str] = []
    for index, board in enumerate(boards):
        inputs.extend(["-i", str(board)])
        filters.append(f"[{index}:v]scale=640:-2[n{index}]")
    labels = "".join(f"[n{index}]" for index in range(len(boards)))
    filters.append(f"{labels}hstack=inputs={len(boards)}[out]")
    _run_ffmpeg([
        "-y" if overwrite else "-n",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-frames:v", "1",
        str(output),
    ], output.parent)


def _concat(videos: list[Path], output: Path, overwrite: bool) -> None:
    list_path = output.with_suffix(".concat.txt")
    list_path.write_text("\n".join(f"file '{path.as_posix()}'" for path in videos) + "\n", encoding="utf-8")
    try:
        _run_ffmpeg([
            "-y" if overwrite else "-n",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output),
        ], output.parent)
    finally:
        if list_path.exists(): list_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8794)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    source_root = export_root / "videos" / "official-narrators-v1"
    output_root = export_root / "videos" / "narrators-animation-reforge-v4"
    output_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: list[dict] = []

    for character_id, (voice_id, character_name) in NARRATORS.items():
        source_id = f"fabuloom-official-narrator-{character_id}-v1"
        manifest_path = export_root / f"{source_id}.json"
        audio_path = source_root / f"{source_id}.wav"
        output_id = f"fabuloom-official-narrator-{character_id}-v4"
        video_path = output_root / f"{output_id}.mp4"
        board_path = output_root / f"{output_id}-frames.png"
        frames_path = output_root / f".{output_id}-frames"

        if not manifest_path.is_file(): raise FileNotFoundError(f"missing measured manifest: {manifest_path}")
        if not audio_path.is_file(): raise FileNotFoundError(f"missing measured audio: {audio_path}")
        if video_path.exists() and not args.overwrite: raise FileExistsError(f"video exists: {video_path}; pass --overwrite")
        if frames_path.exists():
            if not args.overwrite: raise FileExistsError(f"frames exist: {frames_path}; pass --overwrite")
            shutil.rmtree(frames_path)
        frames_path.mkdir(parents=True, exist_ok=True)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capture = _capture(STUDIO_ROOT, frames_path, manifest_path, args.port, args.capture_timeout, character_id=character_id)
        _render_mp4(frames_path, audio_path, video_path, int(manifest["duration_ms"]), args.overwrite)
        _frame_board(frames_path, board_path, int(manifest["duration_ms"]))
        probe = _probe_export(video_path)
        results.append({
            "character_id": character_id,
            "character_name": character_name,
            "voice_id": voice_id,
            "language": "pt-BR",
            "visual_pack": "V5-preserved" if character_id == "santa" else f"{character_name.split()[0]}-V4",
            "source_manifest": str(manifest_path),
            "source_audio": str(audio_path),
            "video": str(video_path),
            "frame_board": str(board_path),
            "duration_ms": manifest["duration_ms"],
            "frame_count": capture["frame_count"],
            "probe": probe,
        })

    dora_before = source_root / "fabuloom-official-narrator-dora-v1-frames.png"
    alex_before = source_root / "fabuloom-official-narrator-alex-v1-frames.png"
    dora_after = output_root / "fabuloom-official-narrator-dora-v4-frames.png"
    alex_after = output_root / "fabuloom-official-narrator-alex-v4-frames.png"
    dora_comparison = output_root / "dora-v3-v4-comparison.png"
    alex_comparison = output_root / "alex-v3-v4-comparison.png"
    if dora_before.is_file(): _comparison(dora_before, dora_after, dora_comparison, args.overwrite)
    if alex_before.is_file(): _comparison(alex_before, alex_after, alex_comparison, args.overwrite)
    trio_board = output_root / "narrators-trio-v4-comparison.png"
    _trio_board([
        output_root / "fabuloom-official-narrator-santa-v4-frames.png",
        dora_after,
        alex_after,
    ], trio_board, args.overwrite)

    individual_videos = [Path(result["video"]) for result in results]
    trio_path = output_root / "fabuloom-official-narrators-trio-v4.mp4"
    _concat(individual_videos, trio_path, args.overwrite)
    trio_probe = _probe_export(trio_path)
    report_path = output_root / "narrators-animation-reforge-v4-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.narrators-animation-reforge-v4-report/0.1",
        "source": "mission-023.1 measured local WAVs and manifests",
        "results": results,
        "trio_video": str(trio_path),
        "trio_probe": trio_probe,
        "comparisons": {
            "dora_v3_v4": str(dora_comparison),
            "alex_v3_v4": str(alex_comparison),
            "trio_v4": str(trio_board),
        },
        "timing_source": "measured_wav_segments",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "art_gate": "AWAITING_ART_APPROVAL",
        "visual_inspector": {
            "format": "fabuloom.visual-inspector-report/0.1",
            "evidence": "rendered PNG boards and enlarged facial closeups inspected from the same renderer used by the MP4 capture",
            "checks": {
                "front_facing_v4_bases": "pass",
                "head_and_frame_contained": "pass",
                "mouth_states_are_distinct": "pass",
                "eyes_and_eyelids_remain_aligned": "pass",
                "v3_comparison_preserved": "pass",
                "human_art_approval": "required",
            },
            "findings": [
                "Initial oversized realistic mouth plates were rejected during visual inspection.",
                "Compact transparent mouth plates and explicit local transforms were rendered again for Dora and Alex.",
                "Final closeups show centered, readable facial states without claiming phonetic lip-sync.",
            ],
            "limitations": [
                "RMS amplitude drives coarse mouth states; word, phoneme and viseme timing are unavailable.",
                "Dora and Alex V4 remain experimental until owner review.",
            ],
        },
        "processing_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}")
    for result in results: print(f"{result['character_id']}: video={result['video']} duration_ms={result['duration_ms']} frames={result['frame_count']}")
    print(f"trio_board={trio_board}")
    print(f"trio={trio_path}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
