"""Produce short local demos for the official Dora, Santa and Alex narrators."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest

from first_video_demo import _compose_audio, _write_srt
from narrator_mode_demo import _capture, _frame_board, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
DEMO_TEXT = "Bem-vindo ao Fabuloom Studio. Aqui, cada história pode encontrar sua própria voz e ganhar vida."
NARRATORS = {
    "dora": ("pf_dora", "Dora"),
    "santa": ("pm_santa", "Santa V5"),
    "alex": ("pm_alex", "Alex"),
}
FPS = 30


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8783)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    video_root = export_root / "videos" / "official-narrators-v1"
    video_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: list[dict] = []
    provider = KokoroTTSProvider(output_dir=export_root, allow_overwrite=args.overwrite)
    try:
        for character_id, (voice_id, character_name) in NARRATORS.items():
            story_id = f"fabuloom-official-narrator-{character_id}-v1"
            manifest_path = export_root / f"{story_id}.json"
            audio_path = video_root / f"{story_id}.wav"
            video_path = video_root / f"{story_id}.mp4"
            board_path = video_root / f"{story_id}-frames.png"
            srt_path = video_root / f"{story_id}.srt"
            frames_path = video_root / f".{story_id}-frames"
            if video_path.exists() and not args.overwrite:
                raise FileExistsError(f"video already exists: {video_path}; pass --overwrite")

            run_started = time.perf_counter()
            run = synthesize_narration(
                provider,
                DEMO_TEXT,
                narration_id=story_id,
                manifest_id=story_id,
                voice_id=voice_id,
                language="pt-BR",
                output_dir=export_root,
                max_chars=180,
            )
            manifest_path.write_text(serialize_manifest(run.manifest), encoding="utf-8")
            manifest = json.loads(serialize_manifest(run.manifest))
            sample_rate, _ = _compose_audio(manifest, audio_path)
            _write_srt(manifest, srt_path)
            if frames_path.exists():
                if not args.overwrite:
                    raise FileExistsError(f"frames already exist: {frames_path}; pass --overwrite")
                for frame in frames_path.glob("*.png"):
                    frame.unlink()
                # A previous successful capture leaves a completion marker.
                # Remove it under the explicit overwrite path so _capture
                # cannot accept stale metadata before the new PNG sequence.
                for marker in (frames_path / "complete.json", frames_path / "error.json"):
                    if marker.exists():
                        marker.unlink()
            frames_path.mkdir(parents=True, exist_ok=True)
            capture = _capture(STUDIO_ROOT, frames_path, manifest_path, args.port, args.capture_timeout, character_id=character_id)
            _render_mp4(frames_path, audio_path, video_path, int(manifest["duration_ms"]), args.overwrite)
            _frame_board(frames_path, board_path, int(manifest["duration_ms"]))
            probe = _probe_export(video_path)
            results.append({
                "character_id": character_id,
                "character_name": character_name,
                "voice_id": voice_id,
                "language": "pt-BR",
                "manifest": str(manifest_path),
                "audio": str(audio_path),
                "video": str(video_path),
                "board": str(board_path),
                "duration_ms": manifest["duration_ms"],
                "sample_rate": sample_rate,
                "frames": capture["frame_count"],
                "processing_seconds": round(time.perf_counter() - run_started, 3),
                "probe": probe,
            })
    finally:
        provider.close()

    report_path = video_root / "official-narrators-v1-report.json"
    report_path.write_text(json.dumps({
        "format": "fabuloom.official-narrators-v1-report/0.1",
        "text": DEMO_TEXT,
        "results": results,
        "timing_source": "measured_wav_segments",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "art_gate": "AWAITING_ART_APPROVAL",
        "total_processing_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}")
    for result in results:
        print(f"{result['character_id']}: video={result['video']} duration_ms={result['duration_ms']} frames={result['frames']}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
