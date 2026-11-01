"""Offline checks for the Topazioverse Book 1 pilot orchestration."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples" / "topazioverse_book1_pilot_demo.py"
SPEC = importlib.util.spec_from_file_location("topazioverse_book1_pilot_demo", MODULE_PATH)
assert SPEC and SPEC.loader
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def _manifest():
    segments = []
    cursor = 0
    for paragraph_index in range(9):
        duration = 1000 + paragraph_index * 10
        pause = 100 if paragraph_index < 8 else 0
        segments.append(
            {
                "start_ms": cursor,
                "end_ms": cursor + duration,
                "duration_ms": duration,
                "text": f"segment {paragraph_index}",
                "metadata": {"paragraph_index": paragraph_index, "pause_after_ms": pause},
            }
        )
        cursor += duration + pause
    return {"duration_ms": cursor, "segments": segments}


def test_scene_schedule_uses_measured_boundaries():
    scenes = PILOT.build_scene_schedule(_manifest())
    assert scenes[0]["start_ms"] == 0
    assert scenes[0]["end_ms"] == 1100
    assert scenes[1]["start_ms"] == 1100
    assert scenes[2]["start_ms"] == 2210
    assert scenes[-1]["end_ms"] == _manifest()["duration_ms"]
    assert scenes[2]["source_paragraphs"] == [5, 6, 7, 8]


def test_source_range_and_voice_contract():
    assert PILOT.SOURCE_PARAGRAPHS == tuple(range(3, 12))
    assert PILOT.VOICE_ID == "pm_santa"
    assert PILOT.LANGUAGE == "pt-BR"
    assert PILOT.WIDTH == 1920 and PILOT.HEIGHT == 1080


def test_capture_page_keeps_development_labels_out_of_video():
    html = (ROOT / "frontend" / "capture-topazioverse-pilot.html").read_text(encoding="utf-8")
    assert "pm_santa" not in html
    assert "SANTA · pm_santa · pt-BR" not in html
    assert "TOPAZIOVERSE" in html
    assert "O DESPERTAR DOS CRISTAIS" in html
    assert "A NOITE EM QUE TOPÁZIO PAROU" in html


def test_scene_assets_are_relative_to_the_pilot_export():
    scenes = PILOT.build_scene_schedule(_manifest())
    assert all(scene["image"].startswith(f"{PILOT.PROJECT_ID}/") for scene in scenes)
    assert all(":\\" not in scene["image"] and "/" in scene["image"] for scene in scenes)
