"""Produce the Chapter 11 cinematic episode in isolated, resumable stages.

The source DOCX and external cinematic clips are immutable inputs.  The runner
creates measured Kokoro narration, a voice-priority Alba mix, a Canvas-based
Santa V5 narrative section, and separate 16:9/9:16 masters.  External video
audio is never mapped into the result.
"""

from __future__ import annotations

import argparse
from array import array
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import wave
from urllib.parse import urlencode, urlparse
from zipfile import ZipFile
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "examples"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from ctv_001_vertical_cinema import _find_edge, _materialize_frames


FABULOOM_ROOT = Path(os.environ.get("FABULOOM_ROOT", r"E:\Fabuloom")).resolve()
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
OUTPUT_ROOT = EXPORT_ROOT / "cronicas-book1-capitulo11-cinematic-v1"
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
MUSIC_SOURCE = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Alba Quando a Luz Rasga o Céu.mp3"
LIBRARY_ROOT = FABULOOM_ROOT / "workspace" / "inputs" / "biblioteca videos e musicas"
PUBLIC_REGISTRY = PROJECT_ROOT / "assets" / "scene-registry.json"
CHARACTER_REGISTRY = PROJECT_ROOT / "assets" / "character-registry.json"
CAPTURE_PAGE = PROJECT_ROOT / "frontend" / "capture-cronicas-cap11-narrative.html"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
HORIZONTAL = (1920, 1080)
VERTICAL = (1080, 1920)
STAGE_FILE = OUTPUT_ROOT / "BATCH-STATUS.json"
FULL_MANIFEST_FILE = OUTPUT_ROOT / "manifest" / "chapter11-full.json"
STORY_MANIFEST_FILE = OUTPUT_ROOT / "manifest" / "chapter11-story.json"

EXTERNAL_NAMES = {
    "intro_horizontal": "FBS-001-INTRO-H-O-Despertar-do-Cristal.mp4",
    "intro_vertical": "FBS-001-INTRO-V-O-Despertar-do-Cristal.mp4",
    "santa_v1": "santa-cinematic-opening-v-v1.mp4",
    "santa_v2": "santa-cinematic-opening-v-v2.mp4",
}

ENVIRONMENT_SOURCES = {
    "road": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-10" / "assets" / "generated" / "asset-001.png",
    "pillar_path": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-005.png",
    "stone_map": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-001.png",
    "crystal_reflection": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-009.png",
    "memory_fissure": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-09" / "assets" / "generated" / "asset-005.png",
    "black_fissure": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-06" / "assets" / "generated" / "asset-008.png",
    "gaia_silence": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-10" / "assets" / "generated" / "asset-007.png",
    "cave_threshold": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-06" / "assets" / "generated" / "asset-004.png",
    "central_chamber": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-014.png",
    "cracked_doorway": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-016.png",
    "observatory": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-05" / "assets" / "generated" / "asset-006.png",
    "crystal_crack": FABULOOM_ROOT / "workspace" / "exports" / "cronicas-book1-batch-05-10" / "capitulo-06" / "assets" / "generated" / "asset-012.png",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=capture, text=True)


def probe(path: Path) -> dict:
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    return json.loads(result.stdout)


def duration_ms(path: Path) -> int:
    return round(float(probe(path)["format"]["duration"]) * 1000)


def audio_stream(metadata: dict) -> dict | None:
    return next((item for item in metadata.get("streams", []) if item.get("codec_type") == "audio"), None)


def video_stream(metadata: dict) -> dict | None:
    return next((item for item in metadata.get("streams", []) if item.get("codec_type") == "video"), None)


def _load_docx_paragraphs(path: Path) -> list[str]:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return ["".join(node.text or "" for node in paragraph.iter(namespace + "t")) for paragraph in root.iter(namespace + "p")]


def _heading_match(text: str, number: int) -> bool:
    return bool(re.match(rf"^Cap[ií]tulo\s+{number}(?:\s*[—:-]|$)", text.strip(), re.IGNORECASE))


def chapter_display_title(heading: str, number: int) -> str:
    normalized = re.sub(r"\s+", " ", heading.replace("\r", " ").replace("\n", " ")).strip()
    match = re.match(rf"^Cap[ií]tulo\s+{number}\s*(?:[—:-]\s*)?(.+?)\s*$", normalized, re.IGNORECASE)
    if not match:
        raise ValueError(f"CHAPTER_HEADING_INVALID: {heading!r}")
    title = re.sub(r"\s+", " ", match.group(1)).strip(" .—:-")
    if not title or re.search(rf"^Cap[ií]tulo\s+{number}\b", title, re.IGNORECASE):
        raise ValueError(f"CHAPTER_DISPLAY_TITLE_INVALID: {heading!r}")
    return title


def load_chapter11() -> dict:
    if not SOURCE_DOC.is_file():
        raise FileNotFoundError(SOURCE_DOC)
    paragraphs = _load_docx_paragraphs(SOURCE_DOC)
    matches11 = [(i, value.strip()) for i, value in enumerate(paragraphs) if _heading_match(value, 11)]
    matches12 = [(i, value.strip()) for i, value in enumerate(paragraphs) if _heading_match(value, 12)]
    if len(matches11) != 1 or len(matches12) != 1 or matches12[0][0] <= matches11[0][0]:
        raise ValueError(f"SOURCE_BOUNDARY_INVALID: chapter11={matches11}, chapter12={matches12}")
    start, heading = matches11[0]
    end, next_heading = matches12[0]
    selected = [(i, value.strip()) for i, value in enumerate(paragraphs[start + 1:end]) if value.strip()]
    text = "\n\n".join(value for _, value in selected)
    if not text:
        raise ValueError("SOURCE_BOUNDARY_INVALID: Chapter 11 text is empty")
    return {
        "number": 11,
        "chapter_heading": heading,
        "chapter_display_title": chapter_display_title(heading, 11),
        "heading_paragraph": start,
        "next_chapter_heading": next_heading,
        "paragraph_indices": [start + 1 + index for index, _ in selected],
        "paragraphs": [value for _, value in selected],
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "word_count": len(re.findall(r"\S+", text)),
        "source_doc_sha256": sha256(SOURCE_DOC),
    }


def external_inventory() -> dict:
    inventory = {}
    for key, name in EXTERNAL_NAMES.items():
        path = LIBRARY_ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        metadata = probe(path)
        video = video_stream(metadata)
        if not video:
            raise ValueError(f"external asset has no video stream: {path}")
        inventory[key] = {
            "path": str(path),
            "name": name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "duration_ms": round(float(metadata["format"]["duration"]) * 1000),
            "width": int(video["width"]),
            "height": int(video["height"]),
            "fps": video.get("r_frame_rate"),
            "video_codec": video.get("codec_name"),
            "audio_present": audio_stream(metadata) is not None,
            "audio_codec": (audio_stream(metadata) or {}).get("codec_name"),
            "audio_channels": (audio_stream(metadata) or {}).get("channels"),
            "audio_policy": "discarded_with_explicit_-an_and_video-only_mapping",
            "approval_status": "owner_supplied_external_asset_pending_rights_confirmation",
        }
    if not MUSIC_SOURCE.is_file():
        raise FileNotFoundError(MUSIC_SOURCE)
    metadata = probe(MUSIC_SOURCE)
    stream = audio_stream(metadata)
    inventory["music_alba"] = {
        "path": str(MUSIC_SOURCE),
        "name": MUSIC_SOURCE.name,
        "sha256": sha256(MUSIC_SOURCE),
        "bytes": MUSIC_SOURCE.stat().st_size,
        "duration_ms": round(float(metadata["format"]["duration"]) * 1000),
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate", 0)),
        "channels": int(stream.get("channels", 0)),
        "rights_status": "commercial_rights_pending_owner_confirmation",
        "speed_and_pitch": "preserved",
    }
    return inventory


def original_episode_hashes() -> dict[str, str]:
    roots = [
        EXPORT_ROOT / "topazio-book1-capitulo1-cronicas-v2",
        EXPORT_ROOT / "topazio-book1-capitulo2-cronicas",
        EXPORT_ROOT / "topazio-book1-capitulo3-cronicas",
        EXPORT_ROOT / "topazio-book1-capitulo4-cronicas",
        EXPORT_ROOT / "cronicas-book1-batch-05-10",
        EXPORT_ROOT / "vertical-cinema-book1-v1",
    ]
    values: dict[str, str] = {}
    for root in roots:
        if root.is_dir():
            for path in root.rglob("*.mp4"):
                values[str(path)] = sha256(path)
    return values


def status(stage: str, *, state: str = "RUNNING", next_action: str = "", details: dict | None = None) -> None:
    payload = {}
    if STAGE_FILE.is_file():
        payload = json.loads(STAGE_FILE.read_text(encoding="utf-8"))
    payload.update({"mission": "CRONICAS-CAP11-CIN-001", "state": state, "stage": stage, "updated_at": now_iso(), "next_action": next_action})
    if details:
        payload.update(details)
    write_json(STAGE_FILE, payload)
    print(f"[CAP11] etapa={stage} estado={state} próxima={next_action}", flush=True)


def copy_immutable(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        if sha256(target) != sha256(source):
            raise RuntimeError(f"OUTPUT_COLLISION: {target}")
        return
    shutil.copyfile(source, target)


def copy_assets(inventory: dict) -> dict:
    external_dir = OUTPUT_ROOT / "assets" / "external"
    for key, item in inventory.items():
        if key == "music_alba":
            continue
        copy_immutable(Path(item["path"]), external_dir / item["name"])
    selected = {}
    env_dir = OUTPUT_ROOT / "assets" / "environments"
    for key, source in ENVIRONMENT_SOURCES.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        target = env_dir / f"{key}.png"
        copy_immutable(source, target)
        selected[key] = {"path": str(target), "sha256": sha256(target), "source": str(source), "policy": "approved_environment_plate_reused"}
    library = FABULOOM_ROOT / "workspace" / "exports" / "official-scenes" / "santa-library-topazioverse-v1" / "library-base.png"
    if not library.is_file():
        raise FileNotFoundError(library)
    library_target = OUTPUT_ROOT / "assets" / "official-scenes" / "santa-library-topazioverse-v1" / "library-base.png"
    copy_immutable(library, library_target)
    selected["santa_library"] = {"path": str(library_target), "sha256": sha256(library_target), "source": str(library), "policy": "official_library_reused"}
    write_json(OUTPUT_ROOT / "assets-index" / "external-and-environment-assets.json", {"external": inventory, "selected_environment": selected})
    return selected


def synthesize_block(provider: KokoroTTSProvider, text: str, block_id: str, output_dir: Path) -> dict:
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    run_result = synthesize_narration(
        provider,
        text,
        narration_id=f"topazio-book1-capitulo11-cin-{block_id}",
        manifest_id=f"topazio-book1-capitulo11-cin-{block_id}",
        timeline_id=f"topazio-book1-capitulo11-cin-{block_id}-timeline",
        language=LANGUAGE,
        voice_id=VOICE_ID,
        output_dir=output_dir,
        max_chars=360,
        sentence_pause_ms=180,
        question_pause_ms=320,
        paragraph_pause_ms=350,
    )
    manifest = json.loads(serialize_manifest(run_result.manifest))
    manifest["metadata"].update({"editorial_block": block_id, "voice_id": VOICE_ID, "language": LANGUAGE})
    write_json(manifest_path, manifest)
    return manifest


def local_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"expected file URI, got {uri}")
    return Path(parsed.path.lstrip("/"))


def merge_manifests(intro: dict, story: dict, outro: dict, chapter: dict, bumper_ms: int) -> tuple[dict, dict, dict]:
    blocks = [("HOST_INTRO", intro), ("STORY_CHAPTER", story), ("HOST_OUTRO", outro)]
    segments = []
    editorial_blocks = []
    cursor = bumper_ms
    story_segments = []
    for block_name, source_manifest in blocks:
        block_start = cursor
        for source in source_manifest["segments"]:
            segment = copy.deepcopy(source)
            metadata = dict(segment.get("metadata", {}))
            metadata["editorial_block"] = block_name
            if block_name == "STORY_CHAPTER":
                paragraph_index = int(metadata.get("paragraph_index", 0))
                metadata["source_paragraph"] = chapter["paragraph_indices"][min(paragraph_index, len(chapter["paragraph_indices"]) - 1)]
            segment["metadata"] = metadata
            segment["start_ms"] = cursor
            segment["end_ms"] = cursor + int(segment["duration_ms"])
            segment["track_id"] = "voice"
            segments.append(segment)
            if block_name == "STORY_CHAPTER":
                story_segments.append(copy.deepcopy(segment))
            cursor = segment["end_ms"] + int(metadata.get("pause_after_ms", 0))
        editorial_blocks.append({"id": block_name.lower(), "type": block_name, "start_ms": block_start, "end_ms": cursor})
    full = {
        "format_version": "0.1.0",
        "id": "topazio-book1-capitulo11-cinematic",
        "timeline_id": "topazio-book1-capitulo11-cinematic-timeline",
        "duration_ms": cursor,
        "segments": segments,
        "animation_events": [],
        "metadata": {
            "provider_id": "kokoro",
            "voice_id": VOICE_ID,
            "language": LANGUAGE,
            "chapter_heading": chapter["chapter_heading"],
            "chapter_display_title": chapter["chapter_display_title"],
            "editorial_blocks": editorial_blocks,
            "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
            "source_paragraphs": chapter["paragraph_indices"],
            "temporal_source": "measured_wav",
            "word_phoneme_viseme_timing": "unavailable",
            "expressive_question_intonation": "not_verified",
        },
    }
    story_duration = story_segments[-1]["end_ms"] - story_segments[0]["start_ms"] if story_segments else 0
    story_rebased = copy.deepcopy(story)
    story_rebased["id"] = "topazio-book1-capitulo11-cinematic-story"
    story_rebased["timeline_id"] = "topazio-book1-capitulo11-cinematic-story-timeline"
    story_rebased["duration_ms"] = story["duration_ms"]
    story_rebased["segments"] = []
    story_start = int(story_segments[0]["start_ms"]) if story_segments else 0
    for segment in story_segments:
        item = copy.deepcopy(segment)
        item["start_ms"] -= story_start
        item["end_ms"] -= story_start
        story_rebased["segments"].append(item)
    story_rebased["metadata"] = dict(story_rebased.get("metadata", {}))
    story_rebased["metadata"].update({"editorial_block": "STORY_CHAPTER", "chapter_heading": chapter["chapter_heading"], "chapter_display_title": chapter["chapter_display_title"], "temporal_source": "measured_wav"})
    return full, story_rebased, {"editorial_blocks": editorial_blocks, "story_duration_ms": story_duration, "bumper_ms": bumper_ms}


def compose_voice(manifest: dict, output_path: Path) -> tuple[int, int]:
    segments = manifest["segments"]
    first = local_path(segments[0]["audio_uri"])
    with wave.open(str(first), "rb") as wav:
        sample_rate = wav.getframerate()
        if (wav.getnchannels(), wav.getsampwidth()) != (1, 2):
            raise ValueError("Kokoro voice must be mono PCM-16")
    combined = array("h")
    written = 0
    for segment in segments:
        path = local_path(segment["audio_uri"])
        with wave.open(str(path), "rb") as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (sample_rate, 1, 2):
                raise ValueError(f"inconsistent voice WAV: {path}")
            target = round(int(segment["start_ms"]) * sample_rate / 1000)
            combined.extend([0] * max(0, target - written))
            combined.frombytes(wav.readframes(wav.getnframes()))
            written = target + wav.getnframes()
    target_frames = round(int(manifest["duration_ms"]) * sample_rate / 1000)
    combined.extend([0] * max(0, target_frames - written))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(combined.tobytes())
    return sample_rate, len(combined)


def write_srt(manifest: dict, path: Path) -> None:
    def stamp(ms: int) -> str:
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = []
    for index, segment in enumerate(manifest["segments"], 1):
        lines = "\n".join(textwrap.wrap(segment["text"], width=72, break_long_words=False))
        blocks.append(f"{index}\n{stamp(int(segment['start_ms']))} --> {stamp(int(segment['end_ms']))}\n{lines}\n")
    write_text(path, "\n".join(blocks))


def write_sfx_bed(path: Path, duration: int, scene_starts: list[int]) -> None:
    rate = 48_000
    frames = max(1, round(duration * rate / 1000))
    events = [(max(0, start / 1000), kind) for start, kind in zip(scene_starts, ("wind", "crystal", "water", "memory"), strict=False)]
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
        block = 4096
        for offset in range(0, frames, block):
            count = min(block, frames - offset)
            pcm = array("h")
            for frame in range(count):
                t = (offset + frame) / rate
                value = 0.0
                for start, kind in events:
                    age = t - start
                    if 0 <= age < 2.8:
                        envelope = min(1.0, age * 14.0, (2.8 - age) * 2.5)
                        frequency = {"wind": 74, "crystal": 680, "water": 190, "memory": 116}[kind]
                        value += math.sin(2 * math.pi * frequency * age) * envelope * 0.018
                sample = max(-32767, min(32767, round(value * 32767)))
                pcm.append(sample); pcm.append(round(sample * 0.88))
            wav.writeframes(pcm.tobytes())


def make_music_loop(source: Path, output: Path, total_ms: int) -> None:
    if output.is_file():
        return
    total = total_ms / 1000
    source_duration = float(probe(source)["format"]["duration"])
    count = max(1, math.ceil(total / source_duration) + 1)
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n"]
    for _ in range(count):
        args.extend(["-i", str(source)])
    filters = [f"[{i}:a]aresample=48000,atrim=0:{source_duration:.6f},asetpts=PTS-STARTPTS[m{i}]" for i in range(count)]
    current = "m0"
    crossfade = min(4.0, max(1.0, source_duration / 30))
    for i in range(1, count):
        label = f"x{i}"
        filters.append(f"[{current}][m{i}]acrossfade=d={crossfade:.3f}:c1=tri:c2=tri[{label}]")
        current = label
    args.extend(["-filter_complex", ";".join(filters), "-map", f"[{current}]", "-t", f"{total:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)])
    output.parent.mkdir(parents=True, exist_ok=True)
    run(args)


def mix_audio(voice: Path, music: Path, sfx: Path, output: Path, duration: int) -> None:
    if output.is_file():
        return
    seconds = duration / 1000
    graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.115,atrim=duration={seconds:.3f},afade=t=in:st=0:d=2,afade=t=out:st={max(0, seconds - 6):.3f}:d=6[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=6:attack=45:release=650:makeup=1[ducked];"
        f"[2:a]aresample=48000,volume=0.08,atrim=duration={seconds:.3f}[sfx];"
        "[voice_st][ducked][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.90:attack=5:release=500[out]"
    )
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(voice), "-i", str(music), "-i", str(sfx), "-filter_complex", graph, "-map", "[out]", "-t", f"{seconds:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)])


def copy_asset_path(selected: dict, key: str) -> str:
    path = Path(selected[key]["path"])
    return path.relative_to(EXPORT_ROOT).as_posix()


def build_story_plan(story_manifest: dict, selected: dict, orientation: str) -> dict:
    scene_keys = ["road", "pillar_path", "stone_map", "crystal_reflection", "memory_fissure", "black_fissure", "gaia_silence", "cave_threshold", "central_chamber", "cracked_doorway", "observatory", "crystal_crack"]
    segments = list(story_manifest["segments"])
    groups = []
    q, r = divmod(len(segments), len(scene_keys))
    cursor = 0
    for index, key in enumerate(scene_keys):
        size = q + (1 if index < r else 0)
        group = segments[cursor:cursor + size]
        cursor += size
        if not group:
            continue
        groups.append({
            "id": f"story-{index + 1:02d}-{key}",
            "kind": "story",
            "image": copy_asset_path(selected, key),
            "camera": "crystal" if "crystal" in key or "memory" in key else "road" if key in {"road", "pillar_path"} else "memory" if key in {"black_fissure", "cave_threshold"} else "wide",
            "start_ms": int(group[0]["start_ms"]),
            "end_ms": int(group[-1]["end_ms"]) + int(group[-1].get("metadata", {}).get("pause_after_ms", 0)),
            "source_paragraphs": sorted({int(item.get("metadata", {}).get("source_paragraph", -1)) for item in group if int(item.get("metadata", {}).get("source_paragraph", -1)) >= 0}),
            "environment_only": True,
            "character_registry_id": "santa-v5-base",
        })
    if not groups:
        raise ValueError("story plan contains no scenes")
    groups[-1]["end_ms"] = int(story_manifest["duration_ms"])
    return {
        "format": "fabuloom.topazioverse-chapter/0.3",
        "mission": "CRONICAS-CAP11-CIN-001",
        "orientation": orientation,
        "canvas": {"width": VERTICAL[0], "height": VERTICAL[1]} if orientation == "vertical" else {"width": HORIZONTAL[0], "height": HORIZONTAL[1]},
        "fps": FPS,
        "manifest": STORY_MANIFEST_FILE.relative_to(EXPORT_ROOT).as_posix(),
        "transition_ms": 900,
        "narrator": "Santa V5",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "narrator_visibility": "all_story_scenes_medallion",
        "story_visual_policy": "approved_environment_plates_only",
        "scenes": groups,
    }


def capture_frames(plan_path: Path, orientation: str, frames_root: Path, port: int, timeout: float) -> tuple[Path, dict]:
    from topazio_book1_chapter1_cronicas_demo import _materialize_frames, _wait_for_http

    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"cap11-{orientation}-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT)})
    server = subprocess.Popen([sys.executable, str(PROJECT_ROOT / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)], cwd=str(PROJECT_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        root_url = f"http://127.0.0.1:{port}/capture-cronicas-cap11-narrative.html"
        _wait_for_http(root_url, 20)
        relative = plan_path.relative_to(EXPORT_ROOT).as_posix()
        query = urlencode({"session": session, "timeline": f"/exports/{relative}", "fps": FPS, "orientation": orientation})
        url = f"{root_url}?{query}"
        command = [edge, "--headless=new", "--disable-gpu", "--dump-dom", "--hide-scrollbars", "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout
        try:
            while not complete.exists() and not error.exists() and time.monotonic() < deadline:
                time.sleep(.25)
            if error.exists():
                raise RuntimeError(error.read_text(encoding="utf-8"))
            if not complete.exists():
                raise TimeoutError(f"capture timeout: {session_dir}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            frames = _materialize_frames(session_dir, completion)
            expected = int(completion["frame_count"])
            if len(frames) != expected:
                raise RuntimeError(f"capture incomplete: expected {expected}, found {len(frames)}")
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


def existing_capture(frames_root: Path, orientation: str) -> tuple[Path, dict] | None:
    """Reuse the newest complete capture so a later stage can resume safely."""
    from topazio_book1_chapter1_cronicas_demo import _materialize_frames

    candidates = sorted(frames_root.glob(f"cap11-{orientation}-*"), key=lambda path: path.stat().st_mtime, reverse=True)
    for session_dir in candidates:
        complete = session_dir / "complete.json"
        if not complete.is_file():
            continue
        try:
            metadata = json.loads(complete.read_text(encoding="utf-8"))
            frames = _materialize_frames(session_dir, metadata)
            if len(frames) == int(metadata["frame_count"]):
                return session_dir, metadata
        except (OSError, KeyError, TypeError, ValueError):
            continue
    return None


def encode_narrative(session_dir: Path, output: Path, duration: int, dimensions: tuple[int, int]) -> None:
    if output.is_file():
        return
    width, height = dimensions
    frames = sorted(session_dir.glob("*.jpg"))
    if not frames:
        raise FileNotFoundError(session_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-framerate", str(FPS), "-i", str(session_dir / "%06d.jpg"), "-frames:v", str(len(frames)), "-vf", f"scale={width}:{height}:flags=lanczos,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "20", "-r", str(FPS), str(output)])


def conformed_video(source: Path, output: Path, duration_ms: int, dimensions: tuple[int, int]) -> None:
    if output.is_file():
        return
    width, height = dimensions
    seconds = duration_ms / 1000
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS},format=yuv420p"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(source), "-t", f"{seconds:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "18", "-r", str(FPS), str(output)])


def cinematic_host_clip(first: Path, second: Path, duration_ms: int, output: Path, dimensions: tuple[int, int]) -> dict:
    if output.is_file():
        return {"output": str(output), "duration_ms": duration_ms, "sources": [str(first), str(second)]}
    width, height = dimensions
    remaining = duration_ms / 1000
    first_duration = float(probe(first)["format"]["duration"])
    second_duration = float(probe(second)["format"]["duration"])
    requested: list[tuple[Path, float]] = []
    for source, available in ((first, first_duration), (second, second_duration), (first, first_duration), (second, second_duration)):
        if remaining <= .001: break
        amount = min(available, remaining)
        requested.append((source, amount))
        remaining -= amount
    if remaining > .05:
        raise RuntimeError(f"cinematic host footage too short by {remaining:.3f}s")
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n"]
    for source, _ in requested: args.extend(["-i", str(source)])
    filters = []
    labels = []
    for index, ((_, amount)) in enumerate(requested):
        label = f"v{index}"
        filters.append(f"[{index}:v]trim=duration={amount:.6f},setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS},format=yuv420p[{label}]")
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")
    args.extend(["-filter_complex", ";".join(filters), "-map", "[outv]", "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "18", "-r", str(FPS), str(output)])
    output.parent.mkdir(parents=True, exist_ok=True)
    run(args)
    return {"output": str(output), "duration_ms": duration_ms, "sources": [str(item[0]) for item in requested], "source_durations_ms": [round(item[1] * 1000) for item in requested], "audio_policy": "all_external_video_audio_discarded"}


def concat_picture(parts: list[Path], output: Path, dimensions: tuple[int, int]) -> None:
    if output.is_file():
        return
    list_file = output.with_suffix(".concat.txt")
    write_text(list_file, "\n".join(f"file '{path.as_posix().replace("'", "'\\''")}'" for path in parts) + "\n")
    width, height = dimensions
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-f", "concat", "-safe", "0", "-i", str(list_file), "-vf", f"scale={width}:{height},format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "18", "-r", str(FPS), str(output)])


def mux_final(picture: Path, audio: Path, output: Path) -> None:
    if output.is_file():
        return
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)])


def validate_video(path: Path, dimensions: tuple[int, int]) -> dict:
    metadata = probe(path)
    video = video_stream(metadata)
    audio = audio_stream(metadata)
    if not video or (int(video["width"]), int(video["height"])) != dimensions:
        raise RuntimeError(f"invalid video geometry: {path}")
    if video.get("codec_name") != "h264" or audio is None or audio.get("codec_name") != "aac" or int(audio.get("sample_rate", 0)) != 48000 or int(audio.get("channels", 0)) != 2:
        raise RuntimeError(f"invalid delivery streams: {path}")
    decode = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(path), "-f", "null", "NUL"], capture_output=True, text=True)
    if decode.returncode != 0 or decode.stderr.strip():
        raise RuntimeError(f"FFmpeg decode failed for {path}: {decode.stderr[-1000:]}")
    black = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(path), "-vf", "blackdetect=d=0.15:pic_th=0.98", "-an", "-f", "null", "NUL"], capture_output=True, text=True)
    black_events = [line for line in (black.stdout + black.stderr).splitlines() if "black_start:" in line]
    return {"path": str(path), "duration_seconds": float(metadata["format"]["duration"]), "width": int(video["width"]), "height": int(video["height"]), "fps": video.get("r_frame_rate"), "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name"), "audio_rate": int(audio.get("sample_rate", 0)), "audio_channels": int(audio.get("channels", 0)), "blackdetect_events": black_events, "decode_passed": True}


def measure_audio(path: Path) -> dict:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    values = {}
    for key in ("mean_volume", "max_volume"):
        for line in result.stderr.splitlines():
            if key in line: values[key] = line.split(":", 1)[1].strip()
    loudness = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=framelog=verbose", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    summary = [line.strip() for line in loudness.stderr.splitlines() if "I:" in line or "TP:" in line][-4:]
    return {"volumedetect": values, "ebur128_tail": summary}


def board(path: Path, timestamps: list[float], output: Path, dimensions: tuple[int, int]) -> None:
    with tempfile.TemporaryDirectory(prefix="cap11-board-") as directory:
        samples = []
        for index, timestamp in enumerate(timestamps):
            sample = Path(directory) / f"sample-{index}.png"
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{timestamp:.3f}", "-i", str(path), "-frames:v", "1", str(sample)])
            samples.append(sample)
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n"]
        for sample in samples: args.extend(["-i", str(sample)])
        cols = 3
        rows = math.ceil(len(samples) / cols)
        filters = [f"[{index}:v]scale={dimensions[0] // cols}:{dimensions[1] // rows}:force_original_aspect_ratio=decrease,pad={dimensions[0] // cols}:{dimensions[1] // rows}:(ow-iw)/2:(oh-ih)/2:color=black[v{index}]" for index in range(len(samples))]
        layout = "|".join(f"{(index % cols) * (dimensions[0] // cols)}_{(index // cols) * (dimensions[1] // rows)}" for index in range(len(samples)))
        filters.append("".join(f"[v{index}]" for index in range(len(samples))) + f"xstack=inputs={len(samples)}:layout={layout}:fill=black[out]")
        args[args.index("-n")] = "-y"
        args.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)])
        output.parent.mkdir(parents=True, exist_ok=True)
        run(args)


def build_timeline(full: dict, story_plan_h: dict, story_plan_v: dict, host_meta: dict, bumper_ms: int) -> dict:
    blocks = full["metadata"]["editorial_blocks"]
    return {
        "format": "fabuloom.cronicas-cap11-cinematic/0.1",
        "chapter_heading": full["metadata"]["chapter_heading"],
        "chapter_display_title": full["metadata"]["chapter_display_title"],
        "source_document": full["metadata"]["source_document"],
        "source_doc_sha256": full["metadata"].get("source_doc_sha256"),
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE},
        "music": {"source": str(MUSIC_SOURCE), "asset": MUSIC_SOURCE.name, "ducking": "sidechain voice-priority", "rights": "pending owner confirmation"},
        "bumper_ms": bumper_ms,
        "editorial_blocks": blocks,
        "host_cinematic": host_meta,
        "narrative_plans": {"horizontal": story_plan_h, "vertical": story_plan_v},
        "external_video_audio": "excluded",
        "word_phoneme_viseme_timing": "unavailable",
    }


def write_reports(chapter: dict, inventory: dict, full: dict, story_plan_h: dict, story_plan_v: dict, validation: dict, audio: dict, original_before: dict, original_after: dict, processing_seconds: float) -> None:
    changed = sorted(path for path, digest in original_before.items() if original_after.get(path) != digest)
    report = {
        "mission": "CRONICAS-CAP11-CIN-001",
        "title": chapter["chapter_heading"],
        "display_title": chapter["chapter_display_title"],
        "source": {"docx": str(SOURCE_DOC), "sha256": chapter["source_doc_sha256"], "paragraphs": chapter["paragraph_indices"], "text_sha256": chapter["text_sha256"], "word_count": chapter["word_count"]},
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "timing_source": "measured_wav", "word_phoneme_viseme_timing": "unavailable"},
        "music": inventory["music_alba"],
        "external_assets": {key: value for key, value in inventory.items() if key != "music_alba"},
        "manifest": {"duration_ms": full["duration_ms"], "segments": len(full["segments"]), "blocks": full["metadata"]["editorial_blocks"]},
        "plans": {"horizontal": story_plan_h, "vertical": story_plan_v},
        "validation": validation,
        "audio_measurements": audio,
        "original_episode_integrity": {"before_count": len(original_before), "after_count": len(original_after), "changed_paths": changed, "passed": not changed},
        "audio_policy": "external cinematic MP4 audio excluded with -an/video-only maps; final audio is Kokoro + Alba + local effects bed",
        "human_artistic_approval": "pending",
        "rights": "Suno music and owner-supplied external cinematic clips require confirmation before publication",
        "processing_seconds": round(processing_seconds, 3),
    }
    write_json(OUTPUT_ROOT / "reports" / "chapter11-technical-report.json", report)
    lines = [
        "# Crônicas de Topázio — Capítulo 11 — O eco que não morre",
        "",
        "## Resultado",
        "",
        f"- Duração total medida: `{full['duration_ms']} ms`.",
        f"- Segmentos Kokoro: `{len(full['segments'])}`; voz `{VOICE_ID}` / `{LANGUAGE}`.",
        "- Abertura e encerramento usam os clipes cinematográficos externos sem qualquer áudio embutido.",
        "- Narrativa utiliza Santa V5 no medalhão, RMS para a boca e apenas placas ambientais aprovadas.",
        "- Timestamps de palavras, fonemas e visemas não estão disponíveis e não foram inventados.",
        "",
        "## Áudio",
        "",
        "- Música: `Alba Quando a Luz Rasga o Céu.mp3`, sem alteração de velocidade ou tom.",
        "- Ducking voice-priority por sidechain, fade-in/out e limiter final.",
        "- Efeitos locais discretos; não duplicam nem substituem a voz.",
        "- Direitos comerciais da faixa e autorização dos clipes externos: pendentes.",
        "",
        "## Validação",
        "",
        f"- Horizontal: `{json.dumps(validation.get('horizontal'), ensure_ascii=False)}`.",
        f"- Vertical: `{json.dumps(validation.get('vertical'), ensure_ascii=False)}`.",
        f"- Integridade dos MP4s anteriores 01–10: `{'PASS' if not changed else 'FAIL'}`.",
        "- Aprovação artística humana: pendente.",
    ]
    write_text(OUTPUT_ROOT / "reports" / "chapter11-technical-report.md", "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port-horizontal", type=int, default=8791)
    parser.add_argument("--port-vertical", type=int, default=8792)
    parser.add_argument("--capture-timeout", type=float, default=3600)
    parser.add_argument("--skip-vertical", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    status("PREFLIGHT_START", next_action="validar DOCX, biblioteca e imutabilidade")
    chapter = load_chapter11()
    inventory = external_inventory()
    original_before = original_episode_hashes()
    selected = copy_assets(inventory)
    write_json(OUTPUT_ROOT / "manifest" / "source-chapter11.json", chapter)
    write_json(OUTPUT_ROOT / "assets-index" / "original-episode-hashes-before.json", original_before)
    status("PREFLIGHT_OK", next_action="sintetizar blocos host e narrativa")
    status("VOICE_START", next_action="inicializar Kokoro pm_santa")
    audio_root = OUTPUT_ROOT / "audio"
    provider = KokoroTTSProvider(output_dir=audio_root)
    try:
        intro_text = f"Saudações, Guardiões! Hoje abrimos mais uma página de O Despertar dos Cristais. O capítulo 11 se chama {chapter['chapter_display_title']}. Sentem-se comigo e vamos entrar nesta história juntos."
        outro_text = f"E assim encerramos o capítulo 11, {chapter['chapter_display_title']}. Obrigado por me acompanharem, Guardiões. A história continua no próximo capítulo. Até a próxima jornada!"
        intro = synthesize_block(provider, intro_text, "host-intro", audio_root / "host-intro")
        story = synthesize_block(provider, chapter["text"], "story-chapter11", audio_root / "story")
        outro = synthesize_block(provider, outro_text, "host-outro", audio_root / "host-outro")
    finally:
        provider.close()
    status("VOICE_OK", next_action="compor manifesto integral e legendas")
    ext_dir = OUTPUT_ROOT / "assets" / "external"
    bumper_source_h = ext_dir / EXTERNAL_NAMES["intro_horizontal"]
    bumper_source_v = ext_dir / EXTERNAL_NAMES["intro_vertical"]
    bumper_ms = int(inventory["intro_horizontal"]["duration_ms"])
    full, story_rebased, timing = merge_manifests(intro, story, outro, chapter, bumper_ms)
    full["metadata"]["source_doc_sha256"] = chapter["source_doc_sha256"]
    write_json(FULL_MANIFEST_FILE, full)
    write_json(STORY_MANIFEST_FILE, story_rebased)
    write_srt(full, OUTPUT_ROOT / "subtitles" / "chapter11.srt")
    story_start = next(item["start_ms"] for item in full["metadata"]["editorial_blocks"] if item["type"] == "STORY_CHAPTER")
    story_end = next(item["end_ms"] for item in full["metadata"]["editorial_blocks"] if item["type"] == "STORY_CHAPTER")
    status("MANIFEST_OK", next_action="preparar música Alba, efeitos e mixagem")
    voice_path = OUTPUT_ROOT / "audio" / "chapter11-full-voice.wav"
    if not voice_path.is_file(): compose_voice(full, voice_path)
    music_path = OUTPUT_ROOT / "audio" / "alba-loop.wav"
    make_music_loop(MUSIC_SOURCE, music_path, int(full["duration_ms"]))
    effects_path = OUTPUT_ROOT / "audio" / "chapter11-effects-bed.wav"
    if not effects_path.is_file(): write_sfx_bed(effects_path, int(full["duration_ms"]), [story_start, story_start + (story_end - story_start) // 3, story_start + 2 * (story_end - story_start) // 3])
    mix_path = OUTPUT_ROOT / "audio" / "chapter11-mix.wav"
    mix_audio(voice_path, music_path, effects_path, mix_path, int(full["duration_ms"]))
    status("MIX_OK", next_action="capturar e renderizar narrativa horizontal")
    story_plan_h = build_story_plan(story_rebased, selected, "horizontal")
    story_plan_v = build_story_plan(story_rebased, selected, "vertical")
    h_plan_path = OUTPUT_ROOT / "timelines" / "narrative-horizontal.json"
    v_plan_path = OUTPUT_ROOT / "timelines" / "narrative-vertical.json"
    write_json(h_plan_path, story_plan_h); write_json(v_plan_path, story_plan_v)
    narrative_h = OUTPUT_ROOT / "videos" / "narrative-horizontal-video.mp4"
    horizontal_capture = existing_capture(OUTPUT_ROOT / ".frames", "horizontal") if not narrative_h.is_file() else None
    if horizontal_capture is None and not narrative_h.is_file():
        horizontal_capture = capture_frames(h_plan_path, "horizontal", OUTPUT_ROOT / ".frames", args.port_horizontal, args.capture_timeout)
    if horizontal_capture is None:
        horizontal_capture = existing_capture(OUTPUT_ROOT / ".frames", "horizontal")
    if horizontal_capture is None:
        raise RuntimeError("não foi possível localizar captura horizontal completa")
    horizontal_story_frames, h_completion = horizontal_capture
    vertical_story_frames = None
    status("CAPTURE_HORIZONTAL_OK", next_action="renderizar narrativa horizontal")
    encode_narrative(horizontal_story_frames, narrative_h, int(story_rebased["duration_ms"]), HORIZONTAL)
    status("NARRATIVE_HORIZONTAL_OK", next_action="adaptar clipes cinematográficos e montar master horizontal")
    intro_host_h = OUTPUT_ROOT / "videos" / "host-opening-horizontal.mp4"
    outro_host_h = OUTPUT_ROOT / "videos" / "host-closing-horizontal.mp4"
    host_meta = {}
    host_meta["opening_horizontal"] = cinematic_host_clip(ext_dir / EXTERNAL_NAMES["santa_v1"], ext_dir / EXTERNAL_NAMES["santa_v2"], int(intro["duration_ms"]), intro_host_h, HORIZONTAL)
    host_meta["closing_horizontal"] = cinematic_host_clip(ext_dir / EXTERNAL_NAMES["santa_v2"], ext_dir / EXTERNAL_NAMES["santa_v1"], int(outro["duration_ms"]), outro_host_h, HORIZONTAL)
    bumper_h = OUTPUT_ROOT / "videos" / "fabuloom-intro-horizontal.mp4"
    conformed_video(bumper_source_h, bumper_h, bumper_ms, HORIZONTAL)
    picture_h = OUTPUT_ROOT / "videos" / "chapter11-horizontal-picture.mp4"
    concat_picture([bumper_h, intro_host_h, narrative_h, outro_host_h], picture_h, HORIZONTAL)
    final_h = OUTPUT_ROOT / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-horizontal.mp4"
    mux_final(picture_h, mix_path, final_h)
    horizontal_validation = validate_video(final_h, HORIZONTAL)
    horizontal_validation["audio"] = measure_audio(mix_path)
    board(final_h, [0.5, bumper_ms / 1000 + 1, (story_start + (story_end - story_start) // 2) / 1000, story_end / 1000 - 1, float(probe(final_h)["format"]["duration"]) - 3, float(probe(final_h)["format"]["duration"]) - .5], OUTPUT_ROOT / "boards" / "chapter11-horizontal-board.png", HORIZONTAL)
    status("HORIZONTAL_QA_OK", next_action="iniciar versão vertical somente após gate horizontal", details={"horizontal_validation": horizontal_validation})
    if not args.skip_vertical:
        status("CAPTURE_VERTICAL_START", next_action="capturar narrativa vertical")
        narrative_v = OUTPUT_ROOT / "videos" / "narrative-vertical-video.mp4"
        vertical_capture = existing_capture(OUTPUT_ROOT / ".frames", "vertical") if not narrative_v.is_file() else None
        if vertical_capture is None and not narrative_v.is_file():
            vertical_capture = capture_frames(v_plan_path, "vertical", OUTPUT_ROOT / ".frames", args.port_vertical, args.capture_timeout)
        if vertical_capture is None:
            vertical_capture = existing_capture(OUTPUT_ROOT / ".frames", "vertical")
        if vertical_capture is None:
            raise RuntimeError("não foi possível localizar captura vertical completa")
        vertical_story_frames, v_completion = vertical_capture
        status("CAPTURE_VERTICAL_OK", next_action="renderizar narrativa vertical")
        encode_narrative(vertical_story_frames, narrative_v, int(story_rebased["duration_ms"]), VERTICAL)
        intro_host_v = OUTPUT_ROOT / "videos" / "host-opening-vertical.mp4"
        outro_host_v = OUTPUT_ROOT / "videos" / "host-closing-vertical.mp4"
        host_meta["opening_vertical"] = cinematic_host_clip(ext_dir / EXTERNAL_NAMES["santa_v1"], ext_dir / EXTERNAL_NAMES["santa_v2"], int(intro["duration_ms"]), intro_host_v, VERTICAL)
        host_meta["closing_vertical"] = cinematic_host_clip(ext_dir / EXTERNAL_NAMES["santa_v2"], ext_dir / EXTERNAL_NAMES["santa_v1"], int(outro["duration_ms"]), outro_host_v, VERTICAL)
        bumper_v = OUTPUT_ROOT / "videos" / "fabuloom-intro-vertical.mp4"
        conformed_video(bumper_source_v, bumper_v, bumper_ms, VERTICAL)
        picture_v = OUTPUT_ROOT / "videos" / "chapter11-vertical-picture.mp4"
        concat_picture([bumper_v, intro_host_v, narrative_v, outro_host_v], picture_v, VERTICAL)
        final_v = OUTPUT_ROOT / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-vertical.mp4"
        mux_final(picture_v, mix_path, final_v)
        vertical_validation = validate_video(final_v, VERTICAL)
        vertical_validation["audio"] = measure_audio(mix_path)
        final_duration = float(probe(final_v)["format"]["duration"])
        board(final_v, [0.5, bumper_ms / 1000 + 1, (story_start + (story_end - story_start) // 2) / 1000, story_end / 1000 - 1, final_duration - 3, final_duration - .5], OUTPUT_ROOT / "boards" / "chapter11-vertical-board.png", VERTICAL)
    else:
        vertical_validation = {"status": "BLOCKED_BY_OPTION", "reason": "--skip-vertical"}
    original_after = original_episode_hashes()
    validation = {"horizontal": horizontal_validation, "vertical": vertical_validation, "audio_source_policy": "external_mp4_audio_excluded", "source_clip_scene2_used": host_meta.get("opening_horizontal", {}).get("sources", [])[1:]}
    write_json(OUTPUT_ROOT / "timelines" / "chapter11-master.json", build_timeline(full, story_plan_h, story_plan_v, host_meta, bumper_ms))
    write_json(OUTPUT_ROOT / "assets-index" / "original-episode-hashes-after.json", original_after)
    write_reports(chapter, inventory, full, story_plan_h, story_plan_v, validation, measure_audio(mix_path), original_before, original_after, time.perf_counter() - started)
    write_json(OUTPUT_ROOT / "reports" / "scene-transition-report.json", {"transitions": ["FBS bumper -> Santa cinematic opening", "Santa cinematic opening -> Santa V5 medallion narrative", "Santa V5 medallion narrative -> Santa cinematic closing"], "method": "frame-board inspection plus exact block boundaries", "lip_sync": "not_claimed_for_external_cinematic_clips; narrative mouth uses RMS only", "scene2_used": host_meta.get("opening_horizontal", {}).get("sources", [])[1:]})
    status("QA_OK", state="DONE", next_action="aguardar aprovação artística, direitos musicais e autorização dos clipes externos", details={"completed_formats": ["horizontal", "vertical"] if not args.skip_vertical else ["horizontal"], "validation": validation})
    print(json.dumps({"output_root": str(OUTPUT_ROOT), "horizontal": str(OUTPUT_ROOT / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-horizontal.mp4"), "vertical": str(OUTPUT_ROOT / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-vertical.mp4") if not args.skip_vertical else None, "duration_ms": full["duration_ms"], "processing_seconds": round(time.perf_counter() - started, 3)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
