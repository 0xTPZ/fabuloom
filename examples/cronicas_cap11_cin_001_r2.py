"""Create the Chapter 11 R2 transition revision without resynthesis or recapture.

R1 component videos and measured Kokoro WAVs are immutable inputs.  R2 adds
editorial pauses, deterministic crystal/page transition clips, shifted
manifests/SRT, a sample-accurate voice/effects timeline, and separate masters.
"""

from __future__ import annotations

from array import array
import copy
from datetime import datetime, timezone
import json
import math
import random
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "examples"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cronicas_cap11_cin_001 import (  # noqa: E402
    EXPORT_ROOT,
    FPS,
    HORIZONTAL,
    VERTICAL,
    board,
    make_music_loop,
    measure_audio,
    mix_audio,
    probe,
    run,
    validate_video,
    write_json,
    write_srt,
    write_text,
)


R1_ROOT = EXPORT_ROOT / "cronicas-book1-capitulo11-cinematic-v1"
R2_ROOT = EXPORT_ROOT / "cronicas-book1-capitulo11-cinematic-r2"
R1_FULL = R1_ROOT / "manifest" / "chapter11-full.json"
R1_STORY = R1_ROOT / "manifest" / "chapter11-story.json"
R1_VOICE = R1_ROOT / "audio" / "chapter11-full-voice.wav"
R1_EFFECTS = R1_ROOT / "audio" / "chapter11-effects-bed.wav"
R1_MUSIC = R1_ROOT / "audio" / "alba-loop.wav"
MUSIC_SOURCE = Path(r"E:\Fabuloom\workspace\inputs\music\book1\Alba Quando a Luz Rasga o Céu.mp3")

GAP_AFTER_HOST_MS = 1_000
GAP_BEFORE_OUTRO_MS = 1_200
TOTAL_GAPS_MS = GAP_AFTER_HOST_MS + GAP_BEFORE_OUTRO_MS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def status(stage: str, *, state: str = "RUNNING", next_action: str = "", details: dict | None = None) -> None:
    path = R2_ROOT / "BATCH-STATUS.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    payload.update({"mission": "CRONICAS-CAP11-CIN-001-R2", "state": state, "stage": stage, "next_action": next_action, "updated_at": now_iso()})
    if details:
        payload.update(details)
    write_json(path, payload)
    print(f"[CAP11-R2] etapa={stage} estado={state} próxima={next_action}", flush=True)


def block(manifest: dict, block_type: str) -> dict:
    return next(item for item in manifest["metadata"]["editorial_blocks"] if item["type"] == block_type)


def shifted_manifest(r1: dict) -> tuple[dict, dict, dict]:
    intro = block(r1, "HOST_INTRO")
    story = block(r1, "STORY_CHAPTER")
    outro = block(r1, "HOST_OUTRO")
    shifts = {"HOST_INTRO": 0, "STORY_CHAPTER": GAP_AFTER_HOST_MS, "HOST_OUTRO": TOTAL_GAPS_MS}
    full = copy.deepcopy(r1)
    full["id"] = "topazio-book1-capitulo11-cinematic-r2"
    full["timeline_id"] = "topazio-book1-capitulo11-cinematic-r2-timeline"
    full["duration_ms"] = int(r1["duration_ms"]) + TOTAL_GAPS_MS
    full["metadata"] = dict(full["metadata"])
    full["metadata"].update({
        "revision": "R2",
        "source_manifest": "../cronicas-book1-capitulo11-cinematic-v1/manifest/chapter11-full.json",
        "editorial_transition_policy": "measured pauses with magical page/crystal dissolves",
        "editorial_gaps_ms": {"after_host_intro": GAP_AFTER_HOST_MS, "before_host_outro": GAP_BEFORE_OUTRO_MS},
        "audio_policy": "reuse measured Kokoro WAVs; no resynthesis",
    })
    for segment in full["segments"]:
        shift = shifts[str(segment["metadata"]["editorial_block"])]
        segment["start_ms"] = int(segment["start_ms"]) + shift
        segment["end_ms"] = int(segment["end_ms"]) + shift
    full["metadata"]["editorial_blocks"] = [
        {**intro, "start_ms": int(intro["start_ms"]), "end_ms": int(intro["end_ms"])},
        {**story, "start_ms": int(story["start_ms"]) + GAP_AFTER_HOST_MS, "end_ms": int(story["end_ms"]) + GAP_AFTER_HOST_MS},
        {**outro, "start_ms": int(outro["start_ms"]) + TOTAL_GAPS_MS, "end_ms": int(outro["end_ms"]) + TOTAL_GAPS_MS},
    ]
    story_manifest = json.loads(R1_STORY.read_text(encoding="utf-8"))
    story_manifest["id"] = "topazio-book1-capitulo11-cinematic-r2-story"
    story_manifest["timeline_id"] = "topazio-book1-capitulo11-cinematic-r2-story-timeline"
    story_manifest["metadata"] = dict(story_manifest.get("metadata", {}))
    story_manifest["metadata"].update({"revision": "R2", "source_manifest": "../cronicas-book1-capitulo11-cinematic-v1/manifest/chapter11-story.json"})
    transitions = {
        "transition_1": {"id": "host-to-story-crystal-page", "start_ms": int(intro["end_ms"]), "end_ms": int(intro["end_ms"]) + GAP_AFTER_HOST_MS, "duration_ms": GAP_AFTER_HOST_MS, "kind": "magical_page_crystal_dissolve", "audio": "Alba continues; subtle crystal/page cue"},
        "transition_2": {"id": "story-to-host-crystal-page", "start_ms": int(story["end_ms"]) + GAP_AFTER_HOST_MS, "end_ms": int(story["end_ms"]) + TOTAL_GAPS_MS, "duration_ms": GAP_BEFORE_OUTRO_MS, "kind": "magical_page_crystal_dissolve", "audio": "Alba continues; subtle crystal/page cue"},
    }
    timing = {"intro_end_ms": int(intro["end_ms"]), "story_start_ms": int(story["start_ms"]) + GAP_AFTER_HOST_MS, "story_end_ms": int(story["end_ms"]) + GAP_AFTER_HOST_MS, "outro_start_ms": int(outro["start_ms"]) + TOTAL_GAPS_MS, "duration_ms": full["duration_ms"], "transitions": transitions}
    full["metadata"]["transitions"] = list(transitions.values())
    return full, story_manifest, timing


def extract_rgb(path: Path, width: int, height: int, *, last: bool) -> bytes:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    args += ["-sseof", "-0.08"] if last else ["-ss", "0"]
    args += ["-i", str(path), "-frames:v", "1", "-vf", f"scale={width}:{height}:flags=lanczos,format=rgb24", "-f", "rawvideo", "pipe:1"]
    result = subprocess.run(args, check=True, capture_output=True)
    expected = width * height * 3
    if len(result.stdout) != expected:
        raise RuntimeError(f"unexpected RGB frame size for {path}: {len(result.stdout)} != {expected}")
    return result.stdout


def paint_glow(buffer: bytearray, width: int, height: int, cx: float, cy: float, radius: float, color: tuple[int, int, int], alpha: float) -> None:
    left = max(0, int(cx - radius)); right = min(width - 1, int(cx + radius))
    top = max(0, int(cy - radius)); bottom = min(height - 1, int(cy + radius))
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            distance = math.hypot(x - cx, y - cy)
            if distance >= radius:
                continue
            strength = alpha * (1.0 - distance / radius) ** 2
            offset = (y * width + x) * 3
            for channel in range(3):
                buffer[offset + channel] = min(255, round(buffer[offset + channel] * (1 - strength) + color[channel] * strength))


def transition_frame(old: bytes, new: bytes, width: int, height: int, progress: float, particles: list[dict[str, float]]) -> bytes:
    eased = progress * progress * (3 - 2 * progress)
    frame = bytearray(len(old))
    for offset in range(0, len(frame), 3):
        frame[offset] = round(old[offset] * (1 - eased) + new[offset] * eased)
        frame[offset + 1] = round(old[offset + 1] * (1 - eased) + new[offset + 1] * eased)
        frame[offset + 2] = round(old[offset + 2] * (1 - eased) + new[offset + 2] * eased)
    sweep = (progress * 1.25 - 0.15) * width
    for y in range(height):
        x = int(sweep + (y / max(1, height - 1) - 0.5) * width * 0.12)
        for xx in range(max(0, x - 3), min(width, x + 4)):
            offset = (y * width + xx) * 3
            strength = 0.20 * math.sin(math.pi * progress)
            frame[offset] = min(255, round(frame[offset] * (1 - strength) + 248 * strength))
            frame[offset + 1] = min(255, round(frame[offset + 1] * (1 - strength) + 213 * strength))
            frame[offset + 2] = min(255, round(frame[offset + 2] * (1 - strength) + 108 * strength))
    for particle in particles:
        x = particle["x"] + particle["vx"] * (progress - 0.5) * width
        y = particle["y"] + particle["vy"] * (progress - 0.5) * height
        life = (progress + particle["phase"]) % 1.0
        alpha = 0.42 * math.sin(math.pi * life) * math.sin(math.pi * progress)
        if alpha > 0.001:
            paint_glow(frame, width, height, x, y, particle["radius"], particle["color"], alpha)
    return bytes(frame)


def make_transition_frames(first: Path, second: Path, frames_dir: Path, dimensions: tuple[int, int], duration_ms: int, seed: int) -> int:
    if list(frames_dir.glob("*.ppm")):
        return len(list(frames_dir.glob("*.ppm")))
    width, height = dimensions
    sample_width = 480 if width >= height else 270
    sample_height = 270 if width >= height else 480
    old = extract_rgb(first, sample_width, sample_height, last=True)
    new = extract_rgb(second, sample_width, sample_height, last=False)
    rng = random.Random(seed)
    particles = [{"x": rng.random() * sample_width, "y": rng.random() * sample_height, "vx": rng.uniform(-0.28, 0.28), "vy": rng.uniform(-0.35, 0.35), "radius": rng.uniform(1.5, 4.5), "phase": rng.random(), "color": rng.choice([(91, 205, 255), (255, 216, 115), (237, 247, 255)])} for _ in range(34)]
    count = max(1, round(duration_ms * FPS / 1000))
    frames_dir.mkdir(parents=True, exist_ok=True)
    header = f"P6\n{sample_width} {sample_height}\n255\n".encode("ascii")
    for index in range(count):
        progress = (index + 0.5) / count
        target = frames_dir / f"{index:06d}.ppm"
        target.write_bytes(header + transition_frame(old, new, sample_width, sample_height, progress, particles))
    return count


def encode_transition(frames_dir: Path, output: Path, dimensions: tuple[int, int], frame_count: int) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    output.unlink(missing_ok=True)
    width, height = dimensions
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "%06d.ppm"), "-frames:v", str(frame_count), "-vf", f"scale={width}:{height}:flags=lanczos,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(FPS), str(output)])


def concat_silent(parts: list[Path], output: Path, dimensions: tuple[int, int]) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    output.unlink(missing_ok=True)
    list_file = output.with_suffix(".concat.txt")
    lines = [f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in parts]
    write_text(list_file, "\n".join(lines) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-an", "-movflags", "+faststart", str(output)])
    except subprocess.CalledProcessError:
        output.unlink(missing_ok=True)
        width, height = dimensions
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-vf", f"scale={width}:{height},format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "18", "-r", str(FPS), str(output)])


def insert_silences(source: Path, output: Path, insertions: list[tuple[int, int]]) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    with wave.open(str(source), "rb") as wav:
        params = wav.getparams()
        raw = wav.readframes(wav.getnframes())
    frame_width = params.nchannels * params.sampwidth
    pieces = bytearray()
    cursor = 0
    for cut_ms, gap_ms in sorted(insertions):
        cut_frame = min(params.nframes, round(cut_ms * params.framerate / 1000))
        start_byte = cursor * frame_width
        end_byte = cut_frame * frame_width
        pieces.extend(raw[start_byte:end_byte])
        pieces.extend(b"\x00" * (round(gap_ms * params.framerate / 1000) * frame_width))
        cursor = cut_frame
    pieces.extend(raw[cursor * frame_width:])
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(bytes(pieces))


def add_transition_sfx(source: Path, output: Path, transition_starts_ms: list[int]) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    with wave.open(str(source), "rb") as wav:
        params = wav.getparams()
        samples = array("h")
        samples.frombytes(wav.readframes(wav.getnframes()))
    rate = params.framerate
    channels = params.nchannels
    for start_ms in transition_starts_ms:
        start = round(start_ms * rate / 1000) * channels
        length = round(0.9 * rate)
        for frame in range(length):
            index = start + frame * channels
            if index >= len(samples):
                break
            age = frame / rate
            envelope = math.exp(-3.5 * age) * min(1.0, age * 24.0)
            value = 0.045 * envelope * (math.sin(2 * math.pi * 660 * age) + 0.55 * math.sin(2 * math.pi * 990 * age))
            sample = max(-32767, min(32767, round(value * 32767)))
            for channel in range(channels):
                samples[index + channel] = max(-32767, min(32767, samples[index + channel] + sample))
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(samples.tobytes())


def main() -> int:
    started = __import__("time").perf_counter()
    R2_ROOT.mkdir(parents=True, exist_ok=True)
    status("PREFLIGHT", next_action="verificar R1, componentes e manifestos")
    if not R1_FULL.is_file() or not R1_VOICE.is_file() or not R1_EFFECTS.is_file() or not MUSIC_SOURCE.is_file():
        raise FileNotFoundError("R1 manifests/audio or Alba source missing")
    r1_full = json.loads(R1_FULL.read_text(encoding="utf-8"))
    r1_story = json.loads(R1_STORY.read_text(encoding="utf-8"))
    full, story_manifest, timing = shifted_manifest(r1_full)
    write_json(R2_ROOT / "manifest" / "chapter11-full-r2.json", full)
    write_json(R2_ROOT / "manifest" / "chapter11-story-r2.json", story_manifest)
    write_json(R2_ROOT / "manifest" / "source-r1-reference.json", {"root": str(R1_ROOT), "duration_ms": r1_full["duration_ms"], "transitions_added_ms": TOTAL_GAPS_MS})
    write_srt(full, R2_ROOT / "subtitles" / "chapter11-r2.srt")
    write_json(R2_ROOT / "timelines" / "chapter11-r2.json", {"format": "fabuloom.cronicas-cap11-cinematic/0.2", "revision": "R2", "source_timeline": str(R1_ROOT / "timelines" / "chapter11-master.json"), "editorial_blocks": full["metadata"]["editorial_blocks"], "transitions": timing["transitions"], "audio": {"voice": "reused measured Kokoro pm_santa", "music": "Alba unchanged speed/pitch", "ducking": "sidechain voice-priority"}, "recapture": False})
    status("MANIFEST_R2_OK", next_action="inserir pausas sample-precisas e cues discretos")
    r2_voice = R2_ROOT / "audio" / "chapter11-r2-full-voice.wav"
    insert_silences(R1_VOICE, r2_voice, [(block(r1_full, "HOST_INTRO")["end_ms"], GAP_AFTER_HOST_MS), (block(r1_full, "STORY_CHAPTER")["end_ms"], GAP_BEFORE_OUTRO_MS)])
    r2_effects_base = R2_ROOT / "audio" / "chapter11-r2-effects-base.wav"
    insert_silences(R1_EFFECTS, r2_effects_base, [(block(r1_full, "HOST_INTRO")["end_ms"], GAP_AFTER_HOST_MS), (block(r1_full, "STORY_CHAPTER")["end_ms"], GAP_BEFORE_OUTRO_MS)])
    r2_effects = R2_ROOT / "audio" / "chapter11-r2-effects-bed.wav"
    add_transition_sfx(r2_effects_base, r2_effects, [timing["transitions"]["transition_1"]["start_ms"], timing["transitions"]["transition_2"]["start_ms"]])
    r2_music = R2_ROOT / "audio" / "alba-r2-loop.wav"
    make_music_loop(MUSIC_SOURCE, r2_music, full["duration_ms"])
    r2_mix = R2_ROOT / "audio" / "chapter11-r2-mix.wav"
    mix_audio(r2_voice, r2_music, r2_effects, r2_mix, full["duration_ms"])
    status("AUDIO_R2_OK", next_action="gerar transições visuais a partir dos componentes R1")
    validations = {}
    boards = {}
    for orientation, dimensions in (("horizontal", HORIZONTAL), ("vertical", VERTICAL)):
        video_root = R1_ROOT / "videos"
        if orientation == "horizontal":
            parts = [video_root / "fabuloom-intro-horizontal.mp4", video_root / "host-opening-horizontal.mp4", video_root / "narrative-horizontal-video.mp4", video_root / "host-closing-horizontal.mp4"]
        else:
            parts = [video_root / "fabuloom-intro-vertical.mp4", video_root / "host-opening-vertical.mp4", video_root / "narrative-vertical-video.mp4", video_root / "host-closing-vertical.mp4"]
        if not all(path.is_file() for path in parts):
            raise FileNotFoundError(f"missing R1 component for {orientation}")
        transition_root = R2_ROOT / "transitions" / orientation
        t1_frames = make_transition_frames(parts[1], parts[2], transition_root / "host-to-story", dimensions, GAP_AFTER_HOST_MS, 1101 if orientation == "horizontal" else 1102)
        t2_frames = make_transition_frames(parts[2], parts[3], transition_root / "story-to-host", dimensions, GAP_BEFORE_OUTRO_MS, 1201 if orientation == "horizontal" else 1202)
        t1 = R2_ROOT / "videos" / f"transition-host-to-story-{orientation}.mp4"
        t2 = R2_ROOT / "videos" / f"transition-story-to-host-{orientation}.mp4"
        encode_transition(transition_root / "host-to-story", t1, dimensions, t1_frames)
        encode_transition(transition_root / "story-to-host", t2, dimensions, t2_frames)
        picture = R2_ROOT / "videos" / f"chapter11-picture-{orientation}-r2.mp4"
        concat_silent([parts[0], parts[1], t1, parts[2], t2, parts[3]], picture, dimensions)
        final = R2_ROOT / "videos" / f"cronicas-capitulo11-o-eco-que-nao-morre-{orientation}-r2.mp4"
        from cronicas_cap11_cin_001 import mux_final
        mux_final(picture, r2_mix, final)
        validations[orientation] = {**validate_video(final, dimensions), "audio": measure_audio(r2_mix)}
        transition_times = [timing["transitions"]["transition_1"]["start_ms"] / 1000, (timing["transitions"]["transition_1"]["start_ms"] + GAP_AFTER_HOST_MS / 2) / 1000, timing["transitions"]["transition_1"]["end_ms"] / 1000, timing["transitions"]["transition_2"]["start_ms"] / 1000, (timing["transitions"]["transition_2"]["start_ms"] + GAP_BEFORE_OUTRO_MS / 2) / 1000, timing["transitions"]["transition_2"]["end_ms"] / 1000]
        board_path = R2_ROOT / "boards" / f"chapter11-transitions-{orientation}-r2.png"
        board(final, transition_times, board_path, dimensions)
        boards[orientation] = str(board_path)
    report = {"mission": "CRONICAS-CAP11-CIN-001-R2", "base_revision": str(R1_ROOT), "source_manifest": str(R1_FULL), "voice": {"provider": "kokoro", "voice_id": "pm_santa", "language": "pt-BR", "resynthesis": False}, "music": {"source": str(MUSIC_SOURCE), "speed_pitch_changed": False, "ducking": "sidechain voice-priority", "rights": "pending owner confirmation"}, "pauses": {"after_host_intro_ms": GAP_AFTER_HOST_MS, "before_host_outro_ms": GAP_BEFORE_OUTRO_MS}, "transitions": timing["transitions"], "duration_ms": full["duration_ms"], "narrative_capture_reused": True, "r1_preserved": True, "validations": validations, "boards": boards, "audio_policy": "external cinematic video audio remains excluded", "human_audition": "pending", "processing_seconds": round(__import__("time").perf_counter() - started, 3)}
    write_json(R2_ROOT / "reports" / "chapter11-r2-technical-report.json", report)
    write_text(R2_ROOT / "reports" / "chapter11-r2-technical-report.md", "\n".join([
        "# Crônicas de Topázio — Capítulo 11 — Revisão R2",
        "",
        "- Revisão pontual sobre R1; os WAVs Kokoro e a captura Canvas foram reutilizados.",
        f"- Pausa apresentação → narrativa: {GAP_AFTER_HOST_MS} ms.",
        f"- Pausa narrativa → encerramento: {GAP_BEFORE_OUTRO_MS} ms.",
        f"- Duração do manifesto R2: {full['duration_ms']} ms; música Alba contínua e sem alteração de velocidade/tom.",
        "- Transições: dissolução de página/energia cristalina com partículas determinísticas e blends dos frames adjacentes.",
        "- Áudio dos clipes cinematográficos externos continua excluído; fala permanece exclusivamente Kokoro pm_santa.",
        "- FFprobe, decode FFmpeg e blackdetect foram executados nos dois masters.",
        "- Audição humana e aprovação artística continuam pendentes.",
        "",
    ]))
    status("QA_OK", state="DONE", next_action="aguardar audição e aprovação artística", details={"duration_ms": full["duration_ms"], "validations": validations, "r1_preserved": True})
    print(json.dumps({"output_root": str(R2_ROOT), "horizontal": validations["horizontal"]["path"], "vertical": validations["vertical"]["path"], "duration_ms": full["duration_ms"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

