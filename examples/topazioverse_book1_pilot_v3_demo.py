"""Render the Topazioverse Book 1 pilot V3 with Santa as host.

V3 preserves the measured V2 story manifest, voice and scene plan. It adds
two independently measured Kokoro host manifests, composes the three editorial
blocks into one timeline, and captures the same Santa V5 renderer used by the
stage. Generated media stays under the local exports workspace.
"""

from __future__ import annotations

import argparse
import copy
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
    frame_board,
    probe,
    write_srt,
)


V3_PROJECT_ID = "topazioverse-book1-episode1-pilot-v3"
V1_PROJECT_ID = "topazioverse-book1-episode1-pilot"
V1_ROOT = EXPORT_ROOT / V1_PROJECT_ID
PROJECT_ROOT = EXPORT_ROOT / V3_PROJECT_ID
V1_MANIFEST = V1_ROOT / "manifest.json"
V1_TIMELINE = V1_ROOT / "timeline" / f"{V1_PROJECT_ID}.json"
MUSIC = Path(r"E:\Fabuloom\workspace\inputs\music\book1\Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3")
AMBIENCE = Path(r"E:\Fabuloom\workspace\inputs\ambience\book1\rain-window-closed.wav")
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
CAPTURE_FPS = 15
OUTPUT_FPS = 30
WIDTH = 1920
HEIGHT = 1080
EDITORIAL_TRANSITION_MS = 1000

INTRO_TEXT = (
    "Saudações, viajantes! Sejam bem-vindos ao Topazioverse.\n\n"
    "Antes de começarmos, quero contar uma coisa: este universo está apenas começando a ganhar vida diante dos seus olhos.\n\n"
    "Estamos construindo nossas histórias com muita dedicação, e seria uma alegria ter vocês conosco nessa jornada.\n\n"
    "Se gostarem, deixem um comentário e compartilhem com outros viajantes.\n\n"
    "Agora, acomodem-se... Nossa história está prestes a começar."
)
OUTRO_TEXT = (
    "E assim começa nossa jornada por Topázio, meus amigos.\n\n"
    "Mas quero saber uma coisa: o que vocês acharam desse primeiro encontro com nosso universo?\n\n"
    "Contem nos comentários. Vou adorar conhecer suas impressões.\n\n"
    "Se quiserem acompanhar os próximos capítulos, inscrevam-se e compartilhem nossa história.\n\n"
    "Obrigado por estarem aqui, Guardiões. Até nossa próxima aventura!"
)


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _host_manifest(
    *,
    narration_id: str,
    text: str,
    manifest_path: Path,
    audio_dir: Path,
    resynthesize: bool,
    overwrite: bool,
) -> tuple[dict, dict]:
    if manifest_path.is_file() and not resynthesize:
        return json.loads(manifest_path.read_text(encoding="utf-8")), {"status": "reused", "processing_seconds": 0.0}
    provider = KokoroTTSProvider(output_dir=audio_dir, allow_overwrite=overwrite)
    started = time.perf_counter()
    try:
        run = synthesize_narration(
            provider,
            text,
            narration_id=narration_id,
            manifest_id=narration_id,
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
            "model_load_seconds": max(
                (float(result.metadata.get("model_load_seconds") or 0.0) for result in run.results),
                default=0.0,
            ),
        }
    finally:
        provider.close()


def _shift_segments(manifest: dict, offset_ms: int, block_id: str) -> list[dict]:
    shifted = []
    for segment in manifest["segments"]:
        value = copy.deepcopy(segment)
        value["id"] = f"{block_id.lower()}-{segment['id']}"
        value["dialogue_id"] = f"{block_id.lower()}-{segment['dialogue_id']}"
        value["start_ms"] = int(segment["start_ms"]) + offset_ms
        value["end_ms"] = int(segment["end_ms"]) + offset_ms
        value["metadata"] = dict(value.get("metadata") or {})
        value["metadata"]["editorial_block"] = block_id
        value["metadata"]["source_segment_id"] = segment["id"]
        shifted.append(value)
    return shifted


def build_combined_manifest(
    intro: dict,
    story: dict,
    outro: dict,
    *,
    transition_ms: int = EDITORIAL_TRANSITION_MS,
) -> tuple[dict, dict]:
    intro_duration = int(intro["duration_ms"])
    story_start = intro_duration + transition_ms
    story_duration = int(story["duration_ms"])
    story_end = story_start + story_duration
    outro_start = story_end + transition_ms
    outro_duration = int(outro["duration_ms"])
    duration_ms = outro_start + outro_duration
    manifest = {
        "animation_events": [],
        "duration_ms": duration_ms,
        "format_version": "0.1.0",
        "id": V3_PROJECT_ID,
        "metadata": {
            "language": LANGUAGE,
            "narration_id": V3_PROJECT_ID,
            "segment_count": len(intro["segments"]) + len(story["segments"]) + len(outro["segments"]),
            "sequence_order": "editorial_block_order",
            "status": "completed",
            "temporal_source": "measured_wav",
            "voice_id": VOICE_ID,
            "editorial_blocks": ["HOST_INTRO", "STORY_CHAPTER", "HOST_OUTRO"],
            "story_source_manifest": f"{V1_PROJECT_ID}/manifest.json",
        },
        "segments": (
            _shift_segments(intro, 0, "HOST_INTRO")
            + _shift_segments(story, story_start, "STORY_CHAPTER")
            + _shift_segments(outro, outro_start, "HOST_OUTRO")
        ),
    }
    blocks = {
        "HOST_INTRO": {
            "id": "HOST_INTRO",
            "kind": "host_intro",
            "start_ms": 0,
            "audio_end_ms": intro_duration,
            "end_ms": story_start,
            "audio_duration_ms": intro_duration,
            "transition_after_ms": transition_ms,
            "text_source": "editorial_host_copy",
        },
        "STORY_CHAPTER": {
            "id": "STORY_CHAPTER",
            "kind": "story_chapter",
            "start_ms": story_start,
            "audio_end_ms": story_end,
            "end_ms": outro_start,
            "audio_duration_ms": story_duration,
            "transition_after_ms": transition_ms,
            "text_source": "reused_v2_measured_manifest",
        },
        "HOST_OUTRO": {
            "id": "HOST_OUTRO",
            "kind": "host_outro",
            "start_ms": outro_start,
            "audio_end_ms": duration_ms,
            "end_ms": duration_ms,
            "audio_duration_ms": outro_duration,
            "transition_after_ms": 0,
            "text_source": "editorial_host_copy",
        },
    }
    return manifest, {
        "intro_duration_ms": intro_duration,
        "story_start_ms": story_start,
        "story_end_ms": story_end,
        "outro_start_ms": outro_start,
        "outro_duration_ms": outro_duration,
        "duration_ms": duration_ms,
        "blocks": [blocks["HOST_INTRO"], blocks["STORY_CHAPTER"], blocks["HOST_OUTRO"]],
    }


def build_timeline(block_info: dict, story_timeline: dict) -> dict:
    story_start = block_info["story_start_ms"]
    scenes = []
    for source in story_timeline["scenes"]:
        scene = copy.deepcopy(source)
        scene["start_ms"] += story_start
        scene["end_ms"] += story_start
        scenes.append(scene)
    return {
        "format": "fabuloom.topazioverse-pilot/0.3",
        "title": "O Despertar dos Cristais — Capítulo 1",
        "manifest": f"{V3_PROJECT_ID}/manifest.json",
        "duration_ms": block_info["duration_ms"],
        "editorial_blocks": block_info["blocks"],
        "transition_ms": EDITORIAL_TRANSITION_MS,
        "narrator": "Santa V5",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "narrator_visibility": "entire_program",
        "timing_source": "measured_wav_segments_plus_explicit_editorial_pauses",
        "word_phoneme_viseme_timing": "unavailable",
        "story_source_manifest": f"{V1_PROJECT_ID}/manifest.json",
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "ambience_asset": "workspace/inputs/ambience/book1/rain-window-closed.wav",
        "scenes": scenes,
    }


def mix_audio_v3(
    voice: Path,
    music: Path,
    ambience: Path,
    output: Path,
    duration_ms: int,
    story_start_ms: int,
    story_end_ms: int,
    outro_start_ms: int,
    *,
    overwrite: bool,
) -> None:
    duration = duration_ms / 1000
    story_start = story_start_ms / 1000
    story_end = story_end_ms / 1000
    outro_start = outro_start_ms / 1000
    fade_start = max(0.0, duration - 4.0)
    # The score is quiet under host copy, returns to the V2 level in the story,
    # and rises gently during the outro while sidechain ducking stays active.
    music_volume = (
        f"if(lt(t\\,{story_start:.3f})\\,0.06\\,"
        f"if(lt(t\\,{story_end:.3f})\\,0.11\\,"
        f"0.08+0.04*min(1\\,max(0\\,(t-{outro_start:.3f})/6))))"
    )
    filter_graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=eval=frame:volume={music_volume},atrim=duration={duration:.3f},"
        f"afade=t=in:st=0:d=3,afade=t=out:st={fade_start:.3f}:d=4[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=8:attack=80:release=700:makeup=1[ducked];"
        f"[2:a]aresample=48000,volume=0.008,atrim=duration={duration:.3f},afade=t=in:st=0:d=3,"
        f"afade=t=out:st={fade_start:.3f}:d=4[amb];"
        "[voice_st][ducked][amb]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95[out]"
    )
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
            "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
            "-stream_loop", "-1", "-i", str(ambience), "-filter_complex", filter_graph,
            "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2",
            "-c:a", "pcm_s16le", str(output),
        ],
        check=True,
    )


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


def capture_frames_v3(timeline_path: Path, frames_root: Path, *, port: int, timeout: float) -> tuple[Path, dict]:
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
        _wait_http(f"http://127.0.0.1:{port}/capture-topazioverse-pilot-v3.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazioverse-pilot-v3.html?session={session}&timeline=/exports/{relative}&fps={CAPTURE_FPS}"
        browser = subprocess.Popen(
            [edge, "--headless=new", "--hide-scrollbars", "--window-size=1920,1080",
             "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
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
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
            "-framerate", str(OUTPUT_FPS), "-i", str(frames_dir / "%06d.jpg"), "-i", str(audio),
            "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(output),
        ],
        check=True,
    )


def block_board(frames_dir: Path, block_info: dict, output: Path, *, overwrite: bool) -> None:
    labels = [("HOST INTRO", block_info["blocks"][0]["start_ms"]), ("STORY CHAPTER", block_info["blocks"][1]["start_ms"] + 7000), ("HOST OUTRO", block_info["blocks"][2]["start_ms"] + 3000)]
    with tempfile.TemporaryDirectory(prefix=".block-board-", dir=output.parent) as temp:
        files = []
        for index, (label, timestamp) in enumerate(labels):
            frame = frames_dir / f"{max(0, round(timestamp * OUTPUT_FPS / 1000)):06d}.jpg"
            target = Path(temp) / f"{index}.png"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame),
                "-vf", f"scale=640:360,drawtext=text='{label}':x=24:y=24:fontsize=28:fontcolor=white:box=1:boxcolor=0x071426cc",
                str(target),
            ], check=True)
            files.append(target)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(files[0]), "-i", str(files[1]), "-i", str(files[2]), "-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3[out]", "-map", "[out]", str(output)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resynthesize-host", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8775)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    for required in (V1_MANIFEST, V1_TIMELINE, MUSIC, AMBIENCE):
        if not required.is_file():
            raise FileNotFoundError(required)
    audio_dir = PROJECT_ROOT / "audio"
    host_dir = audio_dir / "host"
    timeline_dir = PROJECT_ROOT / "timeline"
    captures_dir = PROJECT_ROOT / "captures"
    frames_root = PROJECT_ROOT / ".frames"
    for directory in (audio_dir, host_dir, timeline_dir, captures_dir, frames_root, PROJECT_ROOT / "reports"):
        directory.mkdir(parents=True, exist_ok=True)

    intro_manifest, intro_synthesis = _host_manifest(
        narration_id=f"{V3_PROJECT_ID}-host-intro", text=INTRO_TEXT,
        manifest_path=host_dir / "intro-manifest.json", audio_dir=host_dir,
        resynthesize=args.resynthesize_host, overwrite=args.overwrite,
    )
    outro_manifest, outro_synthesis = _host_manifest(
        narration_id=f"{V3_PROJECT_ID}-host-outro", text=OUTRO_TEXT,
        manifest_path=host_dir / "outro-manifest.json", audio_dir=host_dir,
        resynthesize=args.resynthesize_host, overwrite=args.overwrite,
    )
    story_manifest = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    story_timeline = json.loads(V1_TIMELINE.read_text(encoding="utf-8"))
    manifest, block_info = build_combined_manifest(intro_manifest, story_manifest, outro_manifest)
    manifest_path = PROJECT_ROOT / "manifest.json"
    _json(manifest_path, manifest)
    timeline = build_timeline(block_info, story_timeline)
    timeline_path = timeline_dir / f"{V3_PROJECT_ID}.json"
    _json(timeline_path, timeline)
    write_srt(manifest, timeline_dir / f"{V3_PROJECT_ID}.srt")
    voice_path = audio_dir / f"{V3_PROJECT_ID}-voice.wav"
    compose_voice(manifest, voice_path)
    mix_path = audio_dir / f"{V3_PROJECT_ID}-mix.wav"
    mix_audio_v3(
        voice_path, MUSIC, AMBIENCE, mix_path, block_info["duration_ms"],
        block_info["story_start_ms"], block_info["story_end_ms"], block_info["outro_start_ms"],
        overwrite=args.overwrite,
    )
    if args.reuse_capture:
        existing = sorted(frames_root.glob("capture-*/complete.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not existing:
            raise FileNotFoundError("no V3 capture available")
        session_dir = existing[0].parent
        completion = json.loads(existing[0].read_text(encoding="utf-8"))
        _materialize_source_frames(session_dir, completion, block_info["duration_ms"])
    else:
        session_dir, completion = capture_frames_v3(timeline_path, frames_root, port=args.port, timeout=args.capture_timeout)
    video_path = PROJECT_ROOT / f"{V3_PROJECT_ID}.mp4"
    render_mp4(session_dir, mix_path, video_path, block_info["duration_ms"], overwrite=args.overwrite)
    frame_count = int((block_info["duration_ms"] * OUTPUT_FPS + 999) // 1000)
    board_path = captures_dir / f"{V3_PROJECT_ID}-frames.png"
    frame_board(session_dir, board_path, frame_count, overwrite=args.overwrite)
    blocks_board_path = captures_dir / f"{V3_PROJECT_ID}-blocks.png"
    block_board(session_dir, block_info, blocks_board_path, overwrite=args.overwrite)
    video_probe = probe(video_path)
    audio_probe = probe(mix_path)
    report = {
        "project": V3_PROJECT_ID,
        "video": str(video_path),
        "manifest": str(manifest_path),
        "timeline": str(timeline_path),
        "voice_wav": str(voice_path),
        "mix_wav": str(mix_path),
        "frames": str(session_dir),
        "frame_board": str(board_path),
        "blocks_board": str(blocks_board_path),
        "duration_ms": block_info["duration_ms"],
        "blocks": block_info["blocks"],
        "host_text": {"intro": INTRO_TEXT, "outro": OUTRO_TEXT},
        "host_synthesis": {"intro": intro_synthesis, "outro": outro_synthesis},
        "story_source": {"manifest": str(V1_MANIFEST), "duration_ms": story_manifest["duration_ms"], "segment_count": len(story_manifest["segments"])},
        "capture_fps": CAPTURE_FPS,
        "output_fps": OUTPUT_FPS,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "music": MUSIC.name,
        "music_origin": "owner-provided Suno generation; publication rights pending plan/terms confirmation",
        "audio_probe": audio_probe,
        "video_probe": video_probe,
        "timing_source": "measured_host_and_story_wav_segments_plus_explicit_editorial_pauses",
        "word_phoneme_viseme_timing": "unavailable",
        "state": "completed_pending_human_audio_visual_review",
    }
    _json(PROJECT_ROOT / "reports" / "pilot-v3-result.json", report)
    (PROJECT_ROOT / "reports" / "technical-report.md").write_text(
        "# Topazioverse Book 1 — Piloto V3\n\n"
        "Santa V5 atua como anfitrião consciente do público. A história literária foi preservada e recebeu apenas blocos editoriais externos medidos separadamente.\n\n"
        f"- Intro: `{block_info['intro_duration_ms']} ms`; transição: `{EDITORIAL_TRANSITION_MS} ms`.\n"
        f"- História V2 reutilizada: `{story_manifest['duration_ms']} ms`, `{len(story_manifest['segments'])}` segmentos, sem nova síntese.\n"
        f"- Outro: `{block_info['outro_duration_ms']} ms`; duração total: `{block_info['duration_ms']} ms`.\n"
        f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; boca do Santa usa RMS.\n"
        f"- Música: `{MUSIC.name}`; 0.06 sob host, 0.11 durante a história, crescimento suave no outro, com ducking sidechain.\n"
        f"- FFprobe vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n"
        f"- FFprobe mix: `{json.dumps(audio_probe, ensure_ascii=False, sort_keys=True)}`\n"
        "- Não existem timestamps de palavras, fonemas ou visemas; legendas usam apenas intervalos de segmentos WAV medidos.\n"
        "- Direitos de publicação da faixa fornecida pelo proprietário/Suno ainda dependem da confirmação do plano/termos.\n"
        "- Revisão humana de inteligibilidade, equilíbrio musical e qualidade artística permanece obrigatória.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
