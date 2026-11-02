"""Offline contract checks for the CB-002 finalization pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


STUDIO_ROOT = Path(__file__).resolve().parents[1]
DEMO = STUDIO_ROOT / "examples" / "cronicas_breves_cb002_cb003_demo.py"
CB002 = Path(r"E:\Fabuloom\workspace\exports\cronicas-breves\cb-002-a-sombra-que-olhava-para-o-sol")


def test_cb002_finalization_declares_existing_track_and_voice_decision() -> None:
    source = DEMO.read_text(encoding="utf-8")
    assert '"A Sombra que Olhava para o Sol.mp3"' in source
    assert "A faixa existente é específica para o episódio" in source
    assert '"preserve_original_measured_narration"' in source
    assert "Sem evidência clara de melhoria acústica" in source
    assert "music-selection.md" in source
    assert "voice-improvements.md" in source


def test_cb002_final_report_validates_final_video_when_local_artifacts_exist() -> None:
    report_path = CB002 / "reports" / "technical-report.json"
    if not report_path.exists():
        pytest.skip("local CB-002 final artifacts are not part of a source checkout")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("export_status") == "BLOCKED_BY_MISSING_MUSIC":
        pytest.skip("CB-002 final export has not been run in this checkout")
    assert report["export_status"] == "completed_pending_human_artistic_review"
    assert report["duration_ms"] == 55105
    assert report["segments"] == 17
    assert report["music"]["exists"] is True
    assert report["music"]["selection_reason"]
    assert report["voice_direction"]["decision"] == "preserve_original_measured_narration"
    assert report["word_phoneme_viseme_timing"] == "unavailable"
    assert report["validation"] == {
        "duration_coherent": True,
        "ffmpeg_decode": True,
        "blackdetect": {"passed": True, "detections": [], "returncode": 0},
        "subtitle_sync": True,
        "safe_area": True,
        "santa_rendered": True,
        "draft_characters_absent": True,
    }
    video = next(stream for stream in report["probe"]["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in report["probe"]["streams"] if stream["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 1080, 1920)
    assert (audio["codec_name"], audio["channels"], audio["channel_layout"]) == ("aac", 2, "stereo")
    assert (CB002 / "reports" / "music-selection.md").exists()
    assert (CB002 / "reports" / "voice-improvements.md").exists()
