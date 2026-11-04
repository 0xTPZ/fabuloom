from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "cronicas_cap11_cin_001.py"
CAPTURE = ROOT / "frontend" / "capture-cronicas-cap11-narrative.html"
DOC = ROOT / "docs" / "CRONICAS-CAP11-CIN-001.md"
R2_RUNNER = ROOT / "examples" / "cronicas_cap11_cin_001_r2.py"


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


def test_cap11_r2_preserves_r1_and_uses_measured_editorial_gaps():
    source = R2_RUNNER.read_text(encoding="utf-8")
    assert 'R2_ROOT = EXPORT_ROOT / "cronicas-book1-capitulo11-cinematic-r2"' in source
    assert 'GAP_AFTER_HOST_MS = 1_000' in source
    assert 'GAP_BEFORE_OUTRO_MS = 1_200' in source
    assert '"r1_preserved": True' in source
    assert '"narrative_capture_reused": True' in source
    assert '"resynthesis": False' in source


def test_cap11_r2_has_deterministic_crystal_page_transitions_and_updated_captions():
    source = R2_RUNNER.read_text(encoding="utf-8")
    assert '"kind": "magical_page_crystal_dissolve"' in source
    assert "insert_silences" in source
    assert '"chapter11-r2.srt"' in source
    assert "transition-host-to-story" in source
    assert "transition-story-to-host" in source
    assert 'f"cronicas-capitulo11-o-eco-que-nao-morre-{orientation}-r2.mp4"' in source

