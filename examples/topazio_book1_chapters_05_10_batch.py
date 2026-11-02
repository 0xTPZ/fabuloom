"""Produce Crônicas de Topázio Book 1 chapters 05–10 in isolated checkpoints.

The DOCX is the editorial source of truth.  This runner reuses the proven
Chapter 2/3 Canvas and FFmpeg path, while keeping chapter configuration,
outputs, captures and checkpoints separate for every episode.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode

import topazio_book1_chapter3_cronicas_demo as chapter3
import topazio_book1_chapter1_cronicas_demo as v1

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.scene_assets import SceneAssetRegistry
from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
BATCH_ROOT = EXPORT_ROOT / "cronicas-book1-batch-05-10"
BATCH_STATUS_PATH = BATCH_ROOT / "BATCH-STATUS.json"
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "scene-registry.json"
CHARACTER_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "character-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
TRANSITION_MS = 900
APPROVED_CHARACTER_ID = "santa-v5-base"
RUNNER_VERSION = "mission-037-chapter-batch-v1"
QUESTION_PAUSE_MS = 320
SENTENCE_PAUSE_MS = 180
PARAGRAPH_PAUSE_MS = 350
MAX_CHARS = 360


# All entries point to environment/object plates already used by approved
# Book 1 productions.  No story character or draft asset is selected here.
ASSET_LIBRARY = {
    "c1:08-vulcao-osai.png": ("topazio-book1-capitulo1-cronicas", "08-vulcao-osai.png"),
    "c1:09-vila-incendio.png": ("topazio-book1-capitulo1-cronicas", "09-vila-incendio.png"),
    "c1v2:03-templo-gaia-crack.png": ("topazio-book1-capitulo1-cronicas-v2", "03-templo-gaia-crack.png"),
    "c1v2:06-temple-altar-v2.png": ("topazio-book1-capitulo1-cronicas-v2", "06-temple-altar-v2.png"),
    "c2:01-cave-threshold.png": ("topazio-book1-capitulo2-cronicas", "01-cave-threshold.png"),
    "c2:03-memory-fissure.png": ("topazio-book1-capitulo2-cronicas", "03-memory-fissure.png"),
    "c2:04-dawn-road.png": ("topazio-book1-capitulo2-cronicas", "04-dawn-road.png"),
    "c2:05-elemental-signs.png": ("topazio-book1-capitulo2-cronicas", "05-elemental-signs.png"),
    "c2:06-gaia-silence.png": ("topazio-book1-capitulo2-cronicas", "06-gaia-silence.png"),
    "c2:07-primordial-altar.png": ("topazio-book1-capitulo2-cronicas", "07-primordial-altar.png"),
    "c2:08-crystal-reflection.png": ("topazio-book1-capitulo2-cronicas", "08-crystal-reflection.png"),
    "c2:10-pillar-path.png": ("topazio-book1-capitulo2-cronicas", "10-pillar-path.png"),
    "c3:03-blue-call-mark.png": ("topazio-book1-capitulo3-cronicas", "03-blue-call-mark.png"),
    "c3:06-torches-ignite.png": ("topazio-book1-capitulo3-cronicas", "06-torches-ignite.png"),
    "c3:07-light-reflection.png": ("topazio-book1-capitulo3-cronicas", "07-light-reflection.png"),
    "c3:09-central-chamber.png": ("topazio-book1-capitulo3-cronicas", "09-central-chamber.png"),
    "c3:10-crystal-crack.png": ("topazio-book1-capitulo3-cronicas", "10-crystal-crack.png"),
    "c3:11-elemental-aftermath.png": ("topazio-book1-capitulo3-cronicas", "11-elemental-aftermath.png"),
    "c3:12-black-fissure.png": ("topazio-book1-capitulo3-cronicas", "12-black-fissure.png"),
    "c4:01-circular-scar.png": ("topazio-book1-capitulo4-cronicas", "01-circular-scar.png"),
    "c4:02-crystal-ring.png": ("topazio-book1-capitulo4-cronicas", "02-crystal-ring.png"),
    "c4:06-tower-fire-rings.png": ("topazio-book1-capitulo4-cronicas", "06-tower-fire-rings.png"),
    "c4:07-black-water-trident.png": ("topazio-book1-capitulo4-cronicas", "07-black-water-trident.png"),
    "c4:08-courtyard-aftermath.png": ("topazio-book1-capitulo4-cronicas", "08-courtyard-aftermath.png"),
    "c4:09-observatory-signals.png": ("topazio-book1-capitulo4-cronicas", "09-observatory-signals.png"),
    "c4:10-mask-scythe-parapet.png": ("topazio-book1-capitulo4-cronicas", "10-mask-scythe-parapet.png"),
    "c4:11-stone-map.png": ("topazio-book1-capitulo4-cronicas", "11-stone-map.png"),
    "c4:12-cracked-doorway.png": ("topazio-book1-capitulo4-cronicas", "12-cracked-doorway.png"),
    "c4:13-aerial-temple-storm.png": ("topazio-book1-capitulo4-cronicas", "13-aerial-temple-storm.png"),
}


def _plan(*keys: str) -> tuple[tuple[str, str], ...]:
    return tuple((key, camera) for key, camera in zip(keys, (
        "wide", "drift", "push", "lateral", "close", "orbit", "approach", "pulse", "tilt", "pull",
        "reveal", "return", "wide_alt", "push_alt", "lateral_alt", "close_alt", "orbit_alt", "approach_alt", "pulse_alt", "fade",
    ), strict=True))


CHAPTER_PLANS = {
    5: _plan(
        "c4:11-stone-map.png", "c2:05-elemental-signs.png", "c4:02-crystal-ring.png", "c3:03-blue-call-mark.png",
        "c2:10-pillar-path.png", "c4:09-observatory-signals.png", "c1v2:06-temple-altar-v2.png", "c4:01-circular-scar.png",
        "c2:08-crystal-reflection.png", "c4:11-stone-map.png", "c3:07-light-reflection.png", "c4:02-crystal-ring.png",
        "c2:07-primordial-altar.png", "c3:09-central-chamber.png", "c4:13-aerial-temple-storm.png", "c4:12-cracked-doorway.png",
        "c2:05-elemental-signs.png", "c4:09-observatory-signals.png", "c4:01-circular-scar.png", "c4:12-cracked-doorway.png",
    ),
    6: _plan(
        "c1:08-vulcao-osai.png", "c4:06-tower-fire-rings.png", "c3:11-elemental-aftermath.png", "c2:01-cave-threshold.png",
        "c1:08-vulcao-osai.png", "c4:13-aerial-temple-storm.png", "c2:07-primordial-altar.png", "c3:12-black-fissure.png",
        "c4:02-crystal-ring.png", "c1v2:03-templo-gaia-crack.png", "c4:06-tower-fire-rings.png", "c3:10-crystal-crack.png",
        "c1:08-vulcao-osai.png", "c4:07-black-water-trident.png", "c3:11-elemental-aftermath.png", "c2:01-cave-threshold.png",
        "c4:13-aerial-temple-storm.png", "c4:12-cracked-doorway.png", "c1:08-vulcao-osai.png", "c4:02-crystal-ring.png",
    ),
    7: _plan(
        "c1:08-vulcao-osai.png", "c4:06-tower-fire-rings.png", "c4:07-black-water-trident.png", "c3:11-elemental-aftermath.png",
        "c1:09-vila-incendio.png", "c4:08-courtyard-aftermath.png", "c2:07-primordial-altar.png", "c3:10-crystal-crack.png",
        "c4:06-tower-fire-rings.png", "c4:07-black-water-trident.png", "c1:08-vulcao-osai.png", "c3:12-black-fissure.png",
        "c4:08-courtyard-aftermath.png", "c2:05-elemental-signs.png", "c4:02-crystal-ring.png", "c3:11-elemental-aftermath.png",
        "c4:13-aerial-temple-storm.png", "c4:12-cracked-doorway.png", "c1:08-vulcao-osai.png", "c4:07-black-water-trident.png",
    ),
    8: _plan(
        "c3:03-blue-call-mark.png", "c3:07-light-reflection.png", "c4:09-observatory-signals.png", "c4:13-aerial-temple-storm.png",
        "c3:06-torches-ignite.png", "c2:05-elemental-signs.png", "c4:02-crystal-ring.png", "c3:12-black-fissure.png",
        "c4:09-observatory-signals.png", "c3:07-light-reflection.png", "c4:13-aerial-temple-storm.png", "c2:08-crystal-reflection.png",
        "c3:03-blue-call-mark.png", "c3:10-crystal-crack.png", "c4:02-crystal-ring.png", "c4:12-cracked-doorway.png",
        "c3:12-black-fissure.png", "c4:13-aerial-temple-storm.png", "c3:07-light-reflection.png", "c4:09-observatory-signals.png",
    ),
    9: _plan(
        "c4:10-mask-scythe-parapet.png", "c4:01-circular-scar.png", "c4:11-stone-map.png", "c3:12-black-fissure.png",
        "c2:03-memory-fissure.png", "c4:13-aerial-temple-storm.png", "c3:10-crystal-crack.png", "c4:12-cracked-doorway.png",
        "c4:10-mask-scythe-parapet.png", "c4:01-circular-scar.png", "c2:03-memory-fissure.png", "c3:12-black-fissure.png",
        "c4:11-stone-map.png", "c4:09-observatory-signals.png", "c3:10-crystal-crack.png", "c4:02-crystal-ring.png",
        "c4:13-aerial-temple-storm.png", "c4:10-mask-scythe-parapet.png", "c4:01-circular-scar.png", "c4:12-cracked-doorway.png",
    ),
    10: _plan(
        "c2:04-dawn-road.png", "c4:08-courtyard-aftermath.png", "c3:12-black-fissure.png", "c1:09-vila-incendio.png",
        "c4:07-black-water-trident.png", "c4:11-stone-map.png", "c2:06-gaia-silence.png", "c3:11-elemental-aftermath.png",
        "c4:13-aerial-temple-storm.png", "c2:04-dawn-road.png", "c4:08-courtyard-aftermath.png", "c3:12-black-fissure.png",
        "c4:07-black-water-trident.png", "c4:11-stone-map.png", "c2:06-gaia-silence.png", "c3:11-elemental-aftermath.png",
        "c4:13-aerial-temple-storm.png", "c4:12-cracked-doorway.png", "c2:04-dawn-road.png", "c4:11-stone-map.png",
    ),
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _update_batch_status(*, lot: str, chapter: int | None, stage: str, next_action: str, started_at: float | None = None) -> None:
    """Persist and print the current single-job state for long batch runs."""
    index = {}
    index_path = BATCH_ROOT / "BATCH-INDEX.json"
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    chapters = index.get("chapters", [])
    completed = [item["chapter"] for item in chapters if item.get("status") == "DONE"]
    failures = [{"chapter": item.get("chapter"), "error": item.get("error")} for item in chapters if item.get("status") == "FAILED"]
    status = {
        "format": "fabuloom.cronicas-batch-status/0.1",
        "state": "RUNNING",
        "lot": lot,
        "chapter": chapter,
        "stage": stage,
        "completed_chapters": sorted(completed),
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3) if started_at is not None else None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "next_action": next_action,
    }
    _write_json(BATCH_STATUS_PATH, status)
    print(
        f"[MISSÃO 037] lote={lot} capítulo={chapter or '-'} etapa={stage} "
        f"concluídos={status['completed_chapters']} falhas={len(failures)} "
        f"tempo={status['elapsed_seconds'] if status['elapsed_seconds'] is not None else '-'}s "
        f"próxima={next_action}",
        flush=True,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _chapter_heading(text: str, number: int) -> bool:
    return bool(re.match(rf"^Cap[ií]tulo\s+{number}(?:\s*[—:-]|$)", text.strip(), re.IGNORECASE))


def _load_docx_paragraphs(path: Path) -> list[str]:
    from docx import Document
    return [paragraph.text for paragraph in Document(path).paragraphs]


def preflight_source(path: Path = SOURCE_DOC) -> dict[int, dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    paragraphs = _load_docx_paragraphs(path)
    headings: dict[int, tuple[int, str]] = {}
    for number in range(5, 12):
        matches = [(index, value.strip()) for index, value in enumerate(paragraphs) if _chapter_heading(value, number)]
        if len(matches) != 1:
            raise ValueError(f"SOURCE_BOUNDARY_INVALID: chapter {number} matches={matches}")
        headings[number] = matches[0]
    chapters: dict[int, dict] = {}
    for number in range(5, 11):
        start, title = headings[number]
        next_start, _ = headings[number + 1]
        if next_start <= start + 1:
            raise ValueError(f"SOURCE_BOUNDARY_INVALID: empty chapter {number}")
        selected = tuple(value.strip() for value in paragraphs[start + 1:next_start] if value.strip())
        text = "\n\n".join(selected)
        if not text:
            raise ValueError(f"SOURCE_BOUNDARY_INVALID: empty text chapter {number}")
        chapters[number] = {
            "number": number,
            "title": title,
            "heading_paragraph": start,
            "first_narrative_paragraph": start + 1,
            "last_narrative_paragraph": next_start - 1,
            "end_exclusive": next_start,
            "next_chapter_heading_paragraph": next_start,
            "raw_paragraph_count": next_start - start - 1,
            "paragraph_indices": [index for index in range(start + 1, next_start) if paragraphs[index].strip()],
            "paragraph_count": len(selected),
            "word_count": len(re.findall(r"\S+", text)),
            "text_characters": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text": text,
            "paragraphs": selected,
        }
    return {"source_doc": str(path), "source_doc_sha256": _sha256(path), "paragraph_count": len(paragraphs), "chapters": chapters}


def _host_texts(number: int, title: str) -> tuple[str, str]:
    intro = (
        "Saudações, Guardiões!\n\n"
        f"Hoje abrimos mais uma página de O Despertar dos Cristais.\n"
        f"O capítulo {number} se chama:\n\n{title}.\n\n"
        "Sentem-se comigo na biblioteca, e vamos entrar nesta história juntos."
    )
    outro = (
        f"E assim encerramos o capítulo {number}, {title}.\n\n"
        "Obrigado por me acompanharem, Guardiões.\n"
        "A história continua no próximo capítulo.\n\n"
        "Até a próxima jornada!"
    )
    return intro, outro


def _set_globals(config: dict) -> None:
    base = chapter3.base
    for module in (chapter3, base):
        module.FABULOOM_ROOT = FABULOOM_ROOT
        module.EXPORT_ROOT = EXPORT_ROOT
        module.PROJECT_ID = config["project_id"]
        module.PROJECT_ROOT = config["project_root"]
        module.SOURCE_DOC = SOURCE_DOC
        module.MUSIC = MUSIC
        module.REGISTRY = REGISTRY
        module.CHARACTER_REGISTRY_PATH = CHARACTER_REGISTRY_PATH
        module.VOICE_ID = VOICE_ID
        module.LANGUAGE = LANGUAGE
        module.TRANSITION_MS = TRANSITION_MS
        module.APPROVED_CHARACTER_ID = APPROVED_CHARACTER_ID
        module.SCENE_SPECS = config["scene_specs"]
        module.SOURCE_PARAGRAPH_START = config["source"]["first_narrative_paragraph"]
        module.SOURCE_PARAGRAPH_END_EXCLUSIVE = config["source"]["end_exclusive"]
        module.SOURCE_CHAPTER_TITLE = config["source"]["title"]
    chapter3.HOST_INTRO = config["host_intro"]
    chapter3.HOST_OUTRO = config["host_outro"]
    base.HOST_INTRO = config["host_intro"]
    base.HOST_OUTRO = config["host_outro"]


def _make_config(number: int, source: dict, batch: dict) -> dict:
    project_id = f"topazio-book1-capitulo{number:02d}-cronicas-037"
    project_root = BATCH_ROOT / f"capitulo-{number:02d}"
    asset_specs = []
    for index, (key, camera) in enumerate(CHAPTER_PLANS[number], 1):
        source_project, source_name = ASSET_LIBRARY[key]
        asset_specs.append({"id": f"shot-{index:03d}", "key": key, "source_project": source_project, "source_name": source_name, "filename": f"asset-{index:03d}.png", "camera": camera})
    scene_specs = tuple((item["id"], item["filename"], item["camera"]) for item in asset_specs)
    title = source["title"]
    host_intro, host_outro = _host_texts(number, title)
    return {
        "number": number,
        "batch": batch,
        "project_id": project_id,
        "project_root": project_root,
        "source": source,
        "host_intro": host_intro,
        "host_outro": host_outro,
        "asset_specs": asset_specs,
        "scene_specs": scene_specs,
    }


def _copy_assets(config: dict) -> None:
    target = config["project_root"] / "assets" / "generated"
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in config["asset_specs"]:
        source = EXPORT_ROOT / item["source_project"] / "assets" / "generated" / item["source_name"]
        if not source.is_file():
            raise FileNotFoundError(f"approved environment plate missing: {source}")
        destination = target / item["filename"]
        if not destination.is_file() or _sha256(destination) != _sha256(source):
            shutil.copy2(source, destination)
        copied.append({**item, "source_path": str(source), "destination": str(destination), "sha256": _sha256(destination)})
    _write_json(config["project_root"] / "assets" / "asset-provenance.json", {"policy": "approved_environment_plates_only", "assets": copied})


def _fingerprint(config: dict) -> str:
    payload = {
        "runner": RUNNER_VERSION,
        "source_doc_sha256": config["batch"]["source_doc_sha256"],
        "source": {key: value for key, value in config["source"].items() if key not in {"text", "paragraphs"}},
        "host_intro": config["host_intro"],
        "host_outro": config["host_outro"],
        "voice": VOICE_ID,
        "language": LANGUAGE,
        "segmentation": {"max_chars": MAX_CHARS, "sentence_pause_ms": SENTENCE_PAUSE_MS, "question_pause_ms": QUESTION_PAUSE_MS, "paragraph_pause_ms": PARAGRAPH_PAUSE_MS},
        "scene_specs": config["scene_specs"],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _load_checkpoints(root: Path) -> dict:
    path = root / "checkpoints.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"fingerprint": None, "stages": {}}


def _stage_done(root: Path, stage: str, fingerprint: str, required: tuple[Path, ...]) -> bool:
    checkpoints = _load_checkpoints(root)
    return checkpoints.get("fingerprint") == fingerprint and checkpoints.get("stages", {}).get(stage, {}).get("status") == "DONE" and all(path.is_file() for path in required)


def _mark_stage(root: Path, stage: str, fingerprint: str, artifacts: tuple[Path, ...], **extra: object) -> None:
    checkpoints = _load_checkpoints(root)
    checkpoints["fingerprint"] = fingerprint
    checkpoints.setdefault("stages", {})[stage] = {"status": "DONE", "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "artifacts": [str(path) for path in artifacts], **extra}
    _write_json(root / "checkpoints.json", checkpoints)


def _synthesize_block(provider: KokoroTTSProvider, text: str, narration_id: str, output_dir: Path, *, overwrite: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    run = synthesize_narration(
        provider, text, narration_id=narration_id, manifest_id=narration_id,
        timeline_id=f"{narration_id}-timeline", language=LANGUAGE, voice_id=VOICE_ID,
        output_dir=output_dir, max_chars=MAX_CHARS,
        sentence_pause_ms=SENTENCE_PAUSE_MS, question_pause_ms=QUESTION_PAUSE_MS,
        paragraph_pause_ms=PARAGRAPH_PAUSE_MS,
    )
    manifest = json.loads(serialize_manifest(run.manifest))
    manifest["metadata"].update({
        "editorial_block": narration_id,
        "speed": 1.0,
        "question_pause_ms": QUESTION_PAUSE_MS,
        "expressive_question_intonation": "not_verified",
    })
    _write_json(manifest_path, manifest)
    return manifest


def _compose_manifest(config: dict, intro: dict, story: dict, outro: dict) -> dict:
    base = chapter3.base
    base.PROJECT_ID = config["project_id"]
    base.SOURCE_PARAGRAPH_START = config["source"]["first_narrative_paragraph"]
    base.SOURCE_PARAGRAPH_END_EXCLUSIVE = config["source"]["end_exclusive"]
    base.SOURCE_CHAPTER_TITLE = config["source"]["title"]
    base.HOST_INTRO = config["host_intro"]
    base.HOST_OUTRO = config["host_outro"]
    manifest = base.compose_episode_manifest(intro, story, outro)
    manifest["metadata"].update({
        "source_doc_sha256": config["batch"]["source_doc_sha256"],
        "source_paragraph_indices": config["source"]["paragraph_indices"],
        "question_pause_ms": QUESTION_PAUSE_MS,
        "sentence_pause_ms": SENTENCE_PAUSE_MS,
        "paragraph_pause_ms": PARAGRAPH_PAUSE_MS,
        "tts_speed": 1.0,
        "expressive_question_intonation": "not_verified",
        "host_location": "santa-library-topazioverse-v1",
        "santa_visibility_policy": "all_scenes_medallion",
    })
    return manifest


def _validate_story_coverage(config: dict, manifest: dict) -> None:
    segments = [item for item in manifest["segments"] if item.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]
    actual = _normalized(" ".join(segment["text"] for segment in segments))
    expected = _normalized(config["source"]["text"])
    if actual != expected:
        raise ValueError(f"story text coverage mismatch for chapter {config['number']}")


def _timeline(config: dict, manifest: dict, library_path: Path, library_sha256: str) -> dict:
    base = chapter3.base
    scenes = list(base.build_scene_schedule(manifest, library_path, library_sha256))
    for scene in scenes:
        scene["character_registry_id"] = APPROVED_CHARACTER_ID
        scene["library_asset_id"] = "santa-library-topazioverse-v1"
        scene["library_sha256"] = library_sha256
        if scene["kind"] == "story":
            scene["character_visual_policy"] = "Santa V5 medallion only; no story characters"
            scene["environment_only"] = True
    return {
        "format": "fabuloom.topazioverse-chapter/0.2",
        "title": f"Crônicas de Topázio — Livro 1 — Capítulo {config['number']}: {config['source']['title'].split('—', 1)[-1].strip()}",
        "manifest": f"{config['project_id']}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_doc_sha256": config["batch"]["source_doc_sha256"],
        "source_paragraphs": config["source"]["paragraph_indices"],
        "source_paragraph_end_separator": config["source"]["end_exclusive"] - 1,
        "next_chapter_heading_paragraph": config["source"]["next_chapter_heading_paragraph"],
        "source_text_sha256": config["source"]["text_sha256"],
        "source_word_count": config["source"]["word_count"],
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "music_rights": "pending_owner_confirmation",
        "scene_registry": "assets/scene-registry.json",
        "character_registry": "assets/character-registry.json",
        "library_asset_id": "santa-library-topazioverse-v1",
        "library_asset_sha256": library_sha256,
        "narrator": "Santa V5",
        "narrator_character_registry_id": APPROVED_CHARACTER_ID,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "question_pause_ms": QUESTION_PAUSE_MS,
        "expressive_question_intonation": "not_verified",
        "character_policy": {"approved_only": True, "draft_rendering": "blocked", "story_visuals": "environment_only"},
        "scenes": scenes,
    }


def _capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float, chapter_number: int, project_id: str) -> tuple[Path, dict]:
    edge = v1._find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{chapter_number:02d}-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT)})
    server = subprocess.Popen([
        sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"),
        "--port", str(port), "--capture-dir", str(frames_root),
    ], cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        url_root = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter2.html"
        v1._wait_for_http(url_root, 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        query = urlencode({"session": session, "timeline": f"/exports/{relative}", "fps": FPS, "chapterLabel": f"CAPÍTULO {chapter_number:02d}", "chapterNumber": str(chapter_number), "captureMode": project_id})
        url = f"{url_root}?{query}"
        command = [edge, "--headless=new", "--disable-gpu", "--disable-gpu-compositing", "--force-device-scale-factor=1", "--disable-background-networking", "--dump-dom", "--hide-scrollbars", "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout_seconds
        while not complete.exists() and not error.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        if error.exists():
            raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists():
            raise TimeoutError(f"Canvas capture did not complete: {session_dir}")
        completion = json.loads(complete.read_text(encoding="utf-8"))
        frames = v1._materialize_frames(session_dir, completion)
        if len(frames) != int(completion["frame_count"]):
            raise RuntimeError(f"capture incomplete: expected {completion['frame_count']} frames, found {len(frames)}")
        return session_dir, completion
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _write_srt(manifest: dict, path: Path) -> None:
    def stamp(ms: int) -> str:
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = [f"{index}\n{stamp(int(segment['start_ms']))} --> {stamp(int(segment['end_ms']))}\n{segment['text']}\n" for index, segment in enumerate(manifest["segments"], 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def _decode_ok(video: Path) -> bool:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0", "-f", "null", "NUL"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg decode failed for {video}: {result.stderr[-2000:]}")
    return True


def _blackdetect(video: Path) -> list[str]:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(video), "-vf", "blackdetect=d=0.10:pix_th=0.10", "-an", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    return [line.strip() for line in (result.stderr or "").splitlines() if "black_start:" in line]


def _copy_visibility_samples(project_root: Path, visibility: dict) -> dict:
    destination = project_root / "captures" / "scene-samples"
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in visibility.get("samples", []):
        source = Path(item["rendered_frame"])
        target = destination / f"{item['scene_id']}.jpg"
        shutil.copy2(source, target)
        copied.append({**item, "rendered_frame": str(target)})
    return {**visibility, "samples": copied}


def _write_reports(config: dict, manifest: dict, timeline: dict, video_probe: dict, mix_probe: dict, visibility: dict, *, processing_seconds: float, black_intervals: list[str], decode_ok: bool, source_snapshot: dict) -> dict:
    root = config["project_root"]
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    questions = [
        {"text": segment["text"], "start_ms": segment["start_ms"], "end_ms": segment["end_ms"], "block": segment.get("metadata", {}).get("editorial_block")}
        for segment in manifest["segments"] if "?" in segment["text"]
    ]
    video_stream = next(stream for stream in video_probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in video_probe["streams"] if stream["codec_type"] == "audio")
    srt_path = root / "timeline" / f"capitulo{config['number']:02d}.srt"
    report = {
        "format": "fabuloom.cronicas-chapter-037/0.1",
        "chapter": config["number"],
        "title": config["source"]["title"],
        "state": "completed_pending_human_artistic_review",
        "video": str(root / "videos" / f"fabuloom-cronicas-de-topazio-livro1-capitulo{config['number']:02d}.mp4"),
        "manifest": str(root / "manifest.json"),
        "timeline": str(root / "timeline" / f"capitulo{config['number']:02d}.json"),
        "srt": str(srt_path),
        "frame_board": str(root / "captures" / f"chapter{config['number']:02d}-board.png"),
        "duration_ms": manifest["duration_ms"],
        "segments": len(manifest["segments"]),
        "story_segments": len([item for item in manifest["segments"] if item.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]),
        "scenes": len(timeline["scenes"]),
        "source": {key: value for key, value in config["source"].items() if key not in {"text", "paragraphs"}},
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "speed": 1.0, "question_pause_ms": QUESTION_PAUSE_MS},
        "expressive_question_intonation": "not_verified",
        "question_samples": questions,
        "video_probe": video_probe,
        "audio_probe": mix_probe,
        "validation": {
            "source_coverage": True,
            "srt_segment_count": len(srt_path.read_text(encoding="utf-8").strip().split("\n\n")),
            "ffmpeg_decode": decode_ok,
            "blackdetect_intervals": black_intervals,
            "dimensions": [int(video_stream["width"]), int(video_stream["height"])],
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
            "audio_sample_rate": audio_stream.get("sample_rate"),
            "audio_channels": audio_stream.get("channels"),
            "santa_visibility": visibility.get("passed", False),
            "draft_characters": "blocked",
        },
        "approved_character_id": APPROVED_CHARACTER_ID,
        "library_asset_id": "santa-library-topazioverse-v1",
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "music_rights": "pending_owner_confirmation",
        "processing_seconds": round(processing_seconds, 3),
        "previous_chapters_snapshot": source_snapshot,
    }
    _write_json(reports / "episode-result.json", report)
    _write_json(reports / "santa-visibility-report.json", visibility)
    _write_json(reports / "source-boundary.json", {key: value for key, value in config["source"].items() if key not in {"text", "paragraphs"}})
    _write_json(reports / "validation.json", report["validation"])
    (reports / "technical-report.md").write_text(
        f"# Crônicas de Topázio — Livro 1 — Capítulo {config['number']:02d}\n\n"
        f"- Título-fonte: `{config['source']['title']}`\n- Parágrafos não vazios: `{config['source']['paragraph_count']}`; palavras: `{config['source']['word_count']}`; hash: `{config['source']['text_sha256']}`\n"
        f"- Segmentos medidos: `{len(manifest['segments'])}`; planos: `{len(timeline['scenes'])}`; duração: `{manifest['duration_ms']} ms`\n"
        f"- Vídeo: `{video_stream['width']}×{video_stream['height']}`, `{video_stream.get('codec_name')}`, `{video_stream.get('r_frame_rate')}`; áudio: `{audio_stream.get('codec_name')}`, `{audio_stream.get('sample_rate')} Hz`, `{audio_stream.get('channels')} canais`\n"
        f"- Processamento: `{processing_seconds:.2f} s`; decode: `{decode_ok}`; blackdetect: `{black_intervals}`\n"
        f"- Santa V5: `santa-v5-base`, biblioteca `santa-library-topazioverse-v1`, medalhão em todas as cenas; DRAFT bloqueado.\n"
        "- Voz: `pm_santa` / `pt-BR`, velocidade `1.0`. A segmentação preserva pontuação, usa pausa de pergunta de `320 ms` e não inventa alinhamento de palavra/fonema/visema.\n"
        "- Entonação interrogativa: `not_verified`; a Missão 032 não comprovou controle acústico de emoção/pitch.\n"
        "- Música original preservada, sem alteração de tom/velocidade; ducking voz→música; direitos comerciais Suno pendentes.\n"
        "- Aprovação artística e audição humana continuam pendentes.\n",
        encoding="utf-8",
    )
    (reports / "voice-improvements.md").write_text(
        "# Direção vocal e segmentação\n\n"
        f"- Voz preservada: `{VOICE_ID}` / `{LANGUAGE}`; velocidade fixa `1.0`.\n- Segmentação: `max_chars={MAX_CHARS}`, pausa de frase `{SENTENCE_PAUSE_MS} ms`, pergunta `{QUESTION_PAUSE_MS} ms`, parágrafo `{PARAGRAPH_PAUSE_MS} ms`.\n"
        "- A pausa de pergunta é a melhoria mensurável reaproveitada da Missão 032; não há claim de pitch, SSML, emoção ou alinhamento fonético.\n"
        "- A entonação expressiva foi registrada como `not_verified`; as amostras e o resultado precisam de audição humana.\n"
        f"- Amostras temporais de perguntas encontradas: `{len(questions)}`; detalhes no `episode-result.json`.\n",
        encoding="utf-8",
    )
    (reports / "mix-report.md").write_text(
        f"# Mixagem\n\n- Música: `{MUSIC}`; origem Suno; sem alteração de pitch/velocidade.\n- Ducking: sidechain voz→música, voice-priority; limiter final herdado do pipeline aprovado.\n- Direitos comerciais: `pending_owner_confirmation`.\n- Voz: `pm_santa` / `pt-BR`.\n",
        encoding="utf-8",
    )
    return report


def _write_metadata(config: dict, manifest: dict) -> None:
    duration_seconds = int(manifest["duration_ms"] // 1000)
    minutes, seconds = divmod(duration_seconds, 60)
    title = f"Crônicas de Topázio — Livro 1 | Capítulo {config['number']}: {config['source']['title']}"
    payload = {
        "title": title,
        "description": f"Capítulo {config['number']} de O Despertar dos Cristais, narrado por Santa V5.\n\nDuração: {minutes:02d}:{seconds:02d}.",
        "hashtags": ["#CronicasDeTopazio", "#Topazioverse", "#Fantasia", "#Narracao"],
        "chapter": {"number": config["number"], "title": config["source"]["title"], "book": "Livro 1 — O Despertar dos Cristais"},
        "duration_ms": manifest["duration_ms"],
        "voice": "Santa V5 / Kokoro pm_santa / pt-BR",
        "music": "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "publication_pending": ["human artistic approval", "human listening review", "Suno commercial rights confirmation"],
        "published": False,
    }
    _write_json(config["project_root"] / "metadata" / "youtube-metadata.json", payload)


def _previous_snapshot() -> dict:
    snapshot = {}
    for number in range(1, 5):
        path = EXPORT_ROOT / f"topazio-book1-capitulo{number}-cronicas" / "videos" / f"fabuloom-cronicas-de-topazio-livro1-capitulo{number}.mp4"
        if path.is_file():
            snapshot[str(number)] = {"path": str(path), "sha256": _sha256(path), "size": path.stat().st_size}
    return snapshot


def _prepare_chapter(config: dict) -> None:
    root = config["project_root"]
    for name in ("audio", "timeline", "captures", "reports", "videos", ".frames", "metadata"):
        (root / name).mkdir(parents=True, exist_ok=True)
    _copy_assets(config)
    _write_json(root / "source-boundary.json", {key: value for key, value in config["source"].items() if key not in {"text", "paragraphs"}})
    (root / "timeline" / f"capitulo{config['number']:02d}-source-excerpt.txt").write_text(config["source"]["text"] + "\n", encoding="utf-8")


def produce_chapter(config: dict, *, port: int, timeout_seconds: float, overwrite: bool, source_snapshot: dict) -> dict:
    _set_globals(config)
    root = config["project_root"]
    _prepare_chapter(config)
    fingerprint = _fingerprint(config)
    manifest_path = root / "manifest.json"
    timeline_path = root / "timeline" / f"capitulo{config['number']:02d}.json"
    video_path = root / "videos" / f"fabuloom-cronicas-de-topazio-livro1-capitulo{config['number']:02d}.mp4"
    board_path = root / "captures" / f"chapter{config['number']:02d}-board.png"
    if not overwrite and _stage_done(root, "QA", fingerprint, (manifest_path, timeline_path, video_path, board_path, root / "reports" / "episode-result.json")):
        return json.loads((root / "reports" / "episode-result.json").read_text(encoding="utf-8"))
    started = time.perf_counter()
    lot = config.get("batch_label", "-")
    def stage(name: str, next_action: str) -> None:
        _update_batch_status(lot=lot, chapter=config["number"], stage=name, next_action=next_action, started_at=started)

    stage("SOURCE_OK", "validar ou reutilizar storyboard")
    scene_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    library_sha256 = _sha256(library_path)
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    character_registry.require_approved(APPROVED_CHARACTER_ID)
    required_assets = tuple(root / "assets" / "generated" / item["filename"] for item in config["asset_specs"])
    if not _stage_done(root, "SOURCE_OK", fingerprint, (root / "source-boundary.json", root / "timeline" / f"capitulo{config['number']:02d}-source-excerpt.txt")):
        _mark_stage(root, "SOURCE_OK", fingerprint, (root / "source-boundary.json",), title=config["source"]["title"])
    stage("STORYBOARD_OK", "sintetizar ou reutilizar áudio Kokoro")
    if not _stage_done(root, "STORYBOARD_OK", fingerprint, required_assets):
        _mark_stage(root, "STORYBOARD_OK", fingerprint, required_assets, asset_count=len(required_assets), policy="approved_environment_plates_only")
    stage("AUDIO_OK", "compor timeline e SRT")
    if not _stage_done(root, "AUDIO_OK", fingerprint, (manifest_path,)):
        provider = KokoroTTSProvider(output_dir=root / "audio", allow_overwrite=overwrite)
        try:
            intro, outro = _host_texts(config["number"], config["source"]["title"])
            intro_manifest = _synthesize_block(provider, intro, f"{config['project_id']}-host-intro", root / "audio" / "host-intro", overwrite=overwrite)
            story_manifest = _synthesize_block(provider, config["source"]["text"], f"{config['project_id']}-story", root / "audio" / "story", overwrite=overwrite)
            outro_manifest = _synthesize_block(provider, outro, f"{config['project_id']}-host-outro", root / "audio" / "host-outro", overwrite=overwrite)
            manifest = _compose_manifest(config, intro_manifest, story_manifest, outro_manifest)
            _validate_story_coverage(config, manifest)
            _write_json(manifest_path, manifest)
            _mark_stage(root, "AUDIO_OK", fingerprint, (manifest_path,), segments=len(manifest["segments"]), duration_ms=manifest["duration_ms"], model_revision=manifest["segments"][0].get("metadata", {}).get("model_revision"))
        except (TTSError, NarrationSynthesisError):
            raise
        finally:
            provider.close()
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stage("TIMELINE_OK", "mixar voz, música e SFX")
    if not timeline_path.is_file() or not _stage_done(root, "TIMELINE_OK", fingerprint, (timeline_path, root / "timeline" / f"capitulo{config['number']:02d}.srt")):
        timeline = _timeline(config, manifest, library_path, library_sha256)
        _write_json(timeline_path, timeline)
        _write_srt(manifest, root / "timeline" / f"capitulo{config['number']:02d}.srt")
        _write_json(root / "storyboard.json", {"chapter": config["number"], "title": config["source"]["title"], "scenes": timeline["scenes"], "assets": config["asset_specs"]})
        _mark_stage(root, "TIMELINE_OK", fingerprint, (timeline_path, root / "timeline" / f"capitulo{config['number']:02d}.srt"), scene_count=len(timeline["scenes"]))
    else:
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    voice_path = root / "audio" / f"{config['project_id']}-voice.wav"
    sfx_path = root / "audio" / f"{config['project_id']}-sfx-bed.wav"
    music_loop_path = root / "audio" / f"{config['project_id']}-music-loop.wav"
    mix_path = root / "audio" / f"{config['project_id']}-mix.wav"
    stage("MIX_OK", "capturar Canvas em um único processo")
    if not _stage_done(root, "MIX_OK", fingerprint, (voice_path, sfx_path, music_loop_path, mix_path)):
        sample_rate = chapter3.base.compose_voice(manifest, voice_path)
        v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
        v1.make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=overwrite)
        chapter3.mix_audio_v2(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]))
        _mark_stage(root, "MIX_OK", fingerprint, (voice_path, sfx_path, music_loop_path, mix_path), sample_rate=sample_rate)
    stage("CAPTURE_OK", "renderizar MP4 e prancha")
    if not _stage_done(root, "CAPTURE_OK", fingerprint, (root / ".frames" / "latest-complete.json")):
        session_dir, completion = _capture_frames(timeline_path, root / ".frames", port=port, timeout_seconds=timeout_seconds, chapter_number=config["number"], project_id=config["project_id"])
        shutil.copy2(session_dir / "complete.json", root / ".frames" / "latest-complete.json")
        _write_json(root / ".frames" / "latest-session.json", {"session_dir": str(session_dir), "completion": completion})
        _mark_stage(root, "CAPTURE_OK", fingerprint, (root / ".frames" / "latest-complete.json",), frame_count=completion["frame_count"], session_dir=str(session_dir))
    session_info = json.loads((root / ".frames" / "latest-session.json").read_text(encoding="utf-8"))
    session_dir = Path(session_info["session_dir"])
    completion = session_info["completion"]
    stage("RENDER_OK", "executar QA técnico e visibilidade de Santa")
    if not _stage_done(root, "RENDER_OK", fingerprint, (video_path, board_path)):
        v1.render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
        v1.frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
        _mark_stage(root, "RENDER_OK", fingerprint, (video_path, board_path), frame_count=completion["frame_count"])
    video_probe = v1.probe(video_path)
    mix_probe = v1.probe(mix_path)
    visibility = chapter3.audit_santa_visibility(session_dir, timeline["scenes"], frame_count=int(completion["frame_count"]))
    visibility = _copy_visibility_samples(root, visibility)
    black_intervals = _blackdetect(video_path)
    decode_ok = _decode_ok(video_path)
    stage("QA_OK", "registrar capítulo e avançar em sequência")
    report = _write_reports(config, manifest, timeline, video_probe, mix_probe, visibility, processing_seconds=time.perf_counter() - started, black_intervals=black_intervals, decode_ok=decode_ok, source_snapshot=source_snapshot)
    _write_metadata(config, manifest)
    if not report["validation"]["santa_visibility"] or black_intervals:
        raise RuntimeError(f"QA failed for chapter {config['number']}: Santa or blackdetect gate")
    _mark_stage(root, "QA", fingerprint, (manifest_path, timeline_path, video_path, board_path, root / "reports" / "episode-result.json"), santa_visibility=True, blackdetect_intervals=black_intervals)
    shutil.rmtree(session_dir, ignore_errors=True)
    _update_batch_status(lot=lot, chapter=config["number"], stage="QA_OK", next_action="registrar capítulo concluído", started_at=started)
    return report


def _write_batch_report(index: dict) -> None:
    lines = ["# Missão 037 — Crônicas de Topázio, capítulos 05–10", "", f"- Estado: `{index['state']}`", f"- Fonte DOCX: `{index['source_doc']}`", f"- Hash DOCX: `{index['source_doc_sha256']}`", "", "## Capítulos", ""]
    for item in index["chapters"]:
        lines.append(f"- Capítulo {item['chapter']:02d}: `{item['status']}` — `{item.get('title', '')}` — duração `{item.get('duration_ms', 'n/a')} ms`; vídeo `{item.get('video', 'n/a')}`")
    if index.get("batch_summaries"):
        lines.extend(["", "## Resumos dos lotes", ""])
        for summary in index["batch_summaries"]:
            lines.append(f"- Lote {summary['lot']}: `{summary['state']}`, duração `{summary['elapsed_seconds']} s`, capítulos `{summary['chapters']}`, arquivos `{summary['files']}`, validações `{summary['validations']}`")
    lines.extend(["", "## Política", "", "- Santa V5 `santa-v5-base` e `santa-library-topazioverse-v1` são obrigatórios em abertura, narrativa e encerramento.", "- Voz `pm_santa` / `pt-BR`; segmentação medida, pergunta `320 ms`, velocidade `1.0`; entonação expressiva `not_verified`.", "- Story visuals usam somente placas ambientais aprovadas; personagens DRAFT bloqueados.", "- Direitos comerciais da música Suno e aprovação artística/auditiva humana continuam pendentes."])
    (BATCH_ROOT / "BATCH-REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_batch(*, overwrite: bool = False, port: int = 8790, capture_timeout: float = 2400) -> dict:
    batch = preflight_source(SOURCE_DOC)
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    source_snapshot = _previous_snapshot()
    configs = [_make_config(number, batch["chapters"][number], batch) for number in range(5, 11)]
    index = {"format": "fabuloom.cronicas-book1-batch/0.1", "runner_version": RUNNER_VERSION, "source_doc": str(SOURCE_DOC), "source_doc_sha256": batch["source_doc_sha256"], "chapters": [], "state": "RUNNING", "previous_chapters_snapshot": source_snapshot}
    _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
    batch_started = time.perf_counter()
    for batch_name, numbers in (("A", (5, 6)), ("B", (7, 8)), ("C", (9, 10))):
        lot_started = time.perf_counter()
        index.setdefault("batch_summaries", [])
        _update_batch_status(lot=batch_name, chapter=None, stage=f"LOTE_{batch_name}_START", next_action=f"iniciar capítulo {numbers[0]:02d}", started_at=batch_started)
        for number in numbers:
            config = next(item for item in configs if item["number"] == number)
            config["batch_label"] = batch_name
            entry = {"chapter": number, "batch": batch_name, "title": config["source"]["title"], "status": "RUNNING", "project_root": str(config["project_root"])}
            index["chapters"] = [item for item in index["chapters"] if item["chapter"] != number] + [entry]
            _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
            _write_batch_report(index)
            _update_batch_status(lot=batch_name, chapter=number, stage="START", next_action="executar preflight do capítulo", started_at=batch_started)
            try:
                result = produce_chapter(config, port=port + number, timeout_seconds=capture_timeout, overwrite=overwrite, source_snapshot=source_snapshot)
                entry.update({"status": "DONE", "title": result["title"], "duration_ms": result["duration_ms"], "segments": result["segments"], "scenes": result["scenes"], "video": result["video"], "manifest": result["manifest"], "srt": result["srt"], "frame_board": result["frame_board"], "validation": result["validation"], "expressive_question_intonation": result["expressive_question_intonation"]})
            except Exception as exc:
                entry.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
                index["chapters"] = [item for item in index["chapters"] if item["chapter"] != number] + [entry]
                _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
                _write_batch_report(index)
                _update_batch_status(lot=batch_name, chapter=number, stage="FAILED", next_action="corrigir o ambiente e retomar o capítulo", started_at=batch_started)
                failed_status = json.loads(BATCH_STATUS_PATH.read_text(encoding="utf-8"))
                failed_status["state"] = "BLOCKED"
                failed_status["failure"] = {"type": type(exc).__name__, "message": str(exc)}
                _write_json(BATCH_STATUS_PATH, failed_status)
                raise
            index["chapters"] = [item for item in index["chapters"] if item["chapter"] != number] + [entry]
            _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
            _write_batch_report(index)
        lot_items = [item for item in index["chapters"] if item.get("batch") == batch_name]
        lot_summary = {
            "lot": batch_name,
            "state": "DONE" if all(item.get("status") == "DONE" for item in lot_items) else "PARTIAL",
            "elapsed_seconds": round(time.perf_counter() - lot_started, 3),
            "chapters": [item["chapter"] for item in lot_items],
            "files": [item.get("video") for item in lot_items],
            "validations": [item.get("validation", {}) for item in lot_items],
        }
        index["batch_summaries"] = [item for item in index.get("batch_summaries", []) if item.get("lot") != batch_name] + [lot_summary]
        _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
        _write_batch_report(index)
        _update_batch_status(lot=batch_name, chapter=None, stage=f"LOTE_{batch_name}_COMPLETE", next_action="iniciar próximo lote" if batch_name != "C" else "finalizar índice geral", started_at=batch_started)
    index["chapters"] = sorted(index["chapters"], key=lambda item: item["chapter"])
    index["state"] = "DONE" if all(item["status"] == "DONE" for item in index["chapters"]) else "PARTIAL"
    index["completed"] = sum(item["status"] == "DONE" for item in index["chapters"])
    index["failed"] = sum(item["status"] != "DONE" for item in index["chapters"])
    index["output_root"] = str(BATCH_ROOT)
    index["elapsed_seconds"] = round(time.perf_counter() - batch_started, 3)
    _write_json(BATCH_ROOT / "BATCH-INDEX.json", index)
    _write_batch_report(index)
    _update_batch_status(lot="C", chapter=None, stage="BATCH_COMPLETE", next_action="aguardar relatório e revisão humana", started_at=batch_started)
    final_status = json.loads(BATCH_STATUS_PATH.read_text(encoding="utf-8"))
    final_status.update({"state": index["state"], "completed_chapters": [item["chapter"] for item in index["chapters"] if item["status"] == "DONE"], "failures": [item for item in index["chapters"] if item["status"] != "DONE"], "next_action": "aguardar relatório e revisão humana"})
    _write_json(BATCH_STATUS_PATH, final_status)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="store_true", help="produce chapters 05–10")
    parser.add_argument("--preflight", action="store_true", help="validate DOCX boundaries only")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--capture-timeout", type=float, default=2400)
    args = parser.parse_args()
    batch = preflight_source(SOURCE_DOC)
    if args.preflight or not args.batch:
        print(json.dumps({key: value for key, value in batch.items() if key != "chapters"} | {"chapters": [{key: value for key, value in chapter.items() if key not in {"text", "paragraphs"}} for chapter in batch["chapters"].values()]}, ensure_ascii=False, indent=2, sort_keys=True))
        if not args.batch:
            return 0
    result = run_batch(overwrite=args.overwrite, port=args.port, capture_timeout=args.capture_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["state"] == "DONE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
