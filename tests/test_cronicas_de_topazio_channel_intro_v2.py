from __future__ import annotations

import importlib.util
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = STUDIO_ROOT / "examples" / "cronicas_de_topazio_channel_intro_v2_demo.py"
SPEC = importlib.util.spec_from_file_location("cronicas_de_topazio_channel_intro_v2_demo", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_v2_keeps_the_approved_canvas_contract_and_output_name():
    assert MODULE.FPS == 30
    assert (MODULE.WIDTH, MODULE.HEIGHT) == (1920, 1080)
    assert MODULE.PROJECT_ID == "cronicas-de-topazio-channel-intro"
    assert MODULE.PROJECT_ROOT / "cronicas-de-topazio-channel-intro-v2.mp4" != MODULE.PROJECT_ROOT / "cronicas-de-topazio-channel-intro.mp4"


def test_music_input_is_defaulted_to_workspace_music_folder():
    assert MODULE.DEFAULT_MUSIC.parent.name == "book1"
    assert MODULE.DEFAULT_MUSIC.parent.parent.name == "music"
    assert MODULE.DEFAULT_MUSIC.suffix == ".mp3"


def test_ducking_graph_uses_voice_as_sidechain_for_music_and_sfx():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "[music][voice]sidechaincompress" in source
    assert "[sfx][voice]sidechaincompress" in source
    assert "ratio=8" in source
    assert "release=700" in source
    assert "alimiter=limit=0.92" in source
    assert "atempo" not in source
    assert "asetrate" not in source


def test_source_music_path_is_contained_by_workspace_music_root():
    path = MODULE._safe_music_path(MODULE.DEFAULT_MUSIC)
    assert path.is_absolute()
    assert path.parent.name == "book1"
