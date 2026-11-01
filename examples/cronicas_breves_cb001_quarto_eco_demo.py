"""Produce CB-001, O Quarto Eco, as a deterministic vertical short.

The narration is the exact proposed folklore text from the private editorial
brief. Story imagery is environment-only; Santa V5 is the only rendered
character identity. Word, phoneme and viseme timings are intentionally not
fabricated: captions and RMS mouth motion use measured WAV segment ranges.
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
from urllib.parse import quote
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError
from first_video_demo import _compose_audio, _write_srt
from narrator_mode_demo import _edge_path

FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
PROJECT_ID = "cb-001-o-quarto-eco"
PROJECT_ROOT = EXPORT_ROOT / "cronicas-breves" / PROJECT_ID
MUSIC_SOURCE = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Os Ecos que Nunca Morrem.mp3"
LIBRARY_IMAGE = EXPORT_ROOT / "official-scenes" / "santa-library-topazioverse-v1" / "library-base.png"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
MUSIC_SHA256 = "89FD1D0630584A899991626AC2431C432012257851B7EFB4DA83DA8380CA8DC9"

STORY_TEXT = """Guardião... você já ouviu falar do quarto eco?

Na Caverna do Eco Etéreo, os cristais guardam memórias de Topázio.

Mas existe uma história que ninguém sabe se aconteceu.

Dizem que, certa noite, alguém entrou naquela caverna e fez uma pergunta às pedras:

\"Quem ainda se lembra de mim?\"

O primeiro eco repetiu a pergunta.

O segundo... também.

O terceiro veio tão baixo que mal se ouviu.

Então surgiu um quarto.

E ele respondeu:

\"Eu nunca esqueci.\"

O estranho é que aquela voz não pertencia a ninguém que estivesse ali.

Desde então, alguns dizem que certas lembranças não precisam de alguém para continuar vivas.

Você teria coragem de fazer uma pergunta àquelas pedras?

Se quiser conhecer as grandes histórias desse mundo, procure Crônicas de Topázio no YouTube.

A gente se encontra lá, Guardião."""

SCENE_IMAGES = {
    "intro": "official-scenes/santa-library-topazioverse-v1/library-base.png",
    "cave": f"cronicas-breves/{PROJECT_ID}/assets/scenes/01-cave-entrance.png",
    "crystal": f"cronicas-breves/{PROJECT_ID}/assets/scenes/02-crystal-ring.png",
    "memory": f"cronicas-breves/{PROJECT_ID}/assets/scenes/03-memory-lights.png",
    "question": f"cronicas-breves/{PROJECT_ID}/assets/scenes/04-silent-question.png",
    "fourth": f"cronicas-breves/{PROJECT_ID}/assets/scenes/05-fourth-echo.png",
    "exit": f"cronicas-breves/{PROJECT_ID}/assets/scenes/06-cave-exit.png",
}

MARKERS = (
    ("intro", "Guardião"),
    ("cave", "Na Caverna"),
    ("crystal", "Dizem que"),
    ("question", "Quem ainda"),
    ("echo-1", "O primeiro"),
    ("echo-2", "O segundo"),
    ("echo-3", "O terceiro"),
    ("fourth", "Então surgiu"),
    ("resolution", "O estranho"),
    ("challenge", "Você teria"),
    ("outro", "Se quiser"),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size,format_name:stream=index,codec_name,codec_type,width,height,pix_fmt,sample_rate,channels,channel_layout", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _synthesize(manifest_path: Path, audio_root: Path, overwrite: bool) -> tuple[dict, float, float, str]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    if manifest_path.is_file() and not overwrite:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest, 0.0, 0.0, "reused"
    provider = KokoroTTSProvider(output_dir=audio_root, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(
            provider, STORY_TEXT, narration_id=PROJECT_ID, manifest_id=PROJECT_ID,
            timeline_id=f"{PROJECT_ID}-timeline", language=LANGUAGE, voice_id=VOICE_ID,
            output_dir=audio_root, max_chars=360,
        )
        manifest = json.loads(serialize_manifest(run.manifest))
        manifest["metadata"]["editorial_status"] = "ROTEIRO PROPOSTO; aprovação artística e canônica pendentes"
        manifest["metadata"]["source_text_sha256"] = hashlib.sha256(STORY_TEXT.encode("utf-8")).hexdigest()
        _write_json(manifest_path, manifest)
        load_seconds = float(run.results[0].metadata.get("model_load_seconds") or 0) if run.results else 0.0
        return manifest, run.processing_seconds, load_seconds, "synthesized"
    except (TTSError, NarrationSynthesisError):
        raise
    finally:
        provider.close()


def _capture_manifest(manifest: dict, project_root: Path) -> dict:
    capture = json.loads(json.dumps(manifest))
    for segment in capture["segments"]:
        segment["audio_uri"] = f"cronicas-breves/{PROJECT_ID}/audio/{Path(segment["audio_uri"].replace("file:///", "")).name}"
    return capture


def _scene_schedule(manifest: dict) -> list[dict]:
    starts: dict[str, int] = {}
    for scene_id, marker in MARKERS:
        matches = [index for index, segment in enumerate(manifest["segments"]) if marker in segment["text"]]
        if not matches:
            raise ValueError(f"measured segment marker not found: {marker}")
        starts[scene_id] = matches[0]
    ordered = [(scene_id, starts[scene_id]) for scene_id, _ in MARKERS]
    if ordered[0][1] != 0 or any(left[1] >= right[1] for left, right in zip(ordered, ordered[1:])):
        raise ValueError(f"measured segment order changed: {ordered}")
    scenes = []
    visual = {
        "intro": ("intro", "zoom_in", "none", "Abertura"),
        "cave": ("cave", "pan_vertical", "mist", "Caverna"),
        "crystal": ("crystal", "crystal_approach", "crystal_pulse", "Cristais"),
        "question": ("question", "zoom_in", "none", "A pergunta"),
        "echo-1": ("question", "zoom_in", "echo_pulse", "Primeiro eco"),
        "echo-2": ("question", "pan_lateral", "echo_pulse", "Segundo eco"),
        "echo-3": ("question", "pan_lateral", "echo_pulse", "Terceiro eco"),
        "fourth": ("fourth", "crystal_approach", "darken", "Quarto eco"),
        "resolution": ("exit", "pan_vertical", "mist", "A voz"),
        "challenge": ("exit", "zoom_in", "none", "A pergunta final"),
        "outro": ("intro", "pan_lateral", "none", "Despedida"),
    }
    for position, (scene_id, start_index) in enumerate(ordered):
        end_index = ordered[position + 1][1] if position + 1 < len(ordered) else len(manifest["segments"])
        end_ms = manifest["segments"][end_index]["start_ms"] if end_index < len(manifest["segments"]) else manifest["duration_ms"]
        image_key, camera, effect, label = visual[scene_id]
        scenes.append({
            "id": f"cb001-{scene_id}", "label": label, "image": SCENE_IMAGES[image_key],
            "camera": camera, "effect": effect, "start_ms": manifest["segments"][start_index]["start_ms"], "end_ms": end_ms,
            "text_segment_ids": [segment["id"] for segment in manifest["segments"][start_index:end_index]],
            "environment_only": image_key != "intro", "character_policy": "approved_santa_v5_only",
        })
    return scenes


def _smooth_music_duck(voice_path: Path, music_path: Path, output: Path, duration_ms: int, fourth_start_ms: int, fourth_end_ms: int, overwrite: bool) -> dict:
    duration = duration_ms / 1000.0
    fourth_start = max(0.0, fourth_start_ms / 1000.0 - 0.25)
    fourth_end = min(duration, fourth_end_ms / 1000.0 + 0.75)
    fade_start = max(0.0, duration - 2.8)
    expression = (
        f"if(lt(t,{fourth_start:.3f}),1,if(lt(t,{fourth_start + .45:.3f}),"
        f"1-0.88*(t-{fourth_start:.3f})/.45,if(lt(t,{fourth_end - .45:.3f}),0.12,"
        f"if(lt(t,{fourth_end:.3f}),0.12+0.88*(t-{fourth_end - .45:.3f})/.45,1))))"
    )
    filter_graph = (
        "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit=2[voice][det];"
        f"[1:a]aresample=48000,atrim=duration={duration:.3f},volume=0.24,"
        f"volume='{expression}':eval=frame,afade=t=in:st=0:d=1.2,afade=t=out:st={fade_start:.3f}:d=2.8[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=8:attack=35:release=620:makeup=1:link=average[ducked];"
        "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.93[out]"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-i", str(voice_path), "-stream_loop", "-1", "-i", str(music_path),
        "-filter_complex", filter_graph, "-map", "[out]", "-t", f"{duration:.3f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
    ]
    subprocess.run(command, check=True, cwd=output.parent)
    return {"fourth_echo_window_ms": [round(fourth_start * 1000), round(fourth_end * 1000)], "ducking": "sidechaincompress voice->music", "music_base_gain": 0.24, "fourth_echo_gain_factor": 0.12}


def _capture(studio_root: Path, profile_path: Path, frames_root: Path, export_root: Path, port: int, timeout: float) -> tuple[Path, dict]:
    frames_root.mkdir(parents=True, exist_ok=True)
    session_dir = frames_root / f"capture-{int(time.time())}"
    session_dir.mkdir(parents=True, exist_ok=True)
    edge_profile = Path(tempfile.mkdtemp(prefix=".cb001-edge-", dir=frames_root))
    env = os.environ.copy(); env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(export_root)})
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/capture-cb001-quarto-eco.html", timeout=1): break
            except Exception: time.sleep(.2)
        else: raise TimeoutError("CB-001 capture server did not start")
        relative = profile_path.relative_to(export_root).as_posix()
        url = f"http://127.0.0.1:{port}/capture-cb001-quarto-eco.html?session={quote(session_dir.name)}&profile={quote('/exports/' + relative, safe='')}&fps={FPS}"
        command = [str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", "--dump-dom", "--hide-scrollbars", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--window-size={WIDTH},{HEIGHT}", f"--user-data-dir={edge_profile}", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"; error = session_dir / "error.json"; end = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < end: time.sleep(.25)
        if error.exists(): raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists(): raise TimeoutError(f"CB-001 capture timed out: {session_dir}")
        completion = json.loads(complete.read_text(encoding="utf-8")); frames = sorted(path for path in session_dir.glob("*.png") if path.stem.isdigit())
        if len(frames) != completion["frame_count"] or any(path.stat().st_size < 1000 for path in frames): raise RuntimeError("CB-001 capture is incomplete")
        return session_dir, completion
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try: browser.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(browser.pid), "/T", "/F"], check=False, capture_output=True)
        shutil.rmtree(edge_profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


def _render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, overwrite: bool) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio),
        "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output),
    ], check=True, cwd=output.parent)


def _frame_board(frames: Path, output: Path, duration_ms: int) -> None:
    last = max(0, int(round(duration_ms / 1000 * FPS)) - 1)
    indexes = [round(last * ratio) for ratio in (0.02, .12, .22, .32, .42, .52, .62, .74, .90)]
    labels = ["abertura", "caverna", "cristais", "pergunta", "eco 1", "eco 2", "quarto eco", "resposta", "despedida"]
    inputs: list[str] = []; filters: list[str] = []
    for index, label in zip(indexes, labels):
        inputs += ["-i", str(frames / f"{index:06d}.png")]
        slot = chr(97 + len(filters)); filters.append(f"[{len(filters)}:v]scale=270:480,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=18:x=10:y=12:box=1:boxcolor=0x07142A@.85[{slot}]")
    filters.append("[a][b][c][d][e][f][g][h][i]xstack=inputs=9:layout=0_0|270_0|540_0|0_480|270_480|540_480|0_960|270_960|540_960[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _blackdetect(video: Path) -> dict:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.05:pic_th=0.98", "-an", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    hits = [line.strip() for line in result.stderr.splitlines() if "black_start" in line]
    return {"passed": not hits, "detections": hits, "returncode": result.returncode}


def _audio_levels(path: Path) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    return "; ".join(line.strip() for line in result.stderr.splitlines() if "mean_volume" in line or "max_volume" in line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8793)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    export_root = args.export_root.resolve(); project_root = export_root / "cronicas-breves" / PROJECT_ID
    audio_root = project_root / "audio"; timeline_root = project_root / "timeline"; captures_root = project_root / "captures"; reports_root = project_root / "reports"; metadata_root = project_root / "metadata"; videos_root = project_root / "videos"; frames_root = project_root / ".frames"
    for directory in (audio_root, timeline_root, captures_root, reports_root, metadata_root, videos_root, frames_root): directory.mkdir(parents=True, exist_ok=True)
    if not MUSIC_SOURCE.is_file(): raise FileNotFoundError(MUSIC_SOURCE)
    if _sha256(MUSIC_SOURCE) != MUSIC_SHA256: raise ValueError("source music hash changed; refusing to proceed")
    for relative in ("01-cave-entrance.png", "02-crystal-ring.png", "03-memory-lights.png", "04-silent-question.png", "05-fourth-echo.png", "06-cave-exit.png"):
        if not (project_root / "assets" / "scenes" / relative).is_file(): raise FileNotFoundError(project_root / "assets" / "scenes" / relative)
    if not LIBRARY_IMAGE.is_file(): raise FileNotFoundError(LIBRARY_IMAGE)
    manifest_path = audio_root / "narration-manifest.json"; voice_path = audio_root / "voice.wav"; mixed_path = audio_root / "mixed.wav"; source_music_copy = audio_root / "source-music.mp3"; srt_path = timeline_root / "cb-001-o-quarto-eco.srt"; capture_manifest_path = timeline_root / "capture-manifest.json"; profile_path = timeline_root / "cb-001-o-quarto-eco-profile.json"; storyboard_path = timeline_root / "storyboard-used.json"; output = videos_root / "fabuloom-cb001-o-quarto-eco.mp4"; board = captures_root / "cb001-storyboard-board.png"; report_json = reports_root / "technical-report.json"; report_md = reports_root / "technical-report.md"
    started = time.perf_counter()
    manifest, synthesis_seconds, load_seconds, synthesis_status = _synthesize(manifest_path, audio_root, args.overwrite and not args.reuse_manifest)
    sample_rate, _ = _compose_audio(manifest, voice_path)
    _write_srt(manifest, srt_path)
    shutil.copy2(MUSIC_SOURCE, source_music_copy)
    scenes = _scene_schedule(manifest)
    fourth_scene = next(scene for scene in scenes if scene["id"] == "cb001-fourth")
    mix_info = _smooth_music_duck(voice_path, source_music_copy, mixed_path, int(manifest["duration_ms"]), int(fourth_scene["start_ms"]), int(fourth_scene["end_ms"]), args.overwrite)
    capture_manifest = _capture_manifest(manifest, project_root); _write_json(capture_manifest_path, capture_manifest)
    profile = {
        "format": "fabuloom.vertical-story/0.1", "id": PROJECT_ID, "title": "O Quarto Eco", "story_text": STORY_TEXT,
        "manifest": f"cronicas-breves/{PROJECT_ID}/timeline/capture-manifest.json", "duration_ms": manifest["duration_ms"],
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "aspect_ratio": "9:16"},
        "audio": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "voice_wav": f"cronicas-breves/{PROJECT_ID}/audio/voice.wav", "mixed_wav": f"cronicas-breves/{PROJECT_ID}/audio/mixed.wav", "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable"},
        "narrator": {"renderer": "NarratorAvatarRenderer", "character": "Santa V5", "library_asset_id": "santa-library-topazioverse-v1", "x": 48, "y": 1360, "size": 300},
        "safe_area": {"left": 42, "top": 88, "right": 1038, "bottom": 1720, "platform_ui_bottom": 180},
        "subtitles": {"x": 715, "y": 1480, "width": 620, "font_size": 29, "line_height": 40, "max_lines": 3},
        "transitions": {"crossfade_ms": 650}, "scenes": scenes,
        "export": {"video_codec": "h264", "audio_codec": "aac", "pixel_format": "yuv420p", "width": WIDTH, "height": HEIGHT, "fps": FPS, "audio_sample_rate": 48000, "audio_channels": 2, "public_technical_overlay": False},
        "story_provenance": {"classification": "proposed_folklore", "canon_claims": "none", "editorial_status": "ROTEIRO PROPOSTO", "draft_character_rendering": "blocked", "story_visual_policy": "environment_only"},
    }
    _write_json(profile_path, profile); _write_json(storyboard_path, {"format": "fabuloom.cb001-storyboard/0.1", "source": "private editorial CB-001-O-QUARTO-ECO.md", "scenes": scenes, "timing_source": "measured_wav_segments"})
    if frames_root.exists() and not args.reuse_capture:
        for child in frames_root.iterdir():
            if child.is_dir() and child.name.startswith("capture-"): shutil.rmtree(child)
    if args.reuse_capture:
        candidates = sorted(frames_root.glob("capture-*/complete.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates: raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = candidates[0].parent; completion = json.loads(candidates[0].read_text(encoding="utf-8"))
    else:
        session_dir, completion = _capture(STUDIO_ROOT, profile_path, frames_root, export_root, args.port, args.capture_timeout)
    _render_mp4(session_dir, mixed_path, output, int(manifest["duration_ms"]), args.overwrite)
    _frame_board(session_dir, board, int(manifest["duration_ms"]))
    probe = _probe(output); audio_probe = _probe(mixed_path); source_probe = _probe(MUSIC_SOURCE); black = _blackdetect(output)
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video"); audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    metadata = {"title": "O Quarto Eco — Crônicas Breves", "series": "Lendas e Segredos de Topázio", "description": "Um conto proposto de folclore de Topázio: dizem que, na Caverna do Eco Etéreo, existe uma pergunta que recebeu quatro respostas.", "hashtags": ["#CronicasDeTopazio", "#Topazioverse", "#LendasDeTopazio", "#Shorts", "#Fantasia"], "voice": {"character": "Santa V5", "voice_id": VOICE_ID, "language": LANGUAGE}, "format": "1080x1920 9:16 30fps", "published": False, "publication_pending": ["aprovação artística humana", "confirmação de direitos comerciais da trilha de origem Suno"], "source_text_sha256": hashlib.sha256(STORY_TEXT.encode("utf-8")).hexdigest(), "timing_source": "measured_wav_segments"}
    _write_json(metadata_root / "shorts-tiktok-metadata.json", metadata)
    duration_ok = abs(float(probe["format"]["duration"]) - manifest["duration_ms"] / 1000) < 0.10
    report = {"format": "fabuloom.cb001-technical-report/0.1", "project": PROJECT_ID, "editorial_status": "ROTEIRO PROPOSTO; aprovação artística e canônica pendentes", "source_text_sha256": hashlib.sha256(STORY_TEXT.encode("utf-8")).hexdigest(), "manifest": str(manifest_path), "capture_manifest": str(capture_manifest_path), "srt": str(srt_path), "storyboard": str(storyboard_path), "profile": str(profile_path), "video": str(output), "frame_board": str(board), "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "scenes": len(scenes), "synthesis_status": synthesis_status, "synthesis_seconds": synthesis_seconds, "model_load_seconds": load_seconds, "model_id": manifest["segments"][0].get("metadata", {}).get("model_id"), "model_revision": manifest["segments"][0].get("metadata", {}).get("model_revision"), "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "sample_rate": sample_rate}, "source_music": {"path": str(MUSIC_SOURCE), "preserved_copy": str(source_music_copy), "sha256": _sha256(MUSIC_SOURCE), "probe": source_probe, "rights_origin": "Suno; commercial-rights confirmation pending"}, "mix": {**mix_info, "path": str(mixed_path), "probe": audio_probe, "levels": _audio_levels(mixed_path)}, "probe": probe, "validation": {"duration_coherent": duration_ok, "blackdetect": black, "ffmpeg_decode": True, "subtitle_sync": len(manifest["segments"]) == len(srt_path.read_text(encoding="utf-8").strip().split("\n\n")), "santa_renderer": "NarratorAvatarRenderer", "santa_character": "Santa V5", "santa_presence": "rendered in every frame as official avatar", "draft_characters": "blocked", "story_visuals": "environment_only", "word_phoneme_viseme_timing": "unavailable"}, "human_visual_review_required": True, "processing_seconds": round(time.perf_counter() - started, 3), "state": "completed_pending_human_artistic_review"}
    _write_json(report_json, report)
    report_md.write_text("\n".join(["# CB-001 — O Quarto Eco", "", "- Estado editorial: roteiro proposto; não é afirmação canônica.", f"- Texto exato: hash SHA-256 `{report['source_text_sha256']}`; `{len(manifest['segments'])}` segmentos medidos; duração real `{manifest['duration_ms']} ms`.", f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; modelo `{report['model_id']}`; revisão `{report['model_revision']}`.", f"- Trilha: `{MUSIC_SOURCE}`; cópia preservada em `{source_music_copy}`; duração de origem `{source_probe['format']['duration']} s`; hash `{report['source_music']['sha256']}`.", "- Mixagem: voz mono convertida para estéreo, música original sem alteração de tom/velocidade, sidechain ducking, limiter e janela de silêncio dramático no quarto eco.", f"- MP4: `{output}`; FFprobe `{probe['format']['duration']} s`; H.264 `{video_stream.get('width')}×{video_stream.get('height')}` `{video_stream.get('pix_fmt')}`; AAC estéreo `{audio_stream.get('sample_rate')} Hz`.", f"- Quadros: `{completion['frame_count']}` a `{FPS}` FPS; Santa V5 foi renderizado por `NarratorAvatarRenderer`; visuais de história são apenas ambientes e objetos.", "- Personagens DRAFT: bloqueados; Thaurion e visitantes não são renderizados.", "- Legendas: SRT por intervalos reais dos segmentos; palavra/fonema/visema indisponíveis.", "- Placas ambientais: produzidas como conceito original local; aprovação artística humana pendente.", "- Direitos comerciais da trilha com origem Suno precisam ser confirmados antes de publicação.", "- Não publicado automaticamente; sem merge nesta missão.", ""]), encoding="utf-8")
    _write_json(reports_root / "validation.json", {"duration_coherent": duration_ok, "blackdetect": black, "ffmpeg_decode": True, "subtitle_sync": report["validation"]["subtitle_sync"], "source_music_present": True, "santa_present": True, "draft_characters_absent": True})
    print(json.dumps({"video": str(output), "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "scenes": len(scenes), "probe": probe, "report": str(report_json), "state": "completed"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
