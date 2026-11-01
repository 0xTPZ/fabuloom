"""Generate isolated Santa V1 expressive-direction comparison samples.

This is a laboratory tool, not a replacement for any approved episode. It
keeps the original CB-002 question text available as a neutral control and
uses only controls that the current Kokoro adapter actually exposes:
punctuation/text boundaries and a small speed variation. Pitch, volume, SSML,
emotion tags and phoneme timing are deliberately not fabricated.
"""

from __future__ import annotations

import argparse
from array import array
import json
import math
from pathlib import Path
import sys
import time
import wave

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationTextSegment, compose_narration_manifest, segment_text
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import SynthesisParameters, SynthesisRequest


FABULOOM_ROOT = Path(r"E:\Fabuloom")
LAB_ROOT = FABULOOM_ROOT / "workspace" / "exports" / "voice-lab" / "mission-032-santa-expressive-v1"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"

QUESTIONS = {
    "q01": "Você já reparou para onde aponta a sua sombra?",
    "q02": "E você, Guardião... olharia para trás?",
}

# These profiles are a direction vocabulary for future narration tooling. The
# comparison set intentionally renders only three profiles because both source
# lines are questions; the welcoming profile remains available for an eventual
# approved greeting without inventing new CB-002 dialogue.
PROFILES = {
    "neutral": {
        "label": "neutral control",
        "speed": 1.00,
        "question_pause_ms": 240,
        "max_chars": 400,
        "texts": QUESTIONS,
    },
    "curious": {
        "label": "curious question",
        "speed": 0.97,
        "question_pause_ms": 320,
        "max_chars": 80,
        "texts": {
            "q01": "Você já reparou… para onde aponta a sua sombra?",
            "q02": "E você, Guardião… olharia para trás?",
        },
    },
    "suspense": {
        "label": "suspense question",
        "speed": 0.92,
        "question_pause_ms": 420,
        "max_chars": 48,
        "texts": {
            "q01": "Você já reparou... para onde aponta a sua sombra?",
            "q02": "E você, Guardião... olharia para trás?",
        },
    },
    "welcoming": {
        "label": "welcoming line direction",
        "speed": 1.00,
        "question_pause_ms": 240,
        "max_chars": 400,
        "texts": {},
    },
}

COMPARISON_PROFILES = ("neutral", "curious", "suspense")


def _validate_inside(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"laboratory output escaped workspace: {candidate}") from exc
    return candidate


def _measure_wav(path: Path) -> dict[str, float | int]:
    with wave.open(str(path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    if sample_width != 2:
        raise ValueError(f"expected PCM-16 WAV, got sample width {sample_width}")
    samples = array("h")
    samples.frombytes(raw)
    if not samples:
        raise ValueError(f"WAV contains no samples: {path}")
    if sys.byteorder != "little":
        samples.byteswap()
    sum_squares = sum(float(sample) * float(sample) for sample in samples)
    rms = math.sqrt(sum_squares / len(samples)) / 32768.0
    peak = max(abs(sample) for sample in samples) / 32768.0
    return {
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frames": frames,
        "duration_ms": round(frames * 1000 / sample_rate),
        "rms": round(rms, 6),
        "peak": round(peak, 6),
    }


def _format_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _write_srt(path: Path, manifest) -> None:
    lines: list[str] = []
    for index, segment in enumerate(manifest.segments, start=1):
        lines.extend(
            [
                str(index),
                f"{_format_timestamp(segment.start_ms)} --> {_format_timestamp(segment.end_ms)}",
                segment.text,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_samples(*, output_root: Path = LAB_ROOT, overwrite: bool = False) -> dict:
    output_root = _validate_inside(LAB_ROOT, output_root)
    audio_root = output_root / "samples"
    manifest_root = output_root / "manifests"
    srt_root = output_root / "srt"
    for directory in (audio_root, manifest_root, srt_root):
        directory.mkdir(parents=True, exist_ok=True)

    provider = KokoroTTSProvider(output_dir=audio_root, allow_overwrite=overwrite)
    generated: list[dict] = []
    started = time.perf_counter()
    try:
        for variant_number, profile_id in enumerate(COMPARISON_PROFILES, start=1):
            profile = PROFILES[profile_id]
            for question_number, question_id in enumerate(("q01", "q02"), start=1):
                sample_id = f"santa-expressive-032-v{variant_number:02d}-{question_id}"
                text = profile["texts"][question_id]
                output_path = _validate_inside(audio_root, audio_root / f"{variant_number:02d}-{profile_id}-{question_id}.wav")
                request = SynthesisRequest(
                    id=sample_id,
                    text=text,
                    voice_id=VOICE_ID,
                    language=LANGUAGE,
                    parameters=SynthesisParameters(speed=profile["speed"]),
                    metadata={
                        "mission": "032",
                        "direction_profile": profile_id,
                        "direction_label": profile["label"],
                        "question_id": question_id,
                        "original_episode_unmodified": True,
                    },
                )
                result = provider.synthesize(request, output_path)
                segmentation_probe = segment_text(
                    text,
                    segment_namespace=sample_id,
                    max_chars=profile["max_chars"],
                    question_pause_ms=profile["question_pause_ms"],
                )
                # Keep one WAV request per comparison sample. The core
                # splitter is still exercised and its count is recorded, but
                # the sample manifest must not duplicate one audio file across
                # multiple artificial segments.
                source_segment = NarrationTextSegment(
                    id=sample_id,
                    text=text,
                    ordinal=0,
                    paragraph_index=0,
                    sentence_index=0,
                    terminal_kind="question",
                    pause_after_ms=profile["question_pause_ms"],
                    pause_source="punctuation",
                )
                manifest = compose_narration_manifest(
                    (source_segment,),
                    (result,),
                    manifest_id=f"{sample_id}-manifest",
                    timeline_id=f"{sample_id}-timeline",
                    metadata={
                        "mission": "032",
                        "direction_profile": profile_id,
                        "direction_label": profile["label"],
                        "question_id": question_id,
                        "voice_id": VOICE_ID,
                        "language": LANGUAGE,
                        "timing_source": "measured_wav",
                        "word_phoneme_viseme_timing": "unavailable",
                        "approved_episode_replacement": False,
                    },
                )
                manifest_path = manifest_root / f"{output_path.stem}.json"
                manifest_path.write_text(serialize_manifest(manifest), encoding="utf-8")
                srt_path = srt_root / f"{output_path.stem}.srt"
                _write_srt(srt_path, manifest)
                measured = _measure_wav(output_path)
                generated.append(
                    {
                        "sample": output_path.name,
                        "manifest": manifest_path.name,
                        "srt": srt_path.name,
                        "profile": profile_id,
                        "label": profile["label"],
                        "question_id": question_id,
                        "text": text,
                        "speed": profile["speed"],
                        "question_pause_ms": profile["question_pause_ms"],
                        "max_chars": profile["max_chars"],
                        "segmentation_probe_segments": len(segmentation_probe),
                        "duration_ms": measured["duration_ms"],
                        "audio": measured,
                        "provider": result.provider_id,
                        "voice_id": result.voice_id,
                        "language": result.language,
                        "timing_source": "audio_duration_only",
                        "word_phoneme_viseme_timing": "unavailable",
                        "episode_replacement": False,
                    }
                )
    finally:
        provider.close()

    report = {
        "format": "fabuloom.santa-expressive-lab/0.1",
        "mission": "032",
        "status": "comparison_samples_ready",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "model_id": provider.model_id,
        "model_revision": provider.model_revision,
        "adapter_capabilities": {
            "supported_parameters": ["speed"],
            "unsupported_parameters": ["pitch", "volume", "extras", "ssml", "emotion_tags"],
            "word_timing": False,
            "phoneme_timing": False,
            "viseme_timing": False,
        },
        "direction_profiles": {
            profile_id: {
                "label": profile["label"],
                "speed": profile["speed"],
                "max_chars": profile["max_chars"],
                "question_pause_ms": profile["question_pause_ms"],
                "rendered_in_comparison": profile_id in COMPARISON_PROFILES,
            }
            for profile_id, profile in PROFILES.items()
        },
        "questions": QUESTIONS,
        "samples": generated,
        "processing_seconds": round(time.perf_counter() - started, 3),
        "original_episodes_modified": False,
        "human_audition_required": True,
        "recommendation_pending": True,
    }
    (output_root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="replace only existing lab samples")
    args = parser.parse_args()
    report = generate_samples(overwrite=args.overwrite)
    print(json.dumps({"status": report["status"], "samples": len(report["samples"]), "output": str(LAB_ROOT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
