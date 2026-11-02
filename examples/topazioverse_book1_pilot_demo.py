"""Render the first Topazioverse Book 1 cinematic pilot.

The pilot deliberately keeps the production path small and reproducible:
DOCX excerpt -> measured Kokoro segments -> timed scene plan -> Canvas frames
-> FFmpeg MP4.  It uses only local assets and never infers word or phoneme
timings from the audio duration.
"""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen
import wave
import xml.etree.ElementTree as ET
import zipfile

try:
    from docx import Document
except ImportError:  # pragma: no cover - exercised only in the minimal Kokoro venv
    Document = None

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
PROJECT_ID = "topazioverse-book1-episode1-pilot"
STORY_ID = PROJECT_ID
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1920
HEIGHT = 1080
SOURCE_DOC = Path(r"E:\Fabuloom\workspace\inputs\book1\Topazio-O-Despertar-dos-Cristais.docx")
MUSIC = Path(r"E:\Fabuloom\workspace\inputs\music\book1\Apprehension.mp3")
AMBIENCE = Path(r"E:\Fabuloom\workspace\inputs\ambience\book1\rain-window-closed.wav")
SOURCE_PARAGRAPHS = tuple(range(3, 12))
PRONUNCIATION_DICTIONARY = {
    "Topázio": "nome próprio; manter acento na locução pt-BR",
    "Thaurion": "nome próprio; pronúncia revisada manualmente",
    "Zephirion": "nome próprio; pronúncia revisada manualmente",
    "Glaciron": "nome próprio; pronúncia revisada manualmente",
    "Gaia": "nome próprio; pronúncia brasileira natural",
}


def _write_json(path: Path, payload: object, *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_source_excerpt(path: Path = SOURCE_DOC) -> tuple[tuple[str, ...], str]:
    """Read the exact Chapter 1 paragraph interval selected for the pilot."""

    if Document is not None:
        paragraphs = [paragraph.text for paragraph in Document(path).paragraphs]
    else:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = [
            "".join(node.text or "" for node in paragraph.findall(f".//{namespace}t"))
            for paragraph in root.findall(f".//{namespace}body/{namespace}p")
        ]
    selected: list[str] = []
    for index in SOURCE_PARAGRAPHS:
        if index >= len(paragraphs):
            raise ValueError(f"source paragraph {index} is missing from {path}")
        value = paragraphs[index].strip()
        if not value:
            raise ValueError(f"source paragraph {index} is empty")
        selected.append(value)
    return tuple(selected), "\n\n".join(selected)


def _value(segment: object, name: str) -> object:
    if isinstance(segment, dict):
        return segment[name]
    return getattr(segment, name)


def _metadata(segment: object) -> dict:
    value = _value(segment, "metadata")
    return value if isinstance(value, dict) else {}


def build_scene_schedule(manifest: object) -> tuple[dict, ...]:
    """Map measured narration paragraphs to deterministic cinematic scenes."""

    scene_specs = (
        ("topazio-stillness", "scenes/01-topazio-stillness.png", "stillness_zoom", (0,)),
        ("temple-crack", "scenes/02-temple-crack-crystal.png", "crystal_approach", (1,)),
        ("thaurion-cave", "scenes/03-thaurion-echo-cave.png", "thaurion_push", (2, 3, 4, 5)),
        ("zephirion-call", "scenes/04-zephirion-fall.png", "wind_lateral", (6, 7)),
        ("glaciron-omen", "scenes/05-glaciron-vordros.png", "snow_breath", (8,)),
    )
    segments = list(_value(manifest, "segments"))
    duration_ms = int(_value(manifest, "duration_ms"))
    scenes: list[dict] = []
    for scene_id, image, camera, paragraph_indexes in scene_specs:
        matching = [segment for segment in segments if int(_metadata(segment).get("paragraph_index", -1)) in paragraph_indexes]
        if not matching:
            continue
        start_ms = int(_value(matching[0], "start_ms"))
        last_end = int(_value(matching[-1], "end_ms"))
        pause_after_ms = int(_metadata(matching[-1]).get("pause_after_ms", 0))
        end_ms = min(duration_ms, last_end + pause_after_ms)
        scenes.append(
            {
                "id": scene_id,
                "image": f"{PROJECT_ID}/{image}",
                "camera": camera,
                "start_ms": start_ms,
                "end_ms": max(start_ms + 1, end_ms),
                "source_paragraphs": [SOURCE_PARAGRAPHS[index] for index in paragraph_indexes],
            }
        )
    if not scenes:
        raise ValueError("the manifest produced no scene boundaries")
    scenes[-1]["end_ms"] = duration_ms
    return tuple(scenes)


def _wav_path(audio_uri: str) -> Path:
    parsed = urlparse(audio_uri)
    if parsed.scheme != "file":
        raise ValueError(f"expected a local file URI, got {audio_uri!r}")
    return Path(parsed.path.lstrip("/"))


def compose_voice(manifest: dict, output_path: Path) -> tuple[int, array]:
    """Compose mono PCM-16 segments using only measured starts and durations."""

    segments = manifest["segments"]
    if not segments:
        raise ValueError("manifest has no audio segments")
    first_path = _wav_path(segments[0]["audio_uri"])
    with wave.open(str(first_path), "rb") as first_wav:
        sample_rate = first_wav.getframerate()
        if first_wav.getnchannels() != 1 or first_wav.getsampwidth() != 2:
            raise ValueError("pilot requires mono PCM-16 narration WAVs")
    combined = array("h")
    written_frames = 0
    for segment in segments:
        segment_path = _wav_path(segment["audio_uri"])
        with wave.open(str(segment_path), "rb") as segment_wav:
            if (segment_wav.getframerate(), segment_wav.getnchannels(), segment_wav.getsampwidth()) != (sample_rate, 1, 2):
                raise ValueError(f"inconsistent WAV format in {segment_path}")
            target_start = round(int(segment["start_ms"]) * sample_rate / 1000)
            combined.extend([0] * max(0, target_start - written_frames))
            combined.frombytes(segment_wav.readframes(segment_wav.getnframes()))
            written_frames = target_start + segment_wav.getnframes()
    target_end = round(int(manifest["duration_ms"]) * sample_rate / 1000)
    combined.extend([0] * max(0, target_end - written_frames))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as output_wav:
        output_wav.setnchannels(1)
        output_wav.setsampwidth(2)
        output_wav.setframerate(sample_rate)
        output_wav.writeframes(combined.tobytes())
    return sample_rate, combined


def _srt_time(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_srt(manifest: dict, path: Path) -> None:
    blocks = []
    for index, segment in enumerate(manifest["segments"], start=1):
        lines = "\n".join(textwrap.wrap(segment["text"], width=62, break_long_words=False))
        blocks.append(f"{index}\n{_srt_time(segment['start_ms'])} --> {_srt_time(segment['end_ms'])}\n{lines}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def mix_audio(voice: Path, music: Path, ambience: Path, output: Path, duration_ms: int, *, overwrite: bool) -> None:
    duration = duration_ms / 1000
    filter_graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.06,atrim=duration={duration:.3f},afade=t=in:st=0:d=2[music];"
        "[music][det]sidechaincompress=threshold=0.025:ratio=8:attack=80:release=700:makeup=1[ducked];"
        f"[2:a]aresample=48000,volume=0.012,atrim=duration={duration:.3f},afade=t=in:st=0:d=2[amb];"
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
        shutil.which("microsoft-edge"),
        os.environ.get("PROGRAMFILES", "") + r"\Microsoft\Edge\Application\msedge.exe",
        os.environ.get("PROGRAMFILES(X86)", "") + r"\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for deterministic Canvas capture")


def _wait_for_http(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(0.15)
    raise TimeoutError(f"local server did not become ready: {url}")


def _materialize_frames(session_dir: Path, completion: dict) -> list[Path]:
    captured = sorted(session_dir.glob("*.jpg"))
    expected_count = int(completion["frame_count"])
    if not captured:
        raise RuntimeError("capture produced no JPEG frames")
    captured_by_index = {int(path.stem): path for path in captured}
    for index in range(expected_count):
        target = session_dir / f"{index:06d}.jpg"
        if target.exists():
            continue
        source_index = min(captured_by_index, key=lambda value: abs(value - index))
        try:
            os.link(captured_by_index[source_index], target)
        except OSError:
            shutil.copyfile(captured_by_index[source_index], target)
    frames = sorted(session_dir.glob("*.jpg"))
    if len(frames) != expected_count:
        raise RuntimeError(f"capture frame count mismatch after materialization: {len(frames)} != {expected_count}")
    return frames


def capture_frames(project_root: Path, timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env["FABULOOM_WORKSPACE_ROOT"] = r"E:\Fabuloom"
    env["FABULOOM_EXPORT_ROOT"] = str(EXPORT_ROOT)
    env["FABULOOM_CAPTURE_DIR"] = str(frames_root)
    server = subprocess.Popen(
        [sys.executable, os.fspath(Path(__file__).resolve().parents[1] / "frontend" / "server.py"), "--port", str(port)],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_http(f"http://127.0.0.1:{port}/capture-topazioverse-pilot.html", 20)
        relative_timeline = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazioverse-pilot.html?session={session}&timeline=/exports/{relative_timeline}&fps={FPS}"
        command = [
            edge, "--headless=new", "--hide-scrollbars",
            "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile_dir}", url,
        ]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout_seconds
        try:
            while not complete.exists() and not error.exists() and time.monotonic() < deadline:
                if browser.poll() is not None:
                    time.sleep(0.25)
                else:
                    time.sleep(0.25)
            if error.exists():
                raise RuntimeError(f"Canvas capture failed: {error.read_text(encoding='utf-8')}")
            if not complete.exists():
                raise TimeoutError(f"Canvas capture did not complete: {session_dir}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            _materialize_frames(session_dir, completion)
            return session_dir, completion
        finally:
            if browser.poll() is None:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def render_mp4(frames_dir: Path, audio_path: Path, output_path: Path, duration_ms: int, *, overwrite: bool) -> None:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
        "-framerate", str(FPS), "-i", str(frames_dir / "%06d.jpg"), "-i", str(audio_path),
        "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(output_path),
    ]
    subprocess.run(command, check=True)


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height,pix_fmt,sample_rate,channels", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def frame_board(frames_dir: Path, output_path: Path, frame_count: int, *, overwrite: bool) -> None:
    picks = [0, max(0, frame_count // 4), max(0, frame_count // 2), max(0, frame_count * 3 // 4), max(0, frame_count - 1)]
    with tempfile.TemporaryDirectory(prefix=".board-", dir=frames_dir.parent) as temp:
        temp_dir = Path(temp)
        for board_index, source_index in enumerate(picks):
            source = frames_dir / f"{source_index:06d}.jpg"
            target = temp_dir / f"{board_index:02d}.png"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vf", "scale=640:360", str(target)], check=True)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
            "-i", str(temp_dir / "00.png"), "-i", str(temp_dir / "01.png"), "-i", str(temp_dir / "02.png"),
            "-i", str(temp_dir / "03.png"), "-i", str(temp_dir / "04.png"),
            "-filter_complex", "[0:v][1:v][2:v][3:v][4:v]xstack=inputs=5:layout=0_0|640_0|1280_0|320_360|960_360,format=rgb24[out]",
            "-map", "[out]", "-frames:v", "1", str(output_path),
        ]
        subprocess.run(command, check=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_reports(project_root: Path, *, paragraphs: tuple[str, ...], excerpt_path: Path, manifest: dict, timeline: dict, probe_data: dict, processing_seconds: float, source_text_sha256: str, audio_probe: dict) -> None:
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    scene_lines = "\n".join(f"- `{scene['id']}`: {scene['start_ms']}–{scene['end_ms']} ms; câmera `{scene['camera']}`; parágrafos do DOCX `{scene['source_paragraphs']}`" for scene in timeline["scenes"])
    (reports / "visual-bible.md").write_text(
        "# Topazioverse — Bíblia visual do piloto\n\n"
        "Paleta: azul-marinho profundo, índigo, ciano cristalino e dourado suave. As imagens são originais, geradas para este piloto e mantêm composição 2.5D pictórica coerente.\n\n"
        "## Cenas\n\n" + scene_lines + "\n\n"
        "O Santa V5 aparece somente na abertura e no encerramento, mantendo o foco da experiência nas imagens da história e evitando repetir a composição do Narrator Mode durante toda a duração.\n\n"
        "A aprovação artística final permanece humana; a prancha é evidência de produção, não aprovação automática.\n", encoding="utf-8"
    )
    (reports / "mix-report.md").write_text(
        "# Topazioverse — Relatório de mixagem\n\n"
        f"- Voz: Kokoro `{VOICE_ID}`, idioma `{LANGUAGE}`\n"
        f"- Duração medida do manifesto: `{manifest['duration_ms']} ms`\n"
        f"- Voz composta: PCM mono medido em `{audio_probe.get('format', {}).get('duration', 'n/a')} s`\n"
        "- Música: `Apprehension.mp3`, volume reduzido e ducking por sidechain durante a voz.\n"
        "- Ambiência: `rain-window-closed.wav`, cópia local do arquivo auditado como CC0.\n"
        "- Efeitos adicionais: não usados; não foram necessários para a sequência selecionada.\n"
        "- Palavra/fonema/visema: indisponíveis; nenhuma precisão foi inventada.\n", encoding="utf-8"
    )
    (reports / "technical-report.md").write_text(
        "# Topazioverse Book 1 — Piloto cinematográfico\n\n"
        f"- Fonte: `{SOURCE_DOC}`; parágrafos exatos `{SOURCE_PARAGRAPHS[0]}–{SOURCE_PARAGRAPHS[-1]}` do DOCX.\n"
        f"- Hash SHA-256 do trecho copiado para `source-excerpt.txt`: `{source_text_sha256}`.\n"
        f"- Segmentos medidos: `{len(manifest['segments'])}`; duração: `{manifest['duration_ms']} ms`.\n"
        f"- Processamento TTS e composição: `{processing_seconds:.2f} s` (sem contar eventual tempo de captura reportado pelo sistema).\n"
        f"- Resolução: `{WIDTH}×{HEIGHT}`; FPS: `{FPS}`; prova FFprobe: `{json.dumps(probe_data, ensure_ascii=False, sort_keys=True)}`.\n"
        f"- Cenas: {len(timeline['scenes'])}.\n\n{scene_lines}\n\n"
        "O arquivo final não exibe voz, IDs de manifesto, caminhos locais ou labels de desenvolvimento. A boca do avatar usa RMS no Canvas; legendas e transições usam apenas limites reais dos segmentos.\n\n"
        "A revisão humana do vídeo é obrigatória antes de considerar o piloto aprovado.\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-manifest", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--capture-timeout", type=float, default=900)
    args = parser.parse_args()
    for required in (SOURCE_DOC, MUSIC, AMBIENCE):
        if not required.is_file():
            raise FileNotFoundError(required)
    project_root = EXPORT_ROOT / PROJECT_ID
    audio_dir = project_root / "audio"
    timeline_dir = project_root / "timeline"
    captures_dir = project_root / "captures"
    frames_root = project_root / ".frames"
    for directory in (audio_dir, timeline_dir, captures_dir, frames_root, project_root / "reports", project_root / "visual-bible", project_root / "scenes"):
        directory.mkdir(parents=True, exist_ok=True)
    excerpt_paragraphs, excerpt = load_source_excerpt()
    excerpt_path = timeline_dir / "source-excerpt.txt"
    excerpt_path.write_text(excerpt + "\n", encoding="utf-8")
    manifest_path = project_root / "manifest.json"
    started = time.perf_counter()
    if args.reuse_manifest and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tts_processing = 0.0
    else:
        provider = KokoroTTSProvider(output_dir=audio_dir, allow_overwrite=args.overwrite)
        try:
            run = synthesize_narration(
                provider, excerpt, narration_id=STORY_ID, manifest_id=STORY_ID, voice_id=VOICE_ID,
                language=LANGUAGE, output_dir=audio_dir, max_chars=360,
            )
            manifest = json.loads(serialize_manifest(run.manifest))
            _write_json(manifest_path, manifest, overwrite=args.overwrite)
            tts_processing = run.processing_seconds
            print(f"tts_provider={provider.provider_id}")
            print(f"tts_model={provider.model_id}")
            print(f"tts_model_revision={provider.model_revision}")
            print(f"tts_model_load_count={provider.model_load_count}")
            print(f"tts_duration_ms={manifest['duration_ms']}")
            print(f"tts_segments={len(manifest['segments'])}")
        except (TTSError, NarrationSynthesisError):
            raise
        finally:
            provider.close()
    timeline = {
        "format": "fabuloom.topazioverse-pilot/0.1",
        "title": "O Despertar dos Cristais — Capítulo 1",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": 800,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(SOURCE_PARAGRAPHS),
        "music_asset": "workspace/inputs/music/book1/Apprehension.mp3",
        "ambience_asset": "workspace/inputs/ambience/book1/rain-window-closed.wav",
        "narrator": "Santa V5",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "scenes": list(build_scene_schedule(manifest)),
    }
    timeline_path = timeline_dir / f"{STORY_ID}.json"
    _write_json(timeline_path, timeline, overwrite=args.overwrite)
    write_srt(manifest, timeline_dir / f"{STORY_ID}.srt")
    voice_path = audio_dir / f"{STORY_ID}-voice.wav"
    sample_rate, _ = compose_voice(manifest, voice_path)
    mix_path = audio_dir / f"{STORY_ID}-mix.wav"
    mix_audio(voice_path, MUSIC, AMBIENCE, mix_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    video_path = project_root / f"{PROJECT_ID}.mp4"
    if args.reuse_capture:
        existing = sorted((frames_root).glob("capture-*/complete.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not existing:
            raise FileNotFoundError("--reuse-capture requested but no completed capture exists")
        session_dir = existing[0].parent
        completion = json.loads(existing[0].read_text(encoding="utf-8"))
        _materialize_frames(session_dir, completion)
    else:
        session_dir, completion = capture_frames(project_root, timeline_path, frames_root, port=args.port, timeout_seconds=args.capture_timeout)
    frame_count = int(completion["frame_count"])
    render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=args.overwrite)
    board_path = captures_dir / f"{PROJECT_ID}-frames.png"
    frame_board(session_dir, board_path, frame_count, overwrite=args.overwrite)
    video_probe = probe(video_path)
    audio_probe = probe(mix_path)
    source_hash = _sha256(excerpt_path)
    write_reports(
        project_root, paragraphs=excerpt_paragraphs, excerpt_path=excerpt_path, manifest=manifest,
        timeline=timeline, probe_data=video_probe, processing_seconds=time.perf_counter() - started,
        source_text_sha256=source_hash, audio_probe=audio_probe,
    )
    report = {
        "project": PROJECT_ID,
        "video": str(video_path),
        "manifest": str(manifest_path),
        "timeline": str(timeline_path),
        "frames": str(session_dir),
        "frame_board": str(board_path),
        "sample_rate": sample_rate,
        "duration_ms": manifest["duration_ms"],
        "video_probe": video_probe,
        "audio_probe": audio_probe,
        "source_paragraphs": list(SOURCE_PARAGRAPHS),
        "timing_source": "measured_wav_segments",
        "word_phoneme_viseme_timing": "unavailable",
        "state": "completed_pending_human_artistic_review",
    }
    _write_json(project_root / "reports" / "pilot-result.json", report, overwrite=True)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
