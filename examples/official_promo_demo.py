"""Produce the Mission 020 official Fabuloom Studio promotional trailer."""

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
from narrator_mode_demo import _edge_path, _probe_export

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
PROJECT_ID = "official-promo-v1"
STORY_ID = "fabuloom-official-promo-v1"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920

STORY_TEXT = """Imagine transformar suas histórias em vídeos narrados, com cenários cinematográficos, personagens animados e trilha sonora.

Conheça o Fabuloom Studio, uma ferramenta gratuita e de código aberto para ajudar criadores a transformar ideias em produções audiovisuais.

Com a ajuda do Codex, você pode automatizar etapas da produção, organizar cenas, preparar narrações e exportar seus vídeos.

Esta é apenas nossa primeira versão. O Fabuloom continua evoluindo e recebe melhorias frequentes.

E queremos você nessa jornada! Envie sugestões, compartilhe ideias e ajude a construir o futuro do Fabuloom.

Fabuloom Studio. Dê vida às suas histórias. Um projeto open source criado por 0xTPZ."""

SCENE_META = (
    ("hook", "intro", "vertical-story-v1/scenes/scene-1-arenhast-city-1080x1920.png", "zoom", "Sua história pode ganhar vida.", "SUA HISTÓRIA PODE GANHAR VIDA."),
    ("presentation", "cinematic", "vertical-story-v1/scenes/scene-2-primordial-temple-1080x1920.png", "pan-up", "Fabuloom Studio", "FABULOOM STUDIO  ·  GRATUITO  ·  OPEN SOURCE"),
    ("tool", "screen", "official-promo-v1/evidence/fabuloom-studio-ui-real.png", "pan-side", "Roteiro → produção → vídeo", "ROTEIRO  →  PRODUÇÃO  →  VÍDEO"),
    ("first-version", "results", "vertical-story-v1/scenes/scene-3-crystal-awakening-1080x1920.png", "zoom", "Primeira versão em desenvolvimento ativo", "PRIMEIRA VERSÃO  ·  EM DESENVOLVIMENTO ATIVO"),
    ("community", "community", "vertical-story-v1/scenes/scene-4-temple-shadow-1080x1920.png", "pan-side", "Suas ideias são bem-vindas", "CONTRIBUA NO GITHUB"),
    ("end", "end", "vertical-story-v1/scenes/scene-5-next-guardian-1080x1920.png", "zoom", "Criado por 0xTPZ", "FABULOOM STUDIO"),
)


def write_json(path: Path, payload: object, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"file exists: {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def partition_segments(segment_count: int, group_count: int) -> list[tuple[int, ...]]:
    if segment_count < group_count:
        raise ValueError(f"promo requires at least {group_count} measured segments, got {segment_count}")
    edges = [round(index * segment_count / group_count) for index in range(group_count + 1)]
    for index in range(1, group_count):
        edges[index] = max(edges[index], edges[index - 1] + 1)
    for index in range(group_count - 1, 0, -1):
        edges[index] = min(edges[index], edges[index + 1] - 1)
    return [tuple(range(edges[index], edges[index + 1])) for index in range(group_count)]


def build_scenes(manifest: dict) -> list[dict]:
    groups = partition_segments(len(manifest["segments"]), len(SCENE_META))
    scenes = []
    for index, ((scene_id, kind, image, camera, label, on_screen), group) in enumerate(zip(SCENE_META, groups)):
        first = manifest["segments"][group[0]]
        last = manifest["segments"][group[-1]]
        end_ms = manifest["duration_ms"] if index == len(SCENE_META) - 1 else last["end_ms"] + int(last.get("metadata", {}).get("pause_after_ms", 0))
        scenes.append({
            "id": scene_id, "kind": kind, "label": label, "image": image, "camera": camera,
            "effect": "particles" if scene_id in {"hook", "end"} else "none", "on_screen": on_screen,
            "start_ms": first["start_ms"], "end_ms": end_ms,
            "text_segment_ids": [manifest["segments"][position]["id"] for position in group],
        })
    return scenes


def generate_music(duration_ms: int, scene_starts: list[int], output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"music exists: {output}; pass --overwrite")
    rate = 24000
    total = max(1, round(duration_ms * rate / 1000))
    roots = (55.0, 65.406, 73.416, 82.407, 73.416, 55.0)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(rate)
        frames = bytearray()
        duration = duration_ms / 1000
        for index in range(total):
            t = index / rate
            section = min(len(roots) - 1, int(t / max(0.001, duration) * len(roots)))
            root = roots[section]
            beat = t * 2.0
            beat_phase = beat % 1.0
            kick = math.exp(-beat_phase * 24) * math.sin(2 * math.pi * (58 - 28 * beat_phase) * t) * .34 if int(beat) % 2 == 0 else 0.0
            snare_phase = (beat - .5) % 1.0
            snare = math.exp(-snare_phase * 30) * math.sin(2 * math.pi * 180 * t) * .11 if int(beat + .5) % 2 == 1 else 0.0
            pad = math.sin(2 * math.pi * root * t) * .18 + math.sin(2 * math.pi * root * 1.5 * t) * .08 + math.sin(2 * math.pi * root * 2 * t) * .045
            arpeggio = math.sin(2 * math.pi * root * (2 + (int(t * 4) % 4) * .5) * t) * (.06 + .02 * math.sin(t * .7))
            shimmer = math.sin(2 * math.pi * root * 8.02 * t + math.sin(t * 1.2)) * .018
            impact = 0.0
            for start_ms in scene_starts[1:]:
                delta = t - start_ms / 1000
                if 0 <= delta < .8: impact += math.exp(-delta * 8) * math.sin(2 * math.pi * (92 - 50 * delta) * delta) * .24
            envelope = min(1.0, t / 1.0, max(0.0, (duration - t) / 2.0))
            value = max(-.92, min(.92, (kick + snare + pad + arpeggio + shimmer + impact) * envelope))
            left = int(value * 32767); right = int((value * .96 + math.sin(t * .23) * .003) * 32767)
            frames.extend(struct.pack("<hh", left, right))
        stream.writeframes(frames)


def generate_sfx(duration_ms: int, scene_starts: list[int], output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"sfx exists: {output}; pass --overwrite")
    rate = 24000; total = max(1, round(duration_ms * rate / 1000)); starts = [start / 1000 for start in scene_starts[1:]]
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(rate)
        frames = bytearray()
        for index in range(total):
            t = index / rate; value = 0.0
            for start in starts:
                delta = t - start
                if 0 <= delta < .55:
                    value += math.exp(-delta * 10) * (math.sin(2 * math.pi * (260 + 900 * delta) * delta) * .10 + math.sin(2 * math.pi * 70 * delta) * .16)
            frames.extend(struct.pack("<hh", int(value * 32767), int(value * .82 * 32767)))
        stream.writeframes(frames)


def mix_audio(voice: Path, music: Path, sfx: Path, output: Path, duration_ms: int, *, include_music: bool, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"mix exists: {output}; pass --overwrite")
    duration = duration_ms / 1000
    fade_start = max(0.0, duration - 2.5)
    if include_music:
        graph = f"[1:a]volume=0.24,afade=t=in:st=0:d=0.8,afade=t=out:st={fade_start:.3f}:d=2.5[music];[music][0:a]sidechaincompress=threshold=0.02:ratio=7:attack=20:release=260:makeup=1[ducked];[0:a]aresample=24000[voice];[2:a]volume=0.62[sfx];[voice][ducked][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
        inputs = ["-i", str(voice), "-i", str(music), "-i", str(sfx)]
    else:
        graph = "[0:a]aresample=24000[voice];[1:a]volume=0.62[sfx];[voice][sfx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
        inputs = ["-i", str(voice), "-i", str(sfx)]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", *inputs, "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "24000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True, cwd=output.parent)


def wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-official-promo.html", timeout=1): return
        except Exception: time.sleep(.2)
    raise TimeoutError("official promo capture server did not start")


def capture(profile: Path, frames: Path, export_root: Path, port: int, timeout: float) -> dict:
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(frames.parent)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None; browser_profile = None
    try:
        wait_for_server(port); browser_profile = Path(tempfile.mkdtemp(prefix=".promo-edge-", dir=frames.parent))
        profile_url = "/exports/" + profile.relative_to(export_root).as_posix()
        url = f"http://127.0.0.1:{port}/capture-official-promo.html?session={quote(frames.name)}&profile={quote(profile_url, safe='')}&fps={FPS}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={browser_profile}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = frames / "complete.json"; deadline = time.monotonic() + timeout
        while not complete.is_file():
            if time.monotonic() >= deadline: raise TimeoutError(f"promo capture timed out after {timeout:.0f}s")
            if edge.poll() is not None:
                error = frames / "error.json"; raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before completion")
            time.sleep(.25)
        result = json.loads(complete.read_text(encoding="utf-8")); images = sorted(path for path in frames.glob("*.png") if path.stem.isdigit())
        if len(images) != result["frame_count"] or any(path.stat().st_size < 1000 for path in images): raise ValueError("promo frames are incomplete")
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


def render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, overwrite: bool) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "2", "-movflags", "+faststart", str(output)], check=True, cwd=output.parent)


def frame_board(profile: dict, frames: Path, output: Path) -> None:
    count = len(list(frames.glob("*.png"))); inputs = []; filters = []
    labels = [scene["label"].replace(":", "\\:") for scene in profile["scenes"]]
    for index, scene in enumerate(profile["scenes"]):
        sample = max(0, min(count - 1, round(((scene["start_ms"] + scene["end_ms"]) / 2) / 1000 * FPS)))
        inputs += ["-i", str(frames / f"{sample:06d}.png")]
        slot = chr(97 + index); filters.append(f"[{index}:v]scale=360:640:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{labels[index]}':fontcolor=white:fontsize=19:x=12:y=14:box=1:boxcolor=0x07142A@.88[{slot}]")
    filters.append("[a][b][c][d][e][f]xstack=inputs=6:layout=0_0|360_0|720_0|0_640|360_640|720_640[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def audio_levels(path: Path) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    return "; ".join(line.strip() for line in result.stderr.splitlines() if "mean_volume" in line or "max_volume" in line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--reuse-manifest", action="store_true"); parser.add_argument("--port", type=int, default=8792); parser.add_argument("--capture-timeout", type=float, default=900)
    args = parser.parse_args()
    export_root = args.export_dir.resolve(); project_root = export_root / PROJECT_ID; videos = export_root / "videos"; evidence = project_root / "evidence"; project_root.mkdir(parents=True, exist_ok=True); videos.mkdir(parents=True, exist_ok=True); evidence.mkdir(parents=True, exist_ok=True)
    ui_source = evidence / "fabuloom-studio-ui-real.png"; results_source = evidence / "vertical-story-results-board.png"; mission_board = videos / "fabuloom-vertical-story-test-v1-frames.png"
    if not ui_source.is_file(): raise FileNotFoundError(f"real local UI screenshot is required: {ui_source}")
    if not results_source.is_file():
        if not mission_board.is_file(): raise FileNotFoundError(f"Mission 019 result board is required: {mission_board}")
        shutil.copy2(mission_board, results_source)
    manifest_path = project_root / f"{STORY_ID}.json"; voice_path = project_root / f"{STORY_ID}-voice.wav"; music_path = project_root / f"{STORY_ID}-original-music.wav"; sfx_path = project_root / f"{STORY_ID}-original-sfx.wav"; main_mix = project_root / f"{STORY_ID}-main-mix.wav"; tiktok_mix = project_root / f"{STORY_ID}-tiktok-ready-mix.wav"; profile_path = project_root / f"{STORY_ID}-profile.json"; timeline_path = project_root / f"{STORY_ID}-timeline.json"; frames = project_root / ".frames"; main_video = videos / "fabuloom-official-promo-v1.mp4"; tiktok_video = videos / "fabuloom-official-promo-v1-tiktok-ready.mp4"; board = videos / "fabuloom-official-promo-v1-frames.png"; srt = videos / "fabuloom-official-promo-v1.srt"; report_json = videos / "fabuloom-official-promo-v1-report.json"; report_md = videos / "fabuloom-official-promo-v1-report.md"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file(): manifest = json.loads(manifest_path.read_text(encoding="utf-8")); synthesis_status = "reutilizada"
    else:
        provider = KokoroTTSProvider(output_dir=project_root, allow_overwrite=args.overwrite)
        try:
            run = synthesize_narration(provider, STORY_TEXT, narration_id=STORY_ID, manifest_id=STORY_ID, voice_id=VOICE_ID, language=LANGUAGE, output_dir=project_root, max_chars=360)
            manifest = json.loads(serialize_manifest(run.manifest)); write_json(manifest_path, manifest, args.overwrite); synthesis_status = f"executada ({run.processing_seconds:.3f} s)"
        except (TTSError, NarrationSynthesisError): raise
        finally: provider.close()
    sample_rate, _ = _compose_audio(manifest, voice_path); _write_srt(manifest, srt); scenes = build_scenes(manifest); scene_starts = [scene["start_ms"] for scene in scenes]; generate_music(int(manifest["duration_ms"]), scene_starts, music_path, args.overwrite); generate_sfx(int(manifest["duration_ms"]), scene_starts, sfx_path, args.overwrite); mix_audio(voice_path, music_path, sfx_path, main_mix, int(manifest["duration_ms"]), include_music=True, overwrite=args.overwrite); mix_audio(voice_path, music_path, sfx_path, tiktok_mix, int(manifest["duration_ms"]), include_music=False, overwrite=args.overwrite)
    profile = {"format": "fabuloom.official-promo/0.1", "id": PROJECT_ID, "title": "FABULOOM STUDIO — SUA HISTÓRIA GANHA VIDA", "story_text": STORY_TEXT, "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "aspect_ratio": "9:16"}, "audio": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "manifest": f"{PROJECT_ID}/{manifest_path.name}", "voice_wav": f"{PROJECT_ID}/{voice_path.name}", "music_wav": f"{PROJECT_ID}/{music_path.name}", "sfx_wav": f"{PROJECT_ID}/{sfx_path.name}", "main_mix_wav": f"{PROJECT_ID}/{main_mix.name}", "tiktok_ready_wav": f"{PROJECT_ID}/{tiktok_mix.name}", "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable"}, "narrator": {"renderer": "NarratorAvatarRenderer", "composition": "Santa V5 Narrator Mode V1.4", "x": 48, "y": 1440, "size": 320, "visible_in": ["presentation", "tool", "first-version"]}, "safe_area": {"left": 48, "top": 110, "right": 1032, "bottom": 1710, "platform_ui_bottom": 180}, "subtitles": {"x": 540, "y": 1510, "width": 930, "font_size": 30, "line_height": 38, "max_lines": 4, "overflow_policy": "shrink_before_rendering_all_lines"}, "transitions": {"crossfade_ms": 450}, "scenes": scenes, "evidence": {"ui_screenshot": f"{PROJECT_ID}/{ui_source.relative_to(project_root).as_posix()}", "results_board": results_source.relative_to(export_root).as_posix()}, "claims": {"free_and_open_source": True, "first_public_phase": True, "active_development": True, "community_contributions_welcome": True, "codex_assisted_local_automation": True, "codex_or_external_services_free": False}, "credits": {"author": "0xTPZ", "repository": "https://github.com/0xTPZ/fabuloom", "license": "MIT for original Fabuloom code", "official_logo": "frontend/assets/logo.svg", "scene_assets": "original Mission 019 workspace assets", "music": "original deterministic local procedural composition", "sfx": "original deterministic local procedural effects", "screen_evidence": "real local browser capture of the current Fabuloom Character Stage", "third_party_media": False}, "export": {"video_codec": "h264", "audio_codec": "aac", "pixel_format": "yuv420p", "width": WIDTH, "height": HEIGHT, "fps": FPS, "audio_sample_rate": 24000, "public_technical_overlay": False}, "platforms": ["TikTok", "YouTube Shorts", "Instagram Reels"], "output_variants": {"main": "voice + original music + original SFX", "tiktok_ready": "voice + original SFX; music slot intentionally left open for platform-licensed music"}}
    profile["duration_ms"] = manifest["duration_ms"]; profile["evidence"]["demo_note"] = "Real local Fabuloom browser evidence is included; no Codex desktop screen recording was available, so no simulated terminal or fabricated operation is shown."; write_json(profile_path, profile, args.overwrite); write_json(timeline_path, {"format": "fabuloom.official-promo-timeline/0.1", "profile": f"{PROJECT_ID}/{profile_path.name}", "duration_ms": manifest["duration_ms"], "scenes": scenes}, args.overwrite)
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"frames exists: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    frames.mkdir(parents=True); capture_result = capture(profile_path, frames, export_root, args.port, args.capture_timeout); render_mp4(frames, main_mix, main_video, int(manifest["duration_ms"]), args.overwrite); render_mp4(frames, tiktok_mix, tiktok_video, int(manifest["duration_ms"]), args.overwrite); frame_board(profile, frames, board)
    main_probe = _probe_export(main_video); tiktok_probe = _probe_export(tiktok_video); elapsed = time.perf_counter() - started
    write_json(project_root / f"{STORY_ID}-credits.json", profile["credits"], args.overwrite); (project_root / f"{STORY_ID}-description-pt-BR.md").write_text("Fabuloom Studio é uma ferramenta gratuita e open source para transformar histórias em produções narradas. Esta é a primeira fase pública do projeto, ainda em desenvolvimento ativo. Sugestões, ideias, bugs e contribuições são bem-vindos: https://github.com/0xTPZ/fabuloom\n", encoding="utf-8"); (project_root / f"{STORY_ID}-description-en.md").write_text("Fabuloom Studio is a free and open-source tool for turning stories into narrated productions. This is the project's first public phase and it is still actively evolving. Suggestions, ideas, bug reports and contributions are welcome: https://github.com/0xTPZ/fabuloom\n", encoding="utf-8")
    report = {"format": "fabuloom.official-promo-report/0.1", "profile": str(profile_path), "manifest": str(manifest_path), "voice": str(voice_path), "music": str(music_path), "sfx": str(sfx_path), "main_mix": str(main_mix), "tiktok_ready_mix": str(tiktok_mix), "main_video": str(main_video), "tiktok_ready_video": str(tiktok_video), "frame_board": str(board), "srt": str(srt), "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "synthesis": synthesis_status, "capture": capture_result, "main_probe": main_probe, "tiktok_probe": tiktok_probe, "voice_levels": audio_levels(voice_path), "main_mix_levels": audio_levels(main_mix), "tiktok_mix_levels": audio_levels(tiktok_mix), "processing_seconds": round(elapsed, 3), "real_screen_evidence": str(ui_source), "codex_screen_recording": False, "technical_overlay": False, "human_review_required": True, "limitations": ["No desktop Codex recording was available; the trailer uses an actual local Fabuloom browser capture and real generated outputs.", "RMS mouth response is amplitude-based, not phonetic alignment.", "TikTok-ready version intentionally omits music so a platform-licensed track can be added later."]}
    write_json(report_json, report, args.overwrite)
    main_video_stream = next(stream for stream in main_probe["streams"] if stream["codec_type"] == "video"); main_audio_stream = next(stream for stream in main_probe["streams"] if stream["codec_type"] == "audio")
    report_md.write_text("\n".join(["# Fabuloom Studio Official Promo V1", "", f"- Título: `FABULOOM STUDIO — SUA HISTÓRIA GANHA VIDA`.", f"- Duração medida: `{manifest['duration_ms']} ms`; segmentos: `{len(manifest['segments'])}`; voz: `Kokoro {VOICE_ID} / {LANGUAGE}`.", f"- Vídeo principal: `{main_video}`; `{main_probe['format']['duration']} s`, `{main_video_stream['codec_name']}`, `{main_video_stream['width']}×{main_video_stream['height']}`, `{main_audio_stream['codec_name']}`.", f"- Versão TikTok-ready: `{tiktok_video}`; narração e SFX sem música incorporada.", f"- Trilha: `{music_path}`; composição procedural original local, sem samples comerciais.", f"- SFX: `{sfx_path}`; transientes originais sincronizados às transições.", f"- Evidência real: `{ui_source}`; screenshot do Fabuloom Character Stage servido localmente. Não foi apresentada uma gravação fictícia do Codex.", f"- Prancha: `{board}`; frames: `{frames}` ({capture_result['frame_count']} a {FPS} FPS).", "- Legendas: todas as palavras de cada segmento são preservadas; o tamanho reduz antes de qualquer quebra adicional.", "- RMS: resposta de amplitude para boca; não é alinhamento fonético.", "- Claims: gratuito, open source, primeira fase pública, desenvolvimento ativo, contribuição comunitária e autoria 0xTPZ.", "- Metadados técnicos não aparecem no vídeo; ficam no perfil e relatório.", "- Aprovação artística humana permanece obrigatória.", ""]), encoding="utf-8")
    print(f"profile={profile_path}"); print(f"manifest={manifest_path}"); print(f"voice={voice_path}"); print(f"music={music_path}"); print(f"sfx={sfx_path}"); print(f"main_mix={main_mix}"); print(f"tiktok_ready_mix={tiktok_mix}"); print(f"main_video={main_video}"); print(f"tiktok_ready_video={tiktok_video}"); print(f"board={board}"); print(f"report={report_md}"); print(f"duration_ms={manifest['duration_ms']}"); print(f"processing_seconds={elapsed:.3f}"); print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
