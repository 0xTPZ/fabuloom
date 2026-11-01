"""Offline contract checks for the Topazioverse pilot V3 editorial blocks."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples" / "topazioverse_book1_pilot_v3_demo.py"
SPEC = importlib.util.spec_from_file_location("topazioverse_book1_pilot_v3_demo", MODULE_PATH)
assert SPEC and SPEC.loader
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def _manifest(prefix: str, duration: int, count: int) -> dict:
    segments = []
    cursor = 0
    for index in range(count):
        segment_duration = duration // count
        end = cursor + segment_duration
        segments.append({
            "id": f"{prefix}-{index}",
            "dialogue_id": f"dialogue-{prefix}-{index}",
            "audio_uri": f"file:///E:/Fabuloom/workspace/exports/{prefix}-{index}.wav",
            "duration_ms": segment_duration,
            "start_ms": cursor,
            "end_ms": end,
            "format_version": "0.1.0",
            "language": "pt-BR",
            "provider_id": "kokoro",
            "voice_id": "pm_santa",
            "text": f"{prefix} {index}",
            "track_id": "voice",
            "metadata": {},
            "word_timings": [],
            "phoneme_timings": [],
            "viseme_timings": [],
        })
        cursor = end
    return {"duration_ms": cursor, "segments": segments}


def test_host_copy_is_explicit_and_does_not_replace_the_story():
    assert "Sejam bem-vindos ao Topazioverse" in PILOT.INTRO_TEXT
    assert "Até nossa próxima aventura" in PILOT.OUTRO_TEXT
    assert "O Despertar dos Cristais" not in PILOT.INTRO_TEXT
    assert "O Despertar dos Cristais" not in PILOT.OUTRO_TEXT


def test_combined_manifest_has_three_non_overlapping_editorial_blocks():
    intro = _manifest("intro", 3000, 2)
    story = _manifest("story", 10000, 3)
    outro = _manifest("outro", 4000, 2)
    combined, info = PILOT.build_combined_manifest(intro, story, outro, transition_ms=500)

    assert [block["id"] for block in info["blocks"]] == ["HOST_INTRO", "STORY_CHAPTER", "HOST_OUTRO"]
    assert info["story_start_ms"] == 3500
    assert info["story_end_ms"] == 13499
    assert info["outro_start_ms"] == 13999
    assert info["duration_ms"] == 17999
    assert combined["duration_ms"] == info["duration_ms"]
    assert len(combined["segments"]) == 7
    assert all(combined["segments"][index]["end_ms"] <= combined["segments"][index + 1]["start_ms"] for index in range(len(combined["segments"]) - 1))


def test_story_segment_boundaries_are_shifted_without_changing_durations():
    intro = _manifest("intro", 3000, 1)
    story = _manifest("story", 9000, 3)
    outro = _manifest("outro", 4000, 1)
    combined, info = PILOT.build_combined_manifest(intro, story, outro, transition_ms=1000)
    story_segments = [segment for segment in combined["segments"] if segment["metadata"]["editorial_block"] == "STORY_CHAPTER"]
    assert story_segments[0]["start_ms"] == info["story_start_ms"]
    assert [segment["duration_ms"] for segment in story_segments] == [segment["duration_ms"] for segment in story["segments"]]
    assert all(segment["metadata"]["source_segment_id"].startswith("story-") for segment in story_segments)


def test_v3_contract_keeps_real_voice_and_no_private_debug_labels_in_capture_page():
    assert PILOT.VOICE_ID == "pm_santa"
    assert PILOT.LANGUAGE == "pt-BR"
    assert PILOT.CAPTURE_FPS == 15 and PILOT.OUTPUT_FPS == 30
    html = (ROOT / "frontend" / "capture-topazioverse-pilot-v3.html").read_text(encoding="utf-8")
    assert "editorial_blocks" in html
    assert "RMS" not in html
    assert "pm_santa" not in html
    assert "SANTA · pm_santa · pt-BR" not in html

