"""Produce the Chapter 3 cinematic episode using the approved Santa V5 only.

The chapter boundaries are read from the source DOCX. Story visuals are
environment-only plates; all character identity is provided by the approved
Santa library medallion through the existing deterministic capture pipeline.
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
from urllib.parse import urlencode

import topazio_book1_chapter2_cronicas_demo as base
import topazio_book1_chapter1_cronicas_demo as v1

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.scene_assets import SceneAssetRegistry
from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError
from topazio_book1_chapter1_cronicas_v2_demo import audit_santa_visibility, mix_audio_v2


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
PROJECT_ID = "topazio-book1-capitulo3-cronicas"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "scene-registry.json"
CHARACTER_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "character-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
TRANSITION_MS = 900
APPROVED_CHARACTER_ID = "santa-v5-base"

HOST_INTRO = """Saudações, Guardiões!

Depois da cicatriz, Gaia finalmente recebe os chamados.
Sete caminhos começam a apontar para o mesmo templo.

Hoje, abrimos o terceiro capítulo de
O Despertar dos Cristais:

Sete caminhos para Gaia.

Entrem na história."""

HOST_OUTRO = """E assim, Guardiões, os caminhos chegaram ao mesmo lugar.

O cristal abriu uma porta que ninguém esperava encontrar.

No próximo capítulo, vamos descobrir o que atravessou essa abertura.

Até a próxima jornada!"""

# Each plate is an environment or object. Reusing a plate changes only the
# camera treatment; it never introduces an unapproved story character.
SCENE_SPECS = (
    ("shot-001-gaia-gate", "01-gaia-gate.png", "gate_dawn"),
    ("shot-002-crystal-towers", "02-crystal-between-towers.png", "crystal_reveal"),
    ("shot-003-blue-call", "03-blue-call-mark.png", "mark_push"),
    ("shot-004-frosted-towers", "04-frosted-towers.png", "frost_lateral"),
    ("shot-005-crossed-blades", "05-crossed-blades.png", "blade_parapet"),
    ("shot-006-torches", "06-torches-ignite.png", "torch_pulse"),
    ("shot-007-light-reflection", "07-light-reflection.png", "beam_descend"),
    ("shot-008-mosaic-corridor", "08-mosaic-corridor.png", "mosaic_push"),
    ("shot-009-central-chamber", "09-central-chamber.png", "chamber_approach"),
    ("shot-010-crystal-crack", "10-crystal-crack.png", "crystal_shock"),
    ("shot-011-elemental-aftermath", "11-elemental-aftermath.png", "elemental_cross"),
    ("shot-012-black-fissure", "12-black-fissure.png", "fissure_open"),
    ("shot-013-gate-reprise", "01-gaia-gate.png", "gate_reprise"),
    ("shot-014-elemental-pulse", "11-elemental-aftermath.png", "elemental_pulse"),
    ("shot-015-golden-reflection", "07-light-reflection.png", "door_reflection"),
    ("shot-016-chamber-wide", "09-central-chamber.png", "chamber_wide"),
    ("shot-017-aftermath", "11-elemental-aftermath.png", "aftermath_pull"),
    ("shot-018-voice-crystal", "10-crystal-crack.png", "voice_crystal"),
    ("shot-019-fissure-tilt", "12-black-fissure.png", "fissure_tilt"),
    ("shot-020-final-breath", "12-black-fissure.png", "fissure_final"),
)


def _sync_base_globals() -> None:
    """Let the existing Chapter 2 helpers operate on this episode."""
    base.FABULOOM_ROOT = FABULOOM_ROOT
    base.EXPORT_ROOT = EXPORT_ROOT
    base.PROJECT_ID = PROJECT_ID
    base.PROJECT_ROOT = PROJECT_ROOT
    base.SOURCE_DOC = SOURCE_DOC
    base.MUSIC = MUSIC
    base.REGISTRY = REGISTRY
    base.CHARACTER_REGISTRY_PATH = CHARACTER_REGISTRY_PATH
    base.VOICE_ID = VOICE_ID
    base.LANGUAGE = LANGUAGE
    base.TRANSITION_MS = TRANSITION_MS
    base.APPROVED_CHARACTER_ID = APPROVED_CHARACTER_ID
    base.SCENE_SPECS = SCENE_SPECS


def load_chapter3(path: Path = SOURCE_DOC) -> tuple[tuple[str, ...], str, dict[str, object]]:
    paragraphs = base._load_docx_paragraphs(path)
    heading = next(index for index, value in enumerate(paragraphs) if base._chapter_heading(value, 3))
    next_heading = next(index for index in range(heading + 1, len(paragraphs)) if base._chapter_heading(paragraphs[index], 4))
    selected = tuple(value.strip() for value in paragraphs[heading + 1:next_heading] if value.strip())
    if (heading, next_heading, len(selected)) != (47, 107, 58):
        raise ValueError(f"unexpected Chapter 3 boundaries: heading={heading}, next={next_heading}, count={len(selected)}")
    base.SOURCE_PARAGRAPH_START = heading + 1
    base.SOURCE_PARAGRAPH_END_EXCLUSIVE = next_heading - 1
    base.SOURCE_CHAPTER_TITLE = paragraphs[heading].strip()
    text = "\n\n".join(selected)
    return selected, text, {
        "title": base.SOURCE_CHAPTER_TITLE,
        "heading_paragraph": heading,
        "first_narrative_paragraph": heading + 1,
        "last_narrative_paragraph": next_heading - 2,
        "end_separator_paragraph": next_heading - 1,
        "next_chapter_heading_paragraph": next_heading,
        "end_exclusive": next_heading - 1,
        "paragraph_count": len(selected),
        "text_characters": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _synthesize_block(provider: KokoroTTSProvider, text: str, narration_id: str, output_dir: Path, *, overwrite: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    run = synthesize_narration(
        provider, text, narration_id=narration_id, manifest_id=narration_id,
        timeline_id=f"{narration_id}-timeline", language=LANGUAGE, voice_id=VOICE_ID,
        output_dir=output_dir, max_chars=360,
    )
    manifest = json.loads(serialize_manifest(run.manifest))
    manifest["metadata"]["editorial_block"] = narration_id
    _write_json(manifest_path, manifest)
    return manifest


def compose_episode_manifest(intro: dict, story: dict, outro: dict) -> dict:
    base.PROJECT_ID = PROJECT_ID
    base.SOURCE_PARAGRAPH_START = 48
    base.SOURCE_PARAGRAPH_END_EXCLUSIVE = 106
    base.SOURCE_CHAPTER_TITLE = "Capítulo 3 — Sete caminhos para Gaia"
    base.HOST_INTRO = HOST_INTRO
    base.HOST_OUTRO = HOST_OUTRO
    return base.compose_episode_manifest(intro, story, outro)


def _copy_generated_assets() -> None:
    target = PROJECT_ROOT / "assets" / "generated"
    required = [name for _, name, _ in SCENE_SPECS]
    missing = [name for name in sorted(set(required)) if not (target / name).is_file()]
    if missing:
        raise FileNotFoundError("Chapter 3 environment plates missing from workspace: " + ", ".join(missing))


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
        "--port", str(port), "--capture-dir", str(frames_root),
    ], cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url_root = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter2.html"
        v1._wait_for_http(url_root, 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        query = urlencode({
            "session": session,
            "timeline": f"/exports/{relative}",
            "fps": FPS,
            "chapterLabel": "CAPÍTULO 3 · SETE CAMINHOS",
            "chapterNumber": "3",
            "captureMode": PROJECT_ID,
        })
        url = f"{url_root}?{query}"
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
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    blocks = []
    for index, segment in enumerate(manifest["segments"], 1):
        blocks.append(f"{index}\n{stamp(segment['start_ms'])} --> {stamp(segment['end_ms'])}\n{segment['text']}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _write_reports(project_root: Path, manifest: dict, timeline: dict, video_probe: dict, mix_probe: dict, *, source_meta: dict, library_path: Path, library_sha256: str, character_registry: CharacterRegistry, visibility: dict, processing_seconds: float) -> None:
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    draft_ids = [item for item in character_registry.ids() if item not in character_registry.approved_ids()]
    (reports / "technical-report.md").write_text(
        "# Missão 028 — Crônicas de Topázio, Livro 1, Capítulo 3\n\n"
        f"- Título-fonte: `{source_meta['title']}`\n- Parágrafos narrativos: `{source_meta['first_narrative_paragraph']}–{source_meta['last_narrative_paragraph']}`; separador `{source_meta['end_separator_paragraph']}`; Capítulo 4 `{source_meta['next_chapter_heading_paragraph']}`\n"
        f"- Hash UTF-8 do recorte: `{source_meta['text_sha256']}`\n- Caracteres: `{source_meta['text_characters']}`\n- Segmentos Kokoro medidos: `{len(manifest['segments'])}`\n"
        f"- Planos: `{len(timeline['scenes'])}` (20 story + host opening/closing)\n- Duração: `{manifest['duration_ms']} ms`\n- Processamento local: `{processing_seconds:.2f} s`\n- Voz: `{VOICE_ID}` / `{LANGUAGE}`\n"
        "- Timestamps de palavra/fonema/visema: indisponíveis; captions e boca usam somente segmentos medidos e RMS.\n- Estado: pendente de aprovação artística humana.\n\n## Política de personagens\n\n"
        f"- Única identidade autorizada: `{APPROVED_CHARACTER_ID}`.\n- Identidades DRAFT bloqueadas: `{draft_ids}`.\n- Cenas de história: environment-only; nenhum guardião DRAFT foi selecionado ou renderizado.\n",
        encoding="utf-8",
    )
    santa_path = character_registry.resolve(APPROVED_CHARACTER_ID)
    (reports / "character-policy-report.md").write_text(
        "# Política de identidade visual\n\n"
        f"- Registry: `assets/character-registry.json`\n- Santa: `{APPROVED_CHARACTER_ID}` / APPROVED\n- Arquivo Santa verificado: `{santa_path}`\n"
        f"- SHA-256 Santa: `{hashlib.sha256(santa_path.read_bytes()).hexdigest()}`\n- DRAFTs registrados e bloqueados: `{', '.join(draft_ids)}`\n"
        "- A composição usa `CharacterRegistry.require_approved`; qualquer status diferente de APPROVED falha antes da composição.\n",
        encoding="utf-8",
    )
    (reports / "scene-library-reuse.md").write_text(
        "# Reuso da biblioteca oficial\n\n"
        "A biblioteca `santa-library-topazioverse-v1` foi resolvida pelo registro estável e reutilizada na abertura, no encerramento e no medalhão do narrador.\n\n"
        f"- Caminho resolvido: `{library_path}`\n- SHA-256: `{library_sha256}`\n- Regeneração: `não`\n",
        encoding="utf-8",
    )
    (reports / "mix-report.md").write_text(
        "# Mixagem do Capítulo 3\n\n"
        f"- Música: `{MUSIC}`; origem Suno; velocidade e tom preservados.\n- Ducking: sidechain voz→música, ratio 5, ataque 45 ms, release 650 ms, base musical 0.13.\n"
        "- SFX: cama procedural existente, volume 0.12; limiter final 0.90.\n- Direitos comerciais Suno: confirmação necessária antes de publicação.\n"
        f"- FFprobe mix: `{json.dumps(mix_probe, ensure_ascii=False, sort_keys=True)}`\n- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (reports / "santa-visibility-report.json").write_text(json.dumps(visibility, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--capture-timeout", type=float, default=2400)
    args = parser.parse_args()
    _sync_base_globals()
    chapter_paragraphs, chapter_text, source_meta = load_chapter3()
    if not SOURCE_DOC.is_file():
        raise FileNotFoundError(SOURCE_DOC)
    if not MUSIC.is_file():
        raise FileNotFoundError(MUSIC)
    for directory in (PROJECT_ROOT / "audio", PROJECT_ROOT / "timeline", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports", PROJECT_ROOT / "videos", PROJECT_ROOT / ".frames", PROJECT_ROOT / "assets" / "generated"):
        directory.mkdir(parents=True, exist_ok=True)
    _copy_generated_assets()
    scene_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    library_sha256 = hashlib.sha256(library_path.read_bytes()).hexdigest()
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    approved = character_registry.require_approved(APPROVED_CHARACTER_ID)
    character_registry.resolve(approved.id)
    excerpt_path = PROJECT_ROOT / "timeline" / "chapter3-source-excerpt.txt"
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
        "title": f"Crônicas de Topázio — Livro 1 — {source_meta['title']}",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(range(48, 106)),
        "source_paragraph_end_separator": 106,
        "next_chapter_heading_paragraph": 107,
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
        "scenes": list(base.build_scene_schedule(manifest, library_path, library_sha256)),
    }
    _write_json(timeline_path, timeline)
    _write_srt(manifest, PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.srt")
    voice_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-voice.wav"
    sample_rate = base.compose_voice(manifest, voice_path)
    sfx_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-sfx-bed.wav"
    if not sfx_path.exists() or args.overwrite:
        v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-music-loop.wav"
    v1.make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    mix_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-mix.wav"
    mix_audio_v2(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]))
    if args.reuse_capture:
        completed = sorted((PROJECT_ROOT / ".frames").glob("capture-*/complete.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not completed:
            raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = completed[0].parent
        completion = json.loads(completed[0].read_text(encoding="utf-8"))
        v1._materialize_frames(session_dir, completion)
    else:
        session_dir, completion = _capture_frames(timeline_path, PROJECT_ROOT / ".frames", port=args.port, timeout_seconds=args.capture_timeout)
    video_path = PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo3.mp4"
    v1.render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
    board_path = PROJECT_ROOT / "captures" / "chapter3-frames.png"
    v1.frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
    video_probe = v1.probe(video_path)
    mix_probe = v1.probe(mix_path)
    visibility = audit_santa_visibility(session_dir, timeline["scenes"], frame_count=int(completion["frame_count"]))
    visibility["scene_count"] = len(timeline["scenes"])
    visibility["passed"] = bool(visibility["passed"] and visibility["scene_count"] == len(timeline["scenes"]))
    _write_reports(PROJECT_ROOT, manifest, timeline, video_probe, mix_probe, source_meta=source_meta, library_path=library_path, library_sha256=library_sha256, character_registry=character_registry, visibility=visibility, processing_seconds=time.perf_counter() - started)
    report = {
        "project": PROJECT_ID, "video": str(video_path), "manifest": str(manifest_path), "timeline": str(timeline_path), "frame_board": str(board_path),
        "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "scenes": len(timeline["scenes"]), "source": source_meta,
        "sample_rate": sample_rate, "video_probe": video_probe, "audio_probe": mix_probe, "library_id": "santa-library-topazioverse-v1", "library_sha256": library_sha256,
        "approved_character_id": APPROVED_CHARACTER_ID, "draft_character_rendering": "blocked", "story_visual_policy": "environment_only",
        "timing_source": "measured_wav_segments", "mouth_source": "pcm16_rms_envelope", "word_phoneme_viseme_timing": "unavailable", "santa_visibility": visibility,
        "state": "completed_pending_human_artistic_review",
    }
    _write_json(PROJECT_ROOT / "reports" / "episode-result.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
