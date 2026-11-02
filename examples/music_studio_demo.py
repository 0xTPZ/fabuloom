"""Create and export the local-first Fabuloom Music Studio V1 project.

The pipeline deliberately treats the owner-supplied music as the source of
truth: FFprobe provides container metadata and FFmpeg-decoded PCM provides the
waveform/RMS envelope. No BPM, beat, or transition timestamps are inferred.
"""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen


STUDIO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(os.environ.get("FABULOOM_WORKSPACE_ROOT", STUDIO_ROOT.parent)).resolve()
EXPORT_ROOT = Path(os.environ.get("FABULOOM_EXPORT_ROOT", WORKSPACE_ROOT / "workspace" / "exports")).resolve()
MUSIC_ROOT = (WORKSPACE_ROOT / "workspace" / "inputs" / "music").resolve()
PROJECT_FORMAT = "fabuloom.music-studio-project/0.1"
CAPTURE_FPS = 5
OUTPUT_FPS = 30
FULL_SIZE = (1920, 1080)
SHORT_SIZE = (1080, 1920)
DEFAULT_ASSET_ROOT = "music-studio/music-studio-v1-o-chamado-do-vazio"


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=False, capture_output=capture_output)


def _safe_relative_music(value: str) -> Path:
    raw = str(value).replace("\\", "/").strip().lstrip("/")
    candidate = (MUSIC_ROOT / raw).resolve()
    try:
        candidate.relative_to(MUSIC_ROOT)
    except ValueError as exc:
        raise ValueError("music asset must stay inside workspace/inputs/music") from exc
    if candidate.suffix.lower() not in {".mp3", ".wav", ".flac", ".m4a", ".ogg"}:
        raise ValueError("unsupported music asset format")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def probe_audio(source: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name,size:stream=index,codec_name,codec_type,sample_rate,channels,channel_layout", "-of", "json", str(source)],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), {})
    duration = float(data.get("format", {}).get("duration") or 0.0)
    return {
        "duration_ms": int(round(duration * 1000)),
        "duration_seconds": round(duration, 6),
        "format_name": data.get("format", {}).get("format_name"),
        "size_bytes": int(data.get("format", {}).get("size") or source.stat().st_size),
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "channel_layout": stream.get("channel_layout"),
    }


def decode_rms(source: Path, *, bars: int = 240) -> tuple[list[float], list[dict]]:
    decoded = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    samples = array("h")
    samples.frombytes(decoded)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return [0.0] * bars, []
    values: list[float] = []
    for index in range(bars):
        start = index * len(samples) // bars
        end = max(start + 1, (index + 1) * len(samples) // bars)
        window = samples[start:end]
        rms = math.sqrt(sum(float(value) * value for value in window) / len(window)) / 32768.0
        values.append(round(min(1.0, rms), 6))
    duration_ms = int(round(len(samples) / 8000 * 1000))
    window_ms = max(1000, round(duration_ms / 24 / 1000) * 1000)
    step_ms = max(1000, window_ms // 4)
    candidates: list[dict] = []
    for start_ms in range(0, max(1, duration_ms - window_ms + 1), step_ms):
        start = start_ms * len(samples) // max(1, duration_ms)
        end = min(len(samples), (start_ms + window_ms) * len(samples) // max(1, duration_ms))
        window = samples[start:max(start + 1, end)]
        rms = math.sqrt(sum(float(value) * value for value in window) / len(window)) / 32768.0
        candidates.append({"start_ms": start_ms, "end_ms": min(duration_ms, start_ms + window_ms), "mean_rms": round(min(1.0, rms), 6), "method": "heuristic_rms_window"})
    candidates.sort(key=lambda item: item["mean_rms"], reverse=True)
    selected: list[dict] = []
    for candidate in candidates:
        if all(candidate["end_ms"] <= item["start_ms"] or candidate["start_ms"] >= item["end_ms"] for item in selected):
            selected.append(candidate)
        if len(selected) == 5:
            break
    selected.sort(key=lambda item: item["start_ms"])
    return values, selected


def analyze_source(source: Path) -> dict:
    metadata = probe_audio(source)
    waveform, candidates = decode_rms(source)
    selected_candidate = max(candidates, key=lambda item: item["mean_rms"], default=None)
    relative = source.relative_to(WORKSPACE_ROOT).as_posix()
    return {
        "format": "fabuloom.music-analysis/0.1",
        "source": {"workspace_relative": relative, "filename": source.name, "sha256": _sha256(source)},
        "metadata": metadata,
        "waveform": {"bars": len(waveform), "values": waveform, "sample_rate_hz": 8000, "method": "ffmpeg_decoded_mono_pcm16_rms"},
        "energy_candidates": candidates,
        "selected_candidate": selected_candidate,
        "timing": {"bpm": "unavailable", "beats": "unavailable", "transitions": "unavailable", "note": "Candidates are RMS windows only; no musical grid is claimed."},
    }


def _project_name_from_source(source: Path) -> str:
    return source.stem.lower().replace(" ", "-").replace("—", "-").replace("_", "-")


def _asset_sources() -> list[tuple[str, Path, str]]:
    scene_root = EXPORT_ROOT / "cronicas-breves" / "cb-001-o-quarto-eco" / "assets" / "scenes"
    names = [
        ("void-entrance", "01-cave-entrance.png", "caverna e entrada"),
        ("crystal-ring", "02-crystal-ring.png", "cristais flutuantes"),
        ("memory-lights", "03-memory-lights.png", "memórias de luz"),
        ("silent-question", "04-silent-question.png", "silêncio dramático"),
        ("fourth-echo", "05-fourth-echo.png", "quarto eco"),
        ("cave-exit", "06-cave-exit.png", "saída e horizonte"),
    ]
    return [(asset_id, scene_root / filename, label) for asset_id, filename, label in names]


def _style(style_id: str) -> dict:
    styles = {
        "topazioverse-living-worlds": {"id": "topazioverse-living-worlds", "label": "Topazioverse Living Worlds", "palette": {"deep": "#060b1c", "mid": "#182c63", "accent": "#7d63ff", "gold": "#e6c77a", "mist": "#b7c8ff"}},
        "obsidian-void": {"id": "obsidian-void", "label": "Obsidian Void", "palette": {"deep": "#05040e", "mid": "#211347", "accent": "#9a64ff", "gold": "#d4b3ff", "mist": "#a9a2d4"}},
        "crystal-dawn": {"id": "crystal-dawn", "label": "Crystal Dawn", "palette": {"deep": "#0b1727", "mid": "#26547b", "accent": "#67d7ff", "gold": "#f1d487", "mist": "#d3f4ff"}},
    }
    return styles.get(style_id, styles["topazioverse-living-worlds"])


def _scene_list(duration_ms: int, *, start_ms: int = 0, end_ms: int | None = None, vertical: bool = False) -> list[dict]:
    end = int(end_ms if end_ms is not None else duration_ms)
    span = max(1, end - start_ms)
    sources = _asset_sources()
    scenes = []
    for index, (asset_id, _source, label) in enumerate(sources):
        scene_start = start_ms + round(index * span / len(sources))
        scene_end = start_ms + round((index + 1) * span / len(sources))
        scenes.append({"id": f"{'short' if vertical else 'full'}-{index + 1:02d}-{asset_id}", "asset_id": asset_id, "label": label, "start_ms": scene_start, "end_ms": scene_end, "camera": {"zoom": round(1.02 + index * 0.012, 4), "pan_x": round((-0.05 + index * 0.02), 4), "pan_y": round((0.02 - index * 0.008), 4)}, "composition": "independent-vertical-framing" if vertical else "horizontal-living-world"})
    return scenes


def create_project(asset: str, style_id: str, short_start_ms: int | None, short_end_ms: int | None, name: str | None) -> tuple[Path, dict]:
    source = _safe_relative_music(asset)
    analysis = analyze_source(source)
    duration_ms = int(analysis["metadata"]["duration_ms"])
    candidates = analysis["energy_candidates"]
    candidate = analysis.get("selected_candidate") or {"start_ms": 0, "end_ms": min(duration_ms, 24000)}
    start = max(0, int(short_start_ms if short_start_ms is not None else candidate["start_ms"]))
    end = min(duration_ms, int(short_end_ms if short_end_ms is not None else candidate["end_ms"]))
    if end <= start:
        raise ValueError("short selection must end after its start")
    if end - start < 15000 or end - start > 30000:
        raise ValueError("short selection must be between 15 and 30 seconds")
    project_id = name or _project_name_from_source(source)
    project_id = "".join(character if character.isalnum() or character in "-_" else "-" for character in project_id.lower()).strip("-") or "music-project"
    project_root = (EXPORT_ROOT / "music-studio" / f"music-studio-v1-{project_id}").resolve()
    project_root.relative_to(EXPORT_ROOT.resolve())
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "audio").mkdir(exist_ok=True)
    (project_root / "assets").mkdir(exist_ok=True)
    (project_root / "videos").mkdir(exist_ok=True)
    (project_root / "previews").mkdir(exist_ok=True)
    (project_root / "captures").mkdir(exist_ok=True)
    (project_root / "reports").mkdir(exist_ok=True)
    source_copy = project_root / "audio" / f"source-music{source.suffix}"
    shutil.copy2(source, source_copy)
    assets = []
    for asset_id, path, label in _asset_sources():
        if not path.is_file():
            raise FileNotFoundError(path)
        target = project_root / "assets" / f"{asset_id}{path.suffix}"
        shutil.copy2(path, target)
        assets.append({"id": asset_id, "path": target.relative_to(project_root).as_posix(), "label": label, "source": "existing approved environmental still from CB-001", "characters": []})
    project = {
        "format": PROJECT_FORMAT,
        "id": project_root.name,
        "asset_root": project_root.relative_to(EXPORT_ROOT).as_posix(),
        "title": "Music Studio · " + source.stem,
        "style": _style(style_id),
        "source": {**analysis["source"], "analysis": analysis["metadata"], "copied_audio": source_copy.relative_to(project_root).as_posix(), "pitch_or_speed_changed": False},
        "analysis": {"waveform": analysis["waveform"], "energy_candidates": analysis["energy_candidates"], "timing": analysis["timing"]},
        "visual_policy": {"mode": "Topazioverse Living Worlds", "narrator": None, "characters": [], "narration": None, "lip_sync": False, "captions": False, "assets_are_environmental_only": True},
        "assets": assets,
        "full": {"width": 1920, "height": 1080, "fps": OUTPUT_FPS, "duration_ms": duration_ms, "audio_start_ms": 0, "audio_end_ms": duration_ms, "scenes": _scene_list(duration_ms)},
        "short": {"width": 1080, "height": 1920, "fps": OUTPUT_FPS, "duration_ms": end - start, "audio_start_ms": start, "audio_end_ms": end, "scenes": _scene_list(end - start, start_ms=0, end_ms=end - start, vertical=True)},
        "short_selection": {"start_ms": start, "end_ms": end, "duration_ms": end - start, "selection_method": "owner_or_highest_rms_candidate", "candidate_method": "heuristic_rms_window"},
        "rights": {"music_origin": "owner-supplied local file; editorially associated with Suno concepts", "commercial_confirmation": "required before publication", "models_or_weights_included": False},
    }
    _json(project_root / "analysis.json", analysis)
    _json(project_root / "project.json", project)
    return project_root, project


def _write_progress(project_root: Path, stage: str, progress: int, **extra: object) -> None:
    _json(project_root / "reports" / "progress.json", {"stage": stage, "progress": progress, **extra})


def _find_edge() -> str:
    for candidate in (shutil.which("msedge"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for deterministic Canvas capture")


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


def _materialize(session_dir: Path, completion: dict) -> int:
    source_count = int(completion["frame_count"])
    source_frames = sorted(session_dir.glob("src-*.jpg"))
    if len(source_frames) != source_count:
        raise RuntimeError(f"source frame count mismatch: {len(source_frames)} != {source_count}")
    duration_ms = int(completion["duration_ms"])
    output_count = max(1, math.ceil(duration_ms * OUTPUT_FPS / 1000))
    for index in range(output_count):
        source_index = min(source_count - 1, round(index * CAPTURE_FPS / OUTPUT_FPS))
        target = session_dir / f"{index:06d}.jpg"
        if not target.exists():
            try:
                os.link(session_dir / f"src-{source_index:06d}.jpg", target)
            except OSError:
                shutil.copyfile(session_dir / f"src-{source_index:06d}.jpg", target)
    return output_count


def capture_frames(project_root: Path, mode: str, frames_root: Path, *, port: int, timeout: float) -> tuple[Path, dict]:
    edge = _find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"music-{mode}-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(WORKSPACE_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT), "FABULOOM_CAPTURE_DIR": str(frames_root)})
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(port)], cwd=str(STUDIO_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        _wait_http(f"http://127.0.0.1:{port}/capture-music-studio.html", 20)
        relative = project_root.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-music-studio.html?session={session}&project=/exports/{relative}/project.json&mode={mode}&fps={CAPTURE_FPS}"
        browser = subprocess.Popen([edge, "--headless=new", "--hide-scrollbars", f"--window-size={1920 if mode == 'full' else 1080},{1080 if mode == 'full' else 1920}", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout
        while not complete.exists() and not error.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        if error.exists():
            raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists():
            raise TimeoutError(session_dir)
        completion = json.loads(complete.read_text(encoding="utf-8"))
        _materialize(session_dir, completion)
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


def render_mp4(frames: Path, audio: Path, output: Path, duration_ms: int, *, start_ms: int = 0, overwrite: bool = False) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-framerate", str(OUTPUT_FPS), "-i", str(frames / "%06d.jpg"), "-ss", f"{start_ms / 1000:.3f}", "-i", str(audio), "-t", f"{duration_ms / 1000:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-frames:v", str(max(1, math.ceil(duration_ms / 1000 * OUTPUT_FPS))), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(OUTPUT_FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)]
    _run(command)


def make_board(frames: Path, duration_ms: int, output: Path, *, vertical: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".music-board-", dir=output.parent) as temp:
        picks = [max(0, min(math.ceil(duration_ms / 1000 * OUTPUT_FPS) - 1, round((duration_ms / 1000 * OUTPUT_FPS - 1) * value))) for value in (0.08, 0.33, 0.58, 0.83)]
        files = []
        for index, frame_index in enumerate(picks):
            source = frames / f"{frame_index:06d}.jpg"
            target = Path(temp) / f"{index:02d}.png"
            width, height = (540, 960) if vertical else (640, 360)
            _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x050814", str(target)])
            files.append(target)
        inputs = [argument for file in files for argument in ("-i", str(file))]
        layout = "|".join(f"{index % 2 * (540 if vertical else 640)}_{index // 2 * (960 if vertical else 360)}" for index in range(len(files)))
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", f"xstack=inputs=4:layout={layout}:fill=black,format=rgb24[out]", "-map", "[out]", "-frames:v", "1", str(output)])


def _probe_output(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,channels,sample_rate", "-of", "json", str(path)], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def export_project(project_path: Path, formats: set[str], *, overwrite: bool = False, port: int = 8797, capture_timeout: float = 1800) -> dict:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if project.get("format") != PROJECT_FORMAT:
        raise ValueError("unsupported Music Studio project format")
    project_root = project_path.parent
    audio = project_root / project["source"]["copied_audio"]
    if not audio.is_file():
        raise FileNotFoundError(audio)
    videos: dict[str, str] = {}
    reports = {"project": project_path.relative_to(EXPORT_ROOT).as_posix(), "source": project["source"], "formats": sorted(formats), "outputs": {}, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for index, mode in enumerate(("full", "short")):
        if mode not in formats:
            continue
        _write_progress(project_root, f"capturing-{mode}", 10 + index * 35, mode=mode)
        timeline = project[mode]
        frame_dir, completion = capture_frames(project_root, mode, project_root / "captures" / mode, port=port + index, timeout=capture_timeout)
        _write_progress(project_root, f"encoding-{mode}", 55 + index * 25, mode=mode)
        output = project_root / "videos" / f"fabuloom-music-studio-{_project_name_from_source(Path(project['source']['filename']))}-{mode}.mp4"
        render_mp4(frame_dir, audio, output, int(timeline["duration_ms"]), start_ms=int(timeline["audio_start_ms"]), overwrite=overwrite)
        board = project_root / "captures" / f"{mode}-board.png"
        make_board(frame_dir, int(timeline["duration_ms"]), board, vertical=mode == "short")
        preview = project_root / "previews" / f"{mode}-preview.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(output), "-t", "8", "-vf", "" + ("scale=270:480" if mode == "short" else "scale=640:360"), "-c:v", "libx264", "-crf", "25", "-c:a", "aac", "-b:a", "96k", str(preview)])
        output_key = f"{mode}_video"
        videos[output_key] = output.relative_to(EXPORT_ROOT).as_posix()
        reports["outputs"][mode] = {"video": output.relative_to(EXPORT_ROOT).as_posix(), "preview": preview.relative_to(EXPORT_ROOT).as_posix(), "board": board.relative_to(EXPORT_ROOT).as_posix(), "completion": completion, "ffprobe": _probe_output(output)}
    _write_progress(project_root, "completed", 100, outputs=videos)
    _json(project_root / "reports" / "technical-report.json", reports)
    (project_root / "reports" / "technical-report.md").write_text("# Fabuloom Music Studio V1 — relatório técnico\n\n" + "\n".join([
        f"- Projeto: `{project['title']}`",
        f"- Fonte: `{project['source']['filename']}`",
        f"- Duração original medida: `{project['source']['analysis']['duration_seconds']:.3f} s`",
        f"- Formato fonte: `{project['source']['analysis']['format_name']}` · `{project['source']['analysis']['sample_rate']} Hz` · `{project['source']['analysis']['channels']} canais`",
        "- Análise: envelope RMS obtido de PCM decodificado por FFmpeg; BPM, beats e transições: indisponíveis.",
        "- Render: Canvas determinístico compartilhado com a prévia; sem personagens, narrador, legendas ou lip-sync.",
        "- Áudio: arquivo original preservado; sem alteração de velocidade ou pitch; AAC apenas no contêiner final.",
        "- Direitos: confirmação comercial da origem Suno continua pendente antes de publicação.",
        "- Revisão artística humana: pendente.",
    ]) + "\n", encoding="utf-8")
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset")
    parser.add_argument("--style", default="topazioverse-living-worlds")
    parser.add_argument("--short-start-ms", type=int)
    parser.add_argument("--short-end-ms", type=int)
    parser.add_argument("--name")
    parser.add_argument("--create-project", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--project")
    parser.add_argument("--formats", default="both")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8797)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    if args.analyze_only:
        source = _safe_relative_music(args.asset or "")
        print(json.dumps(analyze_source(source), ensure_ascii=False, indent=2))
        return 0
    if args.create_project:
        root, project = create_project(args.asset or "", args.style, args.short_start_ms, args.short_end_ms, args.name)
        print(json.dumps({"project_root": str(root), "project": str(root / "project.json"), "id": project["id"], "short_selection": project["short_selection"]}, ensure_ascii=False, indent=2))
        return 0
    if args.project:
        formats = {"full", "short"} if args.formats == "both" else {item.strip() for item in args.formats.split(",") if item.strip()}
        print(json.dumps(export_project(Path(args.project).resolve(), formats, overwrite=args.overwrite, port=args.port, capture_timeout=args.capture_timeout), ensure_ascii=False, indent=2))
        return 0
    parser.error("use --analyze-only, --create-project, or --project")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
