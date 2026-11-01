"""Offline contract checks for the Mission 032 expressive voice lab."""

from __future__ import annotations

import json
from pathlib import Path
import wave

import pytest


STUDIO_ROOT = Path(__file__).resolve().parents[1]
DEMO = STUDIO_ROOT / "examples" / "santa_expressive_v1_lab.py"
LAB_ROOT = Path(r"E:\Fabuloom\workspace\exports\voice-lab\mission-032-santa-expressive-v1")


def test_lab_declares_only_supported_kokoro_controls() -> None:
    source = DEMO.read_text(encoding="utf-8")
    assert 'VOICE_ID = "pm_santa"' in source
    assert 'LANGUAGE = "pt-BR"' in source
    assert '"supported_parameters": ["speed"]' in source
    assert '"unsupported_parameters": ["pitch", "volume", "extras", "ssml", "emotion_tags"]' in source
    assert '"welcoming": {' in source
    assert "original_episode_unmodified" in source
    assert "approved_episode_replacement" in source


def test_lab_preserves_the_two_cb002_control_questions() -> None:
    source = DEMO.read_text(encoding="utf-8")
    assert '"Você já reparou para onde aponta a sua sombra?"' in source
    assert '"E você, Guardião... olharia para trás?"' in source
    assert "NarrationTextSegment" in source
    assert "compose_narration_manifest" in source


def test_local_comparison_report_contains_six_measured_samples() -> None:
    report_path = LAB_ROOT / "report.json"
    if not report_path.exists():
        pytest.skip("Mission 032 local audio lab artifacts are not part of a source checkout")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "comparison_samples_ready"
    assert report["voice_id"] == "pm_santa"
    assert report["language"] == "pt-BR"
    assert report["original_episodes_modified"] is False
    assert report["human_audition_required"] is True
    assert {item["profile"] for item in report["samples"]} == {"neutral", "curious", "suspense"}
    assert len(report["samples"]) == 6

    neutral = {item["question_id"]: item for item in report["samples"] if item["profile"] == "neutral"}
    assert neutral["q01"]["text"] == "Você já reparou para onde aponta a sua sombra?"
    assert neutral["q02"]["text"] == "E você, Guardião... olharia para trás?"
    assert all(item["voice_id"] == "pm_santa" for item in report["samples"])
    assert all(item["language"] == "pt-BR" for item in report["samples"])
    assert all(item["timing_source"] == "audio_duration_only" for item in report["samples"])
    assert all(item["word_phoneme_viseme_timing"] == "unavailable" for item in report["samples"])


def test_local_wavs_manifests_and_srts_agree() -> None:
    report_path = LAB_ROOT / "report.json"
    if not report_path.exists():
        pytest.skip("Mission 032 local audio lab artifacts are not part of a source checkout")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    for item in report["samples"]:
        wav_path = LAB_ROOT / "samples" / item["sample"]
        manifest_path = LAB_ROOT / "manifests" / item["manifest"]
        srt_path = LAB_ROOT / "srt" / item["srt"]
        assert wav_path.exists()
        assert manifest_path.exists()
        assert srt_path.exists()
        with wave.open(str(wav_path), "rb") as wav:
            assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (24000, 1, 2)
            duration_ms = round(wav.getnframes() * 1000 / wav.getframerate())
        assert duration_ms == item["duration_ms"]

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["metadata"]["voice_id"] == "pm_santa"
        assert manifest["metadata"]["timing_source"] == "measured_wav"
        assert manifest["metadata"]["word_phoneme_viseme_timing"] == "unavailable"
        assert len(manifest["segments"]) == 1
        assert manifest["segments"][0]["duration_ms"] == duration_ms
        assert not manifest["segments"][0]["word_timings"]
        assert not manifest["segments"][0]["phoneme_timings"]
        assert not manifest["segments"][0]["viseme_timings"]
        assert len([line for line in srt_path.read_text(encoding="utf-8").splitlines() if line.isdigit()]) == 1
