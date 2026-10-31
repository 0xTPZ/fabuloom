"""Produce Mission 018 with Kokoro, measured scenes and the shared V1.4 avatar."""

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
from urllib.parse import quote
from urllib.request import urlopen

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError

from first_video_demo import _compose_audio, _write_srt
from narrator_mode_demo import FPS, HEIGHT, STUDIO_ROOT, WIDTH, _edge_path, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
PROJECT_ID = "cinematic-story-test-v1"
STORY_ID = "fabuloom-cinematic-story-test-v1"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
STORY_TEXT = """Durante séculos, Arenhast guardou um segredo que ninguém ousava revelar.

Nas profundezas de um templo esquecido, um cristal primordial aguardava seu despertar.

Mas naquela noite, alguém encontrou o caminho até ele. E o destino de Topázio estava prestes a mudar."""

SCENES = (
    ("arenhast-storm", "cinematic-story-test-v1/scenes/scene-1-arenhast-storm.png", "progressive_zoom"),
    ("ancient-temple-crystal", "cinematic-story-test-v1/scenes/scene-2-ancient-temple-crystal.png", "crystal_pulse"),
    ("silhouette-crystal", "cinematic-story-test-v1/scenes/scene-3-silhouette-crystal-final.png", "lateral_pan"),
)


def _write_json(path: Path, payload: object, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-cinematic-story.html", timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError("cinematic capture server did not start")


def _capture(studio_root: Path, frames: Path, timeline: Path, port: int, timeout: float) -> dict:
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(frames.parent)
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None; profile = None
    try:
        _wait_for_server(port)
        profile = Path(tempfile.mkdtemp(prefix=".cinematic-edge-", dir=frames.parent))
        url = f"http://127.0.0.1:{port}/capture-cinematic-story.html?session={quote(frames.name)}&timeline={quote('/exports/' + timeline.relative_to(EXPORT_ROOT).as_posix(), safe='')}&fps={FPS}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = frames / "complete.json"; deadline = time.monotonic() + timeout
        while not complete.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"cinematic capture timed out after {timeout:.0f}s")
            if edge.poll() is not None:
                error = frames / "error.json"; raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited before completion")
            time.sleep(0.25)
        result = json.loads(complete.read_text(encoding="utf-8")); image_frames = sorted(path for path in frames.glob("*.png") if path.stem.isdigit())
        if len(image_frames) != result["frame_count"] or any(path.stat().st_size < 1000 for path in image_frames):
            raise ValueError("cinematic capture frames are incomplete")
        return result
    finally:
        if edge is not None and edge.poll() is None:
            edge.terminate()
            try: edge.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"], check=False, capture_output=True)
        if profile is not None: shutil.rmtree(profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


def _story_schedule(manifest: dict) -> list[dict]:
    if len(manifest["segments"]) < 3:
        raise ValueError("Mission 018 requires at least three measured segments for three scenes")
    groups = ((0,), (1,), tuple(range(2, len(manifest["segments"]))),)
    scenes = []
    for index, ((scene_id, image, camera), group) in enumerate(zip(SCENES, groups)):
        first = manifest["segments"][group[0]]
        last = manifest["segments"][group[-1]]
        end_ms = last["end_ms"] + int(last.get("metadata", {}).get("pause_after_ms", 0))
        if index == len(SCENES) - 1:
            end_ms = manifest["duration_ms"]
        scenes.append({"id": scene_id, "image": image, "camera": camera, "start_ms": first["start_ms"], "end_ms": end_ms, "text_segment_ids": [manifest["segments"][position]["id"] for position in group]})
    return scenes


def _anatomy_board(frames: Path, output: Path) -> None:
    samples = [(0, "cidade · início"), (max(0, len(list(frames.glob("*.png"))) // 3), "templo · cristal"), (max(0, len(list(frames.glob("*.png"))) * 2 // 3), "silhueta · clímax"), (max(0, len(list(frames.glob("*.png"))) - 1), "encerramento")]
    inputs: list[str] = []; filters: list[str] = []
    for slot, (index, label) in zip(("a", "b", "c", "d"), samples):
        inputs += ["-i", str(frames / f"{index:06d}.png")]
        filters.append(f"[{len(inputs)//2-1}:v]scale=640:360:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=24:x=18:y=18:box=1:boxcolor=0x07142A@.88[{slot}]")
    filters.append("[a][b][c][d]xstack=inputs=4:layout=0_0|640_0|0_360|640_360[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--reuse-manifest", action="store_true"); parser.add_argument("--reuse-capture", action="store_true"); parser.add_argument("--port", type=int, default=8788); parser.add_argument("--capture-timeout", type=float, default=600); args = parser.parse_args()
    export_root = args.export_dir.resolve(); project_root = export_root / PROJECT_ID; videos = export_root / "videos"; project_root.mkdir(parents=True, exist_ok=True); videos.mkdir(parents=True, exist_ok=True)
    manifest_path = project_root / f"{STORY_ID}.json"; timeline_path = project_root / f"{STORY_ID}-timeline.json"; audio_path = project_root / f"{STORY_ID}.wav"; frames = project_root / ".frames"; output = videos / "fabuloom-cinematic-story-test-v1.mp4"; board = videos / "fabuloom-cinematic-story-test-v1-frames.png"; srt = videos / "fabuloom-cinematic-story-test-v1.srt"; report = videos / "fabuloom-cinematic-story-test-v1-report.md"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")); synthesis_seconds = 0.0; model_load_seconds = 0.0; synthesis_status = "reutilizada (0.000 s nesta execução)"
    else:
        os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1"); os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
        provider = KokoroTTSProvider(output_dir=project_root, allow_overwrite=args.overwrite)
        try:
            run = synthesize_narration(provider, STORY_TEXT, narration_id=STORY_ID, manifest_id=STORY_ID, voice_id=VOICE_ID, language=LANGUAGE, output_dir=project_root, max_chars=360)
            _write_json(manifest_path, json.loads(serialize_manifest(run.manifest)), args.overwrite); manifest = json.loads(serialize_manifest(run.manifest)); synthesis_seconds = run.processing_seconds; model_load_seconds = float(run.results[0].metadata.get("model_load_seconds") or 0); synthesis_status = f"executada ({synthesis_seconds:.3f} s)"
        except (TTSError, NarrationSynthesisError):
            raise
        finally:
            provider.close()
    scenes = _story_schedule(manifest); timeline = {"format": "fabuloom.cinematic-story/0.1", "title": "O Último Cristal de Arenhast", "manifest": f"{PROJECT_ID}/{manifest_path.name}", "transition_ms": 700, "scenes": scenes, "image_source": "original_generated_assets", "camera_source": "deterministic_canvas_keyframes"}; _write_json(timeline_path, timeline, args.overwrite); _write_srt(manifest, srt)
    sample_rate, _ = _compose_audio(manifest, audio_path)
    if frames.exists() and not args.reuse_capture:
        if not args.overwrite: raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    if args.reuse_capture and not frames.is_dir(): raise FileNotFoundError(f"capture directory does not exist: {frames}")
    frames.mkdir(parents=True, exist_ok=True)
    capture = {"frame_count": len([path for path in frames.glob("*.png") if path.stem.isdigit()]), "fps": FPS, "reused": True} if args.reuse_capture else _capture(STUDIO_ROOT, frames, timeline_path, args.port, args.capture_timeout)
    _render_mp4(frames, audio_path, output, int(manifest["duration_ms"]), args.overwrite); _anatomy_board(frames, board); probe = _probe_export(output); elapsed = time.perf_counter() - started; video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video"); audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report.write_text("\n".join(["# Fabuloom Cinematic Story Test V1", "", f"- Texto: `{STORY_TEXT.replace(chr(10), ' ')}`", f"- Provedor: Kokoro `{VOICE_ID}` · idioma `{LANGUAGE}` · modelo `hexgrad/Kokoro-82M`.", f"- Manifesto medido: `{manifest_path}`; WAV composto: `{audio_path}`; duração real: `{manifest['duration_ms']} ms`.", f"- Segmentos: {len(manifest['segments'])}; cenas calculadas após medição: `{json.dumps(scenes, ensure_ascii=False)}`.", f"- Síntese: `{synthesis_status}`; carregamento do modelo nesta execução: `{model_load_seconds:.3f} s`; tempo total: `{elapsed:.3f} s`.", f"- Frames: `{frames}` ({capture['frame_count']} a {FPS} fps).", f"- MP4: `{output}` ({output.stat().st_size} bytes).", f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']} `{video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`.", f"- Prancha: `{board}`; SRT: `{srt}`.", "- Cena 1 usa zoom progressivo; cena 2 usa aproximação e pulso determinístico de brilho; cena 3 usa panorâmica lateral e escurecimento.", "- Transições: crossfade determinístico de 700 ms entre intervalos derivados dos tempos medidos.", "- Santa V5 Narrator Mode V1.4 é reutilizado no canto inferior esquerdo, com pescoço corrigido, piscadas, boca RMS e voz pm_santa.", "- FilmCraft/EffectCraft foram auditados no TopazioCreativeLab. Suas operações já possuem provas isoladas, mas a integração com o Fabuloom não foi presumida; esta entrega usa o Canvas compartilhado + FFmpeg já comprovados.", "- Word, phoneme and viseme timing: unavailable; captions use measured segment ranges only.", "- Imagens geradas são originais e permanecem em workspace exports; nenhuma imagem de terceiro foi usada.", "- Aprovação artística humana continua obrigatória.", ""]), encoding="utf-8")
    print(f"manifest={manifest_path}"); print(f"audio={audio_path}"); print(f"timeline={timeline_path}"); print(f"frames={frames}"); print(f"video={output}"); print(f"board={board}"); print(f"report={report}"); print(f"duration_ms={manifest['duration_ms']}"); print(f"sample_rate={sample_rate}"); print(f"processing_seconds={elapsed:.3f}"); print(f"probe={json.dumps(probe, ensure_ascii=False)}"); print("state=completed"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
