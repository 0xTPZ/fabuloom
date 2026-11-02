"""Render BT-001, the horizontal behind-the-scenes pilot for Crônicas de Topázio.

The production uses the approved editorial script, measured Kokoro narration,
real local portal captures, existing Fabuloom captures and approved CB stills.
It does not change the portal or any earlier episode.
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
from urllib.error import URLError
from urllib.request import urlopen

EXAMPLES_ROOT = Path(__file__).resolve().parent
STUDIO_ROOT = EXAMPLES_ROOT.parent
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from topazioverse_book1_pilot_demo import write_srt, probe


WORKSPACE_ROOT = Path(os.environ.get("FABULOOM_WORKSPACE_ROOT", STUDIO_ROOT.parent)).resolve()
EXPORT_ROOT = Path(os.environ.get("FABULOOM_EXPORT_ROOT", WORKSPACE_ROOT / "workspace" / "exports")).resolve()
PROJECT_ID = "bastidores/bt-001-por-tras-das-cronicas"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
CAPTURE_FPS = 10
OUTPUT_FPS = 30
WIDTH, HEIGHT = 1920, 1080
MUSIC_SOURCE = WORKSPACE_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
PORTAL_CAPTURE_ROOT = WORKSPACE_ROOT / "workspace" / "captures" / "bt-001" / "portal"
REAL_UI = EXPORT_ROOT / "official-promo" / "evidence" / "fabuloom-studio-ui-real.png"
REAL_NARRATOR = EXPORT_ROOT / "official-promo" / "evidence" / "fabuloom-narrator-mode-real.png"
CB_ROOT = EXPORT_ROOT / "cronicas-breves"

SCRIPT_TEXT = """Guardião, você já se perguntou como uma história chega até a sua tela?

Antes de cada vídeo, existe um livro. E antes de cada livro, um mundo inteiro sendo construído, página por página.

Eu sou Santa. Hoje, quero abrir uma pequena porta para os bastidores das Crônicas de Topázio.

Tudo começa com as histórias de Topázio: O Despertar dos Cristais. O autor escreve, revisa e escolhe os momentos que podem ganhar voz e movimento.

Então entra o Fabuloom Studio. É aqui que minha narração encontra cenários, trilhas sonoras, legendas e movimentos de câmera.

Mas nada disso fica pronto num passe de mágica. Cada cena precisa ser montada, testada e conferida. E a última palavra é sempre do autor.

Agora vem uma parte que eu gosto especialmente.

Você não precisa apenas assistir às histórias. Também pode entrar nesse mundo como leitor.

Este é o Atlas Literário, o portal onde Topázio: O Despertar dos Cristais está disponível para leitura gratuita.

São quarenta e um capítulos, mais o epílogo. Você pode abrir a biblioteca, escolher por onde começar e ler no seu próprio ritmo.

E, no leitor, há opções para deixar a leitura mais confortável. É um lugar feito para as páginas, não só para as telas de vídeo.

O endereço está na descrição: atlasliterario.duckdns.org.

Venha conhecer o livro. Depois, volte para ouvir as histórias comigo.

Porque um mundo não termina quando a narração acaba.

Às vezes, é justamente ali que a sua jornada começa.

Até breve, Guardião."""

BLOCK_RANGES = {
    "HOOK": range(0, 1),
    "BOOK": range(1, 4),
    "STUDIO": range(4, 7),
    "READER": range(7, 9),
    "LIBRARY": range(9, 12),
    "INVITATION": range(12, 16),
}

SCENE_SPECS = (
    ("hook-portal", "HOOK", "portal", "UM LIVRO ANTES DE CADA VÍDEO", "portal/01-home.png", True, 1.0, 0.0, 0.0),
    ("book-home", "BOOK", "portal", "TOPÁZIO · O DESPERTAR DOS CRISTAIS", "portal/03-livro-i-indice.png", False, 1.0, 0.0, 0.0),
    ("book-episodes", "BOOK", "episode", "HISTÓRIAS QUE GANHAM VOZ E MOVIMENTO", "episodes/cb001-still.png", False, 1.03, 0.0, 0.0),
    ("studio-ui", "STUDIO", "ui", "FABULOOM STUDIO · MONTAGEM E TESTE", "real/fabuloom-studio-ui-real.png", False, 1.0, 0.0, 0.0),
    ("narrator-ui", "STUDIO", "ui", "NARRATOR MODE · VOZ, TIMELINE E CENAS", "real/fabuloom-narrator-mode-real.png", False, 1.0, 0.0, 0.0),
    ("storyboards", "STUDIO", "episode", "CADA CENA PRECISA SER CONFERIDA", "storyboards/cb001-storyboard-board.png", False, 1.0, 0.0, 0.0),
    ("reader-entry", "READER", "portal", "VOCÊ TAMBÉM PODE ENTRAR NESSE MUNDO", "portal/02-biblioteca.png", True, 1.0, 0.0, 0.0),
    ("book-index", "LIBRARY", "portal", "41 CAPÍTULOS · MAIS O EPÍLOGO", "portal/03-livro-i-indice.png", False, 1.0, 0.0, 0.0),
    ("reader-sepia", "LIBRARY", "portal", "UM LEITOR FEITO PARA AS PÁGINAS", "portal/05-reader-sepia.png", True, 1.0, 0.0, 0.0),
    ("episode-results", "INVITATION", "episode", "DEPOIS, VOLTE PARA OUVIR AS HISTÓRIAS", "storyboards/cb003-storyboard-board.png", False, 1.0, 0.0, 0.0),
    ("cta", "INVITATION", "cta", "CRÔNICAS DE TOPÁZIO", None, False, 1.0, 0.0, 0.0),
)


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _synthesize_or_reuse(manifest_path: Path, audio_dir: Path, *, overwrite: bool) -> tuple[dict, dict]:
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8")), {"status": "reused", "processing_seconds": 0.0}
    provider = KokoroTTSProvider(output_dir=audio_dir, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(provider, SCRIPT_TEXT, narration_id="bt-001", manifest_id="bt-001", voice_id=VOICE_ID, language=LANGUAGE, output_dir=audio_dir, max_chars=420)
        manifest = json.loads(serialize_manifest(run.manifest))
        _json(manifest_path, manifest)
        return manifest, {"status": "synthesized", "processing_seconds": round(time.perf_counter() - started, 3), "model_load_seconds": max((float(item.metadata.get("model_load_seconds") or 0.0) for item in run.results), default=0.0)}
    finally:
        provider.close()


def _segments_for_paragraphs(manifest: dict, paragraph_range: range) -> list[dict]:
    return [segment for segment in manifest["segments"] if int((segment.get("metadata") or {}).get("paragraph_index", -1)) in paragraph_range]


def build_blocks(manifest: dict) -> list[dict]:
    items = list(BLOCK_RANGES.items())
    blocks = []
    for index, (block_id, paragraph_range) in enumerate(items):
        segments = _segments_for_paragraphs(manifest, paragraph_range)
        if not segments: raise ValueError(f"no measured segments for {block_id}")
        next_segments = _segments_for_paragraphs(manifest, items[index + 1][1]) if index + 1 < len(items) else []
        start_ms = min(int(item["start_ms"]) for item in segments)
        end_ms = min(int(item["start_ms"]) for item in next_segments) if next_segments else int(manifest["duration_ms"])
        blocks.append({"id": block_id, "start_ms": start_ms, "end_ms": end_ms, "paragraphs": list(paragraph_range), "segment_count": len(segments)})
    return blocks


def build_timeline(manifest: dict) -> dict:
    blocks = build_blocks(manifest); by_id = {block["id"]: block for block in blocks}; grouped: dict[str, list[tuple]] = {}
    for spec in SCENE_SPECS: grouped.setdefault(spec[1], []).append(spec)
    scenes = []
    for block_id, specs in grouped.items():
        block = by_id[block_id]; duration = block["end_ms"] - block["start_ms"]
        for index, (scene_id, _, visual, label, asset, portal_badge, zoom, pan_x, pan_y) in enumerate(specs):
            start = block["start_ms"] + round(index * duration / len(specs)); end = block["start_ms"] + round((index + 1) * duration / len(specs))
            scenes.append({"id": scene_id, "block_id": block_id, "visual": visual, "label": label, "asset_path": f"{PROJECT_ID}/assets/{asset}" if asset else None, "portal_badge": portal_badge, "start_ms": start, "end_ms": end, "camera": {"zoom": zoom, "pan_x": pan_x, "pan_y": pan_y}})
    scenes.sort(key=lambda item: (item["start_ms"], item["id"]))
    narration_duration = int(manifest["duration_ms"]); cta_tail = 7000
    scenes[-1]["end_ms"] = narration_duration + cta_tail
    return {"format": "fabuloom.bastidores-bt001/0.1", "title": "Por Trás das Crônicas de Topázio", "manifest": f"{PROJECT_ID}/audio/narration-manifest.json", "duration_ms": narration_duration, "program_duration_ms": narration_duration + cta_tail, "cta_tail_ms": cta_tail, "voice_id": VOICE_ID, "language": LANGUAGE, "narrator": "Santa V5", "timing_source": "measured_kokoro_wav_segments", "word_phoneme_viseme_timing": "unavailable", "blocks": blocks, "scenes": scenes, "portal": {"url": "https://atlasliterario.duckdns.org", "verification": "home → biblioteca → Livro I → capítulo 1 → ferramenta de leitura Sépia", "capture_status": "verified_live_capture"}, "soundtrack": {"source": "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3", "origin": "owner-supplied local music", "ducking": "sidechain compression keyed by Santa narration", "rights": "commercial publication confirmation pending"}}


def _copy_asset(source: Path, relative: str) -> str:
    if not source.is_file(): raise FileNotFoundError(source)
    target = PROJECT_ROOT / "assets" / relative
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    return f"assets/{relative}"


def _extract_still(source: Path, target: Path, seconds: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{seconds:.3f}", "-i", str(source), "-frames:v", "1", "-vf", "scale=1920:-2", str(target)], check=True)


def prepare_assets() -> dict:
    mapping = {
        "portal/01-home.png": PORTAL_CAPTURE_ROOT / "01-home.png",
        "portal/02-biblioteca.png": PORTAL_CAPTURE_ROOT / "02-biblioteca.png",
        "portal/03-livro-i-indice.png": PORTAL_CAPTURE_ROOT / "03-livro-i-indice.png",
        "portal/05-reader-sepia.png": PORTAL_CAPTURE_ROOT / "05-reader-sepia.png",
        "real/fabuloom-studio-ui-real.png": REAL_UI,
        "real/fabuloom-narrator-mode-real.png": REAL_NARRATOR,
        "storyboards/cb001-storyboard-board.png": CB_ROOT / "cb-001-o-quarto-eco" / "captures" / "cb001-storyboard-board.png",
        "storyboards/cb002-storyboard-board.png": CB_ROOT / "cb-002-a-sombra-que-olhava-para-o-sol" / "captures" / "storyboard-board.png",
        "storyboards/cb003-storyboard-board.png": CB_ROOT / "cb-003-a-luz-do-ultimo-viajante" / "captures" / "storyboard-board.png",
    }
    copied = {key: _copy_asset(source, key) for key, source in mapping.items()}
    episodes = {
        "cb001-still.png": (next((CB_ROOT.joinpath("cb-001-o-quarto-eco", "videos").glob("*.mp4")), None), 10.0),
        "cb002-still.png": (next((CB_ROOT.joinpath("cb-002-a-sombra-que-olhava-para-o-sol", "videos").glob("*.mp4")), None), 10.0),
        "cb003-still.png": (next((CB_ROOT.joinpath("cb-003-a-luz-do-ultimo-viajante", "videos").glob("*.mp4")), None), 10.0),
    }
    for name, (source, seconds) in episodes.items():
        if source is None: raise FileNotFoundError(name)
        _extract_still(source, PROJECT_ROOT / "assets" / "episodes" / name, seconds)
        copied[f"episodes/{name}"] = f"assets/episodes/{name}"
    return copied


def mix_audio(voice: Path, music: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000; fade_start = max(0.0, duration - 5)
    graph = (f"[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice_m][det_m];[voice_m]apad,atrim=duration={duration:.3f},pan=stereo|c0=c0|c1=c0[voice];[det_m]apad,atrim=duration={duration:.3f}[det];[1:a]aresample=48000,volume=0.115,atrim=duration={duration:.3f},afade=t=in:st=0:d=2,afade=t=out:st={fade_start:.3f}:d=5[music];[music][det]sidechaincompress=threshold=0.020:ratio=8:attack=80:release=700:makeup=1[ducked];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[mix]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-filter_complex", graph, "-map", "[mix]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True)


def _find_edge() -> str:
    for candidate in (shutil.which("msedge"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if candidate and Path(candidate).is_file(): return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for deterministic Canvas capture")


def _wait_http(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500: return
        except (OSError, URLError): time.sleep(0.15)
    raise TimeoutError(url)


def _materialize(session_dir: Path, completion: dict) -> int:
    source_count = int(completion["frame_count"]); source_frames = sorted(session_dir.glob("src-*.jpg"))
    if len(source_frames) != source_count: raise RuntimeError(f"source frame count mismatch: {len(source_frames)} != {source_count}")
    duration_ms = int(completion["duration_ms"]); output_count = (duration_ms * OUTPUT_FPS + 999) // 1000
    for index in range(output_count):
        source_index = min(source_count - 1, round(index * CAPTURE_FPS / OUTPUT_FPS)); target = session_dir / f"{index:06d}.jpg"
        if not target.exists():
            try: os.link(session_dir / f"src-{source_index:06d}.jpg", target)
            except OSError: shutil.copyfile(session_dir / f"src-{source_index:06d}.jpg", target)
    return output_count


def capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout: float) -> tuple[Path, dict]:
    edge = _find_edge(); frames_root.mkdir(parents=True, exist_ok=True); session = f"capture-{int(time.time())}"; session_dir = frames_root / session; session_dir.mkdir(parents=True, exist_ok=True); profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy(); env["FABULOOM_WORKSPACE_ROOT"] = str(WORKSPACE_ROOT); env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT); env["FABULOOM_CAPTURE_DIR"] = str(frames_root)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=str(STUDIO_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); browser = None
    try:
        _wait_http(f"http://127.0.0.1:{port}/capture-bastidores-bt001.html", 20); relative = timeline_path.relative_to(EXPORT_ROOT).as_posix(); url = f"http://127.0.0.1:{port}/capture-bastidores-bt001.html?session={session}&timeline=/exports/{relative}&fps={CAPTURE_FPS}"
        browser = subprocess.Popen([edge, "--headless=new", "--hide-scrollbars", f"--window-size={WIDTH},{HEIGHT}", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"; error = session_dir / "error.json"; deadline = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < deadline: time.sleep(0.25)
        if error.exists(): raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists(): raise TimeoutError(session_dir)
        completion = json.loads(complete.read_text(encoding="utf-8")); _materialize(session_dir, completion); return session_dir, completion
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try: browser.wait(timeout=5)
            except subprocess.TimeoutExpired: browser.kill()
        server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill()
        shutil.rmtree(profile, ignore_errors=True)


def render_mp4(frames: Path, audio: Path, output: Path, output_count: int, *, overwrite: bool) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(OUTPUT_FPS), "-i", str(frames / "%06d.jpg"), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-frames:v", str(output_count), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-color_range", "tv", "-r", str(OUTPUT_FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)], check=True)


def make_board(frames: Path, timeline: dict, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=".bt001-board-", dir=output.parent) as temp:
        files = []
        for index, scene in enumerate(timeline["scenes"]):
            frame = frames / f"{max(0, round(((scene['start_ms'] + scene['end_ms']) / 2) * OUTPUT_FPS / 1000)):06d}.jpg"; target = Path(temp) / f"{index:02d}.png"; label = scene["label"].replace(":", "\\:").replace("'", "\\'")
            vf = f"scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2:color=0x030914,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':x=12:y=12:fontsize=17:fontcolor=white:box=1:boxcolor=0x071426cc"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame), "-vf", vf, str(target)], check=True); files.append(target)
        inputs = [argument for file in files for argument in ("-i", str(file))]; layout = "|".join(f"{index % 4 * 480}_{index // 4 * 270}" for index in range(len(files)))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", f"xstack=inputs={len(files)}:layout={layout}:fill=black,format=rgb24[out]", "-map", "[out]", "-frames:v", "1", str(output)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--recapture", action="store_true"); parser.add_argument("--port", type=int, default=8794); parser.add_argument("--capture-timeout", type=float, default=1800); args = parser.parse_args()
    if not MUSIC_SOURCE.is_file(): raise FileNotFoundError(MUSIC_SOURCE)
    for directory in (PROJECT_ROOT / "audio" / "segments", PROJECT_ROOT / "assets", PROJECT_ROOT / "timeline", PROJECT_ROOT / "frames", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports", PROJECT_ROOT / "videos"): directory.mkdir(parents=True, exist_ok=True)
    manifest_path = PROJECT_ROOT / "audio" / "narration-manifest.json"; started = time.perf_counter(); manifest, synthesis = _synthesize_or_reuse(manifest_path, PROJECT_ROOT / "audio" / "segments", overwrite=args.overwrite)
    assets = prepare_assets(); timeline = build_timeline(manifest); timeline_path = PROJECT_ROOT / "timeline" / "bt-001-por-tras-das-cronicas.json"; _json(timeline_path, timeline); _json(PROJECT_ROOT / "narration-manifest.json", manifest); _json(PROJECT_ROOT / "storyboard-used.json", {"title": timeline["title"], "format": "1920x1080", "fps": OUTPUT_FPS, "timing_source": timeline["timing_source"], "scenes": timeline["scenes"], "source_assets": assets}); _json(PROJECT_ROOT / "assets.json", {"assets": assets, "authentic_sources": ["live portal capture", "Fabuloom Studio capture", "approved CB-001/002/003 local outputs"], "no_draft_characters": True, "private_data_excluded": True}); shutil.copy2(MUSIC_SOURCE, PROJECT_ROOT / "audio" / "source-music.mp3"); write_srt(manifest, PROJECT_ROOT / "fabuloom-bt-001-bastidores-topazio.srt"); (PROJECT_ROOT / "timeline" / "script-pt-BR.txt").write_text(SCRIPT_TEXT + "\n", encoding="utf-8")
    voice = PROJECT_ROOT / "audio" / "voice.wav"; mix = PROJECT_ROOT / "audio" / "mixed.wav"; output = PROJECT_ROOT / "videos" / "fabuloom-bt-001-bastidores-topazio.mp4"
    if args.overwrite or not voice.exists():
        from topazioverse_book1_pilot_demo import compose_voice
        compose_voice(manifest, voice)
    if args.overwrite or not mix.exists(): mix_audio(voice, MUSIC_SOURCE, mix, int(timeline["program_duration_ms"]), overwrite=True)
    frames_root = PROJECT_ROOT / "frames"
    if args.recapture or not list(frames_root.glob("capture-*/complete.json")):
        session_dir, completion = capture_frames(timeline_path, frames_root, port=args.port, timeout=args.capture_timeout)
    else:
        session_dir = sorted((path.parent for path in frames_root.glob("capture-*/complete.json")), key=lambda path: path.name)[-1]; completion = json.loads((session_dir / "complete.json").read_text(encoding="utf-8")); _materialize(session_dir, completion)
    output_count = (int(timeline["program_duration_ms"]) * OUTPUT_FPS + 999) // 1000; render_mp4(session_dir, mix, output, output_count, overwrite=True); board = PROJECT_ROOT / "captures" / "bt-001-capture-board.png"; make_board(session_dir, timeline, board)
    music_probe = probe(MUSIC_SOURCE); voice_probe = probe(voice); mix_probe = probe(mix); video_probe = probe(output); duration = float(video_probe.get("format", {}).get("duration", 0.0)); report = {"project": "BT-001", "title": "Por Trás das Crônicas de Topázio", "voice": {"provider": "Kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "manifest_duration_ms": manifest["duration_ms"], "audio": str(voice.relative_to(EXPORT_ROOT)).replace("\\", "/")}, "program_duration_ms": timeline["program_duration_ms"], "video_duration_seconds": duration, "canvas": {"width": WIDTH, "height": HEIGHT, "fps": OUTPUT_FPS}, "video": video_probe, "audio": {"voice": voice_probe, "mixed": mix_probe, "music_source": music_probe}, "synthesis": synthesis, "capture": completion, "music_source_sha256": _sha256(MUSIC_SOURCE), "music_rights": "owner-supplied; commercial publication confirmation pending", "portal": timeline["portal"], "review": {"full_av_review": "not claimed; representative frames, stream decode and local artifact inspection completed", "human_artistic_approval": "pending owner review"}, "processing_seconds": round(time.perf_counter() - started, 3)}; _json(PROJECT_ROOT / "reports" / "technical-report.json", report); (PROJECT_ROOT / "reports" / "technical-report.md").write_text(f"# BT-001 — Relatório técnico\n\n- Vídeo: `{output.name}`\n- Duração medida: `{duration:.3f} s`\n- Narração: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; duração medida no manifesto: `{manifest['duration_ms'] / 1000:.3f} s`.\n- Programa: `{timeline['program_duration_ms'] / 1000:.3f} s`, incluindo cauda de CTA de 7 s.\n- Imagem: `{WIDTH}×{HEIGHT}`, `{OUTPUT_FPS} fps`, H.264 `yuv420p`.\n- Áudio: AAC estéreo, 48 kHz; música reduzida por sidechain compressor durante a fala.\n- Portal: captura real verificada em home → biblioteca → Livro I → capítulo 1 → Sépia.\n- Timestamps: segmentos medidos; palavras/fonemas/visemas não disponíveis.\n- Revisão artística humana: pendente.\n", encoding="utf-8"); (PROJECT_ROOT / "reports" / "source-capture-report.md").write_text("# BT-001 — Fontes e capturas\n\nAs telas do Atlas Literário foram capturadas em sessão real, sem alterar o portal. A sequência validada foi: home, biblioteca, Livro I, primeiro capítulo e ferramenta de leitura Sépia. As telas do Fabuloom Studio e do Narrator Mode são capturas locais reais. Os quadros de episódios são extraídos dos MP4s CB-001, CB-002 e CB-003 já existentes; nenhum capítulo foi re-renderizado.\n\nOs nomes técnicos locais e caminhos privados não são exibidos no vídeo.\n", encoding="utf-8"); (PROJECT_ROOT / "reports" / "music-report.md").write_text(f"# BT-001 — Música\n\n- Fonte: `{MUSIC_SOURCE.name}`\n- SHA-256: `{_sha256(MUSIC_SOURCE)}`\n- Tratamento: faixa original preservada; cópia somente para o workspace de exportação; loop controlado, fade-in/out e ducking por sidechain usando a narração de Santa como chave.\n- Direitos: confirmação de direitos comerciais continua pendente antes de publicação.\n", encoding="utf-8"); _json(PROJECT_ROOT / "reports" / "youtube-metadata.json", {"title": "Por Trás das Crônicas de Topázio | Bastidores do Fabuloom Studio", "description": "Como um livro vira narração, cenas e um mundo para explorar. Conheça o Atlas Literário: https://atlasliterario.duckdns.org", "language": "pt-BR", "voice": "Santa · pm_santa", "music_rights_status": "confirm before publication", "chapter_markers": [{"name": block["id"], "start_ms": block["start_ms"]} for block in timeline["blocks"]]}); print(json.dumps({"output": str(output), "duration_seconds": duration, "manifest_duration_ms": manifest["duration_ms"], "program_duration_ms": timeline["program_duration_ms"], "board": str(board), "report": str(PROJECT_ROOT / 'reports' / 'technical-report.json')}, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
