"""Produce the Chapter 2 cinematic episode without unapproved character art.

The manuscript boundaries are read from the source DOCX at runtime.  Only the
approved Santa V5 narrator is rendered; every story plate is an environment or
object-only image.  Audio timing comes from measured Kokoro WAVs and the visual
capture is the same deterministic Canvas/FFmpeg path used by Mission 026.1.
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
from urllib.parse import urlparse
from urllib.request import urlopen
import zipfile
import xml.etree.ElementTree as ET

import topazio_book1_chapter1_cronicas_demo as v1
from topazio_book1_chapter1_cronicas_v2_demo import audit_santa_visibility, mix_audio_v2

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.scene_assets import SceneAssetRegistry
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
PROJECT_ID = "topazio-book1-capitulo2-cronicas"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "scene-registry.json"
CHARACTER_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "character-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1920
HEIGHT = 1080
TRANSITION_MS = 900
APPROVED_CHARACTER_ID = "santa-v5-base"

HOST_INTRO = """Saudações, Guardiões!

Na última página, Topázio parou.

Agora, uma cicatriz antiga começa a responder dentro da caverna.

Abrimos o segundo capítulo de
O Despertar dos Cristais.

Nossa história continua agora!"""

HOST_OUTRO = """E assim, Guardiões, a cicatriz voltou a pulsar.

Thaurion seguiu para Gaia, mas o passado já havia encontrado uma voz.

Até o próximo capítulo!"""


# Environment-only plates, ordered to follow the exact Chapter 2 progression.
# No entry names a character asset and no scene contains a character identity.
SCENE_SPECS = (
    ("shot-001-cave-threshold", "01-cave-threshold.png", "cave_entry"),
    ("shot-002-crystal-pillars", "02-crystal-pillars.png", "crystal_drift"),
    ("shot-003-memory-fissure", "03-memory-fissure.png", "memory_fissure"),
    ("shot-004-dawn-road", "04-dawn-road.png", "road_push"),
    ("shot-005-elemental-signs", "05-elemental-signs.png", "elements_lateral"),
    ("shot-006-gaia-silence", "06-gaia-silence.png", "temple_approach"),
    ("shot-007-burned-roots", "06-gaia-silence.png", "crack_pan"),
    ("shot-008-primordial-altar", "07-primordial-altar.png", "altar_push"),
    ("shot-009-halo-pulse", "07-primordial-altar.png", "halo_pulse"),
    ("shot-010-crystal-reflection", "08-crystal-reflection.png", "reflection_drift"),
    ("shot-011-shadow-crossing", "08-crystal-reflection.png", "shadow_cross"),
    ("shot-012-cave-path", "09-seven-pulses.png", "path_return"),
    ("shot-013-seven-responses", "09-seven-pulses.png", "seven_pulse"),
    ("shot-014-echo-pillar", "10-pillar-path.png", "pillar_close"),
    ("shot-015-crystal-answer", "07-primordial-altar.png", "crystal_answer"),
    ("shot-016-chapter-threshold", "09-seven-pulses.png", "chapter_fade"),
)

SOURCE_PARAGRAPH_START: int
SOURCE_PARAGRAPH_END_EXCLUSIVE: int
SOURCE_CHAPTER_TITLE: str


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _audio_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _local_audio_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"expected local WAV URI, got {uri!r}")
    return Path(parsed.path.lstrip("/"))


def _load_docx_paragraphs(path: Path) -> list[str]:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return [
        "".join(node.text or "" for node in paragraph.findall(f".//{namespace}t"))
        for paragraph in root.findall(f".//{namespace}body/{namespace}p")
    ]


def _chapter_heading(text: str, number: int) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip())
    return bool(re.match(rf"^Cap.*\s{number}(?:\s|[—–-])", normalized, flags=re.IGNORECASE))


def load_chapter(path: Path = SOURCE_DOC) -> tuple[tuple[str, ...], str, dict[str, object]]:
    global SOURCE_PARAGRAPH_START, SOURCE_PARAGRAPH_END_EXCLUSIVE, SOURCE_CHAPTER_TITLE
    paragraphs = _load_docx_paragraphs(path)
    start = next(index for index, value in enumerate(paragraphs) if _chapter_heading(value, 2))
    end = next(index for index in range(start + 1, len(paragraphs)) if _chapter_heading(paragraphs[index], 3))
    selected = tuple(value.strip() for value in paragraphs[start + 1:end] if value.strip())
    if len(selected) != end - start - 1:
        raise ValueError("Chapter 2 contains unexpected blank paragraphs")
    if not selected:
        raise ValueError("Chapter 2 is empty")
    SOURCE_PARAGRAPH_START = start + 1
    SOURCE_PARAGRAPH_END_EXCLUSIVE = end
    SOURCE_CHAPTER_TITLE = paragraphs[start].strip()
    text = "\n\n".join(selected)
    return selected, text, {
        "title": SOURCE_CHAPTER_TITLE,
        "heading_paragraph": start,
        "first_narrative_paragraph": start + 1,
        "last_narrative_paragraph": end - 1,
        "end_exclusive": end,
        "paragraph_count": len(selected),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _synthesize_block(provider: KokoroTTSProvider, text: str, narration_id: str, output_dir: Path, *, overwrite: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    run = synthesize_narration(
        provider,
        text,
        narration_id=narration_id,
        manifest_id=narration_id,
        timeline_id=f"{narration_id}-timeline",
        language=LANGUAGE,
        voice_id=VOICE_ID,
        output_dir=output_dir,
        max_chars=360,
    )
    manifest = json.loads(serialize_manifest(run.manifest))
    manifest["metadata"]["editorial_block"] = narration_id
    _write_json(manifest_path, manifest)
    return manifest


def _adjust_block(manifest: dict, block: str, *, paragraph_offset: int = 0) -> list[dict]:
    result: list[dict] = []
    for source in manifest["segments"]:
        segment = copy.deepcopy(source)
        metadata = dict(segment.get("metadata", {}))
        metadata["editorial_block"] = block
        if block == "STORY_CHAPTER":
            metadata["source_paragraph"] = SOURCE_PARAGRAPH_START + int(metadata.get("paragraph_index", 0))
            metadata["source_document_paragraph"] = metadata["source_paragraph"]
        segment["metadata"] = metadata
        result.append(segment)
    return result


def compose_episode_manifest(intro: dict, story: dict, outro: dict) -> dict:
    blocks = (
        ("HOST_INTRO", _adjust_block(intro, "HOST_INTRO")),
        ("STORY_CHAPTER", _adjust_block(story, "STORY_CHAPTER")),
        ("HOST_OUTRO", _adjust_block(outro, "HOST_OUTRO")),
    )
    segments: list[dict] = []
    editorial_blocks: list[dict] = []
    cursor = 0
    for block_index, (block_name, source_segments) in enumerate(blocks):
        block_start = cursor
        for source in source_segments:
            segment = copy.deepcopy(source)
            duration = int(segment["duration_ms"])
            metadata = dict(segment.get("metadata", {}))
            segment["start_ms"] = cursor
            segment["end_ms"] = cursor + duration
            segment["metadata"] = metadata
            segments.append(segment)
            cursor = segment["end_ms"] + int(metadata.get("pause_after_ms", 0))
        editorial_blocks.append({"id": block_name.lower(), "type": block_name, "start_ms": block_start, "end_ms": cursor})
        if block_index < len(blocks) - 1:
            cursor += TRANSITION_MS
    if not segments:
        raise ValueError("episode contains no narration segments")
    return {
        "format_version": "0.1.0",
        "id": PROJECT_ID,
        "timeline_id": f"{PROJECT_ID}-timeline",
        "duration_ms": cursor,
        "segments": segments,
        "animation_events": [],
        "metadata": {
            "provider_id": "kokoro",
            "voice_id": VOICE_ID,
            "language": LANGUAGE,
            "editorial_blocks": editorial_blocks,
            "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
            "source_paragraphs": list(range(SOURCE_PARAGRAPH_START, SOURCE_PARAGRAPH_END_EXCLUSIVE)),
            "chapter_scope": SOURCE_CHAPTER_TITLE,
            "temporal_source": "measured_wav",
            "word_phoneme_viseme_timing": "unavailable",
        },
    }


def _split_evenly(items: list[dict], count: int) -> list[list[dict]]:
    if len(items) < count:
        raise ValueError(f"cannot create {count} shots from {len(items)} measured story segments")
    quotient, remainder = divmod(len(items), count)
    groups: list[list[dict]] = []
    cursor = 0
    for index in range(count):
        size = quotient + (1 if index < remainder else 0)
        groups.append(items[cursor:cursor + size])
        cursor += size
    return groups


def build_scene_schedule(manifest: dict, library_path: Path, library_sha256: str) -> tuple[dict, ...]:
    blocks = manifest["metadata"]["editorial_blocks"]
    intro = next(item for item in blocks if item["type"] == "HOST_INTRO")
    outro = next(item for item in blocks if item["type"] == "HOST_OUTRO")
    scenes: list[dict] = [{
        "id": "host-library-opening",
        "kind": "host",
        "asset_id": "santa-library-topazioverse-v1",
        "image": "official-scenes/santa-library-topazioverse-v1/library-base.png",
        "camera": "host_wide",
        "start_ms": intro["start_ms"],
        "end_ms": intro["end_ms"],
        "source_paragraphs": [],
        "character_registry_id": APPROVED_CHARACTER_ID,
    }]
    story_segments = [segment for segment in manifest["segments"] if segment.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]
    groups = _split_evenly(story_segments, len(SCENE_SPECS))
    for (scene_id, filename, camera), group in zip(SCENE_SPECS, groups, strict=True):
        metadata = [segment.get("metadata", {}) for segment in group]
        source_paragraphs = sorted({int(item["source_paragraph"]) for item in metadata if "source_paragraph" in item})
        scenes.append({
            "id": scene_id,
            "kind": "story",
            "image": f"{PROJECT_ID}/assets/generated/{filename}",
            "camera": camera,
            "start_ms": int(group[0]["start_ms"]),
            "end_ms": int(group[-1]["end_ms"]) + int(group[-1].get("metadata", {}).get("pause_after_ms", 0)),
            "source_paragraphs": source_paragraphs,
            "character_registry_id": APPROVED_CHARACTER_ID,
            "character_visual_policy": "Santa V5 medallion only; no story characters",
            "environment_only": True,
        })
    scenes.append({
        "id": "host-library-closing",
        "kind": "host",
        "asset_id": "santa-library-topazioverse-v1",
        "image": "official-scenes/santa-library-topazioverse-v1/library-base.png",
        "camera": "host_closing",
        "start_ms": outro["start_ms"],
        "end_ms": outro["end_ms"],
        "source_paragraphs": [],
        "character_registry_id": APPROVED_CHARACTER_ID,
    })
    scenes.sort(key=lambda item: (int(item["start_ms"]), item["id"]))
    scenes[-1]["end_ms"] = int(manifest["duration_ms"])
    if scenes[0]["start_ms"] != 0 or scenes[-1]["end_ms"] != manifest["duration_ms"]:
        raise ValueError("scene schedule does not cover the measured episode")
    for scene in scenes:
        scene["library_asset_id"] = "santa-library-topazioverse-v1"
        scene["library_sha256"] = library_sha256
    return tuple(scenes)


def compose_voice(manifest: dict, output_path: Path) -> int:
    first_path = _local_audio_path(manifest["segments"][0]["audio_uri"])
    import wave
    from array import array
    with wave.open(str(first_path), "rb") as first_wav:
        sample_rate = first_wav.getframerate()
        if (first_wav.getnchannels(), first_wav.getsampwidth()) != (1, 2):
            raise ValueError("episode requires mono PCM-16 narration WAVs")
    combined = array("h")
    written_frames = 0
    for segment in manifest["segments"]:
        path = _local_audio_path(segment["audio_uri"])
        with wave.open(str(path), "rb") as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (sample_rate, 1, 2):
                raise ValueError(f"inconsistent narration WAV format: {path}")
            target_start = round(int(segment["start_ms"]) * sample_rate / 1000)
            combined.extend([0] * max(0, target_start - written_frames))
            combined.frombytes(wav.readframes(wav.getnframes()))
            written_frames = target_start + wav.getnframes()
    target_end = round(int(manifest["duration_ms"]) * sample_rate / 1000)
    combined.extend([0] * max(0, target_end - written_frames))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sample_rate); wav.writeframes(combined.tobytes())
    return sample_rate


def _capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    edge = v1._find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT)})
    server = subprocess.Popen([
        sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"),
        "--port", str(port), "--capture-dir", str(frames_root)
    ], cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url_root = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter2.html"
        v1._wait_for_http(url_root, 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"{url_root}?session={session}&timeline=/exports/{relative}&fps={FPS}"
        command = [edge, "--headless=new", "--disable-gpu", "--dump-dom", "--hide-scrollbars", "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url]
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
                raise TimeoutError(f"Canvas capture did not complete: {session_dir}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            frames = v1._materialize_frames(session_dir, completion)
            if len(frames) != int(completion["frame_count"]):
                raise RuntimeError(f"capture incomplete: expected {completion['frame_count']} frames, found {len(frames)}")
            return session_dir, completion
        finally:
            if browser.poll() is None:
                browser.terminate()
                try: browser.wait(timeout=5)
                except subprocess.TimeoutExpired: browser.kill()
    finally:
        server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _write_srt(manifest: dict, path: Path) -> None:
    import textwrap
    def stamp(ms: int) -> str:
        hours, rem = divmod(ms, 3_600_000); minutes, rem = divmod(rem, 60_000); seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = []
    for index, segment in enumerate(manifest["segments"], 1):
        blocks.append(f"{index}\n{stamp(segment['start_ms'])} --> {stamp(segment['end_ms'])}\n" + "\n".join(textwrap.wrap(segment["text"], 68, break_long_words=False)) + "\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _copy_generated_assets() -> None:
    generated_root = Path(r"C:\Users\User\.codex\generated_images\01a1848e-a0d8-7c63-8677-4b1ea3939168")
    mapping = {
        "01-cave-threshold.png": "exec-77b983cc-6b5a-4c1a-90a9-0b0a59edb233.png",
        "02-crystal-pillars.png": "exec-bbb90a3c-8d6e-423b-a12d-86c9af8f386e.png",
        "03-memory-fissure.png": "exec-0bfcbd70-e338-49f9-8763-24a69f5ad5d1.png",
        "04-dawn-road.png": "exec-bc80233d-04b8-4068-a301-9cce7f9001a2.png",
        "05-elemental-signs.png": "exec-eaf71d27-11d2-4c9d-af59-4dba2e385309.png",
        "06-gaia-silence.png": "exec-46f1d6f0-5308-4f48-a05a-9bd1c4a62b9e.png",
        "07-primordial-altar.png": "exec-1768f577-806c-430e-be4c-66fce561aa1e.png",
        "08-crystal-reflection.png": "exec-ebef8c1e-616a-417b-a576-58b5ef2f0cca.png",
        "09-seven-pulses.png": "exec-6480779c-b1fa-44b9-a754-0d0158bf81e0.png",
        "10-pillar-path.png": "exec-0bfcbd70-e338-49f9-8763-24a69f5ad5d1.png",
    }
    target = PROJECT_ROOT / "assets" / "generated"
    target.mkdir(parents=True, exist_ok=True)
    for destination_name, source_name in mapping.items():
        source = generated_root / source_name
        if not source.is_file(): raise FileNotFoundError(source)
        shutil.copyfile(source, target / destination_name)


def _write_reports(project_root: Path, manifest: dict, timeline: dict, video_probe: dict, mix_probe: dict, *, source_meta: dict, library_path: Path, library_sha256: str, character_registry: CharacterRegistry, visibility: dict, processing_seconds: float) -> None:
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    draft_ids = [item for item in character_registry.ids() if item not in character_registry.approved_ids()]
    (reports / "technical-report.md").write_text(
        "# Missão 027 — Crônicas de Topázio, Livro 1, Capítulo 2\n\n"
        f"- Título-fonte: `{source_meta['title']}`\n- Parágrafos narrativos: `{source_meta['first_narrative_paragraph']}–{source_meta['last_narrative_paragraph']}`\n"
        f"- Hash UTF-8 do recorte: `{source_meta['text_sha256']}`\n- Segmentos Kokoro medidos: `{len(manifest['segments'])}`\n"
        f"- Planos: `{len(timeline['scenes'])}` (16 story + host opening/closing)\n- Duração: `{manifest['duration_ms']} ms`\n"
        f"- Processamento local: `{processing_seconds:.2f} s`\n- Voz: `{VOICE_ID}` / `{LANGUAGE}`\n"
        "- Timestamps de palavra/fonema/visema: indisponíveis; captions e boca usam somente segmentos medidos e RMS.\n"
        "- Estado: pendente de aprovação artística humana.\n\n## Política de personagens\n\n"
        f"- Única identidade autorizada: `{APPROVED_CHARACTER_ID}`.\n- Identidades DRAFT bloqueadas: `{draft_ids}`.\n"
        "- Cenas de história são environment-only; nenhum guardião conceitual DRAFT foi gerado, selecionado ou renderizado.\n",
        encoding="utf-8",
    )
    (reports / "character-policy-report.md").write_text(
        "# Política de identidade visual\n\n"
        f"- Registry público: `assets/character-registry.json`\n- Santa: `{APPROVED_CHARACTER_ID}` / APPROVED\n"
        f"- Arquivo Santa verificado: `{character_registry.resolve(APPROVED_CHARACTER_ID)}`\n"
        f"- SHA-256 Santa: `{hashlib.sha256(character_registry.resolve(APPROVED_CHARACTER_ID).read_bytes()).hexdigest()}`\n"
        f"- DRAFTs registrados e bloqueados: `{', '.join(draft_ids)}`\n"
        "- A validação de produção usa `CharacterRegistry.require_approved`; qualquer status diferente de APPROVED falha antes da composição.\n",
        encoding="utf-8",
    )
    (reports / "scene-library-reuse.md").write_text(
        "# Reuso da biblioteca oficial\n\n"
        "A biblioteca `santa-library-topazioverse-v1` foi resolvida pelo registro estável e reutilizada na abertura, no encerramento e como referência de composição do medalhão.\n\n"
        f"- Caminho resolvido: `{library_path}`\n- SHA-256: `{library_sha256}`\n- Regeneração: `não`\n",
        encoding="utf-8",
    )
    (reports / "mix-report.md").write_text(
        "# Mixagem do Capítulo 2\n\n"
        f"- Música: `{MUSIC}`; origem Suno; velocidade e tom preservados.\n"
        "- Ducking: sidechain voz→música, ratio 5, ataque 45 ms, release 650 ms, base musical 0.13.\n"
        "- SFX: cama procedural existente, volume 0.12; limiter final 0.90.\n"
        "- Direitos comerciais Suno: confirmação necessária antes de publicação.\n"
        f"- FFprobe mix: `{json.dumps(mix_probe, ensure_ascii=False, sort_keys=True)}`\n- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (reports / "santa-visibility-report.json").write_text(json.dumps(visibility, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--capture-timeout", type=float, default=2400)
    args = parser.parse_args()
    if not SOURCE_DOC.is_file(): raise FileNotFoundError(SOURCE_DOC)
    if not MUSIC.is_file(): raise FileNotFoundError(MUSIC)
    chapter_paragraphs, chapter_text, source_meta = load_chapter()
    for directory in (PROJECT_ROOT / "audio", PROJECT_ROOT / "timeline", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports", PROJECT_ROOT / "videos", PROJECT_ROOT / ".frames", PROJECT_ROOT / "assets" / "generated"):
        directory.mkdir(parents=True, exist_ok=True)
    _copy_generated_assets()
    scene_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    library_sha256 = hashlib.sha256(library_path.read_bytes()).hexdigest()
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    approved = character_registry.require_approved(APPROVED_CHARACTER_ID)
    approved_path = character_registry.resolve(approved.id)
    excerpt_path = PROJECT_ROOT / "timeline" / "chapter2-source-excerpt.txt"
    excerpt_path.write_text(chapter_text + "\n", encoding="utf-8")
    manifest_path = PROJECT_ROOT / "manifest.json"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        provider = KokoroTTSProvider(output_dir=PROJECT_ROOT / "audio", allow_overwrite=args.overwrite)
        try:
            intro = _synthesize_block(provider, HOST_INTRO, f"{PROJECT_ID}-host-intro", PROJECT_ROOT / "audio" / "host-intro", overwrite=args.overwrite)
            story = _synthesize_block(provider, "\n\n".join(chapter_paragraphs), f"{PROJECT_ID}-story", PROJECT_ROOT / "audio" / "story", overwrite=args.overwrite)
            outro = _synthesize_block(provider, HOST_OUTRO, f"{PROJECT_ID}-host-outro", PROJECT_ROOT / "audio" / "host-outro", overwrite=args.overwrite)
            manifest = compose_episode_manifest(intro, story, outro)
            _write_json(manifest_path, manifest)
            print(f"tts_provider={provider.provider_id}")
            print(f"tts_model={provider.model_id}")
            print(f"tts_model_revision={provider.model_revision}")
            print(f"tts_model_load_count={provider.model_load_count}")
        except (TTSError, NarrationSynthesisError):
            raise
        finally:
            provider.close()
    timeline_path = PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.json"
    timeline = {
        "format": "fabuloom.topazioverse-chapter/0.2",
        "title": f"Crônicas de Topázio — Livro 1 — {SOURCE_CHAPTER_TITLE}",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(range(SOURCE_PARAGRAPH_START, SOURCE_PARAGRAPH_END_EXCLUSIVE)),
        "source_text_sha256": source_meta["text_sha256"],
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
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
        "character_policy": {"approved_only": True, "draft_rendering": "blocked", "story_visuals": "environment_only"},
        "scenes": list(build_scene_schedule(manifest, library_path, library_sha256)),
    }
    _write_json(timeline_path, timeline)
    _write_srt(manifest, PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.srt")
    voice_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-voice.wav"
    sample_rate = compose_voice(manifest, voice_path)
    sfx_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-sfx-bed.wav"
    if not sfx_path.exists() or args.overwrite: v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-music-loop.wav"
    v1.make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    mix_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-mix.wav"
    mix_audio_v2(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]))
    if args.reuse_capture:
        completed = sorted((PROJECT_ROOT / ".frames").glob("capture-*/complete.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not completed: raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = completed[0].parent; completion = json.loads(completed[0].read_text(encoding="utf-8")); v1._materialize_frames(session_dir, completion)
    else:
        session_dir, completion = _capture_frames(timeline_path, PROJECT_ROOT / ".frames", port=args.port, timeout_seconds=args.capture_timeout)
    video_path = PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo2.mp4"
    v1.render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
    board_path = PROJECT_ROOT / "captures" / "chapter2-frames.png"
    v1.frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
    video_probe = v1.probe(video_path); mix_probe = v1.probe(mix_path)
    visibility = audit_santa_visibility(session_dir, timeline["scenes"], frame_count=int(completion["frame_count"]))
    visibility["scene_count"] = len(timeline["scenes"]); visibility["passed"] = bool(visibility["passed"] and visibility["scene_count"] == len(timeline["scenes"]))
    _write_reports(PROJECT_ROOT, manifest, timeline, video_probe, mix_probe, source_meta=source_meta, library_path=library_path, library_sha256=library_sha256, character_registry=character_registry, visibility=visibility, processing_seconds=time.perf_counter() - started)
    report = {
        "project": PROJECT_ID, "video": str(video_path), "manifest": str(manifest_path), "timeline": str(timeline_path), "frame_board": str(board_path),
        "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "scenes": len(timeline["scenes"]),
        "source": source_meta, "sample_rate": sample_rate, "video_probe": video_probe, "audio_probe": mix_probe,
        "library_id": "santa-library-topazioverse-v1", "library_sha256": library_sha256, "approved_character_id": APPROVED_CHARACTER_ID,
        "draft_character_rendering": "blocked", "story_visual_policy": "environment_only", "timing_source": "measured_wav_segments",
        "mouth_source": "pcm16_rms_envelope", "word_phoneme_viseme_timing": "unavailable", "santa_visibility": visibility,
        "state": "completed_pending_human_artistic_review",
    }
    _write_json(PROJECT_ROOT / "reports" / "episode-result.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
