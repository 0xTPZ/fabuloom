"""Render the Crônicas de Topázio channel introduction.

This production is intentionally separate from the 024.x technology trailer.
It presents only the fictional story universe, uses the real Santa V5 narrator
renderer, and keeps all generated media in the local workspace exports.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

EXAMPLES_ROOT = Path(__file__).resolve().parent
STUDIO_ROOT = EXAMPLES_ROOT.parent
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from official_promo_demo import audio_levels, generate_music, generate_sfx, mix_audio as mix_procedural_audio
from topazioverse_book1_pilot_demo import compose_voice, probe, write_srt


WORKSPACE_ROOT = Path(os.environ.get("FABULOOM_WORKSPACE_ROOT", STUDIO_ROOT.parent)).resolve()
EXPORT_ROOT = Path(os.environ.get("FABULOOM_EXPORT_ROOT", WORKSPACE_ROOT / "workspace" / "exports")).resolve()
PROJECT_ID = "cronicas-de-topazio-channel-intro"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
CAPTURE_FPS = 15
OUTPUT_FPS = 30
WIDTH = 1920
HEIGHT = 1080

SCRIPT_TEXT = (
    "Imagine um mundo onde até o tempo pode parar...\n\n"
    "Onde antigos cristais sustentam o equilíbrio da existência...\n\n"
    "E onde a escuridão desperta quando a luz começa a falhar.\n\n"
    "Saudações, viajante!\n\n"
    "Eu sou Santa, e quero lhe dar as boas-vindas às Crônicas de Topázio.\n\n"
    "Um lugar onde cada história abre as portas para um mundo extraordinário.\n\n"
    "Em Topázio, montanhas guardam segredos antigos.\n\n"
    "Florestas possuem suas próprias vontades.\n\n"
    "Templos esquecidos escondem poderes que poucos ousariam despertar.\n\n"
    "E os Guardiões carregam muito mais do que armas e magia.\n\n"
    "Carregam promessas, lembranças, perdas... e escolhas capazes de transformar o destino de um mundo.\n\n"
    "Aqui, você vai acompanhar grandes aventuras, conhecer personagens extraordinários e descobrir lendas que atravessam gerações.\n\n"
    "Cada capítulo será uma nova viagem.\n\n"
    "Cada personagem terá uma história para contar.\n\n"
    "E cada história poderá revelar algo que você jamais imaginou.\n\n"
    "Se você gosta de fantasia, mistérios, batalhas épicas e histórias que deixam marcas...\n\n"
    "Talvez este seja o seu lugar.\n\n"
    "Prepare-se, Guardião. Nossa primeira jornada está prestes a começar.\n\n"
    "Bem-vindo às Crônicas de Topázio."
)

BLOCK_RANGES = {
    "HOOK": range(0, 3),
    "WELCOME": range(3, 6),
    "UNIVERSE": range(6, 11),
    "STORIES": range(11, 15),
    "INVITATION": range(15, 19),
}

# Each scene is a composition, not a claim that the underlying image depicts a
# confirmed canonical event. Pilot images are reused only where their provenance
# is already recorded; new plates are clearly marked in assets.json.
SCENE_SPECS = (
    ("hook-temple", "HOOK", "image", "TEMPLO DE GAIA", "assets/generated/01-temple-of-gaia.png", "crystal", 1.04, 0.00, 0.00),
    ("hook-frozen", "HOOK", "image", "UM INSTANTE SUSPENSO", "assets/generated/10-time-frozen.png", "freeze", 1.06, -0.02, 0.00),
    ("hook-fissure", "HOOK", "image", "A FISSURA", "assets/generated/02-crystal-fissure.png", "crystal", 1.08, 0.02, -0.01),
    ("welcome-santa", "WELCOME", "host", "SANTA", None, "gold", 1.0, 0.0, 0.0),
    ("welcome-city", "WELCOME", "image", "CRÔNICAS DE TOPÁZIO", "assets/pilot/topazio-city.png", "mist", 1.06, 0.02, 0.00),
    ("universe-panorama", "UNIVERSE", "image", "UM MUNDO EXTRAORDINÁRIO", "assets/generated/03-world-panorama.png", "mist", 1.08, -0.02, 0.00),
    ("universe-thaurion", "UNIVERSE", "image", "SEGREDOS ANTIGOS", "assets/pilot/thaurion-echo-cave.png", "crystal", 1.05, 0.02, 0.00),
    ("universe-vordros", "UNIVERSE", "image", "MONTANHAS DE VORDROS", "assets/pilot/vordros-mountains.png", "snow", 1.06, -0.02, 0.00),
    ("universe-zephirion", "UNIVERSE", "image", "CORRENTES E VENTOS", "assets/pilot/zephirion-currents.png", "wind", 1.07, 0.03, 0.00),
    ("universe-currents", "UNIVERSE", "image", "AS CORRENTES ETERNAS", "assets/generated/04-eternal-currents.png", "wind", 1.05, -0.03, 0.00),
    ("universe-volcano", "UNIVERSE", "image", "O VULCÃO DE OSAI", "assets/generated/05-osai-volcano.png", "ember", 1.07, 0.02, 0.00),
    ("universe-emberion", "UNIVERSE", "image", "EMBERION", "assets/generated/06-emberion.png", "ember", 1.06, -0.02, 0.00),
    ("stories-forest", "STORIES", "image", "A FLORESTA DE MIRAKEL", "assets/generated/07-mirakel-forest.png", "forest", 1.08, 0.02, 0.00),
    ("stories-guardians", "STORIES", "image", "OS GUARDIÕES", "assets/generated/08-guardians.png", "gold", 1.05, -0.02, 0.00),
    ("stories-elemental", "STORIES", "image", "MAGIA ELEMENTAL", "assets/generated/09-elemental-crystal.png", "elemental", 1.09, 0.00, -0.01),
    ("invite-santa", "INVITATION", "host", "PREPARE-SE, GUARDIÃO", None, "gold", 1.0, 0.0, 0.0),
    ("invite-lockup", "INVITATION", "lockup", "CRÔNICAS DE TOPÁZIO", None, "crystal", 1.0, 0.0, 0.0),
)


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _synthesize_or_reuse(manifest_path: Path, audio_dir: Path, *, overwrite: bool) -> tuple[dict, dict]:
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8")), {"status": "reused", "processing_seconds": 0.0}
    provider = KokoroTTSProvider(output_dir=audio_dir, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(
            provider,
            SCRIPT_TEXT,
            narration_id=PROJECT_ID,
            manifest_id=PROJECT_ID,
            voice_id=VOICE_ID,
            language=LANGUAGE,
            output_dir=audio_dir,
            max_chars=420,
        )
        manifest = json.loads(serialize_manifest(run.manifest))
        _json(manifest_path, manifest)
        return manifest, {
            "status": "synthesized",
            "processing_seconds": round(time.perf_counter() - started, 3),
            "model_load_seconds": max((float(item.metadata.get("model_load_seconds") or 0.0) for item in run.results), default=0.0),
        }
    finally:
        provider.close()


def _segments_for_paragraphs(manifest: dict, paragraph_range: range) -> list[dict]:
    return [segment for segment in manifest["segments"] if int((segment.get("metadata") or {}).get("paragraph_index", -1)) in paragraph_range]


def build_blocks(manifest: dict) -> list[dict]:
    items = list(BLOCK_RANGES.items())
    blocks = []
    for index, (block_id, paragraph_range) in enumerate(items):
        segments = _segments_for_paragraphs(manifest, paragraph_range)
        if not segments:
            raise ValueError(f"no measured narration segments for {block_id}")
        next_segments = _segments_for_paragraphs(manifest, items[index + 1][1]) if index + 1 < len(items) else []
        start_ms = min(int(segment["start_ms"]) for segment in segments)
        end_ms = min(int(segment["start_ms"]) for segment in next_segments) if next_segments else int(manifest["duration_ms"])
        blocks.append({"id": block_id, "start_ms": start_ms, "end_ms": end_ms, "paragraphs": list(paragraph_range), "segment_count": len(segments)})
    if blocks[0]["start_ms"] != 0 or blocks[-1]["end_ms"] != int(manifest["duration_ms"]):
        raise ValueError("editorial blocks do not cover measured narration")
    return blocks


def build_scenes(blocks: list[dict]) -> list[dict]:
    by_id = {block["id"]: block for block in blocks}
    grouped: dict[str, list[tuple]] = {}
    for spec in SCENE_SPECS:
        grouped.setdefault(spec[1], []).append(spec)
    scenes = []
    for block_id, specs in grouped.items():
        block = by_id[block_id]
        duration = block["end_ms"] - block["start_ms"]
        for index, (scene_id, _, visual, label, asset_path, effect, zoom, pan_x, pan_y) in enumerate(specs):
            start = block["start_ms"] + round(index * duration / len(specs))
            end = block["start_ms"] + round((index + 1) * duration / len(specs))
            scenes.append({
                "id": scene_id,
                "block_id": block_id,
                "visual": visual,
                "label": label,
                "asset_path": f"{PROJECT_ID}/{asset_path}" if asset_path else None,
                "start_ms": start,
                "end_ms": end,
                "effect": effect,
                "camera": {"zoom": zoom, "pan_x": pan_x, "pan_y": pan_y},
            })
    scenes.sort(key=lambda scene: (scene["start_ms"], scene["id"]))
    return scenes


def build_timeline(manifest: dict) -> dict:
    blocks = build_blocks(manifest)
    return {
        "format": "fabuloom.cronicas-de-topazio-channel-intro/0.1",
        "title": "Crônicas de Topázio — O Portal das Histórias",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": int(manifest["duration_ms"]),
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "narrator": "Santa V5",
        "narrator_visibility": "entire_program",
        "timing_source": "measured_kokoro_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "blocks": blocks,
        "scenes": build_scenes(blocks),
        "soundtrack": {
            "music": f"{PROJECT_ID}/audio/cronicas-original-music.wav",
            "sfx": f"{PROJECT_ID}/audio/cronicas-procedural-sfx.wav",
            "origin": "deterministic local procedural composition and transition effects",
            "rights": "originally generated locally for this production; human release review required",
            "ducking": "voice-priority sidechain compression",
        },
    }


def _find_edge() -> str:
    for candidate in (shutil.which("msedge"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for deterministic Canvas capture")


def _wait_http(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(0.15)
    raise TimeoutError(url)


def _materialize(session_dir: Path, completion: dict) -> int:
    source_count = int(completion["frame_count"])
    source_frames = sorted(session_dir.glob("src-*.jpg"))
    if len(source_frames) != source_count:
        raise RuntimeError(f"source frame count mismatch: {len(source_frames)} != {source_count}")
    duration_ms = int(completion["duration_ms"])
    output_count = (duration_ms * OUTPUT_FPS + 999) // 1000
    for index in range(output_count):
        source_index = min(source_count - 1, round(index * CAPTURE_FPS / OUTPUT_FPS))
        target = session_dir / f"{index:06d}.jpg"
        if target.exists():
            continue
        try:
            os.link(session_dir / f"src-{source_index:06d}.jpg", target)
        except OSError:
            shutil.copyfile(session_dir / f"src-{source_index:06d}.jpg", target)
    if len(list(session_dir.glob("[0-9]*.jpg"))) != output_count:
        raise RuntimeError("materialized frame count mismatch")
    return output_count


def capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout: float) -> tuple[Path, dict]:
    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env["FABULOOM_WORKSPACE_ROOT"] = str(WORKSPACE_ROOT)
    env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT)
    env["FABULOOM_CAPTURE_DIR"] = str(frames_root)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=str(STUDIO_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        _wait_http(f"http://127.0.0.1:{port}/capture-cronicas-de-topazio.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-cronicas-de-topazio.html?session={session}&timeline=/exports/{relative}&fps={CAPTURE_FPS}"
        browser = subprocess.Popen([edge, "--headless=new", "--hide-scrollbars", f"--window-size={WIDTH},{HEIGHT}", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        if error.exists():
            raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists():
            raise TimeoutError(session_dir)
        completion = json.loads(complete.read_text(encoding="utf-8"))
        _materialize(session_dir, completion)
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
        shutil.rmtree(profile, ignore_errors=True)


def render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-framerate", str(OUTPUT_FPS), "-i", str(frames / "%06d.jpg"), "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-s", f"{WIDTH}x{HEIGHT}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output),
    ], check=True)


def make_board(frames: Path, timeline: dict, output: Path, *, overwrite: bool) -> None:
    with tempfile.TemporaryDirectory(prefix=".cronicas-board-", dir=output.parent) as temp:
        files = []
        for index, scene in enumerate(timeline["scenes"]):
            frame = frames / f"{max(0, round(((scene['start_ms'] + scene['end_ms']) / 2) * OUTPUT_FPS / 1000)):06d}.jpg"
            target = Path(temp) / f"{index:02d}.png"
            label = scene["label"].replace(":", "\\:").replace("'", "\\'")
            vf = f"scale=480:270,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':x=12:y=12:fontsize=19:fontcolor=white:box=1:boxcolor=0x071426cc"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame), "-vf", vf, str(target)], check=True)
            files.append(target)
        tile_width, tile_height, columns = 480, 270, 4
        inputs = [argument for file in files for argument in ("-i", str(file))]
        layout = "|".join(f"{index % columns * tile_width}_{index // columns * tile_height}" for index in range(len(files)))
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
            *inputs, "-filter_complex", f"xstack=inputs={len(files)}:layout={layout}:fill=black,format=rgb24[out]",
            "-map", "[out]", "-frames:v", "1", str(output),
        ]
        subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--recapture", action="store_true", help="capture fresh Canvas frames while reusing measured audio")
    parser.add_argument("--rebuild-board", action="store_true", help="rebuild the visual board from an existing capture")
    parser.add_argument("--port", type=int, default=8786)
    parser.add_argument("--capture-timeout", type=float, default=1200)
    args = parser.parse_args()
    for scene in SCENE_SPECS:
        if scene[4] and not (PROJECT_ROOT / scene[4]).is_file():
            raise FileNotFoundError(PROJECT_ROOT / scene[4])
    for directory in (PROJECT_ROOT / "audio", PROJECT_ROOT / "timeline", PROJECT_ROOT / "frames", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports"):
        directory.mkdir(parents=True, exist_ok=True)
    audio_dir = PROJECT_ROOT / "audio"
    timeline_dir = PROJECT_ROOT / "timeline"
    manifest_path = PROJECT_ROOT / "manifest.json"
    started = time.perf_counter()
    manifest, synthesis = _synthesize_or_reuse(manifest_path, audio_dir / "segments", overwrite=args.overwrite)
    timeline = build_timeline(manifest)
    timeline_path = timeline_dir / f"{PROJECT_ID}.json"
    _json(timeline_path, timeline)
    write_srt(manifest, timeline_dir / f"{PROJECT_ID}.srt")
    (timeline_dir / "script-pt-BR.txt").write_text(SCRIPT_TEXT + "\n", encoding="utf-8")
    _json(PROJECT_ROOT / "assets.json", {
        "generated_original_assets": [scene[4] for scene in SCENE_SPECS if scene[4] and "/generated/" in scene[4]],
        "reused_authorized_pilot_assets": [scene[4] for scene in SCENE_SPECS if scene[4] and "/pilot/" in scene[4]],
        "generator": "Codex built-in image generation; original concept plates",
        "canonicality": "Visual direction only; generated plates do not establish new literary canon.",
        "santa": "Santa V5 rendered by the existing NarratorAvatarRenderer",
        "privacy": "No manuscript, private context, model weights or personal media copied into the public repository.",
    })
    voice_path = audio_dir / f"{PROJECT_ID}-voice.wav"
    compose_voice(manifest, voice_path)
    music_path = audio_dir / "cronicas-original-music.wav"
    sfx_path = audio_dir / "cronicas-procedural-sfx.wav"
    scene_starts = [scene["start_ms"] for scene in timeline["scenes"]]
    if args.overwrite or not music_path.is_file():
        generate_music(int(manifest["duration_ms"]), scene_starts, music_path, args.overwrite)
    if args.overwrite or not sfx_path.is_file():
        generate_sfx(int(manifest["duration_ms"]), scene_starts, sfx_path, args.overwrite)
    mix_path = audio_dir / f"{PROJECT_ID}-mix.wav"
    if args.overwrite or not mix_path.is_file():
        mix_procedural_audio(voice_path, music_path, sfx_path, mix_path, int(manifest["duration_ms"]), include_music=True, overwrite=args.overwrite)
    frames_root = PROJECT_ROOT / "frames"
    if args.reuse_capture and not args.recapture:
        existing = sorted(frames_root.glob("capture-*/complete.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not existing:
            raise FileNotFoundError("no existing Crônicas capture available")
        session_dir = existing[0].parent
        completion = json.loads(existing[0].read_text(encoding="utf-8"))
        frame_count = _materialize(session_dir, completion)
    else:
        session_dir, completion = capture_frames(timeline_path, frames_root, port=args.port, timeout=args.capture_timeout)
        frame_count = _materialize(session_dir, completion)
    output = PROJECT_ROOT / "cronicas-de-topazio-channel-intro.mp4"
    force_output = args.overwrite or args.recapture
    if force_output or not output.is_file():
        render_mp4(session_dir, mix_path, output, int(manifest["duration_ms"]), overwrite=force_output)
    board = PROJECT_ROOT / "captures" / "cronicas-de-topazio-channel-intro-frames.png"
    if force_output or args.rebuild_board or not board.is_file():
        make_board(session_dir, timeline, board, overwrite=force_output or args.rebuild_board)
    report = {
        "project": PROJECT_ID,
        "title": "Crônicas de Topázio — O Portal das Histórias",
        "manifest": str(manifest_path),
        "timeline": str(timeline_path),
        "script": str(timeline_dir / "script-pt-BR.txt"),
        "voice": str(voice_path),
        "music": str(music_path),
        "sfx": str(sfx_path),
        "mix": str(mix_path),
        "video": str(output),
        "board": str(board),
        "duration_ms": int(manifest["duration_ms"]),
        "duration_seconds": int(manifest["duration_ms"]) / 1000,
        "segments": len(manifest["segments"]),
        "synthesis": synthesis,
        "capture": {"frames": str(session_dir), "source_fps": CAPTURE_FPS, "output_fps": OUTPUT_FPS, "frame_count": frame_count, "timing_source": "measured_kokoro_wav_segments"},
        "probe": probe(output),
        "voice_levels": audio_levels(voice_path),
        "mix_levels": audio_levels(mix_path),
        "processing_seconds": round(time.perf_counter() - started, 3),
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "music_rights": "original deterministic local procedural composition; release review required",
        "owner_review_required": True,
        "state": "completed_pending_human_artistic_review",
    }
    _json(PROJECT_ROOT / "reports" / "cronicas-result.json", report)
    (PROJECT_ROOT / "reports" / "technical-report.md").write_text(
        "# Crônicas de Topázio — O Portal das Histórias\n\n"
        f"- Duração medida: `{manifest['duration_ms']} ms` (`{manifest['duration_ms'] / 1000:.3f} s`).\n"
        f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; segmentos: `{len(manifest['segments'])}`.\n"
        "- Santa V5 permanece visível em todo o programa: grande nas boas-vindas/despedida e em medalhão nas cenas de fantasia.\n"
        "- A boca usa RMS real; não há alinhamento fonético ou timestamps inventados.\n"
        "- Trilha e SFX são procedurais, determinísticos e gerados localmente; a faixa Suno auditada não foi usada por pendência de direitos.\n"
        "- Os planos novos são arte conceitual original e não ampliam o cânone literário. As imagens do piloto foram reutilizadas com proveniência registrada.\n"
        "- Aprovação humana de narrativa, áudio, continuidade visual e direitos permanece obrigatória.\n",
        encoding="utf-8",
    )
    (PROJECT_ROOT / "reports" / "credits-and-provenance.md").write_text(
        "# Créditos e proveniência\n\n"
        "- Narrador: Santa V5 pelo `NarratorAvatarRenderer` oficial.\n"
        "- Voz: Kokoro `pm_santa`, `pt-BR`.\n"
        "- Imagens geradas: assets originais de fantasia criados localmente para esta produção; não são novos fatos canônicos.\n"
        "- Imagens reutilizadas: cenas locais aprovadas do piloto Topazioverse Book 1, preservadas fora do Git.\n"
        "- Música e SFX: composição procedural local original, sem origem comercial desconhecida registrada.\n"
        "- Faixa Suno em `workspace/inputs/music/book1` foi auditada, mas não utilizada porque os direitos de publicação continuam pendentes.\n"
        "- Nenhum manuscrito, contexto privado, peso de modelo, credencial ou mídia pessoal foi publicado.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
