"""Produce the Chapter 4 cinematic episode with the approved Santa V5 only.

This runner reuses the Chapter 2/3 narration, Canvas and FFmpeg helpers. It
changes only the DOCX range, editorial host text, environment storyboard and
chapter metadata; story characters remain environment-only and DRAFT-blocked.
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
import re

import topazio_book1_chapter3_cronicas_demo as m3

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.scene_assets import SceneAssetRegistry
from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
PROJECT_ID = "topazio-book1-capitulo4-cronicas"
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

No capítulo anterior, uma abertura impossível surgiu sob o cristal.
Agora, em Gaia, sete caminhos precisam aprender a conversar antes que uma nova ameaça encontre passagem.

Hoje, abrimos o quarto capítulo de
O Despertar dos Cristais:

O círculo dos ausentes.

Preparem-se. A história continua."""

HOST_OUTRO = """E assim, Guardiões, a batalha terminou — mas o círculo deixou mais perguntas do que respostas.

Quando a sombra separa as coisas, até uma lembrança pode se tornar perigo.

No próximo capítulo, vamos acompanhar os sinais que surgiram depois desta noite.

Até a próxima jornada!"""


SCENE_SPECS = (
    ("shot-001-circular-scar", "01-circular-scar.png", "scar_reveal"),
    ("shot-002-crystal-ring", "02-crystal-ring.png", "crystal_orbit"),
    ("shot-003-eight-line-rupture", "03-eight-line-rupture.png", "rupture_push"),
    ("shot-004-stone-map", "11-stone-map.png", "map_drift"),
    ("shot-005-observatory-signals", "09-observatory-signals.png", "signals_pan"),
    ("shot-006-cracked-doorway", "12-cracked-doorway.png", "door_approach"),
    ("shot-007-east-gate-attack", "04-east-gate-attack.png", "gate_shake"),
    ("shot-008-frost-gate", "05-frost-gate.png", "frost_sweep"),
    ("shot-009-tower-fire-rings", "06-tower-fire-rings.png", "fire_rings"),
    ("shot-010-black-water", "07-black-water-trident.png", "water_pull"),
    ("shot-011-courtyard-aftermath", "08-courtyard-aftermath.png", "aftermath_wide"),
    ("shot-012-crystal-strategy", "02-crystal-ring.png", "crystal_lateral"),
    ("shot-013-gate-pressure", "04-east-gate-attack.png", "gate_push"),
    ("shot-014-fire-barrier", "06-tower-fire-rings.png", "fire_lateral"),
    ("shot-015-water_release", "07-black-water-trident.png", "water_burst"),
    ("shot-016-seven-return", "08-courtyard-aftermath.png", "return_pull"),
    ("shot-017-night-observatory", "13-aerial-temple-storm.png", "night_aerial"),
    ("shot-018-black-mask", "10-mask-scythe-parapet.png", "mask_reveal"),
    ("shot-019-map-warning", "11-stone-map.png", "map_tilt"),
    ("shot-020-next-threshold", "12-cracked-doorway.png", "threshold_fade"),
)


def _sync_globals() -> None:
    """Configure both imported helper layers for this episode."""
    engine = m3.base
    for module in (m3, engine):
        module.FABULOOM_ROOT = FABULOOM_ROOT
        module.EXPORT_ROOT = EXPORT_ROOT
        module.PROJECT_ID = PROJECT_ID
        module.PROJECT_ROOT = PROJECT_ROOT
        module.SOURCE_DOC = SOURCE_DOC
        module.MUSIC = MUSIC
        module.REGISTRY = REGISTRY
        module.CHARACTER_REGISTRY_PATH = CHARACTER_REGISTRY_PATH
        module.VOICE_ID = VOICE_ID
        module.LANGUAGE = LANGUAGE
        module.TRANSITION_MS = TRANSITION_MS
        module.APPROVED_CHARACTER_ID = APPROVED_CHARACTER_ID
        module.SCENE_SPECS = SCENE_SPECS
    m3.SOURCE_PARAGRAPH_START = 108
    m3.SOURCE_PARAGRAPH_END_EXCLUSIVE = 179
    m3.SOURCE_CHAPTER_TITLE = "Capítulo 4 — O círculo dos ausentes"
    engine.SOURCE_PARAGRAPH_START = 108
    engine.SOURCE_PARAGRAPH_END_EXCLUSIVE = 179
    engine.SOURCE_CHAPTER_TITLE = "Capítulo 4 — O círculo dos ausentes"


def load_chapter4(path: Path = SOURCE_DOC) -> tuple[tuple[str, ...], str, dict[str, object]]:
    paragraphs = m3.base._load_docx_paragraphs(path)
    heading = next(index for index, value in enumerate(paragraphs) if m3.base._chapter_heading(value, 4))
    next_heading = next(index for index in range(heading + 1, len(paragraphs)) if m3.base._chapter_heading(paragraphs[index], 5))
    raw = paragraphs[heading + 1:next_heading]
    selected = tuple(value.strip() for value in raw if value.strip())
    if (heading, next_heading, len(selected)) != (107, 180, 71):
        raise ValueError(f"unexpected Chapter 4 boundaries: heading={heading}, next={next_heading}, count={len(selected)}")
    if next_heading - heading - 1 != 72:
        raise ValueError("Chapter 4 raw paragraph range changed unexpectedly")
    text = "\n\n".join(selected)
    for module in (m3, m3.base):
        module.SOURCE_PARAGRAPH_START = heading + 1
        module.SOURCE_PARAGRAPH_END_EXCLUSIVE = next_heading - 1
        module.SOURCE_CHAPTER_TITLE = paragraphs[heading].strip()
    return selected, text, {
        "title": paragraphs[heading].strip(),
        "heading_paragraph": heading,
        "first_narrative_paragraph": heading + 1,
        "last_narrative_paragraph": next_heading - 2,
        "end_separator_paragraph": next_heading - 1,
        "next_chapter_heading_paragraph": next_heading,
        "end_exclusive": next_heading - 1,
        "raw_paragraph_count": next_heading - heading - 1,
        "paragraph_count": len(selected),
        "text_characters": len(text),
        "word_count": len(re.findall(r"\S+", text)),
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
    engine = m3.base
    engine.PROJECT_ID = PROJECT_ID
    engine.SOURCE_PARAGRAPH_START = 108
    engine.SOURCE_PARAGRAPH_END_EXCLUSIVE = 179
    engine.SOURCE_CHAPTER_TITLE = "Capítulo 4 — O círculo dos ausentes"
    return engine.compose_episode_manifest(intro, story, outro)


def _capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    v1 = m3.v1
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
            "session": session, "timeline": f"/exports/{relative}", "fps": FPS,
            "chapterLabel": "CAPÍTULO 4 · O CÍRCULO DOS AUSENTES", "chapterNumber": "4", "captureMode": PROJECT_ID,
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


def _write_reports(project_root: Path, manifest: dict, timeline: dict, video_probe: dict, mix_probe: dict, *, source_meta: dict, library_path: Path, library_sha256: str, character_registry: CharacterRegistry, visibility: dict, processing_seconds: float) -> None:
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    draft_ids = [item for item in character_registry.ids() if item not in character_registry.approved_ids()]
    (reports / "technical-report.md").write_text(
        "# Missão 029 — Crônicas de Topázio, Livro 1, Capítulo 4\n\n"
        f"- Título-fonte: `{source_meta['title']}`\n- Parágrafos narrativos: `{source_meta['first_narrative_paragraph']}–{source_meta['last_narrative_paragraph']}`; separador `{source_meta['end_separator_paragraph']}`; Capítulo 5 `{source_meta['next_chapter_heading_paragraph']}`\n"
        f"- Parágrafos não vazios: `{source_meta['paragraph_count']}`; palavras: `{source_meta['word_count']}`; caracteres: `{source_meta['text_characters']}`\n- Hash UTF-8: `{source_meta['text_sha256']}`\n"
        f"- Segmentos Kokoro medidos: `{len(manifest['segments'])}`\n- Planos: `{len(timeline['scenes'])}` (20 story + host opening/closing)\n- Duração: `{manifest['duration_ms']} ms`\n- Processamento local: `{processing_seconds:.2f} s`\n- Voz: `{VOICE_ID}` / `{LANGUAGE}`\n"
        "- Timestamps de palavra/fonema/visema: indisponíveis; captions e boca usam somente segmentos medidos e RMS.\n- Estado: pendente de aprovação artística humana.\n\n## Política de personagens\n\n"
        f"- Única identidade autorizada: `{APPROVED_CHARACTER_ID}`.\n- Identidades DRAFT bloqueadas: `{draft_ids}`.\n- Cenas de história: environment-only; nenhuma identidade DRAFT foi selecionada ou renderizada.\n",
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
        "# Reuso da biblioteca oficial\n\nA biblioteca `santa-library-topazioverse-v1` foi resolvida pelo registro estável e reutilizada na abertura, no encerramento e no medalhão do narrador.\n\n"
        f"- Caminho resolvido: `{library_path}`\n- SHA-256: `{library_sha256}`\n- Regeneração: `não`\n",
        encoding="utf-8",
    )
    (reports / "mix-report.md").write_text(
        "# Mixagem do Capítulo 4\n\n"
        f"- Música: `{MUSIC}`; origem Suno; velocidade e tom preservados.\n- Ducking: sidechain voz→música, ratio 5, ataque 45 ms, release 650 ms, base musical 0.13.\n- SFX: cama procedural existente, volume 0.12; limiter final 0.90.\n- Direitos comerciais Suno: confirmação necessária antes de publicação.\n"
        f"- FFprobe mix: `{json.dumps(mix_probe, ensure_ascii=False, sort_keys=True)}`\n- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (reports / "santa-visibility-report.json").write_text(json.dumps(visibility, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_youtube_metadata(project_root: Path, manifest: dict, source_meta: dict) -> None:
    metadata = project_root / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    duration = int(manifest["duration_ms"])
    total_seconds = duration // 1000
    minutes, seconds = divmod(total_seconds, 60)
    title = "Crônicas de Topázio — Livro 1 | Capítulo 4: O Círculo dos Ausentes"
    description = (
        "Em Gaia, depois da ruptura no templo, os caminhos dos Cristais Elementares se encontram diante de uma ameaça que não deveria existir.\n\n"
        "Este é o quarto capítulo de O Despertar dos Cristais, narrado por Santa.\n\n"
        "Capítulo: 4 — O círculo dos ausentes\nLivro: 1 — O Despertar dos Cristais\n"
        f"Duração: {minutes:02d}:{seconds:02d}\n\n"
        "Acompanhe as Crônicas de Topázio e descubra os sinais escondidos em Gaia."
    )
    payload = {
        "title": title,
        "description": description,
        "hashtags": ["#CronicasDeTopazio", "#Topazioverse", "#Fantasia", "#Audiobook", "#Narracao"],
        "chapter": {"number": 4, "title": source_meta["title"], "book": "Livro 1 — O Despertar dos Cristais"},
        "playlist_recommended": "Crônicas de Topázio — Livro 1",
        "duration_ms": duration,
        "credits": {
            "narrator": "Santa V5 / Kokoro pm_santa",
            "music": "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3 (origem Suno)",
            "visuals": "Fabuloom Studio environment plates; Santa V5 official library",
        },
        "provenance": {"source_text_sha256": source_meta["text_sha256"], "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable"},
        "publication_pending": ["human artistic approval", "human listening review", "confirmation of commercial rights for the Suno track"],
        "scheduled_at": None,
        "published": False,
    }
    _write_json(metadata / "youtube-metadata.json", payload)
    (metadata / "youtube-metadata.md").write_text(
        f"# Metadados de estreia — Capítulo 4\n\n## Título\n{title}\n\n## Descrição\n{description}\n\n"
        f"## Hashtags\n{' '.join(payload['hashtags'])}\n\n## Playlist\n{payload['playlist_recommended']}\n\n"
        "## Pendências\n\n- Aprovação artística humana.\n- Audição humana da mixagem.\n- Confirmação dos direitos comerciais da faixa Suno.\n- Nenhuma data ou horário foi definido.\n- Não publicado automaticamente.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--capture-timeout", type=float, default=2400)
    args = parser.parse_args()
    _sync_globals()
    chapter_paragraphs, chapter_text, source_meta = load_chapter4()
    if not SOURCE_DOC.is_file():
        raise FileNotFoundError(SOURCE_DOC)
    if not MUSIC.is_file():
        raise FileNotFoundError(MUSIC)
    for directory in (PROJECT_ROOT / "audio", PROJECT_ROOT / "timeline", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports", PROJECT_ROOT / "videos", PROJECT_ROOT / ".frames", PROJECT_ROOT / "assets" / "generated", PROJECT_ROOT / "metadata"):
        directory.mkdir(parents=True, exist_ok=True)
    m3._copy_generated_assets()
    scene_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    library_sha256 = hashlib.sha256(library_path.read_bytes()).hexdigest()
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    approved = character_registry.require_approved(APPROVED_CHARACTER_ID)
    character_registry.resolve(approved.id)
    (PROJECT_ROOT / "timeline" / "chapter4-source-excerpt.txt").write_text(chapter_text + "\n", encoding="utf-8")
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
    engine = m3.base
    timeline = {
        "format": "fabuloom.topazioverse-chapter/0.2",
        "title": f"Crônicas de Topázio — Livro 1 — {source_meta['title']}",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(range(108, 179)),
        "source_paragraph_end_separator": 179,
        "next_chapter_heading_paragraph": 180,
        "source_text_sha256": source_meta["text_sha256"],
        "source_word_count": source_meta["word_count"],
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
        "scenes": list(engine.build_scene_schedule(manifest, library_path, library_sha256)),
    }
    _write_json(timeline_path, timeline)
    m3._write_srt(manifest, PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.srt")
    voice_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-voice.wav"
    sample_rate = engine.compose_voice(manifest, voice_path)
    sfx_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-sfx-bed.wav"
    if not sfx_path.exists() or args.overwrite:
        m3.v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-music-loop.wav"
    m3.v1.make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    mix_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-mix.wav"
    m3.mix_audio_v2(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]))
    if args.reuse_capture:
        completed = sorted((PROJECT_ROOT / ".frames").glob("capture-*/complete.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not completed:
            raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = completed[0].parent
        completion = json.loads(completed[0].read_text(encoding="utf-8"))
        m3.v1._materialize_frames(session_dir, completion)
    else:
        session_dir, completion = _capture_frames(timeline_path, PROJECT_ROOT / ".frames", port=args.port, timeout_seconds=args.capture_timeout)
    video_path = PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo4.mp4"
    m3.v1.render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
    board_path = PROJECT_ROOT / "captures" / "chapter4-frames.png"
    m3.v1.frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
    video_probe = m3.v1.probe(video_path)
    mix_probe = m3.v1.probe(mix_path)
    visibility = m3.audit_santa_visibility(session_dir, timeline["scenes"], frame_count=int(completion["frame_count"]))
    visibility["scene_count"] = len(timeline["scenes"])
    visibility["passed"] = bool(visibility["passed"] and visibility["scene_count"] == len(timeline["scenes"]))
    _write_reports(PROJECT_ROOT, manifest, timeline, video_probe, mix_probe, source_meta=source_meta, library_path=library_path, library_sha256=library_sha256, character_registry=character_registry, visibility=visibility, processing_seconds=time.perf_counter() - started)
    _write_youtube_metadata(PROJECT_ROOT, manifest, source_meta)
    report = {
        "project": PROJECT_ID, "video": str(video_path), "manifest": str(manifest_path), "timeline": str(timeline_path), "frame_board": str(board_path),
        "youtube_metadata": str(PROJECT_ROOT / "metadata" / "youtube-metadata.json"), "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]),
        "scenes": len(timeline["scenes"]), "source": source_meta, "sample_rate": sample_rate, "video_probe": video_probe, "audio_probe": mix_probe,
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
