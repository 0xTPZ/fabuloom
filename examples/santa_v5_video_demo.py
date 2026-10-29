"""Render Santa V5 with the same deterministic layered engine used by Stage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.parse import quote
from urllib.request import urlopen

from first_video_demo import _compose_audio, _probe, _write_srt


STORY_ID = "fabuloom-santa-v5"
SOURCE_STORY_ID = "fabuloom-santa-v3"
VOICE_ID = "pm_santa"
FPS = 30
WIDTH = 1080
HEIGHT = 1920


def _prepare_manifest(export_dir: Path, overwrite: bool) -> Path:
    source = export_dir / f"{SOURCE_STORY_ID}.json"
    target = export_dir / f"{STORY_ID}.json"
    if not source.is_file():
        raise FileNotFoundError(f"previous measured manifest not found: {source}")
    if target.exists() and not overwrite:
        raise FileExistsError(f"manifest already exists: {target}; pass --overwrite explicitly")
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["id"] = STORY_ID
    payload.setdefault("metadata", {})["narration_id"] = STORY_ID
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _validate_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("segments") or int(payload.get("duration_ms", 0)) <= 0:
        raise ValueError("reused manifest has no measured segments")
    voices = {segment.get("voice_id") for segment in payload["segments"]}
    if voices != {VOICE_ID}:
        raise ValueError(f"manifest voices do not match {VOICE_ID}: {sorted(voices)}")
    for segment in payload["segments"]:
        if not segment.get("audio_uri") or int(segment.get("duration_ms", 0)) <= 0:
            raise ValueError("manifest contains an invalid measured audio segment")
    return payload


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Microsoft Edge is required for deterministic browser capture")


def _wait_for_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/capture-santa-v5.html", timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError("local V5 capture server did not start")


def _capture_frames(studio_root: Path, capture_dir: Path, manifest_path: Path, duration_ms: int, port: int, timeout: float) -> dict:
    env = os.environ.copy()
    env["FABULOOM_CAPTURE_DIR"] = str(capture_dir.parent)
    server = subprocess.Popen([sys.executable, str(studio_root / "frontend" / "server.py"), "--port", str(port)], cwd=studio_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge_process = None
    profile_dir = None
    try:
        _wait_for_server(port)
        profile_dir = Path(tempfile.mkdtemp(prefix=".santa-v5-edge-", dir=capture_dir.parent))
        url = f"http://127.0.0.1:{port}/capture-santa-v5.html?session={quote(capture_dir.name)}&manifest={quote('/exports/' + manifest_path.name, safe='')}&fps={FPS}"
        edge_process = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile_dir}", f"--window-size={WIDTH},{HEIGHT}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        completion = capture_dir / "complete.json"
        deadline = time.monotonic() + timeout
        while not completion.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Santa V5 capture timed out after {timeout:.0f}s")
            if edge_process.poll() is not None:
                error = capture_dir / "error.json"
                detail = error.read_text(encoding="utf-8") if error.is_file() else "no browser error record"
                raise RuntimeError(f"Edge exited before completion: {detail}")
            time.sleep(0.25)
        result = json.loads(completion.read_text(encoding="utf-8"))
        frames = sorted(path for path in capture_dir.glob("*.png") if path.stem.isdigit())
        indexes = [int(path.stem) for path in frames]
        if indexes != list(range(int(result["frame_count"]))):
            raise ValueError("capture frame sequence is not contiguous")
        if any(path.stat().st_size < 1000 for path in frames):
            raise ValueError("capture contains an unexpectedly small PNG")
        if int(result["duration_ms"]) != duration_ms:
            raise ValueError("capture duration differs from measured manifest")
        return result
    finally:
        if edge_process is not None and edge_process.poll() is None:
            edge_process.terminate()
            try:
                edge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(edge_process.pid), "/T", "/F"], check=False, capture_output=True)
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


def _caption_files(manifest: dict, directory: Path) -> list[Path]:
    paths = []
    for index, segment in enumerate(manifest["segments"]):
        path = directory / f".santa-v5-caption-{index:04d}.txt"
        path.write_text("\n".join(textwrap.wrap(segment["text"], width=34, break_long_words=False)), encoding="utf-8")
        paths.append(path)
    return paths


def _render_mp4(manifest: dict, frames: Path, audio: Path, caption_files: list[Path], output: Path, overwrite: bool) -> None:
    duration = int(manifest["duration_ms"]) / 1000
    parts = ["[0:v]setsar=1[stage]"]
    previous = "stage"
    for index, (segment, caption_file) in enumerate(zip(manifest["segments"], caption_files)):
        label = f"caption{index}"
        start = segment["start_ms"] / 1000
        end = segment["end_ms"] / 1000
        parts.append(f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{caption_file.name}':fontcolor=0xFFFFFF:fontsize=38:line_spacing=8:box=1:boxcolor=0x07142A@0.80:boxborderw=18:x=(w-text_w)/2:y=300:enable='between(t,{start:.3f},{end:.3f})'[{label}]")
        previous = label
    parts.append(f"[{previous}]drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='FABULOOM  ·  SANTA V5':fontcolor=0xF7D27A:fontsize=26:x=(w-text_w)/2:y=h-84:enable='gte(t,{max(0, duration - 2.8):.3f})'[v]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(FPS), "-i", str(frames / "%06d.png"), "-i", str(audio), "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "1:a", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def _four_frame_comparison(frames: Path, output: Path, indexes: list[int]) -> None:
    labels = ["rest / neutral", "walk", "sit", "gesture"]
    inputs = []
    filters = []
    for index, label in zip(indexes, labels):
        inputs.extend(["-i", str(frames / f"{index:06d}.png")])
        slot = chr(97 + len(filters))
        filters.append(f"[{len(filters)}:v]scale=270:480,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=22:x=12:y=12:box=1:boxcolor=0x07142A@.8[{slot}]")
    filters.append("[a][b][c][d]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[out]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _v4_v5_comparison(v4_frame: Path, v5_frame: Path, output: Path) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(v4_frame), "-i", str(v5_frame), "-filter_complex", "[0:v]scale=540:-1,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='Santa V4':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.8[a];[1:v]scale=540:-1,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='Santa V5':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.8[b];[a][b]hstack=inputs=2", "-frames:v", "1", str(output)]
    subprocess.run(command, check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).resolve().parents[2] / "workspace" / "exports")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8778)
    parser.add_argument("--capture-timeout", type=float, default=360)
    args = parser.parse_args()
    studio_root = Path(__file__).resolve().parents[1]
    export_dir = args.export_dir.resolve(); video_dir = export_dir / "videos"; video_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _prepare_manifest(export_dir, args.overwrite)
    manifest = _validate_manifest(manifest_path)
    audio_path = video_dir / f"{STORY_ID}.wav"; srt_path = video_dir / f"{STORY_ID}.srt"; output = video_dir / f"{STORY_ID}.mp4"; comparison = video_dir / f"{STORY_ID}-frames-comparison.png"; v4v5 = video_dir / "fabuloom-santa-v4-vs-v5-comparison.png"
    if output.exists() and not args.overwrite: raise FileExistsError(f"video already exists: {output}; pass --overwrite explicitly")
    sample_rate, _ = _compose_audio(manifest, audio_path); _write_srt(manifest, srt_path); caption_files = _caption_files(manifest, video_dir)
    frames = video_dir / f".{STORY_ID}-frames"
    if frames.exists():
        if not args.overwrite: raise FileExistsError(f"capture directory already exists: {frames}; pass --overwrite explicitly")
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    capture = _capture_frames(studio_root, frames, manifest_path, int(manifest["duration_ms"]), args.port, args.capture_timeout)
    _render_mp4(manifest, frames, audio_path, caption_files, output, args.overwrite)
    last = max(0, capture["frame_count"] - 1); _four_frame_comparison(frames, comparison, [0, min(90, last), min(180, last), min(450, last)])
    v4_frame = video_dir / ".fabuloom-santa-v4-frames" / "000180.png"
    if v4_frame.is_file(): _v4_v5_comparison(v4_frame, frames / "000180.png", v4v5)
    probe = _probe(output); video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video"); audio_stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    report = video_dir / f"{STORY_ID}-report.md"
    report.write_text("\n".join([
        "# Fabuloom Santa V5 — relatório de rig e animação", "", "- Personagem: Santa V5 com arte preparada para rig fino; voz `pm_santa`, português brasileiro.", "- Áudio: manifesto medido da demonstração Santa V3 reutilizado; nenhuma nova síntese foi executada.", f"- Manifesto reutilizado/adaptado: `{manifest_path}`", f"- Frames: `{frames}` ({capture['frame_count']} frames at {FPS} fps)", f"- Áudio medido: `{manifest['duration_ms']} ms` at `{sample_rate} Hz`", f"- MP4: `{output}`", f"- FFprobe: `{probe['format']['duration']} s`, `{video_stream['width']}x{video_stream['height']}`, vídeo `{video_stream['codec_name']}`, áudio `{audio_stream['codec_name']}`, `{output.stat().st_size} bytes`", f"- Comparativo de poses: `{comparison}`", f"- Comparativo Santa V4/V5: `{v4v5}`" if v4v5.is_file() else "- Comparativo Santa V4/V5: frame V4 não disponível.", "- Animação: LayeredCharacterRig + LayeredCharacterRenderer + SantaV5SceneRenderer; FFmpeg apenas compõe os frames produzidos pelo mesmo motor do palco.", "- Xícara: posição derivada do plano transformado da camada `right_hand`, com fallback somente para packs sem mão explícita.", "- Boca: envelope RMS do WAV medido; alinhamento fonético/visemas não disponível e não inventado.", "- Limitação: validação visual humana do vídeo completo continua recomendada além dos testes automatizados.", ""]), encoding="utf-8")
    print(f"manifest={manifest_path}"); print(f"audio={audio_path}"); print(f"frames={frames}"); print(f"video={output}"); print(f"comparison={comparison}"); print(f"v4v5_comparison={v4v5}"); print(f"report={report}"); print(f"probe={json.dumps(probe, ensure_ascii=False, sort_keys=True)}"); print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
