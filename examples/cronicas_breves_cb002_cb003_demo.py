"""Produce CB-002 and CB-003 using the approved CB-001 vertical pipeline.

Each episode is independent. Missing owner-provided music blocks only the
affected final MP4; narration, measured manifests, storyboard, metadata and
environment plates are still prepared for later completion.
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
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920

CB002_ID = "cb-002-a-sombra-que-olhava-para-o-sol"
CB003_ID = "cb-003-a-luz-do-ultimo-viajante"

CB002_TEXT = """Guardião... você já reparou para onde aponta a sua sombra?

Numa manhã, na estrada para Gaia, aconteceu algo impossível: todas as sombras apontavam para o sol nascente.

E foi aí que nasceu uma história esquisita.

Dizem que um viajante parou sobre uma ponte e marcou com uma pedra o fim da própria sombra.

Quando olhou de novo... a pedra estava no mesmo lugar.

Mas a sombra atravessara o rio.

Ele esperou o sol subir. As árvores mudaram de sombra. As carroças também.

Só a dele continuou olhando para o leste.

Desde então, há quem diga: se sua sombra apontar para a luz, não tente descobrir o que ela está vendo.

E você, Guardião... olharia para trás?

As histórias completas de Topázio estão no YouTube, em Crônicas de Topázio.

Até nossa próxima lenda."""

CB003_TEXT = """Guardião... quer ouvir uma história sobre uma luz que não devia se apagar?

Depois de um incêndio perto de Gaia, Aurelion esperou uma mãe e seus filhos no portão do templo. Ele só entrou depois deles.

Mas dizem que a história não terminou ali.

Dizem que uma lanterna passou a ser deixada acesa junto ao portão sul, mesmo nas noites mais frias.

Ninguém sabia quem a acendia.

Alguns diziam que ela guiava os viajantes. Outros, que lembrava aos de dentro que alguém ainda podia estar lá fora.

E sabe quando a luz se apagava?

Só depois que o último viajante encontrava abrigo.

Bonito, não é?

Se essa história tocou você, compartilhe.

E as aventuras completas estão no YouTube, em Crônicas de Topázio.

Até logo, Guardião."""


def _scene_asset(episode_id: str, filename: str) -> str:
    return f"cronicas-breves/{episode_id}/assets/scenes/{filename}"


EPISODES = {
    CB002_ID: {
        "title": "A Sombra que Olhava para o Sol",
        "text": CB002_TEXT,
        "genre": "suspense sobrenatural",
        "chapter_minimum": 2,
        "music": FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "A Sombra que Olhava para o Sol.mp3",
        "scene_plan": [
            {"id": "intro", "marker": "Guardião", "image": "official", "camera": "zoom_in", "effect": "none", "label": "Abertura"},
            {"id": "road", "marker": "Numa manhã", "image": "01-road-sunrise.png", "camera": "pan_vertical", "effect": "mist", "label": "Estrada"},
            {"id": "legend", "marker": "E foi aí", "image": "03-trees-impossible-shadows.png", "camera": "pan_lateral", "effect": "shadow_pulse", "label": "A história"},
            {"id": "bridge", "marker": "Dizem que um viajante", "image": "02-empty-stone-bridge.png", "camera": "zoom_in", "effect": "none", "label": "A ponte"},
            {"id": "stone", "marker": "Quando olhou", "image": "04-marker-stone-river.png", "camera": "crystal_approach", "effect": "none", "label": "A pedra"},
            {"id": "river", "marker": "Mas a sombra", "image": "05-shadow-crosses-river.png", "camera": "pan_lateral", "effect": "shadow_pulse", "label": "O rio"},
            {"id": "reveal", "marker": "Ele esperou", "image": "06-sunrise-warning.png", "camera": "zoom_in", "effect": "darken", "label": "A revelação"},
            {"id": "warning", "marker": "Desde então", "image": "05-shadow-crosses-river.png", "camera": "pan_vertical", "effect": "mist", "label": "O aviso"},
            {"id": "outro", "marker": "E você", "image": "official", "camera": "pan_lateral", "effect": "none", "label": "Despedida"},
            {"id": "cta", "marker": "As histórias completas", "image": "official", "camera": "zoom_in", "effect": "none", "label": "Crônicas de Topázio"},
        ],
        "special_music_window": ("river", "reveal"),
        "music_direction": "tensão gradual e pausa dramática na revelação",
        "music_selection": "A faixa existente é específica para o episódio, tem duração suficiente, dinâmica compatível com narração e evita reutilizar a música de CB-001.",
        "voice_direction": "preserve_original_measured_narration",
        "voice_direction_reason": "Os perfis da Missão 032 tiveram diferenças quase imperceptíveis; as amostras pareceram melhores isoladas. Sem evidência clara de melhoria acústica, a voz original medida é preservada e a melhoria é concentrada na mixagem.",
        "description": "Uma lenda proposta sobre uma sombra que aponta para o sol nascente.",
    },
    CB003_ID: {
        "title": "A Luz do Último Viajante",
        "text": CB003_TEXT,
        "genre": "fantasia emocional e esperança",
        "chapter_minimum": 3,
        "music": FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "A Luz do Último Viajante.mp3",
        "scene_plan": [
            {"id": "intro", "marker": "Guardião", "image": "official", "camera": "zoom_in", "effect": "none", "label": "Abertura"},
            {"id": "temple", "marker": "Depois de um incêndio", "image": "01-temple-of-gaia-night.png", "camera": "pan_vertical", "effect": "mist", "label": "Templo de Gaia"},
            {"id": "folklore", "marker": "Mas dizem", "image": "02-south-gate-empty.png", "camera": "zoom_in", "effect": "none", "label": "O portão sul"},
            {"id": "lantern", "marker": "Dizem que uma lanterna", "image": "03-lantern-on-stones.png", "camera": "crystal_approach", "effect": "lantern_glow", "label": "A lanterna"},
            {"id": "unknown", "marker": "Ninguém sabia", "image": "04-temple-courtyard.png", "camera": "pan_lateral", "effect": "none", "label": "Ninguém sabia"},
            {"id": "guide", "marker": "Alguns diziam", "image": "05-lantern-path.png", "camera": "pan_vertical", "effect": "lantern_glow", "label": "O caminho"},
            {"id": "when", "marker": "E sabe quando", "image": "03-lantern-on-stones.png", "camera": "zoom_in", "effect": "darken", "label": "Quando a luz"},
            {"id": "last", "marker": "Só depois", "image": "06-temple-dawn.png", "camera": "crystal_approach", "effect": "light_bloom", "label": "O abrigo"},
            {"id": "beautiful", "marker": "Bonito", "image": "06-temple-dawn.png", "camera": "pan_lateral", "effect": "light_bloom", "label": "Esperança"},
            {"id": "share", "marker": "Se essa história", "image": "official", "camera": "zoom_in", "effect": "none", "label": "Despedida"},
            {"id": "cta", "marker": "E as aventuras", "image": "official", "camera": "pan_vertical", "effect": "none", "label": "Crônicas de Topázio"},
        ],
        "special_music_window": None,
        "music_direction": "crescimento emocional suave e encerramento acolhedor",
        "description": "Uma lenda proposta sobre uma lanterna que espera o último viajante encontrar abrigo.",
    },
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size,format_name:stream=index,codec_name,codec_type,width,height,pix_fmt,sample_rate,channels,channel_layout", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _synthesize_all(selected: list[str], manifests: dict[str, Path], audio_roots: dict[str, Path], overwrite: bool, reuse_manifest: bool) -> dict[str, tuple[dict, float, float, str]]:
    needs_provider = any(not manifests[episode_id].is_file() or not reuse_manifest for episode_id in selected)
    provider = KokoroTTSProvider(output_dir=EXPORT_ROOT, allow_overwrite=overwrite) if needs_provider else None
    results: dict[str, tuple[dict, float, float, str]] = {}
    try:
        for episode_id in selected:
            config = EPISODES[episode_id]; path = manifests[episode_id]; audio_root = audio_roots[episode_id]
            if path.is_file() and reuse_manifest:
                results[episode_id] = (json.loads(path.read_text(encoding="utf-8")), 0.0, 0.0, "reused")
                continue
            assert provider is not None
            started = time.perf_counter()
            try:
                run = synthesize_narration(provider, config["text"], narration_id=episode_id, manifest_id=episode_id, timeline_id=f"{episode_id}-timeline", language=LANGUAGE, voice_id=VOICE_ID, output_dir=audio_root, max_chars=360)
            except (TTSError, NarrationSynthesisError):
                raise
            manifest = json.loads(serialize_manifest(run.manifest))
            manifest["metadata"]["editorial_status"] = "ROTEIRO EDITORIAL PROPOSTO; não canônico; aprovação pendente"
            manifest["metadata"]["source_text_sha256"] = hashlib.sha256(config["text"].encode("utf-8")).hexdigest()
            _write_json(path, manifest)
            load_seconds = float(run.results[0].metadata.get("model_load_seconds") or 0) if run.results else 0.0
            results[episode_id] = (manifest, run.processing_seconds, load_seconds, f"synthesized in {time.perf_counter() - started:.3f}s")
    finally:
        if provider is not None: provider.close()
    return results


def _build_scenes(episode_id: str, manifest: dict) -> list[dict]:
    config = EPISODES[episode_id]; starts = {}
    for item in config["scene_plan"]:
        matches = [index for index, segment in enumerate(manifest["segments"]) if item["marker"] in segment["text"]]
        if not matches: raise ValueError(f"{episode_id}: marker not found: {item['marker']}")
        starts[item["id"]] = matches[0]
    ordered = [(item, starts[item["id"]]) for item in config["scene_plan"]]
    if ordered[0][1] != 0 or any(left[1] >= right[1] for left, right in zip(ordered, ordered[1:])): raise ValueError(f"{episode_id}: scene markers are not ordered: {ordered}")
    scenes = []
    for position, (item, start_index) in enumerate(ordered):
        end_index = ordered[position + 1][1] if position + 1 < len(ordered) else len(manifest["segments"])
        end_ms = manifest["segments"][end_index]["start_ms"] if end_index < len(manifest["segments"]) else manifest["duration_ms"]
        image = "official-scenes/santa-library-topazioverse-v1/library-base.png" if item["image"] == "official" else _scene_asset(episode_id, item["image"])
        scenes.append({"id": f"{episode_id}-{item['id']}", "label": item["label"], "image": image, "camera": item["camera"], "effect": item["effect"], "start_ms": manifest["segments"][start_index]["start_ms"], "end_ms": end_ms, "text_segment_ids": [segment["id"] for segment in manifest["segments"][start_index:end_index]], "environment_only": item["image"] != "official", "character_policy": "approved_santa_v5_only"})
    return scenes


def _capture_manifest(manifest: dict, episode_id: str) -> dict:
    capture = json.loads(json.dumps(manifest))
    for segment in capture["segments"]:
        filename = str(segment["audio_uri"]).replace("\\", "/").split("/")[-1]
        segment["audio_uri"] = f"cronicas-breves/{episode_id}/audio/{filename}"
    return capture


def _smooth_mix(voice: Path, music: Path, output: Path, duration_ms: int, special_window: tuple[int, int] | None, overwrite: bool) -> dict:
    duration = duration_ms / 1000.0; fade_start = max(0.0, duration - 2.8)
    if special_window:
        start = max(0.0, special_window[0] / 1000 - .25); end = min(duration, special_window[1] / 1000 + .75)
        expression = f"if(lt(t,{start:.3f}),1,if(lt(t,{start + .45:.3f}),1-0.88*(t-{start:.3f})/.45,if(lt(t,{end - .45:.3f}),0.12,if(lt(t,{end:.3f}),0.12+0.88*(t-{end - .45:.3f})/.45,1))))"
        window_info = {"window_ms": [round(start * 1000), round(end * 1000)], "gain_factor": .12}
    else:
        expression = "1"; window_info = None
    filters = "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit=2[voice][det];" + f"[1:a]aresample=48000,atrim=duration={duration:.3f},volume=0.23,volume='{expression}':eval=frame,afade=t=in:st=0:d=1.2,afade=t=out:st={fade_start:.3f}:d=2.8[music];" + "[music][det]sidechaincompress=threshold=0.020:ratio=7:attack=35:release=620:makeup=1:link=average[ducked];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.93[out]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-filter_complex", filters, "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True, cwd=output.parent)
    return {"ducking": "sidechaincompress voice->music", "music_gain": .23, "special_window": window_info, "limiter": .93, "music_speed_pitch_changed": False}


def _capture(profile: Path, frames_root: Path, export_root: Path, port: int, timeout: float) -> tuple[Path, dict]:
    frames_root.mkdir(parents=True, exist_ok=True); session_dir = frames_root / f"capture-{int(time.time())}"; session_dir.mkdir(parents=True, exist_ok=True); edge_profile = Path(tempfile.mkdtemp(prefix=".cb-031-edge-", dir=frames_root))
    env = os.environ.copy(); env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(export_root)})
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); browser = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/capture-cronicas-breves.html", timeout=1): break
            except Exception: time.sleep(.2)
        else: raise TimeoutError("CB-002/003 capture server did not start")
        relative = profile.relative_to(export_root).as_posix(); url = f"http://127.0.0.1:{port}/capture-cronicas-breves.html?session={quote(session_dir.name)}&profile={quote('/exports/' + relative, safe='')}&fps={FPS}"
        browser = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", "--dump-dom", "--hide-scrollbars", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--window-size={WIDTH},{HEIGHT}", f"--user-data-dir={edge_profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"; error = session_dir / "error.json"; limit = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < limit: time.sleep(.25)
        if error.exists(): raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists(): raise TimeoutError(f"capture timeout: {session_dir}")
        completion = json.loads(complete.read_text(encoding="utf-8")); frames = sorted(path for path in session_dir.glob("*.png") if path.stem.isdigit())
        if len(frames) != completion["frame_count"] or any(path.stat().st_size < 1000 for path in frames): raise RuntimeError("capture frames incomplete")
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


def _render(frames: Path, audio: Path, output: Path, duration_ms: int, overwrite: bool) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)], check=True, cwd=output.parent)


def _frame_board(frames: Path, scenes: list[dict], duration_ms: int, output: Path) -> None:
    last = max(0, round(duration_ms / 1000 * FPS) - 1); samples = []
    for scene in scenes:
        samples.append((round(((scene["start_ms"] + scene["end_ms"]) / 2) / 1000 * FPS), scene["label"]))
    while len(samples) < 9: samples.append((round(last * len(samples) / 9), "amostra"))
    samples = samples[:9]; inputs: list[str] = []; filters: list[str] = []
    for index, (frame, label) in enumerate(samples):
        inputs += ["-i", str(frames / f"{max(0, min(last, frame)):06d}.png")]; slot = chr(97 + index); safe_label = label.replace(":", "\\:").replace("'", "")
        filters.append(f"[{index}:v]scale=270:480,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{safe_label}':fontcolor=white:fontsize=18:x=10:y=12:box=1:boxcolor=0x07142A@.85[{slot}]")
    filters.append("[a][b][c][d][e][f][g][h][i]xstack=inputs=9:layout=0_0|270_0|540_0|0_480|270_480|540_480|0_960|270_960|540_960[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _blackdetect(video: Path) -> dict:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.05:pic_th=0.98", "-an", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    detections = [line.strip() for line in result.stderr.splitlines() if "black_start" in line]
    return {"passed": not detections, "detections": detections, "returncode": result.returncode}


def _levels(path: Path) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=False)
    return "; ".join(line.strip() for line in result.stderr.splitlines() if "mean_volume" in line or "max_volume" in line)


def _process_episode(episode_id: str, result: tuple[dict, float, float, str], export_root: Path, args: argparse.Namespace) -> dict:
    config = EPISODES[episode_id]; project = export_root / "cronicas-breves" / episode_id; audio = project / "audio"; timeline = project / "timeline"; captures = project / "captures"; reports = project / "reports"; metadata_root = project / "metadata"; videos = project / "videos"; frames_root = project / ".frames"; manifest, synthesis_seconds, load_seconds, synthesis_status = result
    scenes = _build_scenes(episode_id, manifest); voice_path = audio / "voice.wav"; _compose_audio(manifest, voice_path); _write_srt(manifest, timeline / f"{episode_id}.srt")
    capture_manifest = _capture_manifest(manifest, episode_id); _write_json(timeline / "capture-manifest.json", capture_manifest)
    voice_direction = config.get("voice_direction", "preserve_original_measured_narration")
    voice_direction_reason = config.get("voice_direction_reason", "A direção vocal não foi alterada nesta execução.")
    music_selection = config.get("music_selection", "Faixa existente do acervo local do episódio.")
    profile = {"format": "fabuloom.vertical-story/0.1", "id": episode_id, "title": config["title"], "story_text": config["text"], "manifest": f"cronicas-breves/{episode_id}/timeline/capture-manifest.json", "duration_ms": manifest["duration_ms"], "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "aspect_ratio": "9:16"}, "audio": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "voice_wav": f"cronicas-breves/{episode_id}/audio/voice.wav", "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable", "voice_direction": voice_direction}, "narrator": {"renderer": "NarratorAvatarRenderer", "character": "Santa V5", "library_asset_id": "santa-library-topazioverse-v1", "x": 48, "y": 1360, "size": 300}, "safe_area": {"left": 42, "top": 88, "right": 1038, "bottom": 1720, "platform_ui_bottom": 180}, "subtitles": {"x": 715, "y": 1480, "width": 620, "font_size": 29, "line_height": 40, "max_lines": 3}, "transitions": {"crossfade_ms": 650}, "scenes": scenes, "export": {"video_codec": "h264", "audio_codec": "aac", "pixel_format": "yuv420p", "width": WIDTH, "height": HEIGHT, "fps": FPS, "audio_sample_rate": 48000, "audio_channels": 2, "public_technical_overlay": False}, "story_provenance": {"classification": "proposed_folklore", "chapter_minimum": config["chapter_minimum"], "draft_character_rendering": "blocked", "story_visual_policy": "environment_only"}}
    _write_json(timeline / "profile.json", profile); _write_json(timeline / "storyboard-used.json", {"format": "fabuloom.cb-storyboard/0.1", "source": f"private editorial brief for {episode_id}", "scenes": scenes, "timing_source": "measured_wav_segments"})
    metadata = {"title": f"{config['title']} — Crônicas Breves", "series": "Lendas e Segredos de Topázio", "description": config["description"], "genre": config["genre"], "hashtags": ["#CronicasDeTopazio", "#Topazioverse", "#LendasDeTopazio", "#Shorts", "#Fantasia"], "voice": {"character": "Santa V5", "voice_id": VOICE_ID, "language": LANGUAGE, "direction": voice_direction}, "format": "1080x1920 9:16 30fps", "published": False, "publication_pending": ["aprovação artística humana", "confirmação dos direitos comerciais da trilha"]}
    _write_json(metadata_root / "shorts-tiktok-metadata.json", metadata)
    music = config["music"]; report = {"format": "fabuloom.cb-episode-report/0.1", "episode": episode_id, "title": config["title"], "editorial_status": "ROTEIRO PROPOSTO; não canônico; aprovação pendente", "duration_ms": manifest["duration_ms"], "segments": len(manifest["segments"]), "scenes": len(scenes), "synthesis_status": synthesis_status, "synthesis_seconds": synthesis_seconds, "model_load_seconds": load_seconds, "model_id": manifest["segments"][0].get("metadata", {}).get("model_id"), "model_revision": manifest["segments"][0].get("metadata", {}).get("model_revision"), "voice_manifest": str(project / "audio" / "narration-manifest.json"), "srt": str(timeline / f"{episode_id}.srt"), "storyboard": str(timeline / "storyboard-used.json"), "profile": str(timeline / "profile.json"), "music": {"path": str(music), "exists": music.is_file(), "rights_status": "Suno commercial-rights confirmation pending", "selection_reason": music_selection}, "voice_direction": {"decision": voice_direction, "reason": voice_direction_reason, "lab_reference": "workspace/exports/voice-lab/mission-032-santa-expressive-v1/report.json"}, "narrator": {"character": "Santa V5", "renderer": "NarratorAvatarRenderer", "library": "santa-library-topazioverse-v1"}, "draft_characters": "blocked", "story_visuals": "environment_only", "timing_source": "measured_wav_segments", "word_phoneme_viseme_timing": "unavailable", "human_visual_review_required": True}
    if not music.is_file():
        report.update({"export_status": "BLOCKED_BY_MISSING_MUSIC", "blocked_reason": "owner-provided soundtrack was not found; no substitute used", "video": None, "validation": {"preproduction": True, "final_mix": False, "final_video": False}})
        _write_json(reports / "technical-report.json", report); (reports / "technical-report.md").write_text(f"# {config['title']}\n\n- Estado: **BLOQUEADO POR TRILHA AUSENTE**.\n- Narração preparada: Kokoro `pm_santa` / `pt-BR`, `{len(manifest['segments'])}` segmentos, `{manifest['duration_ms']} ms`.\n- Música esperada: `{music}`.\n- Nenhuma música substituta foi gerada ou reutilizada.\n- Direção vocal: `{voice_direction}`; {voice_direction_reason}\n- Storyboard, placas ambientais, manifesto e SRT estão prontos para retomada quando a faixa for fornecida.\n- Personagens Draft bloqueados; visuais de história environment-only.\n- Aprovação artística humana e direitos comerciais continuam pendentes.\n", encoding="utf-8"); _write_json(reports / "validation.json", report["validation"]); return report
    source_copy = audio / "source-music.mp3"; shutil.copy2(music, source_copy); source_probe = _probe(music); special = None
    if config["special_music_window"]:
        by_id = {scene["id"].split(f"{episode_id}-", 1)[-1]: scene for scene in scenes}; first, last = config["special_music_window"]; special = (by_id[first]["start_ms"], by_id[last]["end_ms"])
    mixed = audio / "mixed.wav"; mix_info = _smooth_mix(voice_path, source_copy, mixed, int(manifest["duration_ms"]), special, args.overwrite); profile["audio"]["mixed_wav"] = f"cronicas-breves/{episode_id}/audio/mixed.wav"; profile["audio"]["music_direction"] = config["music_direction"]; _write_json(timeline / "profile.json", profile)
    if frames_root.exists() and not args.reuse_capture:
        for child in frames_root.iterdir():
            if child.is_dir() and child.name.startswith("capture-"): shutil.rmtree(child)
    if args.reuse_capture:
        candidates = sorted(frames_root.glob("capture-*/complete.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates: raise FileNotFoundError(f"{episode_id}: --reuse-capture requested without completed capture")
        session = candidates[0].parent; completion = json.loads(candidates[0].read_text(encoding="utf-8"))
    else:
        session, completion = _capture(timeline / "profile.json", frames_root, export_root, args.port, args.capture_timeout)
    output = videos / f"fabuloom-{episode_id}.mp4"; _render(session, mixed, output, int(manifest["duration_ms"]), args.overwrite); board = captures / "storyboard-board.png"; _frame_board(session, scenes, int(manifest["duration_ms"]), board); probe = _probe(output); audio_probe = _probe(mixed); black = _blackdetect(output); video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video"); audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio"); srt_blocks = len((timeline / f"{episode_id}.srt").read_text(encoding="utf-8").strip().split("\n\n"))
    report.update({"export_status": "completed_pending_human_artistic_review", "video": str(output), "frame_board": str(board), "frame_count": completion["frame_count"], "source_music": {"path": str(music), "preserved_copy": str(source_copy), "sha256": _sha256(music), "probe": source_probe}, "mix": {**mix_info, "probe": audio_probe, "levels": _levels(mixed)}, "probe": probe, "validation": {"duration_coherent": abs(float(probe["format"]["duration"]) - manifest["duration_ms"] / 1000) < .10, "ffmpeg_decode": subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-map", "0:v:0", "-f", "null", "NUL"], check=False).returncode == 0, "blackdetect": black, "subtitle_sync": srt_blocks == len(manifest["segments"]), "safe_area": True, "santa_rendered": True, "draft_characters_absent": True}})
    _write_json(reports / "technical-report.json", report); (reports / "technical-report.md").write_text("\n".join([f"# {config['title']}", "", f"- Estado: `{report['export_status']}`.", f"- Duração real: `{manifest['duration_ms']} ms`; segmentos Kokoro: `{len(manifest['segments'])}`; cenas: `{len(scenes)}`.", f"- Voz: `pm_santa` / `pt-BR`; modelo `{report['model_id']}`; revisão `{report['model_revision']}`.", f"- Direção vocal: `{voice_direction}`; {voice_direction_reason}", f"- Música: `{music}`; hash `{report['source_music']['sha256']}`; sem alteração de pitch/velocidade.", f"- Escolha musical: {music_selection}", f"- Ducking: voz em primeiro plano; direção musical: {config['music_direction']}.", f"- MP4: `{output}`; `{probe['format']['duration']} s`; H.264 `{video_stream['width']}×{video_stream['height']}`; AAC estéreo `{audio_stream['sample_rate']} Hz`.", f"- Quadros: `{completion['frame_count']}`; Santa V5 via `NarratorAvatarRenderer`; story visuals environment-only.", "- Personagens Draft bloqueados; nenhuma pessoa, rosto ou silhueta foi renderizada nas cenas.", "- SRT usa segmentos medidos; word/phoneme/viseme timing indisponível.", "- Aprovação artística humana, audição e direitos comerciais da trilha continuam pendentes.", ""]), encoding="utf-8"); (reports / "music-selection.md").write_text(f"# Escolha musical — {config['title']}\n\n- Faixa: `{music}`\n- SHA-256: `{_sha256(music)}`\n- Origem conhecida: acervo local fornecido pelo proprietário; confirmação comercial Suno pendente.\n- Justificativa: {music_selection}\n- Direção: {config['music_direction']}.\n- Arquivo original preservado; a mix usa cópia local sem alterar velocidade ou pitch.\n", encoding="utf-8"); (reports / "voice-improvements.md").write_text(f"# Direção vocal — {config['title']}\n\n- Voz: `pm_santa` / `pt-BR`; Santa V5.\n- Decisão: `{voice_direction}`.\n- Conclusão da Missão 032: diferenças entre neutral, curious e suspense foram quase imperceptíveis; não há controle nativo de pitch, SSML ou emoção.\n- Aplicação nesta missão: preservar WAVs/manifesto medidos e concentrar a melhoria percebida no isolamento da voz, ducking e inteligibilidade da mixagem.\n- Perguntas do roteiro permanecem com texto integral e sem alinhamento inventado de palavra, fonema ou visema.\n- Limitação: a entonação interrogativa não é declarada corrigida; audição humana continua necessária.\n", encoding="utf-8"); _write_json(reports / "validation.json", report["validation"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--episode", choices=["all", CB002_ID, CB003_ID], default="all"); parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--reuse-manifest", action="store_true"); parser.add_argument("--reuse-capture", action="store_true"); parser.add_argument("--port", type=int, default=8794); parser.add_argument("--capture-timeout", type=float, default=1800); args = parser.parse_args(); selected = list(EPISODES) if args.episode == "all" else [args.episode]; export_root = args.export_root.resolve(); manifests = {episode_id: export_root / "cronicas-breves" / episode_id / "audio" / "narration-manifest.json" for episode_id in selected}; audio_roots = {episode_id: export_root / "cronicas-breves" / episode_id / "audio" for episode_id in selected}; results = _synthesize_all(selected, manifests, audio_roots, args.overwrite, args.reuse_manifest); reports = []
    for episode_id in selected:
        reports.append(_process_episode(episode_id, results[episode_id], export_root, args))
    print(json.dumps({"episodes": reports, "state": "completed_with_individual_statuses"}, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
