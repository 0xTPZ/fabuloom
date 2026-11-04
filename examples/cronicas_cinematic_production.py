"""Registered, parameterized runner for a Crônicas cinematic chapter.

This adapter deliberately reuses the approved Chapter 2/4 helpers instead of
creating a second renderer.  It accepts a validated request JSON, writes only
inside the supplied isolated output root, and records a checkpoint after every
stage so the EngineService can resume an interrupted production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import re
from urllib.parse import urlencode

# The runner is executed as a script by EngineService; keeping its sibling
# directory explicit also makes controlled direct imports deterministic.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import topazio_book1_chapter1_cronicas_demo as v1
import topazio_book1_chapter2_cronicas_demo as base
from topazio_book1_chapter1_cronicas_v2_demo import audit_santa_visibility, mix_audio_v2

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.kokoro import KokoroTTSProvider


_CONFIGURED_ROOT = os.environ.get("FABULOOM_ROOT") or os.environ.get("FABULOOM_WORKSPACE_ROOT")
if not _CONFIGURED_ROOT:
    raise RuntimeError("FABULOOM_ROOT or FABULOOM_WORKSPACE_ROOT must be configured")
FABULOOM_ROOT = Path(_CONFIGURED_ROOT).resolve()
PRODUCT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
DEFAULT_MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Alba Quando a Luz Rasga o Céu.mp3"
SOURCE_DOC_DEFAULT = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
REGISTRY = PRODUCT_ROOT / "assets" / "scene-registry.json"
CHARACTER_REGISTRY_PATH = PRODUCT_ROOT / "assets" / "character-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
TRANSITION_MS = 900
APPROVED_CHARACTER_ID = "santa-v5-base"

# These are approved environment/object plates already used by Chapter 4.  A
# fresh production receives copies in its own output root; approved outputs and
# the source library are never modified.
SCENE_SPECS = (
    ("shot-001-forest-threshold", "01-circular-scar.png", "cave_entry"),
    ("shot-002-root-crystal", "02-crystal-ring.png", "crystal_drift"),
    ("shot-003-ancient-map", "11-stone-map.png", "memory_fissure"),
    ("shot-004-forest-storm", "13-aerial-temple-storm.png", "wind"),
    ("shot-005-crystal-signal", "09-observatory-signals.png", "seven_pulse"),
    ("shot-006-hidden-door", "12-cracked-doorway.png", "temple_approach"),
    ("shot-007-shadow-grove", "10-mask-scythe-parapet.png", "shadow_cross"),
    ("shot-008-black-water", "07-black-water-trident.png", "reflection_drift"),
    ("shot-009-aftermath", "08-courtyard-aftermath.png", "road_push"),
    ("shot-010-crystal-fire", "06-tower-fire-rings.png", "altar_push"),
    ("shot-011-final-threshold", "04-east-gate-attack.png", "chapter_fade"),
    ("shot-012-night-canopy", "05-frost-gate.png", "host_closing"),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path must stay inside {root}: {resolved}") from exc
    return resolved


def _resolve_input(value: str | None, *, root: Path, default: Path) -> Path:
    if not value:
        return default
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    return _inside(candidate, root)


def _chapter_heading(text: str, number: int) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip())
    return bool(re.match(rf"^Cap.*\s{number}(?:\s|[—–:-])", normalized, flags=re.IGNORECASE))


def _load_chapter(path: Path, number: int) -> tuple[tuple[str, ...], str, dict[str, object]]:
    paragraphs = base._load_docx_paragraphs(path)
    heading = next((index for index, value in enumerate(paragraphs) if _chapter_heading(value, number)), None)
    if heading is None:
        raise ValueError(f"chapter {number} heading not found in {path}")
    next_heading = next((index for index in range(heading + 1, len(paragraphs)) if _chapter_heading(paragraphs[index], number + 1)), None)
    if next_heading is None:
        raise ValueError(f"chapter {number + 1} heading not found after chapter {number}")
    selected = tuple(value.strip() for value in paragraphs[heading + 1:next_heading] if value.strip())
    if not selected:
        raise ValueError(f"chapter {number} has no narrative paragraphs")
    text = "\n\n".join(selected)
    title = paragraphs[heading].strip()
    base.SOURCE_PARAGRAPH_START = heading + 1
    base.SOURCE_PARAGRAPH_END_EXCLUSIVE = next_heading
    base.SOURCE_CHAPTER_TITLE = title
    return selected, text, {
        "title": title,
        "heading_paragraph": heading,
        "first_narrative_paragraph": heading + 1,
        "last_narrative_paragraph": next_heading - 1,
        "next_chapter_heading_paragraph": next_heading,
        "paragraph_count": len(selected),
        "text_characters": len(text),
        "word_count": len(re.findall(r"\S+", text)),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _title_without_prefix(value: str, number: int) -> str:
    return re.sub(rf"^Cap.*?\s{number}\s*[—–:-]\s*", "", value.strip(), flags=re.IGNORECASE).strip()


def _sync_helpers(project_id: str, project_root: Path, source_doc: Path, music: Path, title: str) -> None:
    values = {
        "FABULOOM_ROOT": FABULOOM_ROOT,
        "EXPORT_ROOT": EXPORT_ROOT,
        "PROJECT_ID": project_id,
        "PROJECT_ROOT": project_root,
        "SOURCE_DOC": source_doc,
        "MUSIC": music,
        "REGISTRY": REGISTRY,
        "CHARACTER_REGISTRY_PATH": CHARACTER_REGISTRY_PATH,
        "VOICE_ID": VOICE_ID,
        "LANGUAGE": LANGUAGE,
        "TRANSITION_MS": TRANSITION_MS,
        "APPROVED_CHARACTER_ID": APPROVED_CHARACTER_ID,
        "SCENE_SPECS": SCENE_SPECS,
        "SOURCE_CHAPTER_TITLE": title,
        "HOST_INTRO": f"Saudações, Guardiões!\n\nHoje abrimos o capítulo {project_id.split('capitulo', 1)[-1].split('-', 1)[0]} de\nO Despertar dos Cristais:\n\n{_title_without_prefix(title, int(project_id.split('capitulo', 1)[-1].split('-', 1)[0]))}.\n\nA história continua.",
        "HOST_OUTRO": "E assim, Guardiões, a floresta revelou apenas o primeiro de seus segredos.\n\nA jornada continua no próximo capítulo.\n\nAté a próxima jornada!",
    }
    for key, value in values.items():
        setattr(base, key, value)


def _checkpoint(output_root: Path, *, stage: str, state: str = "completed", **details: object) -> None:
    path = output_root / "CHECKPOINT.json"
    previous: dict[str, object] = {}
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            previous = {}
    stages = dict(previous.get("stages") or {})
    stages[stage] = {"state": state, "updated_at": time.time(), **details}
    _write_json(output_root / "CHECKPOINT.json", {"format": "fabuloom.cinematic-checkpoint/0.1", "state": state, "current_stage": stage, "stages": stages})
    print(json.dumps({"stage": stage, "state": state, **details}, ensure_ascii=False), flush=True)


def _copy_scene_assets(project_root: Path) -> None:
    source_root = EXPORT_ROOT / "topazio-book1-capitulo4-cronicas" / "assets" / "generated"
    target_root = project_root / "assets" / "generated"
    target_root.mkdir(parents=True, exist_ok=True)
    for _, filename, _ in SCENE_SPECS:
        source = source_root / filename
        target = target_root / filename
        if not source.is_file():
            raise FileNotFoundError(f"approved environment plate unavailable: {source}")
        if not target.exists():
            shutil.copyfile(source, target)


def _capture(timeline_path: Path, frames_root: Path, *, orientation: str, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    edge = v1._find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{orientation}-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT)})
    server = subprocess.Popen([sys.executable, str(PRODUCT_ROOT / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)], cwd=str(PRODUCT_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url_root = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter2.html"
        v1._wait_for_http(url_root, 25)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        query = urlencode({"session": session, "timeline": f"/exports/{relative}", "fps": FPS, "chapterLabel": "CAPÍTULO 12 · A FLORESTA QUE ESCOLHE", "chapterNumber": "12", "captureMode": "fab-prod-004", "orientation": orientation})
        browser_size = "1080,1920" if orientation == "vertical" else "1920,1080"
        url = f"{url_root}?{query}"
        command = [edge, "--headless=new", "--disable-gpu", "--dump-dom", "--hide-scrollbars", f"--window-size={browser_size}", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout_seconds
        try:
            while not complete.exists() and not error.exists() and time.monotonic() < deadline:
                time.sleep(0.25)
            if error.exists():
                raise RuntimeError(error.read_text(encoding="utf-8"))
            if not complete.exists():
                raise TimeoutError(f"Canvas capture timed out: {session_dir}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            frames = v1._materialize_frames(session_dir, completion)
            if len(frames) != int(completion["frame_count"]):
                raise RuntimeError(f"capture incomplete: expected {completion['frame_count']}, found {len(frames)}")
            return session_dir, completion
        finally:
            if browser.poll() is None:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _write_srt(manifest: dict, path: Path) -> None:
    def stamp(ms: int) -> str:
        hours, remainder = divmod(ms, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, millis = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = [f"{index}\n{stamp(int(segment['start_ms']))} --> {stamp(int(segment['end_ms']))}\n{segment['text']}\n" for index, segment in enumerate(manifest["segments"], 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def _probe(path: Path) -> dict[str, object]:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _run_variant(project_root: Path, timeline_path: Path, mix_path: Path, manifest: dict, variant: str, *, port: int, timeout_seconds: float) -> dict[str, object]:
    video_path = project_root / "videos" / f"cronicas-capitulo12-a-floresta-que-escolhe-{variant}.mp4"
    if not video_path.is_file():
        frames_root = project_root / ".frames" / variant
        session, completion = _capture(timeline_path, frames_root, orientation=variant, port=port, timeout_seconds=timeout_seconds)
        v1.render_mp4(session, mix_path, video_path, int(manifest["duration_ms"]), overwrite=False)
        board = project_root / "captures" / f"chapter12-{variant}-frames.png"
        v1.frame_board(session, board, int(completion["frame_count"]), overwrite=False)
    probe = _probe(video_path)
    return {"variant": variant, "path": str(video_path), "probe": probe, "frame_board": str(project_root / "captures" / f"chapter12-{variant}-frames.png")}


def run(request_path: Path) -> dict[str, object]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    chapter = int(request["chapter"])
    output_root = _inside(Path(str(request["output_root"])), FABULOOM_ROOT)
    source_doc = _resolve_input(request.get("source_document"), root=FABULOOM_ROOT, default=SOURCE_DOC_DEFAULT)
    music = _resolve_input(request.get("music_asset_id"), root=FABULOOM_ROOT, default=DEFAULT_MUSIC)
    if not source_doc.is_file():
        raise FileNotFoundError(source_doc)
    if not music.is_file():
        raise FileNotFoundError(music)
    output_root.mkdir(parents=True, exist_ok=True)
    _checkpoint(output_root, stage="inputs", details={"source_document": str(source_doc), "music": str(music)})
    paragraphs, chapter_text, source_meta = _load_chapter(source_doc, chapter)
    extracted_title = _title_without_prefix(str(source_meta["title"]), chapter)
    requested_title = str(request.get("chapter_title") or extracted_title).strip()
    if requested_title.casefold() != extracted_title.casefold():
        raise ValueError(f"requested title does not match DOCX: {requested_title!r} != {extracted_title!r}")
    project_id = output_root.name
    _sync_helpers(project_id, output_root, source_doc, music, str(source_meta["title"]))
    for directory in (output_root / "audio", output_root / "timeline", output_root / "captures", output_root / "reports", output_root / "videos", output_root / ".frames", output_root / "assets" / "generated", output_root / "metadata", output_root / "source"):
        directory.mkdir(parents=True, exist_ok=True)
    _copy_scene_assets(output_root)
    source_meta["requested_title"] = requested_title
    source_meta["source_document_sha256"] = _sha256(source_doc)
    _write_json(output_root / "source" / "chapter-source.json", source_meta)
    (output_root / "source" / "chapter-text.txt").write_text(chapter_text + "\n", encoding="utf-8")
    _checkpoint(output_root, stage="source-validated", details=source_meta)
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    character_registry.require_approved(APPROVED_CHARACTER_ID)
    scene_registry = base.SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    library_hash = _sha256(library_path)
    manifest_path = output_root / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("metadata", {}).get("chapter_scope") != source_meta["title"]:
            raise ValueError("existing manifest belongs to a different source chapter")
    else:
        provider = KokoroTTSProvider(output_dir=output_root / "audio", allow_overwrite=False)
        try:
            intro_text = str(base.HOST_INTRO)
            outro_text = str(base.HOST_OUTRO)
            intro = base._synthesize_block(provider, intro_text, f"cap{chapter}-host-intro", output_root / "audio" / "host-intro", overwrite=False)
            story = base._synthesize_block(provider, chapter_text, f"cap{chapter}-story", output_root / "audio" / "story", overwrite=False)
            outro = base._synthesize_block(provider, outro_text, f"cap{chapter}-host-outro", output_root / "audio" / "host-outro", overwrite=False)
            manifest = base.compose_episode_manifest(intro, story, outro)
            _write_json(manifest_path, manifest)
            _write_json(output_root / "reports" / "tts-report.json", {"provider": provider.provider_id, "model": provider.model_id, "model_revision": provider.model_revision, "model_load_count": provider.model_load_count, "voice_id": VOICE_ID, "language": LANGUAGE})
        finally:
            provider.close()
    _checkpoint(output_root, stage="narration", details={"manifest": str(manifest_path), "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "voice_id": VOICE_ID, "language": LANGUAGE})
    timeline_path = output_root / "timeline" / "chapter12.json"
    timeline = {
        "format": "fabuloom.cronicas-cinematic-production/0.1",
        "title": f"Crônicas de Topázio — Livro 1 — {source_meta['title']}",
        "manifest": f"{project_id}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": str(source_doc.relative_to(FABULOOM_ROOT)).replace("\\", "/"),
        "source_paragraphs": list(range(int(source_meta["first_narrative_paragraph"]), int(source_meta["next_chapter_heading_paragraph"]))),
        "source_text_sha256": source_meta["text_sha256"],
        "music_asset": str(music.relative_to(FABULOOM_ROOT)).replace("\\", "/"),
        "scene_registry": "assets/scene-registry.json",
        "character_registry": "assets/character-registry.json",
        "library_asset_id": "santa-library-topazioverse-v1",
        "library_asset_sha256": library_hash,
        "narrator": "Santa V5",
        "narrator_character_registry_id": APPROVED_CHARACTER_ID,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "character_policy": {"approved_only": True, "draft_rendering": "blocked", "story_visuals": "environment_only"},
        "scenes": list(base.build_scene_schedule(manifest, library_path, library_hash)),
    }
    _write_json(timeline_path, timeline)
    _write_srt(manifest, output_root / "timeline" / "chapter12.srt")
    _checkpoint(output_root, stage="timeline", details={"timeline": str(timeline_path), "scenes": len(timeline["scenes"])})
    voice_path = output_root / "audio" / "chapter12-voice.wav"
    if not voice_path.is_file():
        base.compose_voice(manifest, voice_path)
    sfx_path = output_root / "audio" / "chapter12-sfx-bed.wav"
    if not sfx_path.is_file():
        v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop = output_root / "audio" / "chapter12-music-loop.wav"
    if not music_loop.is_file():
        v1.make_crossfaded_music_loop(music, music_loop, int(manifest["duration_ms"]), overwrite=False)
    mix_path = output_root / "audio" / "chapter12-mix.wav"
    if not mix_path.is_file():
        mix_audio_v2(voice_path, music_loop, sfx_path, mix_path, int(manifest["duration_ms"]))
    _checkpoint(output_root, stage="audio-mixed", details={"voice": str(voice_path), "mix": str(mix_path), "music": str(music), "sample_rate": 48000, "channels": 2, "ducking": "sidechain voice-priority", "limiter": 0.90})
    variants = tuple(request.get("output_variants") or ("horizontal", "vertical"))
    results = []
    for index, variant in enumerate(variants):
        if variant not in {"horizontal", "vertical"}:
            raise ValueError(f"unsupported output variant: {variant}")
        _checkpoint(output_root, stage=f"capture-{variant}", state="running", details={"variant": variant, "ordinal": index + 1, "total": len(variants)})
        result = _run_variant(output_root, timeline_path, mix_path, manifest, variant, port=8787 + index, timeout_seconds=float(request.get("capture_timeout", 2400)))
        results.append(result)
        _checkpoint(output_root, stage=f"capture-{variant}", state="completed", details=result)
        _checkpoint(output_root, stage=f"export-{variant}", details=result)
    visibility = {item["variant"]: {"status": "rendered", "frame_board": item["frame_board"]} for item in results}
    report = {
        "format": "fabuloom.cinematic-production-result/0.1",
        "status": "completed_pending_human_artistic_review",
        "chapter": chapter,
        "title": extracted_title,
        "source": source_meta,
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "word_phoneme_viseme_timing": "unavailable"},
        "music": {"path": str(music), "ducking": "sidechain voice-priority", "limiter": 0.90, "rights_review_required": True},
        "timeline": str(timeline_path),
        "outputs": results,
        "character_policy": {"approved_only": True, "approved_id": APPROVED_CHARACTER_ID, "draft_rendering": "blocked", "story_visuals": "environment_only"},
        "visibility": visibility,
        "artistic_review": "REVIEW_REQUIRED",
    }
    _write_json(output_root / "reports" / "technical-qa.json", report)
    _write_json(output_root / "reports" / "production-result.json", report)
    _checkpoint(output_root, stage="complete", state="completed", outputs=results)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args()
    run(args.request.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
