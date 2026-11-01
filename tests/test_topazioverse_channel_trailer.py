"""Offline contract checks for the TopazioVerse channel trailer pipeline."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples" / "topazioverse_channel_trailer_demo.py"
SPEC = importlib.util.spec_from_file_location("topazioverse_channel_trailer_demo", MODULE_PATH)
assert SPEC and SPEC.loader
TRAILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAILER)


def _manifest(paragraph_count: int, duration_ms: int = 7000) -> dict:
    segments = []
    paragraph_duration = duration_ms // paragraph_count
    for index in range(paragraph_count):
        start_ms = index * paragraph_duration
        end_ms = duration_ms if index == paragraph_count - 1 else (index + 1) * paragraph_duration
        segments.append({
            "id": f"segment-{index}",
            "audio_uri": f"file:///E:/Fabuloom/workspace/exports/test-{index}.wav",
            "duration_ms": end_ms - start_ms,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "metadata": {"paragraph_index": index},
            "text": f"parágrafo {index}",
        })
    return {"duration_ms": duration_ms, "segments": segments}


def test_editorial_blocks_keep_the_required_order_and_cover_audio():
    blocks = TRAILER.build_blocks(_manifest(15), TRAILER.BLOCK_RANGES)
    assert [block["id"] for block in blocks] == [
        "CHANNEL_INTRO",
        "STORIES_SHOWCASE",
        "MUSIC_SHOWCASE",
        "GAMES_SHOWCASE",
        "TECH_SHOWCASE",
        "COMMUNITY_INVITATION",
        "CHANNEL_OUTRO",
    ]
    assert blocks[0]["start_ms"] == 0
    assert blocks[-1]["end_ms"] == 7000
    assert all(block["start_ms"] < block["end_ms"] for block in blocks)


def test_vertical_teaser_is_a_condensed_measured_program():
    blocks = TRAILER.build_blocks(_manifest(7), TRAILER.VERTICAL_BLOCK_RANGES)
    assert len(TRAILER.VERTICAL_SCRIPT_TEXT.split()) < len(TRAILER.SCRIPT_TEXT.split())
    assert [block["id"] for block in blocks] == [
        "CHANNEL_INTRO",
        "STORIES_SHOWCASE",
        "MUSIC_SHOWCASE",
        "GAMES_SHOWCASE",
        "TECH_SHOWCASE",
        "COMMUNITY_INVITATION",
        "CHANNEL_OUTRO",
    ]
    assert blocks[-1]["end_ms"] == 7000


def test_scene_schedule_has_real_and_explicit_conceptual_visuals():
    timeline = TRAILER.build_timeline(
        _manifest(15),
        manifest_ref="topazioverse-channel-trailer/manifest.json",
        block_ranges=TRAILER.BLOCK_RANGES,
        scene_specs=TRAILER.SCENE_SPECS,
        title="test",
    )
    assert len(timeline["scenes"]) == 15
    assert any(scene["visual"] == "real_ui" and scene["asset_path"] for scene in timeline["scenes"])
    assert any(scene["visual"] == "games_concept" for scene in timeline["scenes"])
    assert all(scene["start_ms"] < scene["end_ms"] for scene in timeline["scenes"])
    assert timeline["timing_source"] == "measured_kokoro_wav_segments"
    assert timeline["word_phoneme_viseme_timing"] == "unavailable"


def test_trailer_uses_santa_and_capture_page_uses_real_narrator_renderer():
    assert TRAILER.VOICE_ID == "pm_santa"
    assert TRAILER.LANGUAGE == "pt-BR"
    assert TRAILER.CAPTURE_FPS == 15
    assert TRAILER.OUTPUT_FPS == 30
    html = (ROOT / "frontend" / "capture-topazioverse-channel-trailer.html").read_text(encoding="utf-8")
    assert "NarratorAvatarRenderer" in html
    assert "createRmsReader" in html
    assert "measured_kokoro_wav_segments" in html
    assert "word_phoneme_viseme_timing" in html

