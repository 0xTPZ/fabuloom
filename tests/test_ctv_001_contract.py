from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "examples" / "ctv_001_vertical_cinema.py").read_text(encoding="utf-8")
CAPTURE = (ROOT / "frontend" / "capture-topazio-book1-vertical.html").read_text(encoding="utf-8")


def test_ctv_runner_declares_vertical_contract_and_batch_lots():
    assert 'RUNNER_VERSION = "ctv-001-vertical-cinema-v1.1-environment-only"' in RUNNER
    assert "WIDTH = 1080" in RUNNER
    assert "HEIGHT = 1920" in RUNNER
    assert 'lots = [("A", (1, 2)), ("B", (3, 4)), ("C", (5, 6)), ("D", (7, 8)), ("E", (9, 10))]' in RUNNER
    assert 'VOICE_ID = "pm_santa"' in RUNNER
    assert 'LANGUAGE = "pt-BR"' in RUNNER


def test_ctv_runner_preserves_measured_voice_and_music_safety():
    assert "measured_wav_segments" in RUNNER
    assert "music-cue-sheet.json" in RUNNER
    assert "sidechaincompress" in RUNNER
    assert "rights_status" in RUNNER
    assert "character_asset_blocked_by_environment_only_policy" in RUNNER


def test_vertical_capture_has_safe_area_and_no_story_characters():
    assert "tiktok_safe_area_overlay" in CAPTURE
    assert "draft_character_rendering" in CAPTURE
    assert "narrator_visibility" in CAPTURE
    assert "blocked character asset in vertical scene plan" in CAPTURE
    assert "HISTÓRIA COMPLETA NO PERFIL" in CAPTURE
