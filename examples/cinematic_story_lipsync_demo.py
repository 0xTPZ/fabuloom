"""Regenerate Mission 018 with the corrected absolute-time RMS lip-sync path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from cinematic_story_test_demo import (
    EXPORT_ROOT,
    FPS,
    PROJECT_ID,
    STORY_ID,
    STUDIO_ROOT,
    _capture,
    _probe_export,
    _render_mp4,
)

VIDEO_ROOT = EXPORT_ROOT / "videos"
OLD_VIDEO = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.mp4"
NEW_VIDEO = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync.mp4"
MOUTH_BOARD = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync-mouth-states.png"
COMPARISON_BOARD = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync-before-after.png"
DIFFERENCE_BOARD = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync-difference.png"
REPORT_JSON = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync-report.json"
REPORT_MD = VIDEO_ROOT / "fabuloom-cinematic-story-test-v1.1-lipsync-report.md"


def _frame_index(time_ms: int, frame_count: int) -> int:
    return max(0, min(frame_count - 1, int(round(time_ms / 1000 * FPS))))


def _drawtext(label: str, x: int = 16, y: int = 16) -> str:
    safe = label.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{safe}':fontcolor=white:fontsize=22:x={x}:y={y}:box=1:boxcolor=0x07142A@.88"


def _mouth_board(frames: Path, output: Path, rms_samples: list[dict]) -> None:
    frame_count = len(list(frames.glob("*.png")))
    inputs: list[str] = []
    filters: list[str] = []
    for index, sample in enumerate(rms_samples):
        frame = frames / f"{_frame_index(sample['time_ms'], frame_count):06d}.png"
        inputs += ["-i", str(frame)]
        label = f"{sample['label']} | RMS {sample['amplitude']:.3f} | {sample['mouth_state']}"
        slot = chr(97 + index)
        filters.append(f"[{index}:v]crop=318:318:74:674,scale=420:420:flags=lanczos,{_drawtext(label)}[{slot}]")
    filters.append("[a][b][c][d][e]xstack=inputs=5:layout=0_0|420_0|840_0|0_420|420_420[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _comparison_board(old_video: Path, new_video: Path, output: Path, time_ms: int) -> None:
    seconds = f"{time_ms / 1000:.3f}"
    filter_graph = ";".join([
        f"[0:v]crop=318:318:74:674,scale=420:420:flags=lanczos,{_drawtext('V1 regression')}[old]",
        f"[1:v]crop=318:318:74:674,scale=420:420:flags=lanczos,{_drawtext('V1.1 corrected')}[new]",
        "[old][new]hstack=inputs=2[out]",
    ])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", seconds, "-i", str(old_video), "-ss", seconds, "-i", str(new_video), "-filter_complex", filter_graph, "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _difference_board(old_video: Path, new_video: Path, output: Path, time_ms: int) -> None:
    seconds = f"{time_ms / 1000:.3f}"
    filter_graph = "[0:v][1:v]blend=all_mode=difference,crop=318:318:74:674,scale=840:840:flags=lanczos[out]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", seconds, "-i", str(old_video), "-ss", seconds, "-i", str(new_video), "-filter_complex", filter_graph, "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8789)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    project_root = export_root / PROJECT_ID
    manifest_path = project_root / f"{STORY_ID}.json"
    timeline_path = project_root / f"{STORY_ID}-timeline.json"
    audio_path = project_root / f"{STORY_ID}.wav"
    frames = project_root / ".frames-lipsync-v1.1"
    for required in (manifest_path, timeline_path, audio_path, OLD_VIDEO):
        if not required.is_file(): raise FileNotFoundError(f"required Mission 018 artifact is missing: {required}")
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        import shutil
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    started = time.perf_counter()
    capture = _capture(STUDIO_ROOT, frames, timeline_path, args.port, args.capture_timeout)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _render_mp4(frames, audio_path, NEW_VIDEO, int(manifest["duration_ms"]), args.overwrite)
    probe = _probe_export(NEW_VIDEO)
    rms_samples = capture.get("rms_samples", [])
    if len(rms_samples) != 5: raise ValueError("capture did not return the five required RMS diagnostic states")
    _mouth_board(frames, MOUTH_BOARD, rms_samples)
    strongest = max(rms_samples, key=lambda sample: sample["amplitude"])
    _comparison_board(OLD_VIDEO, NEW_VIDEO, COMPARISON_BOARD, int(strongest["time_ms"]))
    _difference_board(OLD_VIDEO, NEW_VIDEO, DIFFERENCE_BOARD, int(strongest["time_ms"]))
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report = {
        "format": "fabuloom.cinematic-story-lipsync/0.1",
        "cause": "cinematic capture called the RMS reader without its measured sampleRate, so the absolute-time window became NaN and returned zero amplitude for every frame",
        "previous_pipeline": "Mission 017.4 capture passed sampleRate to the equivalent reader",
        "fix": "shared decodeMonoPcm16Wav/composePcmSegments/createRmsReader helpers and explicit sampleRate propagation",
        "manifest": str(manifest_path),
        "audio": str(audio_path),
        "capture": str(frames),
        "rms_samples": rms_samples,
        "strongest_sample": strongest,
        "resolved_assets": {sample["label"]: sample["resolved_asset"] for sample in rms_samples},
        "frame_count": capture["frame_count"],
        "video": str(NEW_VIDEO),
        "comparison": str(COMPARISON_BOARD),
        "difference": str(DIFFERENCE_BOARD),
        "duration_ms": manifest["duration_ms"],
        "probe": probe,
        "processing_seconds": round(time.perf_counter() - started, 3),
        "official_assets_modified": False,
        "scenes_modified": False,
        "word_phoneme_viseme_timing": "unavailable",
        "human_visual_review_required": True,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Mission 018.1 — lip-sync regression report",
        "",
        f"- Causa comprovada: {report['cause']}.",
        f"- Correção: {report['fix']}.",
        f"- Áudio e manifesto reutilizados: `{audio_path}` / `{manifest_path}`; nenhuma nova síntese.",
        f"- Frames corrigidos: `{frames}` ({capture['frame_count']} a {FPS} FPS).",
        f"- MP4: `{NEW_VIDEO}`; FFprobe `{probe['format']['duration']} s`, {video_stream['codec_name']} {video_stream['width']}×{video_stream['height']}, {audio_stream['codec_name']} {audio_stream['sample_rate']} Hz.",
        f"- Prancha de estados: `{MOUTH_BOARD}`.",
        f"- Comparação V1/V1.1: `{COMPARISON_BOARD}`; diferença restrita ao recorte do avatar: `{DIFFERENCE_BOARD}`.",
        "",
        "## Amostras reais",
        "",
        "| Estado | Tempo | RMS | Estado desenhado | Asset |",
        "|---|---:|---:|---|---|",
    ]
    lines.extend(f"| {sample['label']} | {sample['time_ms']} ms | {sample['amplitude']:.4f} | {sample['mouth_state']} | `{sample['resolved_asset']}` |" for sample in rms_samples)
    lines += ["", "Tempos de palavras, fonemas e visemas permanecem indisponíveis. Aprovação visual humana continua obrigatória.", ""]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"manifest={manifest_path}")
    print(f"audio={audio_path}")
    print(f"frames={frames}")
    print(f"video={NEW_VIDEO}")
    print(f"mouth_board={MOUTH_BOARD}")
    print(f"comparison={COMPARISON_BOARD}")
    print(f"difference={DIFFERENCE_BOARD}")
    print(f"report={REPORT_MD}")
    print(f"rms_samples={json.dumps(rms_samples, ensure_ascii=False)}")
    print(f"processing_seconds={report['processing_seconds']}")
    print(f"probe={json.dumps(probe, ensure_ascii=False)}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
