"""Render the complete Chapter 1 cinematic episode for Cronicas de Topazio.

The episode is intentionally reproducible and local:

DOCX paragraphs 3-22 -> measured Kokoro blocks -> reusable scene registry
-> deterministic Canvas frames -> Suno ducked mix -> FFmpeg MP4.

The prior pilot audio for paragraphs 3-11 is copied into this episode as a
preserved measured source.  Only the missing chapter paragraphs and the new
editorial host text are synthesized.  No word, phoneme, or viseme timing is
invented when the provider exposes only real WAV duration.
"""

from __future__ import annotations

import argparse
from array import array
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen
import wave
import zipfile
import xml.etree.ElementTree as ET

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.scene_assets import SceneAssetRegistry
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError

from topazioverse_book1_pilot_demo import (
    _find_edge,
    _materialize_frames,
    _sha256,
    _wait_for_http,
    frame_board,
    probe,
    render_mp4,
)


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
PROJECT_ID = "topazio-book1-capitulo1-cronicas"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
PREVIOUS_PILOT = EXPORT_ROOT / "topazioverse-book1-episode1-pilot-v3"
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "scene-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1920
HEIGHT = 1080
SOURCE_PARAGRAPHS = tuple(range(3, 23))
TRANSITION_MS = 900

HOST_INTRO = """Saudações, Guardiões!

Existem mundos que nascem de grandes batalhas.
Outros, de antigas promessas.

Mas Topázio estava prestes a descobrir
que até o próprio tempo poderia parar.

Hoje, abrimos as páginas de
O Despertar dos Cristais.

E como aqui não gostamos de enrolação...
chega de conversa!

Nossa história começa agora!"""

HOST_OUTRO = """E assim, Guardiões, o primeiro sinal foi dado.

Mas o que realmente despertou naquela noite?

Essa resposta começa a tomar forma
em nossa próxima jornada.

Até o próximo capítulo!"""


def _write_json(path: Path, payload: object, *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _audio_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _load_docx_paragraphs(path: Path) -> list[str]:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs: list[str] = []
    for paragraph in root.findall(f".//{namespace}body/{namespace}p"):
        paragraphs.append("".join(node.text or "" for node in paragraph.findall(f".//{namespace}t")))
    return paragraphs


def load_chapter(path: Path = SOURCE_DOC) -> tuple[tuple[str, ...], str]:
    paragraphs = _load_docx_paragraphs(path)
    selected = []
    for index in SOURCE_PARAGRAPHS:
        if index >= len(paragraphs):
            raise ValueError(f"source paragraph {index} is missing from {path}")
        value = paragraphs[index].strip()
        if not value:
            raise ValueError(f"source paragraph {index} is empty")
        selected.append(value)
    return tuple(selected), "\n\n".join(selected)


def _segment_metadata(segment: dict) -> dict:
    value = segment.get("metadata", {})
    return value if isinstance(value, dict) else {}


def _local_audio_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"expected local WAV URI, got {uri!r}")
    return Path(parsed.path.lstrip("/"))


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
    _write_json(manifest_path, manifest, overwrite=True)
    return manifest


def _copy_reused_story(project_root: Path, *, overwrite: bool) -> list[dict]:
    source_manifest = json.loads((PREVIOUS_PILOT / "manifest.json").read_text(encoding="utf-8"))
    reused_dir = project_root / "audio" / "reused-story"
    reused_dir.mkdir(parents=True, exist_ok=True)
    output: list[dict] = []
    ordinal = 0
    for source in source_manifest["segments"]:
        metadata = _segment_metadata(source)
        if metadata.get("editorial_block") != "STORY_CHAPTER":
            continue
        source_path = _local_audio_path(source["audio_uri"])
        target = reused_dir / f"chapter1-reused-{ordinal:04d}.wav"
        if not target.exists() or overwrite:
            shutil.copyfile(source_path, target)
        segment = copy.deepcopy(source)
        segment["audio_uri"] = _audio_uri(target)
        segment["metadata"] = dict(metadata)
        segment["metadata"]["source_paragraph"] = int(metadata.get("paragraph_index", -1)) + 3
        segment["metadata"]["source_audio"] = "topazioverse-book1-episode1-pilot-v3"
        segment["metadata"]["editorial_block"] = "STORY_CHAPTER"
        segment["track_id"] = "voice"
        output.append(segment)
        ordinal += 1
    if len(output) != 46:
        raise ValueError(f"expected 46 reusable pilot story segments, found {len(output)}")
    return output


def _adjust_new_story_segments(manifest: dict) -> list[dict]:
    output = []
    for source in manifest["segments"]:
        segment = copy.deepcopy(source)
        metadata = _segment_metadata(segment)
        metadata["source_paragraph"] = int(metadata.get("paragraph_index", -1)) + 12
        metadata["editorial_block"] = "STORY_CHAPTER"
        segment["metadata"] = metadata
        output.append(segment)
    return output


def _adjust_editorial_segments(manifest: dict, block: str) -> list[dict]:
    output = []
    for source in manifest["segments"]:
        segment = copy.deepcopy(source)
        metadata = _segment_metadata(segment)
        metadata["editorial_block"] = block
        segment["metadata"] = metadata
        output.append(segment)
    return output


def compose_episode_manifest(intro: dict, old_story: list[dict], new_story: list[dict], outro: dict) -> dict:
    blocks = [
        ("HOST_INTRO", _adjust_editorial_segments(intro, "HOST_INTRO")),
        ("STORY_CHAPTER", old_story + new_story),
        ("HOST_OUTRO", _adjust_editorial_segments(outro, "HOST_OUTRO")),
    ]
    segments: list[dict] = []
    cursor = 0
    editorial_blocks = []
    for block_index, (block_name, source_segments) in enumerate(blocks):
        block_start = cursor
        for source in source_segments:
            segment = copy.deepcopy(source)
            metadata = _segment_metadata(segment)
            duration = int(segment["duration_ms"])
            segment["start_ms"] = cursor
            segment["end_ms"] = cursor + duration
            segment["metadata"] = metadata
            segments.append(segment)
            cursor = segment["end_ms"] + int(metadata.get("pause_after_ms", 0))
        block_end = cursor
        editorial_blocks.append({"id": block_name.lower(), "type": block_name, "start_ms": block_start, "end_ms": block_end})
        if block_index < len(blocks) - 1:
            cursor += TRANSITION_MS
    if not segments:
        raise ValueError("episode contains no narration segments")
    manifest = {
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
            "source_paragraphs": list(SOURCE_PARAGRAPHS),
            "chapter_scope": "Capítulo 1 — A noite em que Topázio parou",
            "temporal_source": "measured_wav",
            "word_phoneme_viseme_timing": "unavailable",
        },
    }
    return manifest


def _segment_bounds(manifest: dict, paragraphs: set[int], *, block: str = "STORY_CHAPTER") -> tuple[int, int] | None:
    matching = [
        segment for segment in manifest["segments"]
        if _segment_metadata(segment).get("editorial_block") == block
        and int(_segment_metadata(segment).get("source_paragraph", -1)) in paragraphs
    ]
    if not matching:
        return None
    return int(matching[0]["start_ms"]), int(matching[-1]["end_ms"]) + int(_segment_metadata(matching[-1]).get("pause_after_ms", 0))


def build_scene_schedule(manifest: dict, registry: SceneAssetRegistry) -> tuple[dict, ...]:
    specs = (
        ("host-library-opening", "library", "library-base", "host_wide", "HOST_INTRO", set()),
        ("chapter-topazio-stillness", "02-vila-rios-suspensos.png", "story", "frozen_river", "STORY_CHAPTER", {3}),
        ("chapter-temple-first-crack", "03-templo-gaia-crack.png", "story", "crystal_approach", "STORY_CHAPTER", {3}),
        ("chapter-echo-cave", "04-caverna-do-eco.png", "story", "cave_push", "STORY_CHAPTER", {4, 5, 6, 7}),
        ("chapter-eternal-currents", "05-correntes-eternas.png", "story", "wind_lateral", "STORY_CHAPTER", {8, 9, 10, 11}),
        ("chapter-vordros", "06-vordros-frozen.png", "story", "snow_breath", "STORY_CHAPTER", {12}),
        ("chapter-abyssal-tide", "07-sea-corals.png", "story", "water_drift", "STORY_CHAPTER", {13}),
        ("chapter-osai-fire", "08-vulcao-osai.png", "story", "ember_pulse", "STORY_CHAPTER", {14, 15}),
        ("chapter-village-fire", "09-vila-incendio.png", "story", "fire_pan", "STORY_CHAPTER", {16, 17, 18}),
        ("chapter-aurelion-ash", "09-vila-incendio.png", "story", "ash_pull", "STORY_CHAPTER", {19, 20, 21}),
        ("chapter-seven-pulses", "03-templo-gaia-crack.png", "story", "crystal_pulse", "STORY_CHAPTER", {22}),
        ("host-library-closing", "library", "host", "host_closing", "HOST_OUTRO", set()),
    )
    blocks = manifest["metadata"]["editorial_blocks"]
    scenes: list[dict] = []
    for scene_id, image, kind, camera, block, paragraphs in specs:
        if block != "STORY_CHAPTER":
            block_entry = next(item for item in blocks if item["type"] == block)
            scenes.append({
                "id": scene_id,
                "kind": "host",
                "asset_id": "santa-library-topazioverse-v1",
                "image": "official-scenes/santa-library-topazioverse-v1/library-base.png",
                "camera": camera,
                "start_ms": block_entry["start_ms"],
                "end_ms": block_entry["end_ms"],
                "source_paragraphs": [],
            })
            continue
        bounds = _segment_bounds(manifest, paragraphs)
        if bounds is None:
            continue
        scenes.append({
            "id": scene_id,
            "kind": kind,
            "image": f"{PROJECT_ID}/assets/generated/{image}",
            "camera": camera,
            "start_ms": bounds[0],
            "end_ms": bounds[1],
            "source_paragraphs": sorted(paragraphs),
        })
    if not scenes:
        raise ValueError("no scenes were produced")
    scenes.sort(key=lambda item: (item["start_ms"], item["id"]))
    scenes[-1]["end_ms"] = manifest["duration_ms"]
    return tuple(scenes)


def compose_voice(manifest: dict, output_path: Path) -> tuple[int, array]:
    segments = manifest["segments"]
    first_path = _local_audio_path(segments[0]["audio_uri"])
    with wave.open(str(first_path), "rb") as first_wav:
        sample_rate = first_wav.getframerate()
        if (first_wav.getnchannels(), first_wav.getsampwidth()) != (1, 2):
            raise ValueError("episode requires mono PCM-16 narration WAVs")
    combined = array("h")
    written_frames = 0
    for segment in segments:
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
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(combined.tobytes())
    return sample_rate, combined


def _write_sfx_bed(path: Path, duration_ms: int) -> None:
    """Create a small deterministic stereo bed of contextual, non-verbal cues."""

    rate = 48_000
    frames = max(1, round(duration_ms * rate / 1000))
    left = [0.0] * frames
    right = [0.0] * frames
    events = (
        (4.0, 1.8, "crystal"),
        (32.0, 2.8, "water"),
        (82.0, 2.5, "wind"),
        (112.0, 2.0, "ice"),
        (137.0, 2.7, "water"),
        (166.0, 2.2, "fire"),
        (194.0, 1.6, "impact"),
    )
    for start, length, kind in events:
        first = min(frames, max(0, round(start * rate)))
        last = min(frames, first + round(length * rate))
        for index in range(first, last):
            progress = (index - first) / max(1, last - first - 1)
            envelope = min(1.0, progress * 16.0, (1.0 - progress) * 7.0)
            t = (index - first) / rate
            if kind == "crystal":
                value = math.sin(2 * math.pi * (720 + 360 * progress) * t) * 0.08
            elif kind == "water":
                value = (math.sin(2 * math.pi * 178 * t) + math.sin(2 * math.pi * 263 * t)) * 0.025
            elif kind == "wind":
                value = math.sin(2 * math.pi * 58 * t) * 0.045 + math.sin(2 * math.pi * 111 * t) * 0.015
            elif kind == "ice":
                value = math.sin(2 * math.pi * (260 + 800 * progress) * t) * 0.04
            elif kind == "fire":
                value = math.sin(2 * math.pi * 96 * t) * 0.05 + math.sin(2 * math.pi * 191 * t) * 0.02
            else:
                value = math.sin(2 * math.pi * 74 * t) * 0.07
            left[index] += value * envelope
            right[index] += value * envelope * (0.86 if kind in {"wind", "water"} else 1.0)
    pcm = array("h")
    for l, r in zip(left, right):
        pcm.append(max(-32767, min(32767, round(l * 32767))))
        pcm.append(max(-32767, min(32767, round(r * 32767))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def _music_duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def make_crossfaded_music_loop(source: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    source_duration = _music_duration(source)
    if duration <= source_duration:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(source), "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2", str(output)]
        subprocess.run(command, check=True)
        return
    crossfade = min(6.0, max(1.0, source_duration / 12))
    inputs = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n"]
    for _ in range(4):
        inputs.extend(["-i", str(source)])
    graph = []
    for index in range(4):
        graph.append(f"[{index}:a]aresample=48000,atrim=0:{source_duration:.6f},asetpts=PTS-STARTPTS[m{index}]")
    graph.append(f"[m0][m1]acrossfade=d={crossfade:.3f}:c1=tri:c2=tri[x1]")
    graph.append(f"[x1][m2]acrossfade=d={crossfade:.3f}:c1=tri:c2=tri[x2]")
    graph.append(f"[x2][m3]acrossfade=d={crossfade:.3f}:c1=tri:c2=tri[music]")
    command = inputs + ["-filter_complex", ";".join(graph), "-map", "[music]", "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2", str(output)]
    subprocess.run(command, check=True)


def mix_audio(voice: Path, music_loop: Path, sfx: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.075,atrim=duration={duration:.3f},afade=t=in:st=0:d=2,afade=t=out:st={max(0, duration - 4):.3f}:d=4[music];"
        "[music][det]sidechaincompress=threshold=0.025:ratio=8:attack=35:release=700:makeup=1[ducked];"
        f"[2:a]aresample=48000,volume=0.16,atrim=duration={duration:.3f}[sfx];"
        "[voice_st][ducked][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.92[out]"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-i", str(voice), "-i", str(music_loop), "-i", str(sfx),
        "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
    ]
    subprocess.run(command, check=True)


def _wait_capture(url: str, timeout: float) -> None:
    _wait_for_http(url, timeout)


def capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env["FABULOOM_WORKSPACE_ROOT"] = str(FABULOOM_ROOT)
    env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT)
    server = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)],
        cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_capture(f"http://127.0.0.1:{port}/capture-topazio-book1-chapter1.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter1.html?session={session}&timeline=/exports/{relative}&fps={FPS}"
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
            _materialize_frames(session_dir, completion)
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


def write_srt(manifest: dict, path: Path) -> None:
    def stamp(ms: int) -> str:
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = []
    for index, segment in enumerate(manifest["segments"], start=1):
        lines = "\n".join(textwrap.wrap(segment["text"], width=68, break_long_words=False))
        blocks.append(f"{index}\n{stamp(segment['start_ms'])} --> {stamp(segment['end_ms'])}\n{lines}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def copy_scene_assets(project_root: Path, *, overwrite: bool) -> None:
    target = project_root / "assets" / "previous-approved"
    target.mkdir(parents=True, exist_ok=True)
    for source in (
        EXPORT_ROOT / "cronicas-de-topazio-channel-intro" / "assets" / "pilot" / "topazio-city.png",
        EXPORT_ROOT / "cronicas-de-topazio-channel-intro" / "assets" / "pilot" / "thaurion-echo-cave.png",
        EXPORT_ROOT / "cronicas-de-topazio-channel-intro" / "assets" / "pilot" / "zephirion-currents.png",
        EXPORT_ROOT / "cronicas-de-topazio-channel-intro" / "assets" / "pilot" / "vordros-mountains.png",
    ):
        if source.is_file():
            destination = target / source.name
            if not destination.exists() or overwrite:
                shutil.copyfile(source, destination)


def write_reports(project_root: Path, manifest: dict, timeline: dict, video_probe: dict, audio_probe: dict, *, processing_seconds: float, source_hash: str, library_path: Path) -> None:
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    scene_lines = "\n".join(f"- `{scene['id']}`: `{scene['start_ms']}–{scene['end_ms']} ms`, câmera `{scene['camera']}`, fonte `{scene['source_paragraphs']}`" for scene in timeline["scenes"])
    (reports / "technical-report.md").write_text(
        "# Crônicas de Topázio — Livro 1, Capítulo 1\n\n"
        "## Escopo editorial\n\n"
        "O episódio usa os parágrafos 3–22 do DOCX original, sem resumir, reordenar ou inserir diálogos. A abertura e o encerramento usam os textos editoriais aprovados da missão.\n\n"
        f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`\n"
        f"- Segmentos medidos: `{len(manifest['segments'])}`\n"
        f"- Duração temporal: `{manifest['duration_ms']} ms`\n"
        f"- Cenas: `{len(timeline['scenes'])}`\n"
        f"- Processamento local: `{processing_seconds:.2f} s`\n"
        f"- Hash do trecho textual exportado: `{source_hash}`\n"
        f"- Biblioteca: `santa-library-topazioverse-v1` -> `{library_path}`\n"
        "- Timestamps de palavras/fonemas/visemas: indisponíveis; legendas e boca usam apenas limites de segmentos e RMS.\n"
        "- Estado: pendente de aprovação artística humana.\n\n"
        "## Cenas\n\n" + scene_lines + "\n",
        encoding="utf-8",
    )
    (reports / "mix-report.md").write_text(
        "# Relatório de trilha\n\n"
        f"- Música: `{MUSIC}`; origem Suno, faixa preservada e sem alteração de velocidade ou tom.\n"
        "- Ducking voz→música: ratio 8, ataque 35 ms, release 700 ms.\n"
        "- Efeitos: cama procedural local com eventos de cristal, água, vento, gelo, fogo e impacto; volume reduzido e limiter final.\n"
        "- Limiter final: 0.92; saída PCM 48 kHz estéreo antes do AAC.\n"
        "- Direitos comerciais da fonte Suno: confirmação necessária antes de publicação.\n"
        f"- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n"
        f"- FFprobe mix: `{json.dumps(audio_probe, ensure_ascii=False, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (reports / "scene-library-reuse.md").write_text(
        "# Biblioteca de cenários\n\n"
        "O cenário oficial de Santa foi registrado por ID estável e resolvido pelo registry público. O PNG-base não contém Santa; a composição do avatar ocorre no Canvas durante captura.\n\n"
        "- ID: `santa-library-topazioverse-v1`\n"
        f"- Arquivo local: `{library_path}`\n"
        f"- SHA-256: `{_sha256(library_path)}`\n"
        "- Reutilizações no episódio: abertura e encerramento; nenhuma regeneração foi necessária.\n"
        "- Registro: `assets/scene-registry.json`\n"
        "- Arte: placa conceitual original, aguardando aprovação artística humana.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8774)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    if not SOURCE_DOC.is_file():
        raise FileNotFoundError(SOURCE_DOC)
    if not MUSIC.is_file():
        raise FileNotFoundError(MUSIC)
    chapter_paragraphs, chapter_text = load_chapter()
    project_root = PROJECT_ROOT
    for directory in (project_root / "audio", project_root / "timeline", project_root / "captures", project_root / ".frames", project_root / "reports", project_root / "assets" / "generated"):
        directory.mkdir(parents=True, exist_ok=True)
    copy_scene_assets(project_root, overwrite=args.overwrite)
    library_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = library_registry.resolve("santa-library-topazioverse-v1")
    excerpt_path = project_root / "timeline" / "source-excerpt.txt"
    excerpt_path.write_text(chapter_text + "\n", encoding="utf-8")
    manifest_path = project_root / "manifest.json"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        provider = KokoroTTSProvider(output_dir=project_root / "audio", allow_overwrite=args.overwrite)
        try:
            intro = _synthesize_block(provider, HOST_INTRO, f"{PROJECT_ID}-host-intro", project_root / "audio" / "host-intro", overwrite=args.overwrite)
            outro = _synthesize_block(provider, HOST_OUTRO, f"{PROJECT_ID}-host-outro", project_root / "audio" / "host-outro", overwrite=args.overwrite)
            new_story_text = "\n\n".join(chapter_paragraphs[9:])
            new_story = _synthesize_block(provider, new_story_text, f"{PROJECT_ID}-story-continued", project_root / "audio" / "story-continued", overwrite=args.overwrite)
            old_story = _copy_reused_story(project_root, overwrite=args.overwrite)
            manifest = compose_episode_manifest(intro, old_story, _adjust_new_story_segments(new_story), outro)
            _write_json(manifest_path, manifest, overwrite=True)
            print(f"tts_provider={provider.provider_id}")
            print(f"tts_model={provider.model_id}")
            print(f"tts_model_revision={provider.model_revision}")
            print(f"tts_model_load_count={provider.model_load_count}")
        except (TTSError, NarrationSynthesisError):
            raise
        finally:
            provider.close()
    timeline_path = project_root / "timeline" / f"{PROJECT_ID}.json"
    timeline = {
        "format": "fabuloom.topazioverse-chapter/0.1",
        "title": "Crônicas de Topázio — Livro 1 — Capítulo 1: A noite em que Topázio parou",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(SOURCE_PARAGRAPHS),
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "scene_registry": "assets/scene-registry.json",
        "library_asset_id": "santa-library-topazioverse-v1",
        "narrator": "Santa V5",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "scenes": list(build_scene_schedule(manifest, library_registry)),
    }
    _write_json(timeline_path, timeline, overwrite=True)
    write_srt(manifest, project_root / "timeline" / f"{PROJECT_ID}.srt")
    voice_path = project_root / "audio" / f"{PROJECT_ID}-voice.wav"
    sample_rate, _ = compose_voice(manifest, voice_path)
    sfx_path = project_root / "audio" / f"{PROJECT_ID}-sfx-bed.wav"
    if not sfx_path.exists() or args.overwrite:
        _write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop_path = project_root / "audio" / f"{PROJECT_ID}-music-loop.wav"
    make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    mix_path = project_root / "audio" / f"{PROJECT_ID}-mix.wav"
    mix_audio(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    if args.reuse_capture:
        completed = sorted((project_root / ".frames").glob("capture-*/complete.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not completed:
            raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = completed[0].parent
        completion = json.loads(completed[0].read_text(encoding="utf-8"))
        _materialize_frames(session_dir, completion)
    else:
        session_dir, completion = capture_frames(timeline_path, project_root / ".frames", port=args.port, timeout_seconds=args.capture_timeout)
    video_path = project_root / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo1.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
    board_path = project_root / "captures" / "chapter1-frames.png"
    frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
    video_probe = probe(video_path)
    audio_probe = probe(mix_path)
    source_hash = _sha256(excerpt_path)
    write_reports(project_root, manifest, timeline, video_probe, audio_probe, processing_seconds=time.perf_counter() - started, source_hash=source_hash, library_path=library_path)
    report = {
        "project": PROJECT_ID,
        "video": str(video_path),
        "manifest": str(manifest_path),
        "timeline": str(timeline_path),
        "frame_board": str(board_path),
        "duration_ms": manifest["duration_ms"],
        "segments": len(manifest["segments"]),
        "scenes": len(timeline["scenes"]),
        "source_paragraphs": list(SOURCE_PARAGRAPHS),
        "sample_rate": sample_rate,
        "video_probe": video_probe,
        "audio_probe": audio_probe,
        "library_id": "santa-library-topazioverse-v1",
        "library_sha256": _sha256(library_path),
        "timing_source": "measured_wav_segments",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "state": "completed_pending_human_artistic_review",
    }
    _write_json(project_root / "reports" / "episode-result.json", report, overwrite=True)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
