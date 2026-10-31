"""Render Dora/Alex facial-system recovery videos from existing local audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from narrator_mode_demo import _capture, _frame_board, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ROOT = EXPORT_ROOT / "videos" / "official-narrators-v1"
OUTPUT_ROOT = EXPORT_ROOT / "videos" / "facial-system-recovery-v1"
NARRATORS = {
    "dora": ("pf_dora", "Dora recovery V1"),
    "santa": ("pm_santa", "Santa V5 reference"),
    "alex": ("pm_alex", "Alex recovery V1"),
}


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _comparison(before: Path, after: Path, output: Path, overwrite: bool) -> None:
    _run_ffmpeg([
        "-y" if overwrite else "-n", "-i", str(before), "-i", str(after),
        "-filter_complex", "[0:v]scale=640:-1[left];[1:v]scale=640:-1[right];[left][right]hstack=inputs=2[out]",
        "-map", "[out]", "-frames:v", "1", str(output),
    ], output.parent)


def _facial_closeups(frames: Path, output: Path, overwrite: bool) -> None:
    last = max(0, len(sorted(path for path in frames.glob("*.png") if path.stem.isdigit())) - 1)
    indexes = [0, max(0, last // 3), max(0, last * 2 // 3), last]
    inputs: list[str] = []
    filters: list[str] = []
    labels = ["neutro", "fala", "fala / piscada", "final"]
    for index, label in enumerate(labels):
        inputs.extend(["-i", str(frames / f"{indexes[index]:06d}.png")])
        filters.append(f"[{index}:v]crop=420:420:30:640,scale=420:420,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=22:x=16:y=16:box=1:boxcolor=0x07142A@.85[f{index}]")
    filters.append("[f0][f1][f2][f3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[out]")
    _run_ffmpeg(["-y" if overwrite else "-n", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()
    export_root = args.export_dir.resolve()
    source_root = export_root / "videos" / "official-narrators-v1"
    output_root = export_root / "videos" / "facial-system-recovery-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: list[dict] = []
    for character_id, (voice_id, name) in NARRATORS.items():
        source_id = f"fabuloom-official-narrator-{character_id}-v1"
        manifest_path = export_root / f"{source_id}.json"
        audio_path = source_root / f"{source_id}.wav"
        video_path = output_root / f"fabuloom-official-narrator-{character_id}-recovery-v1.mp4"
        board_path = output_root / f"fabuloom-official-narrator-{character_id}-recovery-v1-frames.png"
        closeup_path = output_root / f"{character_id}-recovery-v1-facial-closeups.png"
        frames_path = output_root / f".fabuloom-official-narrator-{character_id}-recovery-v1-frames"
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
        results.append({"character_id": character_id, "name": name, "voice_id": voice_id, "language": "pt-BR", "manifest": str(manifest_path), "audio": str(audio_path), "video": str(video_path), "frame_board": str(board_path), "facial_closeups": str(closeup_path), "duration_ms": manifest["duration_ms"], "frame_count": capture["frame_count"], "probe": _probe_export(video_path)})

    comparisons: dict[str, str] = {}
    for character_id in ("dora", "alex"):
        old = EXPORT_ROOT / "videos" / "narrators-animation-reforge-v4" / f"fabuloom-official-narrator-{character_id}-v4-frames.png"
        new = output_root / f"fabuloom-official-narrator-{character_id}-recovery-v1-frames.png"
        target = output_root / f"{character_id}-v4-recovery-comparison.png"
        if old.is_file():
            _comparison(old, new, target, args.overwrite)
            comparisons[character_id] = str(target)

    report_path = output_root / "facial-system-recovery-v1-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.facial-system-recovery-report/0.1",
        "cause": "facial_states assets were returned by the resolver but were not preloaded by LayeredCharacterRenderer; missing state images were skipped by render().",
        "solution": "collectCharacterAssetPaths preloads nested facial state maps; Dora and Alex use same-canvas vector mouth states.",
        "results": results,
        "comparisons": comparisons,
        "prototype": str(output_root / "mouth-recovery-prototype.mp4"),
        "mouth_states": ["closed", "slight", "moderate", "open", "smile"],
        "timing_source": "measured_wav_segments",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
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
