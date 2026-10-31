"""Produce Mission 019: a reusable 1080x1920 vertical cinematic story."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from urllib.parse import quote
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError

from first_video_demo import _compose_audio, _write_srt
from narrator_mode_demo import _edge_path, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
PROJECT_ID = "vertical-story-v1"
STORY_ID = "fabuloom-vertical-story-v1"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
STORY_TEXT = """Você já imaginou uma cidade construída sobre um segredo capaz de destruir um reino inteiro?

Durante centenas de anos, os habitantes de Arenhast acreditaram que os Cristais Primordiais haviam desaparecido.

Mas, nas profundezas de um templo esquecido, uma luz azul começou a despertar.

Naquela noite, as muralhas tremeram. As tochas se apagaram. E uma sombra atravessou os portões do templo.

Ninguém sabia quem havia chegado.

Apenas uma coisa era certa: o cristal havia escolhido seu próximo guardião.

E a história de Topázio estava prestes a mudar."""

SCENE_ASSETS = (
    ("arenhast-city", "vertical-story-v1/scenes/scene-1-arenhast-city-1080x1920.png", "zoom_in", "none", "A cidade e seu segredo"),
    ("primordial-temple", "vertical-story-v1/scenes/scene-2-primordial-temple-1080x1920.png", "pan_vertical", "none", "Os Cristais Primordiais"),
    ("crystal-awakening", "vertical-story-v1/scenes/scene-3-crystal-awakening-1080x1920.png", "crystal_approach", "crystal_pulse", "O despertar"),
    ("temple-shadow", "vertical-story-v1/scenes/scene-4-temple-shadow-1080x1920.png", "pan_lateral", "darken", "A sombra"),
    ("next-guardian", "vertical-story-v1/scenes/scene-5-next-guardian-1080x1920.png", "crystal_approach", "particles", "O próximo guardião"),
)

IMAGE_PROMPTS = [
    "Original 9:16 portrait: Arenhast at night, monumental medieval-fantasy city among dark mountains, ancient walls and tall towers, distant warm-gold castle, storm clouds, deep blue and gold, no text/logo/watermark.",
    "Original 9:16 portrait: ancient underground Arenhast temple, carved columns, inscriptions and geometric symbols of vanished primordial crystals, blue shafts and gold torches, no text/logo/watermark.",
    "Original 9:16 portrait: forgotten circular chamber, one floating primordial blue crystal above a dark stone dais, gold floor rings, mist and restrained dust motes, no text/logo/watermark.",
    "Original 9:16 portrait: temple gates open to a blue-lit interior, one anonymous cloaked silhouette crossing the threshold, mist and dying gold torches, no face, no identifying features, no text/logo/watermark.",
    "Original 9:16 portrait: anonymous backlit cloaked figure before a floating primordial blue crystal, crystal light, gold reflections, mist and subtle particles, no face or identifying details, no text/logo/watermark.",
]


def _write_json(path: Path, payload: object, overwrite: bool) -> None:
    if path.exists() and not overwrite: raise FileExistsError(f"file exists: {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _schedule(manifest: dict) -> list[dict]:
    if len(manifest["segments"]) < 5: raise ValueError("Mission 019 needs at least five measured narration segments")
    last_index = len(manifest["segments"]) - 1
    groups = [(0,), (1,), (2,), (3, 4), tuple(range(5, last_index + 1))]
    scenes = []
    for index, ((scene_id, image, camera, effect, label), group) in enumerate(zip(SCENE_ASSETS, groups)):
        first = manifest["segments"][group[0]]; last = manifest["segments"][group[-1]]
        end_ms = manifest["duration_ms"] if index == len(SCENE_ASSETS) - 1 else last["end_ms"] + int(last.get("metadata", {}).get("pause_after_ms", 0))
        scenes.append({"id": scene_id, "label": label, "image": image, "camera": camera, "effect": effect, "start_ms": first["start_ms"], "end_ms": end_ms, "text_segment_ids": [manifest["segments"][position]["id"] for position in group]})
    return scenes


def _generate_music(duration_ms: int, output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite: raise FileExistsError(f"music exists: {output}; pass --overwrite")
    rate = 24000; channels = 2; total = max(1, round(duration_ms * rate / 1000))
    roots = (73.416, 65.406, 82.407, 73.416, 55.0)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(channels); stream.setsampwidth(2); stream.setframerate(rate)
        frames = bytearray()
        for index in range(total):
            t = index / rate; section = min(len(roots) - 1, int(t / max(1, duration_ms / 1000) * len(roots))); root = roots[section]
            pulse = (math.sin(t * 0.37) + 1) * 0.5
            pad = math.sin(2 * math.pi * root * t) * 0.52 + math.sin(2 * math.pi * root * 2 * t) * 0.22 + math.sin(2 * math.pi * root * 3 * t) * 0.08
            arpeggio = math.sin(2 * math.pi * root * (1.5 + (int(t * .75) % 4) * .25) * t) * (.10 + pulse * .04)
            shimmer = math.sin(2 * math.pi * root * 5.02 * t + pulse * .8) * .035
            envelope = min(1.0, t / 1.8, max(0.0, (duration_ms / 1000 - t) / 2.5))
            value = max(-1.0, min(1.0, (pad * .10 + arpeggio + shimmer) * envelope))
            left = int(value * 32767); right = int((value * .96 + math.sin(t * .19) * .004) * 32767)
            frames.extend(struct.pack("<hh", left, right))
        stream.writeframes(frames)


def _mix_audio(voice: Path, music: Path, output: Path, duration_ms: int, overwrite: bool) -> None:
    duration = duration_ms / 1000
    fade_start = max(0.0, duration - 2.5)
    filter_graph = f"[1:a]volume=0.18,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_start:.3f}:d=2.5[bg];[bg][0:a]sidechaincompress=threshold=0.025:ratio=6:attack=25:release=280:makeup=1[ducked];[0:a]aresample=24000,volume=1.0[voice];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[out]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(voice), "-i", str(music), "-filter_complex", filter_graph, "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "24000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True, cwd=output.parent)


def _audio_levels(path: Path) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    lines = [line.strip() for line in result.stderr.splitlines() if "mean_volume" in line or "max_volume" in line]
    return "; ".join(lines)


def _wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-vertical-story.html", timeout=1): return
        except Exception: time.sleep(.2)
    raise TimeoutError("vertical capture server did not start")


def _capture(profile: Path, frames: Path, export_root: Path, port: int, timeout: float) -> dict:
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(frames.parent)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None; browser_profile = None
    try:
        _wait_for_server(port); browser_profile = Path(tempfile.mkdtemp(prefix=".vertical-edge-", dir=frames.parent))
        profile_url = "/exports/" + profile.relative_to(export_root).as_posix()
        url = f"http://127.0.0.1:{port}/capture-vertical-story.html?session={quote(frames.name)}&profile={quote(profile_url, safe='')}&fps={FPS}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={browser_profile}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = frames / "complete.json"; deadline = time.monotonic() + timeout
        while not complete.is_file():
            if time.monotonic() >= deadline: raise TimeoutError(f"vertical capture timed out after {timeout:.0f}s")
            if edge.poll() is not None:
                error = frames / "error.json"; raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before completion")
            time.sleep(.25)
        result = json.loads(complete.read_text(encoding="utf-8")); images = sorted(path for path in frames.glob("*.png") if path.stem.isdigit())
        if len(images) != result["frame_count"] or any(path.stat().st_size < 1000 for path in images): raise ValueError("vertical frames are incomplete")
        return result
    finally:
        if edge is not None and edge.poll() is None:
            edge.terminate()
            try: edge.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"], check=False, capture_output=True)
        if browser_profile is not None: shutil.rmtree(browser_profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


def _frame_board(profile: dict, frames: Path, output: Path) -> None:
    frame_count = len(list(frames.glob("*.png"))); inputs = []; filters = []
    for index, scene in enumerate(profile["scenes"]):
        sample = int(round(((scene["start_ms"] + scene["end_ms"]) / 2) / 1000 * FPS)); sample = max(0, min(frame_count - 1, sample)); inputs += ["-i", str(frames / f"{sample:06d}.png")]
        slot = chr(97 + index); label = scene["label"].replace(":", "\\:"); filters.append(f"[{index}:v]scale=360:640:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=20:x=14:y=16:box=1:boxcolor=0x07142A@.88[{slot}]")
    filters.append("[a][b][c][d][e]xstack=inputs=5:layout=0_0|360_0|720_0|0_640|360_640[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--reuse-manifest", action="store_true"); parser.add_argument("--port", type=int, default=8790); parser.add_argument("--capture-timeout", type=float, default=900); args = parser.parse_args()
    export_root = args.export_dir.resolve(); project_root = export_root / PROJECT_ID; videos = export_root / "videos"; project_root.mkdir(parents=True, exist_ok=True); videos.mkdir(parents=True, exist_ok=True)
    manifest_path = project_root / f"{STORY_ID}.json"; voice_path = project_root / f"{STORY_ID}-voice.wav"; music_path = project_root / f"{STORY_ID}-original-music.wav"; mixed_path = project_root / f"{STORY_ID}-mixed.wav"; profile_path = project_root / f"{STORY_ID}-profile.json"; timeline_path = project_root / f"{STORY_ID}-timeline.json"; frames = project_root / ".frames"; output = videos / "fabuloom-vertical-story-test-v1.mp4"; board = videos / "fabuloom-vertical-story-test-v1-frames.png"; srt = videos / "fabuloom-vertical-story-test-v1.srt"; report = videos / "fabuloom-vertical-story-test-v1-report.md"; report_json = videos / "fabuloom-vertical-story-test-v1-report.json"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file(): manifest = json.loads(manifest_path.read_text(encoding="utf-8")); synthesis_status = "reutilizada"
    else:
        provider = KokoroTTSProvider(output_dir=project_root, allow_overwrite=args.overwrite)
        try:
            run = synthesize_narration(provider, STORY_TEXT, narration_id=STORY_ID, manifest_id=STORY_ID, voice_id=VOICE_ID, language=LANGUAGE, output_dir=project_root, max_chars=360)
            _write_json(manifest_path, json.loads(serialize_manifest(run.manifest)), args.overwrite); manifest = json.loads(serialize_manifest(run.manifest)); synthesis_status = f"executada ({run.processing_seconds:.3f} s)"
        except (TTSError, NarrationSynthesisError): raise
        finally: provider.close()
    sample_rate, _ = _compose_audio(manifest, voice_path); _write_srt(manifest, srt); _generate_music(int(manifest["duration_ms"]), music_path, args.overwrite); _mix_audio(voice_path, music_path, mixed_path, int(manifest["duration_ms"]), args.overwrite)
    scenes = _schedule(manifest); profile = {"format": "fabuloom.vertical-story/0.1", "id": PROJECT_ID, "title": "O Segredo Sob Arenhast", "story_text": STORY_TEXT, "manifest": f"{PROJECT_ID}/{manifest_path.name}", "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "aspect_ratio": "9:16"}, "audio": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "voice_wav": f"{PROJECT_ID}/{voice_path.name}", "mixed_wav": f"{PROJECT_ID}/{mixed_path.name}", "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable"}, "narrator": {"renderer": "NarratorAvatarRenderer", "composition": "Santa V5 Narrator Mode V1.4", "x": 52, "y": 1300, "size": 340}, "safe_area": {"left": 48, "top": 100, "right": 1032, "bottom": 1710, "platform_ui_bottom": 180}, "subtitles": {"x": 675, "y": 1510, "width": 690, "font_size": 31, "line_height": 43, "max_lines": 3}, "transitions": {"crossfade_ms": 650}, "scenes": scenes, "soundtrack": {"origin": "original deterministic local procedural composition", "path": f"{PROJECT_ID}/{music_path.name}", "gain": 0.18, "ducking": "sidechaincompress on music keyed by narration", "fade_in_ms": 1500, "fade_out_ms": 2500}, "export": {"video_codec": "h264", "audio_codec": "aac", "pixel_format": "yuv420p", "width": WIDTH, "height": HEIGHT, "fps": FPS, "audio_sample_rate": 24000, "public_technical_overlay": False}, "asset_generation": {"tool": "Codex built-in image generation", "assets_original": True, "prompts": IMAGE_PROMPTS}}
    profile["duration_ms"] = manifest["duration_ms"]; _write_json(profile_path, profile, args.overwrite); _write_json(timeline_path, {"format": "fabuloom.vertical-story-timeline/0.1", "profile": f"{PROJECT_ID}/{profile_path.name}", "duration_ms": manifest["duration_ms"], "scenes": scenes}, args.overwrite)
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"frames exists: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    frames.mkdir(parents=True); capture = _capture(profile_path, frames, export_root, args.port, args.capture_timeout); _render_mp4(frames, mixed_path, output, int(manifest["duration_ms"]), args.overwrite); _frame_board(profile, frames, board); probe = _probe_export(output); elapsed = time.perf_counter() - started; video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video"); audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report_data = {"format": "fabuloom.vertical-story-report/0.1", "profile": str(profile_path), "manifest": str(manifest_path), "voice": str(voice_path), "music": str(music_path), "mixed_audio": str(mixed_path), "video": str(output), "frame_board": str(board), "srt": str(srt), "duration_ms": manifest["duration_ms"], "synthesis": synthesis_status, "capture": capture, "probe": probe, "voice_audio_levels": _audio_levels(voice_path), "mixed_audio_levels": _audio_levels(mixed_path), "processing_seconds": round(elapsed, 3), "technical_overlay": False, "human_visual_review_required": True}
    report_json.write_text(json.dumps(report_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_lines = ["# Fabuloom Vertical Cinematic Story V1", "", "- Título: `O Segredo Sob Arenhast`.", f"- Perfil versionado: `{profile_path}`.", f"- Voz Kokoro: `{VOICE_ID}` / `{LANGUAGE}`; síntese: `{synthesis_status}`.", f"- Duração medida: `{manifest['duration_ms']} ms`; segmentos: `{len(manifest['segments'])}`.", f"- Trilha: composição instrumental original procedural local; arquivo `{music_path}`.", f"- Mixagem: voz em primeiro plano, música a -15 dB aproximadamente, fade-in/out e sidechain ducking da trilha pela voz.", f"- Vídeo: `{output}`; FFprobe `{probe['format']['duration']} s`, `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']} `{video_stream.get('pix_fmt')}`, áudio `{audio_stream['codec_name']}` {audio_stream['sample_rate']} Hz.", f"- Frames: `{frames}` ({capture['frame_count']} a {FPS} FPS); prancha `{board}`.", "- Narrador: Santa V5 Narrator Mode V1.4 no canto inferior esquerdo; boca RMS, piscadas e cabeça preservadas.", "- Legendas: intervalos medidos por segmento, tipografia vertical e área segura; sem timestamps inventados.", "- Metadados técnicos no vídeo: não; voz, modelo, caminhos e identificadores permanecem apenas neste relatório/perfil.", f"- Níveis: voz `{report_data['voice_audio_levels']}`; mix `{report_data['mixed_audio_levels']}`.", "- Aprovação artística humana continua obrigatória.", ""]
    report.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"profile={profile_path}"); print(f"manifest={manifest_path}"); print(f"voice={voice_path}"); print(f"music={music_path}"); print(f"mixed_audio={mixed_path}"); print(f"frames={frames}"); print(f"video={output}"); print(f"board={board}"); print(f"report={report}"); print(f"duration_ms={manifest['duration_ms']}"); print(f"processing_seconds={elapsed:.3f}"); print(f"probe={json.dumps(probe, ensure_ascii=False)}"); print("state=completed"); return 0


if __name__ == "__main__": raise SystemExit(main())
