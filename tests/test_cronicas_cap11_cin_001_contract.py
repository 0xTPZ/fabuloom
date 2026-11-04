from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "cronicas_cap11_cin_001.py"
CAPTURE = ROOT / "frontend" / "capture-cronicas-cap11-narrative.html"
DOC = ROOT / "docs" / "CRONICAS-CAP11-CIN-001.md"


def test_cap11_runner_preserves_editorial_title_and_voice_contract():
    source = RUNNER.read_text(encoding="utf-8")
    assert 'VOICE_ID = "pm_santa"' in source
    assert 'LANGUAGE = "pt-BR"' in source
    assert "chapter_display_title" in source
    assert "O capítulo 11 se chama" in source
    assert "E assim encerramos o capítulo 11" in source


def test_cap11_runner_excludes_external_video_audio():
    source = RUNNER.read_text(encoding="utf-8")
    assert '"-an"' in source
    assert 'external_video_audio' in source
    assert "all_external_video_audio_discarded" in source


def test_cap11_runner_has_resume_and_checkpoint_contract():
    source = RUNNER.read_text(encoding="utf-8")
    assert "BATCH-STATUS.json" in source
    assert "existing_capture" in source
    assert "CAPTURE_HORIZONTAL_OK" in source
    assert "CAPTURE_VERTICAL_OK" in source


def test_cap11_capture_is_deterministic_and_orientation_aware():
    source = CAPTURE.read_text(encoding="utf-8")
    assert 'orientation === "vertical"' in source
    assert "sendFrame" in source
    assert "pcm16_rms_envelope" in source
    assert "library_asset_id" in source


def test_cap11_documentation_records_known_limits():
    source = DOC.read_text(encoding="utf-8")
    assert "não é declarada como precisa" in source
    assert "Direitos\ncomerciais" in source
    assert "QA_OK" in source

