from __future__ import annotations

import importlib.util
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = STUDIO_ROOT / "examples" / "cronicas_de_topazio_channel_intro_demo.py"
SPEC = importlib.util.spec_from_file_location("cronicas_de_topazio_channel_intro_demo", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _manifest() -> dict:
    segments = []
    cursor = 0
    for paragraph_index in range(19):
        duration = 700 + paragraph_index * 31
        segments.append(
            {
                "id": f"segment-{paragraph_index:02d}",
                "text": f"Parágrafo {paragraph_index}",
                "start_ms": cursor,
                "end_ms": cursor + duration,
                "duration_ms": duration,
                "audio_uri": f"audio/segment-{paragraph_index:02d}.wav",
                "metadata": {"paragraph_index": paragraph_index},
            }
        )
        cursor += duration + 120
    return {"duration_ms": cursor, "segments": segments}


def test_script_is_fantasy_editorial_copy_with_expected_blocks():
    paragraphs = [item for item in MODULE.SCRIPT_TEXT.split("\n\n") if item]
    assert len(paragraphs) == 19
    assert list(MODULE.BLOCK_RANGES) == ["HOOK", "WELCOME", "UNIVERSE", "STORIES", "INVITATION"]
    assert "Fabuloom" not in MODULE.SCRIPT_TEXT
    assert "Kokoro" not in MODULE.SCRIPT_TEXT


def test_blocks_cover_measured_manifest_without_invented_timecodes():
    manifest = _manifest()
    blocks = MODULE.build_blocks(manifest)
    assert blocks[0]["start_ms"] == 0
    assert blocks[-1]["end_ms"] == manifest["duration_ms"]
    assert all(block["start_ms"] < block["end_ms"] for block in blocks)
    assert all(left["end_ms"] == right["start_ms"] for left, right in zip(blocks, blocks[1:]))
    assert sum(block["segment_count"] for block in blocks) == len(manifest["segments"])


def test_timeline_uses_santa_and_measured_audio_for_seventeen_scenes():
    timeline = MODULE.build_timeline(_manifest())
    assert timeline["voice_id"] == "pm_santa"
    assert timeline["language"] == "pt-BR"
    assert timeline["narrator"] == "Santa V5"
    assert timeline["timing_source"] == "measured_kokoro_wav_segments"
    assert timeline["word_phoneme_viseme_timing"] == "unavailable"
    assert len(timeline["scenes"]) == 17
    assert timeline["scenes"][0]["start_ms"] == 0
    assert timeline["scenes"][-1]["end_ms"] == timeline["duration_ms"]
    assert all(scene["start_ms"] < scene["end_ms"] for scene in timeline["scenes"])


def test_capture_page_uses_real_narrator_renderer_and_rms_audio():
    capture_page = (STUDIO_ROOT / "frontend" / "capture-cronicas-de-topazio.html").read_text(encoding="utf-8")
    assert "NarratorAvatarRenderer" in capture_page
    assert "createRmsReader" in capture_page
    assert "createNarratorTimeline" in capture_page
    assert "speechAmplitude: amplitude" in capture_page
    assert "measured_kokoro_wav_segments" in capture_page
    assert "word_phoneme_viseme_timing: \"unavailable\"" in capture_page


def test_workspace_assets_are_present_without_model_or_private_files():
    project_root = MODULE.PROJECT_ROOT
    expected = {
        "assets/generated/01-temple-of-gaia.png",
        "assets/generated/02-crystal-fissure.png",
        "assets/generated/03-world-panorama.png",
        "assets/generated/04-eternal-currents.png",
        "assets/generated/05-osai-volcano.png",
        "assets/generated/06-emberion.png",
        "assets/generated/07-mirakel-forest.png",
        "assets/generated/08-guardians.png",
        "assets/generated/09-elemental-crystal.png",
        "assets/generated/10-time-frozen.png",
        "assets/pilot/topazio-city.png",
        "assets/pilot/thaurion-echo-cave.png",
        "assets/pilot/vordros-mountains.png",
        "assets/pilot/zephirion-currents.png",
    }
    missing = [path for path in expected if not (project_root / path).is_file()]
    assert not missing, f"missing workspace assets: {missing}"
    assert not list(project_root.rglob("*.onnx"))
    assert not list(project_root.rglob("*.pth"))
    assert not list(project_root.rglob("*.safetensors"))
