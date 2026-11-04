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
import unicodedata
from urllib.error import URLError
from urllib.request import urlopen


SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
from fabuloom_core.paths import FabuloomPaths


STUDIO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = FabuloomPaths.discover(
    product_root=STUDIO_ROOT,
    configured_root=os.environ.get("FABULOOM_ROOT") or os.environ.get("FABULOOM_WORKSPACE_ROOT"),
).root
EXPORT_ROOT = Path(os.environ.get("FABULOOM_EXPORT_ROOT", WORKSPACE_ROOT / "workspace" / "exports")).resolve()
MUSIC_ROOT = (WORKSPACE_ROOT / "workspace" / "inputs" / "music").resolve()
PROJECT_FORMAT = "fabuloom.music-studio-project/0.1"
CAPTURE_FPS = 5
OUTPUT_FPS = 30
FULL_SIZE = (1920, 1080)
SHORT_SIZE = (1080, 1920)
DEFAULT_ASSET_ROOT = "music-studio/music-studio-v1-o-chamado-do-vazio"
BATCH_ROOT = "music-studio/book1-v11"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


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
    if candidate.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
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
    normalized = unicodedata.normalize("NFKD", source.stem).encode("ascii", "ignore").decode("ascii")
    slug = "-".join(part for part in "".join(character.lower() if character.isalnum() else " " for character in normalized).split() if part)
    return slug or f"track-{_sha256(source)[:10]}"


def discover_music(root: Path = MUSIC_ROOT) -> list[Path]:
    """Return only supported files directly inside the mission's book1 folder."""
    return sorted((path for path in root.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS), key=lambda path: path.name.casefold())


def _batch_style_for_source(source: Path) -> str:
    name = source.stem.casefold()
    if "vazio" in name or "sombra" in name:
        return "obsidian-void"
    if "gaia" in name or "ecos" in name:
        return "gaia-contemplative"
    if "alba" in name or "luz" in name or "cristais" in name or "despertar" in name:
        return "crystal-dawn"
    return "topazioverse-living-worlds"


def _short_selection_from_candidate(duration_ms: int, candidate: dict | None, requested_start_ms: int | None, requested_end_ms: int | None) -> tuple[int, int, str]:
    if requested_start_ms is not None or requested_end_ms is not None:
        start = max(0, int(requested_start_ms or 0))
        end = min(duration_ms, int(requested_end_ms if requested_end_ms is not None else start + 24000))
        return start, end, "owner_or_manual_range"
    desired = min(24000, duration_ms)
    if candidate:
        center = (int(candidate["start_ms"]) + int(candidate["end_ms"])) // 2
        start = max(0, min(max(0, duration_ms - desired), center - desired // 2))
    else:
        start = 0
    return start, min(duration_ms, start + desired), "highest_rms_candidate_centered_24s"


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
        "topazioverse-living-worlds": {"id": "topazioverse-living-worlds", "label": "Topazioverse Living Worlds", "palette": {"deep": "#060b1c", "mid": "#182c63", "accent": "#5478c8", "gold": "#e6c77a", "mist": "#b7c8ff", "fog": "#91b4dd", "spark": "#f5d98a", "reflection": "#6e9cdd"}},
        "obsidian-void": {"id": "obsidian-void", "label": "Obsidian Void", "palette": {"deep": "#05040e", "mid": "#211347", "accent": "#5d4f9e", "gold": "#d4b3ff", "mist": "#a9a2d4", "fog": "#74699d", "spark": "#c6b7ff", "reflection": "#695aaf"}},
        "crystal-dawn": {"id": "crystal-dawn", "label": "Crystal Dawn", "palette": {"deep": "#0b1727", "mid": "#26547b", "accent": "#4caeca", "gold": "#f1d487", "mist": "#d3f4ff", "fog": "#9ad4d4", "spark": "#ffe7a2", "reflection": "#7bd3e8"}},
        "gaia-contemplative": {"id": "gaia-contemplative", "label": "Gaia Contemplative", "palette": {"deep": "#071713", "mid": "#234a3e", "accent": "#5a9b74", "gold": "#e8d58a", "mist": "#b9d8b1", "fog": "#80b79a", "spark": "#f3e39e", "reflection": "#76b998"}},
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


def create_project(
    asset: str,
    style_id: str,
    short_start_ms: int | None,
    short_end_ms: int | None,
    name: str | None,
    *,
    project_root_base: Path | None = None,
) -> tuple[Path, dict]:
    source = _safe_relative_music(asset)
    analysis = analyze_source(source)
    duration_ms = int(analysis["metadata"]["duration_ms"])
    candidate = analysis.get("selected_candidate")
    start, end, selection_method = _short_selection_from_candidate(duration_ms, candidate, short_start_ms, short_end_ms)
    if end <= start:
        raise ValueError("short selection must end after its start")
    if end - start < 15000 or end - start > 30000:
        raise ValueError("short selection must be between 15 and 30 seconds")
    project_slug = _project_name_from_source(source)
    requested_name = name or project_slug
    requested_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in requested_name.lower()).strip("-") or "music-project"
    base_root = (project_root_base or (EXPORT_ROOT / "music-studio")).resolve()
    base_root.relative_to(EXPORT_ROOT.resolve())
    project_root = (base_root / (requested_name if project_root_base else f"music-studio-v1-{requested_name}")).resolve()
    project_root.relative_to(EXPORT_ROOT.resolve())
    project_id = project_root.name
    style = _style(_batch_style_for_source(source) if style_id == "auto" else style_id)
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
        "display_title": source.stem,
        "renderer_version": "music-studio-v1.1",
        "style": style,
        "source": {**analysis["source"], "display_title": source.stem, "analysis": analysis["metadata"], "copied_audio": source_copy.relative_to(project_root).as_posix(), "pitch_or_speed_changed": False},
        "analysis": {"waveform": analysis["waveform"], "energy_candidates": analysis["energy_candidates"], "timing": analysis["timing"]},
        "visual_policy": {"mode": "Topazioverse Living Worlds", "narrator": None, "characters": [], "narration": None, "lip_sync": False, "captions": False, "assets_are_environmental_only": True},
        "assets": assets,
        "full": {"width": 1920, "height": 1080, "fps": OUTPUT_FPS, "duration_ms": duration_ms, "audio_start_ms": 0, "audio_end_ms": duration_ms, "scenes": _scene_list(duration_ms)},
        "short": {"width": 1080, "height": 1920, "fps": OUTPUT_FPS, "duration_ms": end - start, "audio_start_ms": start, "audio_end_ms": end, "scenes": _scene_list(end - start, start_ms=0, end_ms=end - start, vertical=True)},
        "short_selection": {"start_ms": start, "end_ms": end, "duration_ms": end - start, "selection_method": selection_method, "candidate_method": "heuristic_rms_window"},
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
        browser = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--disable-gpu-compositing", "--force-device-scale-factor=1", "--disable-background-networking", "--hide-scrollbars", f"--window-size={1920 if mode == 'full' else 1080},{1080 if mode == 'full' else 1920}", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


def _validate_output(path: Path, timeline: dict) -> dict:
    """Validate an encoded pair without rendering it again."""
    expected_duration = int(timeline["duration_ms"])
    probe = _probe_output(path)
    streams = probe.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
    measured = float(probe.get("format", {}).get("duration") or 0.0)
    duration_ok = abs(measured - expected_duration / 1000) <= 0.25
    geometry_ok = (int(video.get("width") or 0), int(video.get("height") or 0)) == (int(timeline["width"]), int(timeline["height"]))
    decode = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], text=True, capture_output=True)
    black = subprocess.run(["ffmpeg", "-hide_banner", "-vf", "blackdetect=d=0.15:pic_th=0.98", "-an", "-i", str(path), "-f", "null", "-"], text=True, capture_output=True)
    black_intervals = [line.strip() for line in (black.stderr or "").splitlines() if "black_start:" in line]
    return {
        "ffprobe": probe,
        "duration_ok": duration_ok,
        "geometry_ok": geometry_ok,
        "decode_ok": decode.returncode == 0,
        "blackdetect_intervals": black_intervals,
        "audio_codec_ok": audio_stream.get("codec_name") == "aac",
        "video_codec_ok": video.get("codec_name") == "h264",
        "all_ok": duration_ok and geometry_ok and decode.returncode == 0 and audio_stream.get("codec_name") == "aac" and video.get("codec_name") == "h264",
    }


def make_board_from_video(video: Path, duration_ms: int, output: Path, *, vertical: bool) -> None:
    """Recover a board when a valid encode exists but its capture session was cleaned."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".music-board-video-", dir=output.parent) as temp:
        files = []
        for index, value in enumerate((0.08, 0.33, 0.58, 0.83)):
            source = Path(temp) / f"{index:02d}.png"
            timestamp = max(0.0, min(max(0.0, duration_ms / 1000 - 0.1), duration_ms / 1000 * value))
            _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{timestamp:.3f}", "-i", str(video), "-frames:v", "1", str(source)])
            files.append(source)
        width, height = (540, 960) if vertical else (640, 360)
        scaled = []
        for index, source in enumerate(files):
            target = Path(temp) / f"scaled-{index:02d}.png"
            _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x050814", str(target)])
            scaled.append(target)
        inputs = [argument for file in scaled for argument in ("-i", str(file))]
        cell_width, cell_height = (540, 960) if vertical else (640, 360)
        layout = "|".join(f"{index % 2 * cell_width}_{index // 2 * cell_height}" for index in range(len(scaled)))
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", f"xstack=inputs=4:layout={layout}:fill=black,format=rgb24[out]", "-map", "[out]", "-frames:v", "1", str(output)])


def _write_technical_report(project_root: Path, project: dict, reports: dict, *, version: str) -> None:
    lines = [
        f"# Fabuloom Music Studio {version} — relatório técnico",
        "",
        f"- Projeto: `{project['title']}`",
        f"- Fonte: `{project['source']['filename']}`",
        f"- Duração original medida: `{project['source']['analysis']['duration_seconds']:.3f} s`",
        f"- Formato fonte: `{project['source']['analysis']['format_name']}` · `{project['source']['analysis']['sample_rate']} Hz` · `{project['source']['analysis']['channels']} canais`",
        f"- Estilo: `{project['style']['label']}`",
        f"- Short: `{project['short_selection']['start_ms']}–{project['short_selection']['end_ms']} ms` · `{project['short_selection']['selection_method']}`",
        "- Análise: envelope RMS obtido de PCM decodificado por FFmpeg; BPM, beats e transições: indisponíveis.",
        "- Efeitos: névoa, partículas, reflexos e fragmentos luminosos orgânicos; sem faixa roxa, polígonos repetitivos ou personagens.",
        "- Render: Canvas determinístico compartilhado com a prévia; sem narrador, legendas ou lip-sync.",
        "- Áudio: arquivo original preservado; sem alteração de velocidade ou pitch; AAC apenas no contêiner final.",
        "- Direitos: confirmação comercial da origem Suno continua pendente antes de publicação.",
        "- Revisão artística humana: pendente.",
        "",
        "## Saídas",
        "",
    ]
    for mode, output in reports.get("outputs", {}).items():
        validation = output.get("validation", {})
        lines.extend([
            f"### {mode}",
            f"- Vídeo: `{output.get('video')}`",
            f"- Prancha: `{output.get('board')}`",
            f"- Duração medida: `{validation.get('ffprobe', {}).get('format', {}).get('duration', '—')} s`",
            f"- Validação: `{'OK' if validation.get('all_ok') else 'FALHA'}` · decode=`{validation.get('decode_ok')}` · blackdetect intervalos=`{len(validation.get('blackdetect_intervals', []))}`",
            "",
        ])
    (project_root / "reports" / "technical-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_project_v11(project_path: Path, formats: set[str], *, overwrite: bool = False, port: int = 8797, capture_timeout: float = 1800) -> dict:
    """Export one V1.1 project, reusing validated outputs on resume."""
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if project.get("format") != PROJECT_FORMAT:
        raise ValueError("unsupported Music Studio project format")
    project_root = project_path.parent
    audio = project_root / project["source"]["copied_audio"]
    if not audio.is_file():
        raise FileNotFoundError(audio)
    reports = {"version": "music-studio-v1.1", "project": project_path.relative_to(EXPORT_ROOT).as_posix(), "source": project["source"], "formats": sorted(formats), "outputs": {}, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for index, mode in enumerate(("full", "short")):
        if mode not in formats:
            continue
        timeline = project[mode]
        output = project_root / "videos" / f"fabuloom-music-studio-{_project_name_from_source(Path(project['source']['filename']))}-{mode}.mp4"
        board = project_root / "captures" / f"{mode}-board.png"
        preview = project_root / "previews" / f"{mode}-preview.mp4"
        reused = False
        validation = None
        if output.is_file() and not overwrite:
            try:
                validation = _validate_output(output, timeline)
                reused = bool(validation["all_ok"])
            except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError):
                reused = False
        if reused:
            _write_progress(project_root, f"reused-{mode}", 50 + index * 25, mode=mode)
            if not board.is_file():
                make_board_from_video(output, int(timeline["duration_ms"]), board, vertical=mode == "short")
            if not preview.is_file():
                _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(output), "-t", "8", "-vf", "scale=270:480" if mode == "short" else "scale=640:360", "-c:v", "libx264", "-crf", "25", "-c:a", "aac", "-b:a", "96k", str(preview)])
        else:
            _write_progress(project_root, f"capturing-{mode}", 10 + index * 35, mode=mode)
            frame_dir, completion = capture_frames(project_root, mode, project_root / "captures" / mode, port=port + index, timeout=capture_timeout)
            _write_progress(project_root, f"encoding-{mode}", 55 + index * 25, mode=mode)
            render_mp4(frame_dir, audio, output, int(timeline["duration_ms"]), start_ms=int(timeline["audio_start_ms"]), overwrite=overwrite or output.exists())
            make_board(frame_dir, int(timeline["duration_ms"]), board, vertical=mode == "short")
            validation = _validate_output(output, timeline)
            if not validation["all_ok"]:
                raise RuntimeError(f"V1.1 output validation failed for {mode}: {validation}")
            _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(output), "-t", "8", "-vf", "scale=270:480" if mode == "short" else "scale=640:360", "-c:v", "libx264", "-crf", "25", "-c:a", "aac", "-b:a", "96k", str(preview)])
            shutil.rmtree(frame_dir, ignore_errors=True)
        reports["outputs"][mode] = {"video": output.relative_to(EXPORT_ROOT).as_posix(), "preview": preview.relative_to(EXPORT_ROOT).as_posix(), "board": board.relative_to(EXPORT_ROOT).as_posix(), "reused": reused, "validation": validation or _validate_output(output, timeline)}
    if set(reports["outputs"]) != set(formats):
        raise RuntimeError("requested Music Studio formats were not all exported")
    _write_progress(project_root, "completed", 100, outputs={mode: item["video"] for mode, item in reports["outputs"].items()})
    _json(project_root / "reports" / "technical-report.json", reports)
    _write_technical_report(project_root, project, reports, version="V1.1")
    return reports


def export_book1_batch(*, overwrite: bool = False, port: int = 8797, capture_timeout: float = 1800) -> dict:
    """Process all supported book1 tracks sequentially and write resumable indexes."""
    batch_root = (EXPORT_ROOT / BATCH_ROOT).resolve()
    batch_root.relative_to(EXPORT_ROOT.resolve())
    batch_root.mkdir(parents=True, exist_ok=True)
    tracks = discover_music(MUSIC_ROOT / "book1")
    preferred = next((track for track in tracks if track.stem.casefold() == "o chamado do vazio"), None)
    if preferred is not None:
        tracks = [preferred] + [track for track in tracks if track != preferred]
    records: list[dict] = []

    def save_index() -> None:
        _json(batch_root / "INDEX.json", {"format": "fabuloom.music-studio-batch/0.1", "version": "music-studio-v1.1", "input_root": (MUSIC_ROOT / "book1").relative_to(WORKSPACE_ROOT).as_posix(), "tracks": records})
        lines = ["# Fabuloom Music Studio V1.1 — Book 1 batch", "", f"- Faixas encontradas: **{len(tracks)}**", f"- Pares concluídos: **{sum(item.get('status') == 'DONE' for item in records)}**", f"- Falhas/pendências: **{sum(item.get('status') != 'DONE' for item in records)}**", "- Direitos comerciais: `pending_owner_confirmation` para todas as faixas.", ""]
        for item in records:
            lines.extend([f"## {item['filename']}", f"- Status: `{item['status']}`", f"- Fonte: `{item['source']}`", f"- SHA-256: `{item['sha256']}`", f"- Estilo: `{item.get('style', '—')}`", f"- Projeto: `{item.get('project', '—')}`", f"- Full: `{item.get('full', '—')}`", f"- Short: `{item.get('short', '—')}`", f"- Duração: `{item.get('duration_seconds', '—')} s`", f"- Short range: `{item.get('short_start_ms', '—')}–{item.get('short_end_ms', '—')} ms`", f"- Erro: `{item.get('error', '—')}`", ""])
        (batch_root / "BATCH-REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    for source in tracks:
        relative = source.relative_to(MUSIC_ROOT).as_posix()
        base_record = {"filename": source.name, "source": source.relative_to(WORKSPACE_ROOT).as_posix(), "sha256": _sha256(source), "status": "PENDING", "rights": "pending_owner_confirmation"}
        try:
            analysis = analyze_source(source)
            candidate = analysis.get("selected_candidate")
            start, end, _ = _short_selection_from_candidate(int(analysis["metadata"]["duration_ms"]), candidate, None, None)
            style_id = _batch_style_for_source(source)
            slug = _project_name_from_source(source)
            project_path = batch_root / slug / "project.json"
            if project_path.is_file():
                existing = json.loads(project_path.read_text(encoding="utf-8"))
                if existing.get("source", {}).get("sha256") != base_record["sha256"]:
                    raise RuntimeError("existing project has a different source hash")
                project_root, project = project_path.parent, existing
            else:
                project_root, project = create_project(relative, style_id, start, end, slug, project_root_base=batch_root)
            reports = export_project_v11(project_root / "project.json", {"full", "short"}, overwrite=overwrite, port=port, capture_timeout=capture_timeout)
            record = {**base_record, "status": "DONE", "project": reports["project"], "style": project["style"]["id"], "duration_seconds": project["source"]["analysis"]["duration_seconds"], "short_start_ms": project["short_selection"]["start_ms"], "short_end_ms": project["short_selection"]["end_ms"], "full": reports["outputs"]["full"]["video"], "short": reports["outputs"]["short"]["video"], "boards": {mode: item["board"] for mode, item in reports["outputs"].items()}, "validation": {mode: item["validation"] for mode, item in reports["outputs"].items()}}
        except Exception as exc:  # Isolate a broken track and keep the batch resumable.
            record = {**base_record, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        records.append(record)
        save_index()
    save_index()
    return {"batch_root": batch_root.relative_to(EXPORT_ROOT).as_posix(), "track_count": len(tracks), "completed": sum(item["status"] == "DONE" for item in records), "failed": sum(item["status"] != "DONE" for item in records), "tracks": records}


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
    parser.add_argument("--batch-book1", action="store_true", help="export every supported track in workspace/inputs/music/book1")
    parser.add_argument("--project")
    parser.add_argument("--formats", default="both")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8797)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    if args.batch_book1:
        print(json.dumps(export_book1_batch(overwrite=args.overwrite, port=args.port, capture_timeout=args.capture_timeout), ensure_ascii=False, indent=2))
        return 0
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
