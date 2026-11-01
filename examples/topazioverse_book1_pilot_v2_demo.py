"""Render the Topazioverse pilot V2 with the owner-provided original score.

The V1 manifest, measured voice WAVs and scene art are reused. Only the mix,
composition and final export are new: Santa V5 remains visible throughout.
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

from topazioverse_book1_pilot_demo import (
    EXPORT_ROOT,
    FPS as OUTPUT_FPS,
    PROJECT_ID as V1_PROJECT_ID,
    frame_board,
    probe,
)


V2_PROJECT_ID = "topazioverse-book1-episode1-pilot-v2"
V1_ROOT = EXPORT_ROOT / V1_PROJECT_ID
PROJECT_ROOT = EXPORT_ROOT / V2_PROJECT_ID
MANIFEST = V1_ROOT / "manifest.json"
VOICE_WAV = V1_ROOT / "audio" / f"{V1_PROJECT_ID}-voice.wav"
MUSIC = Path(r"E:\Fabuloom\workspace\inputs\music\book1\Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3")
AMBIENCE = Path(r"E:\Fabuloom\workspace\inputs\ambience\book1\rain-window-closed.wav")
CAPTURE_FPS = 15
OUTPUT_FPS = 30
WIDTH = 1920
HEIGHT = 1080


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mix_audio_v2(voice: Path, music: Path, ambience: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    fade_start = max(0.0, duration - 4.0)
    filter_graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.11,atrim=duration={duration:.3f},afade=t=in:st=0:d=3,afade=t=out:st={fade_start:.3f}:d=4[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=8:attack=80:release=700:makeup=1[ducked];"
        f"[2:a]aresample=48000,volume=0.010,atrim=duration={duration:.3f},afade=t=in:st=0:d=3,afade=t=out:st={fade_start:.3f}:d=4[amb];"
        "[voice_st][ducked][amb]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-stream_loop", "-1", "-i", str(ambience),
        "-filter_complex", filter_graph, "-map", "[out]", "-t", f"{duration:.3f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
    ]
    subprocess.run(command, check=True)


def _find_edge() -> str:
    candidates = [
        shutil.which("msedge"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for Canvas capture")


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


def _materialize_source_frames(session_dir: Path, completion: dict, duration_ms: int) -> list[Path]:
    source_count = int(completion["frame_count"])
    source_frames = sorted(session_dir.glob("src-*.jpg"))
    if len(source_frames) != source_count:
        raise RuntimeError(f"source frame count mismatch: {len(source_frames)} != {source_count}")
    output_count = int((duration_ms * OUTPUT_FPS + 999) // 1000)
    for output_index in range(output_count):
        source_index = min(source_count - 1, round(output_index * CAPTURE_FPS / OUTPUT_FPS))
        target = session_dir / f"{output_index:06d}.jpg"
        if target.exists():
            continue
        try:
            os.link(session_dir / f"src-{source_index:06d}.jpg", target)
        except OSError:
            shutil.copyfile(session_dir / f"src-{source_index:06d}.jpg", target)
    frames = sorted(session_dir.glob("[0-9]*.jpg"))
    if len(frames) != output_count:
        raise RuntimeError(f"output frame count mismatch: {len(frames)} != {output_count}")
    return frames


def capture_frames_v2(timeline_path: Path, frames_root: Path, *, port: int, timeout: float) -> tuple[Path, dict]:
    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env["FABULOOM_WORKSPACE_ROOT"] = r"E:\Fabuloom"
    env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT)
    env["FABULOOM_CAPTURE_DIR"] = str(frames_root)
    server = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"), "--port", str(port)],
        cwd=str(Path(__file__).resolve().parents[1]), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    browser = None
    try:
        _wait_http(f"http://127.0.0.1:{port}/capture-topazioverse-pilot-v2.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazioverse-pilot-v2.html?session={session}&timeline=/exports/{relative}&fps={CAPTURE_FPS}"
        browser = subprocess.Popen([
            edge, "--headless=new", "--hide-scrollbars", "--window-size=1920,1080",
            "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        if error.exists():
            raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists():
            raise TimeoutError(f"capture did not complete: {session_dir}")
        completion = json.loads(complete.read_text(encoding="utf-8"))
        _materialize_source_frames(session_dir, completion, int(completion["duration_ms"]))
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


def render_mp4(frames_dir: Path, audio: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-framerate", str(OUTPUT_FPS), "-i", str(frames_dir / "%06d.jpg"), "-i", str(audio),
        "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(output),
    ], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8774)
    parser.add_argument("--capture-timeout", type=float, default=1200)
    args = parser.parse_args()
    for required in (MANIFEST, VOICE_WAV, MUSIC, AMBIENCE):
        if not required.is_file():
            raise FileNotFoundError(required)
    audio_dir = PROJECT_ROOT / "audio"
    timeline_dir = PROJECT_ROOT / "timeline"
    captures_dir = PROJECT_ROOT / "captures"
    frames_root = PROJECT_ROOT / ".frames"
    for directory in (audio_dir, timeline_dir, captures_dir, frames_root):
        directory.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    timeline = {
        "format": "fabuloom.topazioverse-pilot/0.2",
        "title": "O Despertar dos Cristais — Capítulo 1",
        "manifest": f"{V1_PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": 800,
        "narrator": "Santa V5",
        "voice_id": "pm_santa",
        "language": "pt-BR",
        "narrator_visibility": "entire_narrative",
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "ambience_asset": "workspace/inputs/ambience/book1/rain-window-closed.wav",
        "scenes": [
            {
                "id": scene["id"], "image": scene["image"], "camera": scene["camera"],
                "start_ms": scene["start_ms"], "end_ms": scene["end_ms"],
                "source_paragraphs": scene["source_paragraphs"],
            }
            for scene in json.loads((V1_ROOT / "timeline" / f"{V1_PROJECT_ID}.json").read_text(encoding="utf-8"))["scenes"]
        ],
    }
    timeline_path = timeline_dir / f"{V2_PROJECT_ID}.json"
    _json(timeline_path, timeline)
    mix_path = audio_dir / f"{V2_PROJECT_ID}-mix.wav"
    mix_audio_v2(VOICE_WAV, MUSIC, AMBIENCE, mix_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    if args.reuse_capture:
        existing = sorted(frames_root.glob("capture-*/complete.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not existing:
            raise FileNotFoundError("no V2 capture available")
        session_dir = existing[0].parent
        completion = json.loads(existing[0].read_text(encoding="utf-8"))
        _materialize_source_frames(session_dir, completion, int(manifest["duration_ms"]))
    else:
        session_dir, completion = capture_frames_v2(timeline_path, frames_root, port=args.port, timeout=args.capture_timeout)
    video_path = PROJECT_ROOT / f"{V2_PROJECT_ID}.mp4"
    render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    board = captures_dir / f"{V2_PROJECT_ID}-frames.png"
    frame_board(session_dir, board, int((int(manifest["duration_ms"]) * OUTPUT_FPS + 999) // 1000), overwrite=args.overwrite)
    video_probe = probe(video_path)
    audio_probe = probe(mix_path)
    report = {
        "project": V2_PROJECT_ID,
        "video": str(video_path),
        "mix": str(mix_path),
        "timeline": str(timeline_path),
        "frames": str(session_dir),
        "frame_board": str(board),
        "duration_ms": manifest["duration_ms"],
        "capture_fps": CAPTURE_FPS,
        "output_fps": OUTPUT_FPS,
        "narrator_visibility": "entire_narrative",
        "voice_id": "pm_santa",
        "music": MUSIC.name,
        "music_origin": "owner-provided Suno generation; publication rights pending plan/terms confirmation",
        "audio_probe": audio_probe,
        "video_probe": video_probe,
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "state": "completed_pending_human_audio_visual_review",
    }
    _json(PROJECT_ROOT / "reports" / "pilot-v2-result.json", report)
    (PROJECT_ROOT / "reports" / "technical-report.md").write_text(
        "# Topazioverse Book 1 — Piloto V2\n\n"
        f"- Música: `{MUSIC.name}`; origem fornecida pelo proprietário/Suno; direitos de publicação ainda pendentes de confirmação.\n"
        f"- Santa V5: visível durante toda a narrativa; voz Kokoro `pm_santa`; boca baseada em RMS.\n"
        f"- Duração: `{manifest['duration_ms']} ms`; captura determinística em `{CAPTURE_FPS}` FPS materializada para `{OUTPUT_FPS}` FPS.\n"
        f"- Mix: volume inicial da trilha `0.11`, ducking sidechain, fade-in/out e limiter.\n"
        f"- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n"
        f"- FFprobe mix: `{json.dumps(audio_probe, ensure_ascii=False, sort_keys=True)}`\n"
        "- A classificação instrumental não é provada por FFprobe; foi preservada como declaração de origem do proprietário.\n"
        "- Revisão humana de inteligibilidade, equilíbrio musical e qualidade artística permanece obrigatória.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
