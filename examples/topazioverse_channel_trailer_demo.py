"""Render the TopazioVerse channel trailer in horizontal and vertical formats.

The script keeps the real Santa V5 renderer and Kokoro boundary. Existing
authorized pilot images and local Fabuloom captures are referenced from the
workspace; unavailable game, blockchain and electronics captures are shown as
explicitly labelled conceptual panels rather than fictional demonstrations.
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
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import synthesize_narration
from fabuloom_core.serialization import serialize_manifest

from topazioverse_book1_pilot_demo import (
    EXPORT_ROOT,
    compose_voice,
    probe,
    write_srt,
)


PROJECT_ID = "topazioverse-channel-trailer"
VERTICAL_PROJECT_ID = "topazioverse-channel-trailer-short-vertical"
V1_PROJECT_ID = "topazioverse-book1-episode1-pilot"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
CAPTURE_FPS = 15
OUTPUT_FPS = 30
HORIZONTAL = (1920, 1080)
VERTICAL = (1080, 1920)
SOURCE_STORY_ROOT = EXPORT_ROOT / "topazioverse-book1-episode1-pilot"
SOURCE_UI = EXPORT_ROOT / "official-promo" / "evidence" / "fabuloom-studio-ui-real.png"
SOURCE_NARRATOR = EXPORT_ROOT / "official-promo" / "evidence" / "fabuloom-narrator-mode-real.png"
MUSIC = EXPORT_ROOT / "official-promo-v1" / "fabuloom-official-promo-v1-original-music.wav"

SCRIPT_TEXT = (
    "Saudações, viajantes! Sejam muito bem-vindos ao TopazioVerse!\n\n"
    "Eu sou Santa, e vou acompanhar vocês por este universo de histórias, ideias e descobertas.\n\n"
    "Talvez você tenha chegado procurando uma boa aventura. Talvez uma música. Ou quem sabe alguma invenção curiosa.\n\n"
    "Pois aqui, gostamos de transformar imaginação em realidade.\n\n"
    "Em nossas histórias, você encontrará cristais ancestrais, reinos misteriosos, heróis e aventuras que ganham vida através de nossas produções cinematográficas.\n\n"
    "Mas nem toda história precisa ser contada com palavras. Também criamos músicas para acompanhar emoções, momentos e jornadas.\n\n"
    "E quando a imaginação pede um mundo para explorar, nós também desenvolvemos jogos e experiências interativas.\n\n"
    "Nosso laboratório vai ainda mais longe. Criamos ferramentas, exploramos inteligência artificial, desenvolvemos tecnologias e experimentamos novas formas de construir o futuro.\n\n"
    "Tudo isso faz parte de um projeto independente, construído passo a passo, com criatividade, dedicação e vontade de aprender.\n\n"
    "E queremos dividir essa jornada com vocês.\n\n"
    "Cada playlist é uma porta para uma experiência diferente.\n\n"
    "Então, escolha sua próxima aventura, explore nossos projetos e conte nos comentários o que mais despertou sua curiosidade.\n\n"
    "Se gostar do que encontrar, inscreva-se e compartilhe nosso canal.\n\n"
    "Eu sou Santa, e estarei aqui para receber você.\n\n"
    "Bem-vindo ao TopazioVerse, Guardião!"
)

# The vertical deliverable is a genuine teaser, not a crop of the full trailer.
# It keeps the same central message and the same narrator/voice while using a
# shorter measured narration suitable for a 30–45 second social cut.
VERTICAL_SCRIPT_TEXT = (
    "Saudações, viajantes! Eu sou Santa, e este é o TopazioVerse.\n\n"
    "Aqui, histórias ganham vida em mundos de mistério, aventura e descoberta.\n\n"
    "Também criamos músicas para acompanhar emoções, momentos e jornadas.\n\n"
    "Quando a imaginação pede um mundo para explorar, desenvolvemos jogos e experiências interativas.\n\n"
    "Nosso laboratório explora inteligência artificial e ferramentas para construir o futuro.\n\n"
    "Tudo isso é uma jornada independente, construída passo a passo, com criatividade e dedicação.\n\n"
    "Escolha sua próxima aventura, explore nossas playlists e venha fazer parte da jornada.\n\n"
    "Bem-vindo ao TopazioVerse, Guardião!"
)

BLOCK_RANGES = {
    "CHANNEL_INTRO": range(0, 4),
    "STORIES_SHOWCASE": range(4, 5),
    "MUSIC_SHOWCASE": range(5, 6),
    "GAMES_SHOWCASE": range(6, 7),
    "TECH_SHOWCASE": range(7, 8),
    "COMMUNITY_INVITATION": range(8, 11),
    "CHANNEL_OUTRO": range(11, 15),
}

VERTICAL_BLOCK_RANGES = {
    "CHANNEL_INTRO": range(0, 1),
    "STORIES_SHOWCASE": range(1, 2),
    "MUSIC_SHOWCASE": range(2, 3),
    "GAMES_SHOWCASE": range(3, 4),
    "TECH_SHOWCASE": range(4, 5),
    "COMMUNITY_INVITATION": range(5, 6),
    "CHANNEL_OUTRO": range(6, 7),
}

SCENE_SPECS = (
    ("intro-host", "CHANNEL_INTRO", "host_large", "SANTA · ANFITRIÃO DO TOPAZIOVERSE", None),
    ("intro-portal", "CHANNEL_INTRO", "crystal_stage", "UM UNIVERSO DE IDEIAS", "story/01-topazio-stillness.png"),
    ("stories-city", "STORIES_SHOWCASE", "image", "HISTÓRIAS", "story/01-topazio-stillness.png"),
    ("stories-temple", "STORIES_SHOWCASE", "image", "MISTÉRIO", "story/02-temple-crack-crystal.png"),
    ("stories-crystal", "STORIES_SHOWCASE", "image", "AVENTURAS", "story/03-thaurion-echo-cave.png"),
    ("stories-realms", "STORIES_SHOWCASE", "image", "NOVOS MUNDOS", "story/05-glaciron-vordros.png"),
    ("music-crystal", "MUSIC_SHOWCASE", "music_concept", "MÚSICA · EMOÇÃO E JORNADA", None),
    ("games-world", "GAMES_SHOWCASE", "games_concept", "CONCEITO VISUAL · JOGOS", None),
    ("tech-studio", "TECH_SHOWCASE", "real_ui", "CAPTURA REAL · FABULOOM STUDIO", "real/fabuloom-studio-ui-real.png"),
    ("tech-laboratory", "TECH_SHOWCASE", "tech_concept", "CONCEITO VISUAL · LABORATÓRIO", None),
    ("community-voice", "COMMUNITY_INVITATION", "real_narrator", "CAPTURA REAL · NARRATOR MODE", "real/fabuloom-narrator-mode-real.png"),
    ("community-network", "COMMUNITY_INVITATION", "community_concept", "CONCEITO VISUAL · COMUNIDADE", None),
    ("outro-host", "CHANNEL_OUTRO", "host_large", "ESCOLHA SUA PRÓXIMA AVENTURA", None),
    ("outro-playlists", "CHANNEL_OUTRO", "playlist_concept", "CADA PLAYLIST É UMA PORTA", None),
    ("outro-lockup", "CHANNEL_OUTRO", "channel_lockup", "TOPAZIOVERSE · IDEIAS EM REALIDADE", None),
)

VERTICAL_SCENE_SPECS = (
    ("vertical-intro-host", "CHANNEL_INTRO", "host_large", "SANTA · ANFITRIÃO DO TOPAZIOVERSE", None),
    ("vertical-stories-city", "STORIES_SHOWCASE", "image", "HISTÓRIAS · MUNDOS QUE GANHAM VIDA", "story/01-topazio-stillness.png"),
    ("vertical-music-crystal", "MUSIC_SHOWCASE", "music_concept", "MÚSICA · EMOÇÃO E JORNADA", None),
    ("vertical-games-world", "GAMES_SHOWCASE", "games_concept", "JOGOS · MUNDOS PARA EXPLORAR", None),
    ("vertical-tech-laboratory", "TECH_SHOWCASE", "tech_concept", "LABORATÓRIO · IA E FUTURO", None),
    ("vertical-community-network", "COMMUNITY_INVITATION", "community_concept", "UMA COMUNIDADE DE VIAJANTES", None),
    ("vertical-outro-lockup", "CHANNEL_OUTRO", "channel_lockup", "TOPAZIOVERSE · IDEIAS EM REALIDADE", None),
)


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _synthesize_or_reuse(
    manifest_path: Path,
    audio_dir: Path,
    *,
    overwrite: bool,
    script_text: str,
    narration_id: str,
    manifest_id: str,
) -> tuple[dict, dict]:
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8")), {"status": "reused", "processing_seconds": 0.0}
    provider = KokoroTTSProvider(output_dir=audio_dir, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(
            provider,
            script_text,
            narration_id=narration_id,
            manifest_id=manifest_id,
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


def build_blocks(manifest: dict, block_ranges: dict[str, range]) -> list[dict]:
    blocks = []
    items = list(block_ranges.items())
    for index, (block_id, paragraph_range) in enumerate(items):
        segments = _segments_for_paragraphs(manifest, paragraph_range)
        if not segments:
            raise ValueError(f"no measured narration segments for {block_id}")
        next_segments = _segments_for_paragraphs(manifest, items[index + 1][1]) if index + 1 < len(items) else []
        start_ms = min(int(segment["start_ms"]) for segment in segments)
        end_ms = min(int(segment["start_ms"]) for segment in next_segments) if next_segments else int(manifest["duration_ms"])
        blocks.append({"id": block_id, "start_ms": start_ms, "end_ms": end_ms, "paragraphs": list(paragraph_range), "segment_count": len(segments)})
    if blocks[0]["start_ms"] != 0 or blocks[-1]["end_ms"] != int(manifest["duration_ms"]):
        raise ValueError("block schedule does not cover the measured narration")
    return blocks


def build_scenes(blocks: list[dict], scene_specs: tuple[tuple, ...]) -> list[dict]:
    by_id = {block["id"]: block for block in blocks}
    grouped: dict[str, list[tuple]] = {}
    for spec in scene_specs:
        grouped.setdefault(spec[1], []).append(spec)
    scenes = []
    for block_id, specs in grouped.items():
        block = by_id[block_id]
        duration = block["end_ms"] - block["start_ms"]
        for index, (scene_id, _, visual, label, asset) in enumerate(specs):
            start = block["start_ms"] + round(index * duration / len(specs))
            end = block["start_ms"] + round((index + 1) * duration / len(specs))
            asset_path = None
            if asset and asset.startswith("story/"):
                asset_path = f"{V1_PROJECT_ID}/scenes/{Path(asset).name}"
            elif asset and asset.startswith("real/"):
                asset_path = f"official-promo/evidence/{Path(asset).name}"
            scenes.append({"id": scene_id, "block_id": block_id, "visual": visual, "label": label, "asset": asset, "asset_path": asset_path, "start_ms": start, "end_ms": end})
    scenes.sort(key=lambda scene: (scene["start_ms"], scene["id"]))
    return scenes


def build_timeline(
    manifest: dict,
    *,
    manifest_ref: str,
    block_ranges: dict[str, range],
    scene_specs: tuple[tuple, ...],
    title: str,
) -> dict:
    blocks = build_blocks(manifest, block_ranges)
    return {
        "format": "fabuloom.topazioverse-channel-trailer/0.1",
        "title": title,
        "manifest": manifest_ref,
        "duration_ms": int(manifest["duration_ms"]),
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "narrator": "Santa V5",
        "narrator_visibility": "entire_program",
        "timing_source": "measured_kokoro_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "blocks": blocks,
        "scenes": build_scenes(blocks, scene_specs),
        "assets": {
            "story_images": "reused authorized local assets from Topazioverse Book 1 pilot",
            "real_captures": ["Fabuloom Studio UI", "Fabuloom Narrator Mode"],
            "conceptual_panels": ["music", "games", "technology", "community", "playlist"],
        },
        "soundtrack": {
            "path": "workspace/exports/official-promo-v1/fabuloom-official-promo-v1-original-music.wav",
            "origin": "existing deterministic procedural local composition from Official Promo V1; no commercial samples recorded",
            "rights": "local original procedural asset; confirm final publication policy before release",
        },
    }


def mix_audio(voice: Path, music: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    fade_start = max(0.0, duration - 4)
    filter_graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.085,atrim=duration={duration:.3f},afade=t=in:st=0:d=2,afade=t=out:st={fade_start:.3f}:d=4[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=8:attack=80:release=700:makeup=1[ducked];"
        "[voice_st][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
    )
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-filter_complex", filter_graph,
        "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
    ], check=True)


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


def capture_frames(timeline_path: Path, frames_root: Path, *, format_name: str, port: int, timeout: float) -> tuple[Path, dict]:
    edge = _find_edge()
    root = frames_root / format_name
    root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=root))
    env = os.environ.copy()
    env["FABULOOM_WORKSPACE_ROOT"] = r"E:\Fabuloom"
    env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT)
    env["FABULOOM_CAPTURE_DIR"] = str(root)
    server = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"), "--port", str(port)], cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        _wait_http(f"http://127.0.0.1:{port}/capture-topazioverse-channel-trailer.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazioverse-channel-trailer.html?session={session}&timeline=/exports/{relative}&fps={CAPTURE_FPS}&format={format_name}"
        browser = subprocess.Popen([edge, "--headless=new", "--hide-scrollbars", f"--window-size={HORIZONTAL[0] if format_name == 'horizontal' else VERTICAL[0]},{HORIZONTAL[1] if format_name == 'horizontal' else VERTICAL[1]}", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


def render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, size: tuple[int, int], *, overwrite: bool) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-framerate", str(OUTPUT_FPS), "-i", str(frames / "%06d.jpg"), "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-s", f"{size[0]}x{size[1]}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output),
    ], check=True)


def make_board(frames: Path, timeline: dict, output: Path, *, columns: int, rows: int, overwrite: bool) -> None:
    with tempfile.TemporaryDirectory(prefix=".trailer-board-", dir=output.parent) as temp:
        files = []
        for index, scene in enumerate(timeline["scenes"]):
            frame = frames / f"{max(0, round(((scene['start_ms'] + scene['end_ms']) / 2) * OUTPUT_FPS / 1000)):06d}.jpg"
            target = Path(temp) / f"{index:02d}.png"
            label = scene["label"].replace(":", "\\:").replace("'", "\\'")
            vf = f"scale=384:216:force_original_aspect_ratio=decrease,pad=384:216:(ow-iw)/2:(oh-ih)/2:color=0x030914,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':x=12:y=12:fontsize=18:fontcolor=white:box=1:boxcolor=0x071426cc"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame), "-vf", vf, str(target)], check=True)
            files.append(target)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", "1", "-i", str(Path(temp) / "%02d.png"), "-frames:v", str(len(files)), "-vf", f"tile={columns}x{rows}", str(output)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8776)
    parser.add_argument("--capture-timeout", type=float, default=1200)
    args = parser.parse_args()
    for required in (MUSIC, SOURCE_UI, SOURCE_NARRATOR):
        if not required.is_file():
            raise FileNotFoundError(required)
    for index in range(1, 6):
        if not list(SOURCE_STORY_ROOT.joinpath("scenes").glob(f"0{index}-*.png")):
            raise FileNotFoundError(f"pilot scene {index}")
    audio_dir = PROJECT_ROOT / "audio"
    timeline_dir = PROJECT_ROOT / "timeline"
    frames_root = PROJECT_ROOT / ".frames"
    captures_dir = PROJECT_ROOT / "captures"
    reports_dir = PROJECT_ROOT / "reports"
    for directory in (audio_dir, timeline_dir, frames_root, captures_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)
    manifest_path = PROJECT_ROOT / "manifest.json"
    manifest, synthesis = _synthesize_or_reuse(
        manifest_path,
        audio_dir / "horizontal",
        overwrite=args.overwrite,
        script_text=SCRIPT_TEXT,
        narration_id=PROJECT_ID,
        manifest_id=PROJECT_ID,
    )
    vertical_manifest_path = PROJECT_ROOT / "vertical-manifest.json"
    vertical_manifest, vertical_synthesis = _synthesize_or_reuse(
        vertical_manifest_path,
        audio_dir / "vertical",
        overwrite=args.overwrite,
        script_text=VERTICAL_SCRIPT_TEXT,
        narration_id=VERTICAL_PROJECT_ID,
        manifest_id=VERTICAL_PROJECT_ID,
    )
    timeline = build_timeline(
        manifest,
        manifest_ref=f"{PROJECT_ID}/manifest.json",
        block_ranges=BLOCK_RANGES,
        scene_specs=SCENE_SPECS,
        title="TopazioVerse — Trailer oficial do canal",
    )
    vertical_timeline = build_timeline(
        vertical_manifest,
        manifest_ref=f"{PROJECT_ID}/vertical-manifest.json",
        block_ranges=VERTICAL_BLOCK_RANGES,
        scene_specs=VERTICAL_SCENE_SPECS,
        title="TopazioVerse — Teaser vertical do canal",
    )
    timeline_path = timeline_dir / f"{PROJECT_ID}.json"
    vertical_timeline_path = timeline_dir / f"{VERTICAL_PROJECT_ID}.json"
    _json(timeline_path, timeline)
    _json(vertical_timeline_path, vertical_timeline)
    write_srt(manifest, timeline_dir / f"{PROJECT_ID}.srt")
    write_srt(vertical_manifest, timeline_dir / f"{VERTICAL_PROJECT_ID}.srt")
    (timeline_dir / "script-pt-BR.txt").write_text(SCRIPT_TEXT + "\n", encoding="utf-8")
    (timeline_dir / "script-pt-BR-vertical.txt").write_text(VERTICAL_SCRIPT_TEXT + "\n", encoding="utf-8")
    _json(PROJECT_ROOT / "assets.json", {
        "story_images": {scene["id"]: f"{V1_PROJECT_ID}/scenes/{Path(scene['asset']).name}" for scene in timeline["scenes"] if scene["asset"] and scene["asset"].startswith("story/")},
        "vertical_story_images": {scene["id"]: f"{V1_PROJECT_ID}/scenes/{Path(scene['asset']).name}" for scene in vertical_timeline["scenes"] if scene["asset"] and scene["asset"].startswith("story/")},
        "real_captures": {"fabuloom_ui": "official-promo/evidence/fabuloom-studio-ui-real.png", "narrator_mode": "official-promo/evidence/fabuloom-narrator-mode-real.png"},
        "conceptual_visuals": sorted({scene["id"] for plan in (timeline, vertical_timeline) for scene in plan["scenes"] if scene["visual"].endswith("concept") or scene["visual"] in {"host_large", "channel_lockup", "playlist_concept", "crystal_stage"}}),
        "authenticity": "Conceptual panels are labelled in-video; real captures are identified as real local captures.",
        "music": timeline["soundtrack"],
    })
    voice_path = audio_dir / "horizontal" / f"{PROJECT_ID}-voice.wav"
    compose_voice(manifest, voice_path)
    mix_path = audio_dir / "horizontal" / f"{PROJECT_ID}-mix.wav"
    mix_audio(voice_path, MUSIC, mix_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    vertical_voice_path = audio_dir / "vertical" / f"{VERTICAL_PROJECT_ID}-voice.wav"
    compose_voice(vertical_manifest, vertical_voice_path)
    vertical_mix_path = audio_dir / "vertical" / f"{VERTICAL_PROJECT_ID}-mix.wav"
    mix_audio(vertical_voice_path, MUSIC, vertical_mix_path, int(vertical_manifest["duration_ms"]), overwrite=args.overwrite)
    outputs = []
    render_jobs = (
        ("horizontal", HORIZONTAL, timeline_path, manifest, mix_path, args.port, f"{PROJECT_ID}-1080p.mp4"),
        ("vertical", VERTICAL, vertical_timeline_path, vertical_manifest, vertical_mix_path, args.port + 1, f"{PROJECT_ID}-short-vertical.mp4"),
    )
    for format_name, size, current_timeline_path, current_manifest, current_mix_path, port, output_name in render_jobs:
        format_root = frames_root / format_name
        if args.reuse_capture:
            existing = sorted(format_root.glob("capture-*/complete.json"), key=lambda path: path.stat().st_mtime, reverse=True)
            if not existing:
                raise FileNotFoundError(f"no {format_name} capture available")
            session_dir = existing[0].parent
            completion = json.loads(existing[0].read_text(encoding="utf-8"))
            frame_count = _materialize(session_dir, completion)
        else:
            session_dir, completion = capture_frames(current_timeline_path, frames_root, format_name=format_name, port=port, timeout=args.capture_timeout)
            frame_count = _materialize(session_dir, completion)
        output = PROJECT_ROOT / output_name
        render_mp4(session_dir, current_mix_path, output, int(current_manifest["duration_ms"]), size, overwrite=args.overwrite)
        outputs.append({"format": format_name, "video": str(output), "frames": str(session_dir), "frame_count": frame_count, "probe": probe(output)})
    board = captures_dir / f"{PROJECT_ID}-frames.png"
    make_board(Path(outputs[0]["frames"]), timeline, board, columns=5, rows=3, overwrite=args.overwrite)
    vertical_board = captures_dir / f"{VERTICAL_PROJECT_ID}-frames.png"
    make_board(Path(outputs[1]["frames"]), vertical_timeline, vertical_board, columns=4, rows=2, overwrite=args.overwrite)
    report = {
        "project": PROJECT_ID,
        "script": str(timeline_dir / "script-pt-BR.txt"),
        "manifest": str(manifest_path),
        "vertical_script": str(timeline_dir / "script-pt-BR-vertical.txt"),
        "vertical_manifest": str(vertical_manifest_path),
        "timeline": str(timeline_path),
        "vertical_timeline": str(vertical_timeline_path),
        "voice": str(voice_path),
        "vertical_voice": str(vertical_voice_path),
        "mix": str(mix_path),
        "vertical_mix": str(vertical_mix_path),
        "board": str(board),
        "vertical_board": str(vertical_board),
        "duration_ms": int(manifest["duration_ms"]),
        "duration_seconds": int(manifest["duration_ms"]) / 1000,
        "vertical_duration_ms": int(vertical_manifest["duration_ms"]),
        "vertical_duration_seconds": int(vertical_manifest["duration_ms"]) / 1000,
        "blocks": timeline["blocks"],
        "scenes": timeline["scenes"],
        "vertical_blocks": vertical_timeline["blocks"],
        "vertical_scenes": vertical_timeline["scenes"],
        "synthesis": synthesis,
        "vertical_synthesis": vertical_synthesis,
        "outputs": outputs,
        "music": timeline["soundtrack"],
        "timing_source": "measured_kokoro_wav_segments",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "human_review_required": True,
        "state": "completed_pending_human_audio_visual_review",
    }
    _json(reports_dir / "trailer-result.json", report)
    (reports_dir / "technical-report.md").write_text(
        "# TopazioVerse — trailer oficial do canal\n\n"
        f"- Duração medida: `{manifest['duration_ms']} ms` (`{manifest['duration_ms'] / 1000:.3f} s`).\n"
        f"- Teaser vertical: `{vertical_manifest['duration_ms']} ms` (`{vertical_manifest['duration_ms'] / 1000:.3f} s`), com roteiro condensado e medição independente.\n"
        f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; segmentos: `{len(manifest['segments'])}`.\n"
        "- Santa V5 é renderizado pelo caminho real do Narrator Mode e permanece visível em todas as cenas.\n"
        "- Os cinco visuais de fantasia são assets locais autorizados/reutilizados do piloto do Livro 1.\n"
        "- Fabuloom Studio e Narrator Mode são capturas reais locais; jogos, blockchain, eletrônica e laboratório sem captura autorizada são identificados como conceito visual.\n"
        f"- Trilha: `{MUSIC}`; composição procedural original local herdada da promoção anterior.\n"
        "- Mix: voz prioritária, sidechain ducking, fades e limiter.\n"
        "- RMS é uma aproximação de boca; não há timestamps de palavras, fonemas ou visemas.\n"
        "- Aprovação artística humana e revisão de direitos permanecem obrigatórias.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
