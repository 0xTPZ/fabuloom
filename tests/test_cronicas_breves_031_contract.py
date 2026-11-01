"""Contract checks for Mission 031's independent CB-002/CB-003 pipeline."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest


STUDIO_ROOT = Path(__file__).resolve().parents[1]
DEMO = STUDIO_ROOT / "examples" / "cronicas_breves_cb002_cb003_demo.py"
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports\cronicas-breves")
CB002 = EXPORT_ROOT / "cb-002-a-sombra-que-olhava-para-o-sol"
CB003 = EXPORT_ROOT / "cb-003-a-luz-do-ultimo-viajante"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mission_031_keeps_exact_voice_and_episode_boundaries() -> None:
    source = _read(DEMO)
    assert 'VOICE_ID = "pm_santa"' in source
    assert 'LANGUAGE = "pt-BR"' in source
    assert 'CB002_ID = "cb-002-a-sombra-que-olhava-para-o-sol"' in source
    assert 'CB003_ID = "cb-003-a-luz-do-ultimo-viajante"' in source
    assert "Guardião... você já reparou para onde aponta a sua sombra?" in source
    assert "Guardião... quer ouvir uma história sobre uma luz que não devia se apagar?" in source
    assert "A Sombra que Olhava para o Sol.mp3" in source
    assert "A Luz do Último Viajante.mp3" in source
    assert "BLOCKED_BY_MISSING_MUSIC" in source
    assert "no substitute used" in source


def test_mission_031_does_not_fallback_to_cb001_music() -> None:
    source = _read(DEMO)
    assert "O Quarto Eco" not in source
    assert "Os Ecos que Nunca Morrem.mp3" not in source
    assert "cb-001-o-quarto-eco" not in source


def test_completed_cb003_report_is_self_consistent_when_local_artifacts_exist() -> None:
    report_path = CB003 / "reports" / "technical-report.json"
    if not report_path.exists():
        pytest.skip("local Mission 031 exports are not part of a source checkout")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["export_status"] == "completed_pending_human_artistic_review"
    assert report["narrator"]["character"] == "Santa V5"
    assert report["narrator"]["renderer"] == "NarratorAvatarRenderer"
    assert report["narrator"]["library"] == "santa-library-topazioverse-v1"
    assert report["draft_characters"] == "blocked"
    assert report["story_visuals"] == "environment_only"
    assert report["timing_source"] == "measured_wav_segments"
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

    probe = report["probe"]
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 1080, 1920)
    assert (audio["codec_name"], audio["channels"], audio["channel_layout"]) == ("aac", 2, "stereo")
    assert report["duration_ms"] == 52000
    assert report["frame_count"] == 1560


def test_completed_cb003_manifest_and_srt_have_measured_segment_count() -> None:
    manifest_path = CB003 / "audio" / "narration-manifest.json"
    srt_path = CB003 / "timeline" / "cb-003-a-luz-do-ultimo-viajante.srt"
    if not manifest_path.exists() or not srt_path.exists():
        pytest.skip("local Mission 031 exports are not part of a source checkout")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    srt = _read(srt_path)
    segments = manifest["segments"]
    assert len(segments) == 15
    assert manifest["metadata"]["voice_id"] == "pm_santa"
    assert manifest["metadata"]["temporal_source"] == "measured_wav"
    assert all(segment["metadata"]["timing_source"] == "audio_duration_only" for segment in segments)
    assert all(not segment["word_timings"] for segment in segments)
    assert len(re.findall(r"(?m)^\d+$", srt)) == len(segments)


def test_missing_cb002_music_blocks_only_cb002_final_video_when_local_report_exists() -> None:
    report_path = CB002 / "reports" / "technical-report.json"
    if not report_path.exists():
        pytest.skip("local Mission 031 exports are not part of a source checkout")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["export_status"] == "BLOCKED_BY_MISSING_MUSIC"
    assert report["music"]["exists"] is False
    assert report["video"] is None
    assert report["validation"]["final_video"] is False
    assert not list((CB002 / "videos").glob("*.mp4"))
