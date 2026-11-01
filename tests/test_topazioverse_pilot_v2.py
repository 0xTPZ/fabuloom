"""Offline contract checks for the Topazioverse pilot V2."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples" / "topazioverse_book1_pilot_v2_demo.py"
SPEC = importlib.util.spec_from_file_location("topazioverse_book1_pilot_v2_demo", MODULE_PATH)
assert SPEC and SPEC.loader
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def test_v2_reuses_measured_v1_voice_and_uses_owner_music():
    assert PILOT.MANIFEST.name == "manifest.json"
    assert PILOT.VOICE_WAV.name.endswith("-voice.wav")
    assert PILOT.MUSIC.name.startswith("Topázio — O Despertar dos Cristais")
    assert PILOT.CAPTURE_FPS == 15
    assert PILOT.OUTPUT_FPS == 30


def test_v2_capture_page_keeps_santa_visible_and_no_debug_identity():
    html = (ROOT / "frontend" / "capture-topazioverse-pilot-v2.html").read_text(encoding="utf-8")
    assert "drawNarrator(avatar" in html
    assert "narrator_visibility: \"entire_narrative\"" in html
    assert "pm_santa" not in html
    assert "SANTA · pm_santa · pt-BR" not in html
    assert "O DESPERTAR DOS CRISTAIS" in html


def test_v2_manifest_reference_stays_inside_exports():
    assert "E:\\" not in PILOT.MUSIC.as_posix()
    assert PILOT.V1_ROOT.is_absolute()
