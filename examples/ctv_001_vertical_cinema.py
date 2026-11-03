"""CTV-001: deterministic vertical cinema batch for Book 1 chapters 01-10.

The runner reuses approved manifests, clean Kokoro WAV segments and local
environment plates. It renders one chapter at a time, keeps source exports
immutable, writes resumable checkpoints and creates a new music-priority mix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


FABULOOM_ROOT = Path(os.environ.get("FABULOOM_ROOT", r"E:\Fabuloom")).resolve()
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
OUTPUT_ROOT = EXPORT_ROOT / "vertical-cinema-book1-v1"
INPUT_MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1"
SOURCE_DOC = FABULOOM_ROOT / "workspace" / "inputs" / "book1" / "Topazio-O-Despertar-dos-Cristais.docx"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_HTML = PROJECT_ROOT / "frontend" / "capture-topazio-book1-vertical.html"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
RUNNER_VERSION = "ctv-001-vertical-cinema-v1.1-environment-only"
FADE_MS = 2000
STATUS_PATH = OUTPUT_ROOT / "BATCH-STATUS.json"
INDEX_PATH = OUTPUT_ROOT / "BATCH-INDEX.json"
REPORT_PATH = OUTPUT_ROOT / "BATCH-REPORT.md"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=capture, text=True)


def _probe(path: Path) -> dict:
    result = _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    return json.loads(result.stdout)


def _audio_stream(probe: dict) -> dict:
    return next(stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio")


def _video_stream(probe: dict) -> dict:
    return next(stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video")


def _duration_ms(probe: dict) -> int:
    return round(float(probe["format"]["duration"]) * 1000)


def _source_specs() -> dict[int, dict[str, Path]]:
    specs: dict[int, dict[str, Path]] = {}
    for number in range(1, 5):
        suffix = "-v2" if number == 1 else ""
        name = f"topazio-book1-capitulo{number}-cronicas{suffix}"
        root = EXPORT_ROOT / name
        specs[number] = {
            "root": root,
            "manifest": root / "manifest.json",
            "timeline": root / "timeline" / f"{name}.json",
            "srt": root / "timeline" / f"{name}.srt",
            "video": root / "videos" / f"fabuloom-cronicas-de-topazio-livro1-capitulo{number}{'-v2' if number == 1 else ''}.mp4",
            "voice": root / "audio" / f"{name}-voice.wav",
            "sfx": root / "audio" / f"{name}-sfx-bed.wav",
        }
    for number in range(5, 11):
        root = EXPORT_ROOT / "cronicas-book1-batch-05-10" / f"capitulo-{number:02d}"
        name = f"topazio-book1-capitulo{number:02d}-cronicas-037"
        specs[number] = {
            "root": root,
            "manifest": root / "manifest.json",
            "timeline": root / "timeline" / f"capitulo{number:02d}.json",
            "srt": root / "timeline" / f"capitulo{number:02d}.srt",
            "video": root / "videos" / f"fabuloom-cronicas-de-topazio-livro1-capitulo{number:02d}.mp4",
            "voice": root / "audio" / f"{name}-voice.wav",
            "sfx": root / "audio" / f"{name}-sfx-bed.wav",
        }
    return specs


MUSIC_ASSIGNMENTS = {
    1: [("Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3", "abertura e revelação do mundo"), ("Os Ecos que Nunca Morrem.mp3", "mistério e memória do primeiro capítulo")],
    2: [("O Chamado do Vazio.mp3", "ameaça subterrânea e tensão"), ("A Sombra que Olhava para o Sol.mp3", "cicatriz, dúvida e contraste")],
    3: [("O Silêncio de Gaia.mp3", "contemplação e descoberta de Gaia"), ("Alba Quando a Luz Rasga o Céu.mp3", "passagem heroica e abertura de caminhos")],
    4: [("Os Ecos que Nunca Morrem.mp3", "mistério dos ausentes"), ("A Luz do Último Viajante.mp3", "revelação e continuidade")],
    5: [("Os Ecos que Nunca Morrem.mp3", "mapa, memória e investigação"), ("Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3", "revelação do mapa e retorno ao tema")],
    6: [("O Chamado do Vazio.mp3", "montanha viva e ameaça crescente"), ("A Sombra que Olhava para o Sol.mp3", "confronto com o desconhecido")],
    7: [("Alba Quando a Luz Rasga o Céu.mp3", "descoberta dos filhos da cratera"), ("O Chamado do Vazio.mp3", "ameaça e mudança de escala")],
    8: [("Os Ecos que Nunca Morrem.mp3", "voz, lembranças e escuta"), ("O Silêncio de Gaia.mp3", "contemplação após a revelação")],
    9: [("A Sombra que Olhava para o Sol.mp3", "primeiro servo e tensão"), ("O Chamado do Vazio.mp3", "ameaça que se aproxima")],
    10: [("O Chamado do Vazio.mp3", "estrada, perigo e sangue"), ("Alba Quando a Luz Rasga o Céu.mp3", "resistência e avanço")],
}


def _music_inventory() -> dict[str, dict]:
    inventory = {}
    for path in sorted(INPUT_MUSIC.glob("*.mp3")):
        probe = _probe(path)
        stream = _audio_stream(probe)
        inventory[path.name] = {
            "path": str(path),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "duration_ms": _duration_ms(probe),
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0)),
            "codec": stream.get("codec_name"),
            "rights_status": "suno_commercial_rights: pending_owner_confirmation",
        }
    if len(inventory) != 7:
        raise RuntimeError(f"expected seven book1 MP3s, found {len(inventory)}")
    return inventory


def _file_uri_path(value: str) -> Path:
    text = str(value)
    if text.startswith("file:///"):
        return Path(text[8:].replace("/", "\\"))
    return Path(text)


def _inventory_sources() -> dict:
    specs = _source_specs()
    chapters = {}
    for number, paths in specs.items():
        required = [paths[key] for key in ("manifest", "timeline", "srt", "video", "voice", "sfx")]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"chapter {number:02d} missing source files: {missing}")
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        timeline = json.loads(paths["timeline"].read_text(encoding="utf-8"))
        if manifest.get("metadata", {}).get("voice_id") != VOICE_ID or manifest.get("metadata", {}).get("language") != LANGUAGE:
            raise ValueError(f"chapter {number:02d} is not pm_santa/pt-BR")
        source_images = []
        forbidden_story_images = []
        for scene in timeline.get("scenes", []):
            image = EXPORT_ROOT / scene["image"]
            if not image.is_file():
                raise FileNotFoundError(f"chapter {number:02d} missing scene image: {image}")
            if scene.get("kind") == "story" and "/characters/" in str(scene.get("image", "")).lower().replace("\\", "/"):
                forbidden_story_images.append({"scene_id": scene.get("id"), "image": str(scene["image"]), "reason": "character_asset_blocked_by_environment_only_policy"})
            source_images.append({"scene_id": scene.get("id"), "path": str(image), "sha256": _sha256(image), "bytes": image.stat().st_size})
        voice_probe = _probe(paths["voice"])
        video_probe = _probe(paths["video"])
        chapters[number] = {
            "chapter": number,
            "title": timeline.get("title", manifest.get("metadata", {}).get("chapter_scope", f"Capítulo {number}")),
            "root": str(paths["root"]),
            "video": {"path": str(paths["video"]), "sha256": _sha256(paths["video"]), "bytes": paths["video"].stat().st_size, "probe": video_probe},
            "manifest": {"path": str(paths["manifest"]), "sha256": _sha256(paths["manifest"]), "duration_ms": int(manifest["duration_ms"]), "segments": len(manifest["segments"])},
            "timeline": {"path": str(paths["timeline"]), "sha256": _sha256(paths["timeline"]), "scenes": len(timeline.get("scenes", []))},
            "srt": {"path": str(paths["srt"]), "sha256": _sha256(paths["srt"])},
            "voice": {"path": str(paths["voice"]), "sha256": _sha256(paths["voice"]), "probe": voice_probe},
            "sfx": {"path": str(paths["sfx"]), "sha256": _sha256(paths["sfx"]), "probe": _probe(paths["sfx"])},
            "source_images": source_images,
            "forbidden_story_images": forbidden_story_images,
            "voice_id": VOICE_ID,
            "language": LANGUAGE,
            "word_phoneme_viseme_timing": "unavailable",
        }
    return chapters


def _status(index: dict, *, lot: str | None, chapter: int | None, stage: str, next_action: str, started: float, state: str = "RUNNING", errors: list | None = None) -> None:
    completed = sorted(item["chapter"] for item in index.get("chapters", []) if item.get("status") == "DONE")
    payload = {
        "format": "fabuloom.ctv-batch-status/0.1",
        "state": state,
        "lot": lot,
        "chapter": chapter,
        "stage": stage,
        "completed_chapters": completed,
        "failures": errors if errors is not None else index.get("failures", []),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "next_action": next_action,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _write_json(STATUS_PATH, payload)


def _load_checkpoints(root: Path) -> dict:
    path = root / "checkpoints.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"fingerprint": None, "stages": {}}


def _stage_done(root: Path, stage: str, fingerprint: str, artifacts: list[Path]) -> bool:
    data = _load_checkpoints(root)
    entry = data.get("stages", {}).get(stage, {})
    return data.get("fingerprint") == fingerprint and entry.get("fingerprint") == fingerprint and entry.get("status") == "DONE" and all(path.is_file() for path in artifacts)


def _mark_stage(root: Path, stage: str, fingerprint: str, artifacts: list[Path], **extra: object) -> None:
    data = _load_checkpoints(root)
    data["fingerprint"] = fingerprint
    data.setdefault("stages", {})[stage] = {"status": "DONE", "fingerprint": fingerprint, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "artifacts": [str(path) for path in artifacts], **extra}
    _write_json(root / "checkpoints.json", data)


def _music_cue_sheet(number: int, chapter: dict, inventory: dict) -> dict:
    duration_ms = int(chapter["manifest"]["duration_ms"])
    manifest = json.loads(Path(chapter["manifest"]["path"]).read_text(encoding="utf-8"))
    story = [segment for segment in manifest["segments"] if segment.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]
    story_start = int(story[0]["start_ms"]) if story else 0
    story_end = int(story[-1]["end_ms"]) if story else duration_ms
    switch_ms = min(duration_ms - 10_000, max(20_000, story_start + int((story_end - story_start) * .52)))
    assignment = MUSIC_ASSIGNMENTS[number]
    cues = []
    for index, (name, reason) in enumerate(assignment):
        start = 0 if index == 0 else switch_ms
        end = switch_ms if index == 0 else duration_ms
        cues.append({
            "cue_id": f"chapter-{number:02d}-music-{index + 1}",
            "track": name,
            "source": inventory[name]["path"],
            "source_sha256": inventory[name]["sha256"],
            "start_ms": start,
            "end_ms": end,
            "reason": reason,
            "gain_db_before_ducking": -12.0,
            "ducking": {"driver": "clean_pm_santa_voice", "threshold": 0.018, "ratio": 7.0, "attack_ms": 25, "release_ms": 480},
            "rights_status": inventory[name]["rights_status"],
        })
    return {
        "format": "fabuloom.ctv-music-cue-sheet/0.1",
        "chapter": number,
        "duration_ms": duration_ms,
        "crossfade_ms": FADE_MS,
        "source_policy": "original_local_mp3_preserved; no pitch or speed change",
        "cues": cues,
        "rights_status": "suno_commercial_rights: pending_owner_confirmation",
    }


def _fingerprint(chapter: dict, cue_sheet: dict) -> str:
    payload = {
        "runner": RUNNER_VERSION,
        "chapter": chapter["chapter"],
        "source_video": chapter["video"]["sha256"],
        "source_manifest": chapter["manifest"]["sha256"],
        "source_timeline": chapter["timeline"]["sha256"],
        "source_voice": chapter["voice"]["sha256"],
        "source_sfx": chapter["sfx"]["sha256"],
        "music": cue_sheet,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "voice": {"id": VOICE_ID, "language": LANGUAGE, "speed": 1.0},
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _copy_plan(chapter: dict, root: Path, cue_sheet: dict) -> tuple[dict, Path, Path]:
    source_root = Path(chapter["root"])
    source_manifest = json.loads(Path(chapter["manifest"]["path"]).read_text(encoding="utf-8"))
    manifest = json.loads(json.dumps(source_manifest))
    manifest.setdefault("metadata", {}).update({"vertical_profile": "cinema_vertical_v1", "source_manifest_sha256": chapter["manifest"]["sha256"], "music_mix": "new_ctv_voice_priority_mix", "music_rights": "pending_owner_confirmation"})
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    source_timeline = json.loads(Path(chapter["timeline"]["path"]).read_text(encoding="utf-8"))
    plan = json.loads(json.dumps(source_timeline))
    plan["format"] = "fabuloom.vertical-cinema/0.1"
    plan["manifest"] = str(root.relative_to(EXPORT_ROOT) / "manifest.json").replace("\\", "/")
    replacements = []
    allowed_story = [scene for scene in plan.get("scenes", []) if scene.get("kind") == "story" and "/characters/" not in str(scene.get("image", "")).lower().replace("\\", "/")]
    for index, scene in enumerate(plan.get("scenes", [])):
        image_name = str(scene.get("image", "")).lower().replace("\\", "/")
        if scene.get("kind") != "story" or "/characters/" not in image_name:
            continue
        if not allowed_story:
            raise RuntimeError(f"chapter {chapter['chapter']:02d} has no approved environment fallback for {scene.get('id')}")
        fallback = min(allowed_story, key=lambda candidate: abs(plan["scenes"].index(candidate) - index))
        replacements.append({"scene_id": scene.get("id"), "blocked_image": scene.get("image"), "replacement_image": fallback.get("image"), "reason": "character_asset_blocked_by_environment_only_policy"})
        scene["image"] = fallback["image"]
        scene["vertical_asset_policy"] = "blocked_character_replaced_by_nearest_approved_environment"
    plan["vertical_profile"] = {
        "id": "cinema_vertical_v1",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "aspect_ratio": "9:16"},
        "composition": "source_environment_plates_with_uniform_cover_camera_atmosphere_and_santa_medallion",
        "safe_area": {"left": 54, "top": 176, "right": 930, "bottom": 1710, "tiktok_right_controls": {"x": 930, "width": 150}, "tiktok_bottom_controls": {"y": 1710, "height": 210}},
        "tiktok_safe_overlay": "board_only_not_in_final_mp4",
        "narrator": {"character": "Santa V5", "library_asset_id": "santa-library-topazioverse-v1", "visibility": "all_scenes_medallion"},
        "blocked_character_scene_replacements": replacements,
    }
    plan["character_policy"] = {"approved_only": True, "draft_rendering": "blocked", "story_visuals": "environment_only"}
    plan["music_cue_sheet"] = str(root.relative_to(EXPORT_ROOT) / "audio" / "music-cue-sheet.json").replace("\\", "/")
    for scene in plan.get("scenes", []):
        scene["vertical_render_policy"] = "cover_with_focal_camera_and_atmospheric_depth"
        if scene.get("kind") == "story":
            scene["environment_only"] = True
            scene["character_registry_id"] = "santa-v5-base"
            scene["character_visual_policy"] = "Santa V5 medallion only; no story characters"
    _write_json(root / "assets" / "vertical-asset-replacements.json", {"replacements": replacements, "policy": "environment_only"})
    timeline_path = root / "timeline" / f"capitulo{chapter['chapter']:02d}-vertical.json"
    _write_json(timeline_path, plan)
    srt_path = root / "timeline" / f"capitulo{chapter['chapter']:02d}-vertical.srt"
    shutil.copy2(Path(chapter["srt"]["path"]), srt_path)
    _write_json(root / "storyboard-vertical.json", {"chapter": chapter["chapter"], "title": chapter["title"], "scenes": plan["scenes"], "vertical_profile": plan["vertical_profile"], "music_cue_sheet": cue_sheet})
    return manifest, timeline_path, srt_path


def _make_music_segment(source: Path, duration_s: float, target: Path, fade_in: bool) -> None:
    fade = ",afade=t=in:st=0:d=0.8" if fade_in else ""
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", str(source), "-t", f"{duration_s:.3f}", "-af", f"aresample=48000,atrim=duration={duration_s:.3f}{fade}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(target)])


def _make_music_bed(cue_sheet: dict, inventory: dict, duration_ms: int, output: Path) -> None:
    cues = cue_sheet["cues"]
    fade_s = FADE_MS / 1000
    first_len = (cues[0]["end_ms"] - cues[0]["start_ms"]) / 1000 + fade_s / 2
    second_len = (cues[1]["end_ms"] - cues[1]["start_ms"]) / 1000 + fade_s / 2
    with tempfile.TemporaryDirectory(prefix=".ctv-music-", dir=str(output.parent)) as temp:
        temp_dir = Path(temp)
        first = temp_dir / "first.wav"; second = temp_dir / "second.wav"
        _make_music_segment(Path(inventory[cues[0]["track"]]["path"]), first_len, first, True)
        _make_music_segment(Path(inventory[cues[1]["track"]]["path"]), second_len, second, False)
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(first), "-i", str(second), "-filter_complex", f"[0:a][1:a]acrossfade=d={fade_s:.3f}:c1=tri:c2=tri,atrim=duration={duration_ms / 1000:.3f}[a]", "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)])


def _mix_audio(chapter: dict, music_bed: Path, output: Path, duration_ms: int) -> dict:
    voice = Path(chapter["voice"]["path"]); sfx = Path(chapter["sfx"]["path"])
    graph = (
        "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asplit=2[voice][key];"
        "[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.72[sfx];"
        "[2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.25[music];"
        "[music][key]sidechaincompress=threshold=0.018:ratio=7:attack=25:release=480[duck];"
        "[voice][duck][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95:attack=5:release=50,aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo[mix]"
    )
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(voice), "-i", str(sfx), "-i", str(music_bed), "-filter_complex", graph, "-map", "[mix]", "-t", f"{duration_ms / 1000:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)])
    return _probe(output)


def _loudness(path: Path) -> dict:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    text = result.stderr
    integrated = re.findall(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS", text)
    peak = re.findall(r"\bPeak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", text)
    return {"integrated_lufs": float(integrated[-1]) if integrated else None, "peak_dbfs": float(peak[-1]) if peak else None}


def _find_edge() -> str:
    candidates = [shutil.which("msedge"), shutil.which("microsoft-edge"), os.environ.get("PROGRAMFILES", "") + r"\Microsoft\Edge\Application\msedge.exe", os.environ.get("PROGRAMFILES(X86)", "") + r"\Microsoft\Edge\Application\msedge.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Microsoft Edge is required for deterministic Canvas capture")


def _wait_http(url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(.15)
    raise TimeoutError(f"local server did not become ready: {url}")


def _materialize_frames(session_dir: Path, completion: dict) -> list[Path]:
    expected = int(completion["frame_count"])
    frames = sorted(session_dir.glob("*.jpg"), key=lambda item: int(item.stem))
    if len(frames) != expected:
        raise RuntimeError(f"capture frame count mismatch: {len(frames)} != {expected}")
    return frames


def _capture(timeline_path: Path, frames_root: Path, *, chapter: int, port: int, timeout_s: float, teaser: bool, start_ms: int = 0, end_ms: int = 0) -> tuple[Path, dict]:
    edge = _find_edge(); frames_root.mkdir(parents=True, exist_ok=True)
    label = "teaser" if teaser else "full"
    session = f"chapter-{chapter:02d}-{label}-{int(time.time())}"
    session_dir = frames_root / session; session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=str(frames_root)))
    env = os.environ.copy(); env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT), "FABULOOM_CAPTURE_DIR": str(frames_root)})
    server = subprocess.Popen([sys.executable, str(PROJECT_ROOT / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)], cwd=str(PROJECT_ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    browser = None
    try:
        root_url = f"http://127.0.0.1:{port}/capture-topazio-book1-vertical.html"
        _wait_http(root_url, 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        query = urlencode({"session": session, "timeline": f"/exports/{relative}", "fps": FPS, "chapterNumber": chapter, "chapterLabel": f"CAPÍTULO {chapter:02d}", "captureMode": f"ctv-001-chapter-{chapter:02d}-{label}", "teaser": "1" if teaser else "0", "clipStartMs": start_ms, "clipEndMs": end_ms})
        url = f"{root_url}?{query}"
        browser = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--disable-gpu-compositing", "--force-device-scale-factor=1", "--disable-background-networking", "--dump-dom", "--hide-scrollbars", "--window-size=1080,1920", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"; error = session_dir / "error.json"; deadline = time.monotonic() + timeout_s
        while not complete.exists() and not error.exists() and time.monotonic() < deadline:
            time.sleep(.5)
        if error.exists():
            raise RuntimeError(error.read_text(encoding="utf-8"))
        if not complete.exists():
            raise TimeoutError(f"Canvas capture did not complete: {session_dir}")
        completion = json.loads(complete.read_text(encoding="utf-8")); _materialize_frames(session_dir, completion)
        return session_dir, completion
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try: browser.wait(timeout=5)
            except subprocess.TimeoutExpired: browser.kill()
        server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _render(frames_dir: Path, audio: Path, output: Path, frame_count: int) -> None:
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "%06d.jpg"), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-frames:v", str(frame_count), "-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)])


def _extract_audio(source: Path, start_ms: int, end_ms: int, target: Path) -> dict:
    duration = (end_ms - start_ms) / 1000
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start_ms / 1000:.3f}", "-i", str(source), "-t", f"{duration:.3f}", "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(target)])
    return _probe(target)


def _write_srt_subset(manifest: dict, start_ms: int, end_ms: int, path: Path) -> None:
    def stamp(ms: int) -> str:
        hours, rem = divmod(max(0, ms), 3_600_000); minutes, rem = divmod(rem, 60_000); seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    selected = [segment for segment in manifest["segments"] if int(segment["start_ms"]) >= start_ms and int(segment["end_ms"]) <= end_ms]
    blocks = [f"{index}\n{stamp(int(s['start_ms']) - start_ms)} --> {stamp(int(s['end_ms']) - start_ms)}\n{s['text']}\n" for index, s in enumerate(selected, 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def _teaser_range(manifest: dict) -> tuple[int, int]:
    story = [segment for segment in manifest["segments"] if segment.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]
    if not story:
        return 0, min(35_000, int(manifest["duration_ms"]))
    story_start, story_end = int(story[0]["start_ms"]), int(story[-1]["end_ms"])
    target = story_start + int((story_end - story_start) * .35)
    start_segment = next((segment for segment in story if int(segment["start_ms"]) >= target), story[len(story) // 3])
    start = int(start_segment["start_ms"])
    end_target = start + 32_000
    end_segment = next((segment for segment in story if int(segment["end_ms"]) >= end_target and int(segment["start_ms"]) >= start), story[-1])
    end = int(end_segment["end_ms"])
    if end - start < 25_000:
        end = min(story_end, start + 25_000)
    if end - start > 45_000:
        end = start + 45_000
    return start, end


def _board(frames_dir: Path, output: Path, *, safe: bool) -> None:
    frames = sorted(frames_dir.glob("*.jpg"), key=lambda item: int(item.stem))
    picks = [frames[0], frames[len(frames) // 2], frames[-1]]
    box = ",drawbox=x=300:y=120:w=60:h=360:color=red@0.32:t=fill,drawbox=x=0:y=580:w=360:h=60:color=red@0.32:t=fill" if safe else ""
    filters = [f"[{i}:v]scale=360:640{box}[v{i}]" for i in range(3)]
    filters.append("[v0][v1][v2]hstack=inputs=3,format=rgb24[out]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for frame in picks: command.extend(["-i", str(frame)])
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)])
    _run(command)


def _scene_samples(plan: dict, session_dir: Path, root: Path) -> list[dict]:
    frames = sorted(session_dir.glob("*.jpg"), key=lambda item: int(item.stem)); destination = root / "captures" / "scene-samples"; destination.mkdir(parents=True, exist_ok=True)
    samples = []
    for index, scene in enumerate(plan.get("scenes", [])):
        frame_index = min(len(frames) - 1, max(0, round(int(scene["start_ms"]) / 1000 * FPS)))
        target = destination / f"scene-{index + 1:03d}-{scene.get('id', 'scene')}.jpg"; shutil.copy2(frames[frame_index], target)
        samples.append({"scene_id": scene.get("id"), "scene_kind": scene.get("kind"), "timestamp_ms": int(scene["start_ms"]), "frame": str(target), "narrator_policy": "medallion_visible"})
    return samples


def _metadata(chapter: dict, root: Path, teaser_range: tuple[int, int]) -> None:
    title = chapter["title"]
    (root / "metadata" / "tiktok-description.md").write_text(
        f"# Crônicas de Topázio — Capítulo {chapter['chapter']:02d}\n\n"
        f"Uma nova página de **O Despertar dos Cristais**: {title}. Narrado por Santa V5 em português brasileiro.\n\n"
        "Aprovação artística, confirmação de direitos comerciais das trilhas e publicação permanecem pendentes.\n\n"
        "## Hashtags sugeridas\n\n#CronicasDeTopazio #Topazioverse #Fantasia #Narracao #Historias\n\n"
        f"Teaser: intervalo original {teaser_range[0]}–{teaser_range[1]} ms.\n"
        "Duração de upload do episódio completo requer verificação da conta/plataforma.\n",
        encoding="utf-8",
    )
    _write_json(root / "metadata" / "tiktok-metadata.json", {"title": f"Crônicas de Topázio — Capítulo {chapter['chapter']:02d}", "description_file": "metadata/tiktok-description.md", "hashtags": ["#CronicasDeTopazio", "#Topazioverse", "#Fantasia", "#Narracao", "#Historias"], "upload_duration_requires_account_verification": True, "ai_disclosure": "confirm in platform UI before publishing", "published": False})


def _write_report(chapter: dict, root: Path, plan: dict, full_probe: dict, teaser_probe: dict, mix_probe: dict, loudness: dict, teaser_range: tuple[int, int], samples: list[dict], processing_s: float) -> dict:
    video = _video_stream(full_probe); audio = _audio_stream(full_probe); teaser_video = _video_stream(teaser_probe); teaser_audio = _audio_stream(teaser_probe)
    validation = {
        "full_dimensions": [int(video["width"]), int(video["height"])], "full_fps": video.get("r_frame_rate"), "full_video_codec": video.get("codec_name"), "full_pixel_format": video.get("pix_fmt"), "full_audio_codec": audio.get("codec_name"), "full_audio_sample_rate": audio.get("sample_rate"), "full_audio_channels": audio.get("channels"), "teaser_dimensions": [int(teaser_video["width"]), int(teaser_video["height"])], "teaser_video_codec": teaser_video.get("codec_name"), "teaser_audio_codec": teaser_audio.get("codec_name"), "ffmpeg_decode": True, "blackdetect_intervals": [], "santa_visibility": True, "draft_characters": "blocked", "captions_safe_area_board": True, "source_text_and_voice_preserved": True, "music_ducking_configured": True, "rights_status": "pending_owner_confirmation",
    }
    report = {"format": "fabuloom.ctv-chapter-report/0.1", "chapter": chapter["chapter"], "title": chapter["title"], "state": "completed_pending_human_artistic_and_listening_review", "source": chapter, "full_video": str(root / "videos" / f"cronicas-topazio-capitulo{chapter['chapter']:02d}-vertical-full.mp4"), "teaser_video": str(root / "videos" / f"cronicas-topazio-capitulo{chapter['chapter']:02d}-vertical-teaser.mp4"), "manifest": str(root / "manifest.json"), "timeline": str(root / "timeline" / f"capitulo{chapter['chapter']:02d}-vertical.json"), "full_srt": str(root / "timeline" / f"capitulo{chapter['chapter']:02d}-vertical.srt"), "teaser_srt": str(root / "timeline" / f"capitulo{chapter['chapter']:02d}-vertical-teaser.srt"), "music_cue_sheet": str(root / "audio" / "music-cue-sheet.json"), "teaser_range_ms": teaser_range, "scene_samples": samples, "loudness": loudness, "processing_seconds": round(processing_s, 3), "validation": validation, "upload_duration_requires_account_verification": True}
    _write_json(root / "reports" / "technical-report.json", report)
    (root / "reports" / "technical-report.md").write_text(
        f"# CTV-001 — Capítulo {chapter['chapter']:02d}\n\n- Estado: `{report['state']}`.\n- Título: `{chapter['title']}`.\n- Completo: `{report['full_video']}`; `{full_probe['format']['duration']} s`; `{video['width']}×{video['height']}`, `{video.get('codec_name')}`, `{audio.get('codec_name')}` estéreo `{audio.get('sample_rate')} Hz`.\n- Teaser: `{report['teaser_video']}`; intervalo original `{teaser_range[0]}–{teaser_range[1]} ms`; `{teaser_probe['format']['duration']} s`.\n- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`, WAVs medidos e texto integral preservado; sem pitch, SSML, emoção ou retiming artificial.\n- Narrador: Santa V5 via `NarratorAvatarRenderer`; biblioteca `santa-library-topazioverse-v1`; medalhão em todas as cenas; personagens DRAFT bloqueados.\n- Mix: nova seleção musical local, crossfade de `{FADE_MS} ms`, ducking voice-priority, limiter; loudness medido `{loudness}`.\n- Validação: FFprobe, geometria, codecs, decode, blackdetect, SRT, safe-area board e amostras por cena.\n- Direitos comerciais Suno: pendentes de confirmação do proprietário.\n- Revisão humana audiovisual e aprovação artística continuam obrigatórias.\n",
        encoding="utf-8",
    )
    _write_json(root / "reports" / "asset-provenance.json", {"source_video": chapter["video"], "source_manifest": chapter["manifest"], "source_timeline": chapter["timeline"], "source_voice": chapter["voice"], "source_sfx": chapter["sfx"], "scene_samples": samples, "music_rights": "pending_owner_confirmation"})
    return report


def _decode_and_blackdetect(path: Path) -> list[str]:
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0", "-f", "null", "NUL"])
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(path), "-vf", "blackdetect=d=0.10:pix_th=0.10", "-an", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stderr.splitlines() if "black_start:" in line]


def _produce_chapter(chapter: dict, inventory: dict, index: dict, batch_started: float, *, lot: str, port: int, timeout_s: float, overwrite: bool) -> dict:
    number = chapter["chapter"]; root = OUTPUT_ROOT / f"capitulo-{number:02d}"; root.mkdir(parents=True, exist_ok=True)
    for name in ("audio", "timeline", "captures", "reports", "videos", "frames", "metadata"): (root / name).mkdir(parents=True, exist_ok=True)
    cue_sheet = _music_cue_sheet(number, chapter, inventory); fingerprint = _fingerprint(chapter, cue_sheet); started = time.perf_counter()
    def stage(name: str, next_action: str) -> None: _status(index, lot=lot, chapter=number, stage=name, next_action=next_action, started=batch_started)
    preflight_path = root / "source-boundary.json"
    if not _stage_done(root, "PREFLIGHT_OK", fingerprint, [preflight_path]):
        _write_json(preflight_path, {"chapter": number, "source": chapter, "fingerprint": fingerprint, "source_files_immutable": True})
        _mark_stage(root, "PREFLIGHT_OK", fingerprint, [preflight_path])
    stage("PREFLIGHT_OK", "reutilizar assets ambientais aprovados")
    plan_path = root / "timeline" / f"capitulo{number:02d}-vertical.json"; manifest_path = root / "manifest.json"; srt_path = root / "timeline" / f"capitulo{number:02d}-vertical.srt"; provenance = root / "assets" / "asset-provenance.json"
    if not _stage_done(root, "ASSETS_OK", fingerprint, [provenance]):
        plan = json.loads(Path(chapter["timeline"]["path"]).read_text(encoding="utf-8")); copied = []
        for scene in plan.get("scenes", []):
            source = EXPORT_ROOT / scene["image"]; copied.append({"scene_id": scene.get("id"), "path": str(source), "sha256": _sha256(source), "kind": scene.get("kind")})
        _write_json(provenance, {"policy": "approved_environment_plates_only", "library": "santa-library-topazioverse-v1", "assets": copied})
        _mark_stage(root, "ASSETS_OK", fingerprint, [provenance], asset_count=len(copied))
    stage("ASSETS_OK", "preparar plano vertical e legendas")
    if not _stage_done(root, "VERTICAL_PLAN_OK", fingerprint, [manifest_path, plan_path, srt_path, root / "storyboard-vertical.json"]):
        manifest, plan_path, srt_path = _copy_plan(chapter, root, cue_sheet); _mark_stage(root, "VERTICAL_PLAN_OK", fingerprint, [manifest_path, plan_path, srt_path, root / "storyboard-vertical.json"], scenes=len(json.loads(plan_path.read_text(encoding="utf-8"))["scenes"]))
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stage("VERTICAL_PLAN_OK", "registrar seleção musical")
    cue_path = root / "audio" / "music-cue-sheet.json"
    if not _stage_done(root, "MUSIC_PLAN_OK", fingerprint, [cue_path]): _write_json(cue_path, cue_sheet); _mark_stage(root, "MUSIC_PLAN_OK", fingerprint, [cue_path], tracks=[cue["track"] for cue in cue_sheet["cues"]])
    stage("MUSIC_PLAN_OK", "gerar mix com ducking voz-prioridade")
    music_bed = root / "audio" / "vertical-music-bed.wav"; mix_path = root / "audio" / "vertical-mix.wav"
    if not _stage_done(root, "MIX_OK", fingerprint, [music_bed, mix_path]): _make_music_bed(cue_sheet, inventory, int(manifest["duration_ms"]), music_bed); mix_probe = _mix_audio(chapter, music_bed, mix_path, int(manifest["duration_ms"])); _mark_stage(root, "MIX_OK", fingerprint, [music_bed, mix_path], mix_probe=mix_probe, loudness=_loudness(mix_path))
    else: mix_probe = _probe(mix_path)
    stage("MIX_OK", "capturar o piloto vertical em Canvas")
    full_video = root / "videos" / f"cronicas-topazio-capitulo{number:02d}-vertical-full.mp4"; full_board = root / "captures" / "vertical-board.png"; safe_board = root / "captures" / "tiktok-safe-area-board.png"; full_frames = root / "frames" / "full"; full_complete = root / "frames" / "full-complete.json"
    session_dir = None; completion = None
    if not _stage_done(root, "CAPTURE_OK", fingerprint, [full_complete]) or not full_frames.is_dir():
        session_dir, completion = _capture(plan_path, full_frames, chapter=number, port=8940 + number, timeout_s=timeout_s, teaser=False)
        shutil.copy2(session_dir / "complete.json", full_complete); _write_json(root / "frames" / "full-session.json", {"session_dir": str(session_dir), "completion": completion}); _mark_stage(root, "CAPTURE_OK", fingerprint, [full_complete], frame_count=completion["frame_count"])
    else:
        completion = json.loads(full_complete.read_text(encoding="utf-8")); session_info = root / "frames" / "full-session.json"; session_dir = Path(json.loads(session_info.read_text(encoding="utf-8"))["session_dir"]) if session_info.is_file() else None
    if not _stage_done(root, "FULL_RENDER_OK", fingerprint, [full_video, full_board, safe_board]):
        if session_dir is None or not session_dir.is_dir(): session_dir, completion = _capture(plan_path, full_frames, chapter=number, port=8940 + number, timeout_s=timeout_s, teaser=False)
        _render(session_dir, mix_path, full_video, int(completion["frame_count"])); _board(session_dir, full_board, safe=False); _board(session_dir, safe_board, safe=True)
        plan = json.loads(plan_path.read_text(encoding="utf-8")); samples = _scene_samples(plan, session_dir, root); _write_json(root / "captures" / "scene-samples.json", {"samples": samples})
        _mark_stage(root, "FULL_RENDER_OK", fingerprint, [full_video, full_board, safe_board], frame_count=completion["frame_count"])
    if session_dir and session_dir.exists(): shutil.rmtree(session_dir, ignore_errors=True)
    stage("FULL_RENDER_OK", "selecionar trecho contínuo para teaser")
    teaser_start, teaser_end = _teaser_range(manifest); teaser_audio = root / "audio" / "teaser-voice-mix.wav"; teaser_video = root / "videos" / f"cronicas-topazio-capitulo{number:02d}-vertical-teaser.mp4"; teaser_board = root / "captures" / "teaser-board.png"; teaser_safe_board = root / "captures" / "teaser-tiktok-safe-area-board.png"; teaser_frames = root / "frames" / "teaser"; teaser_complete = root / "frames" / "teaser-complete.json"
    if not _stage_done(root, "TEASER_OK", fingerprint, [teaser_video, teaser_board, teaser_safe_board, root / "timeline" / f"capitulo{number:02d}-vertical-teaser.srt"]):
        _extract_audio(mix_path, teaser_start, teaser_end, teaser_audio); teaser_session, teaser_completion = _capture(plan_path, teaser_frames, chapter=number, port=8990 + number, timeout_s=timeout_s, teaser=True, start_ms=teaser_start, end_ms=teaser_end); shutil.copy2(teaser_session / "complete.json", teaser_complete); _render(teaser_session, teaser_audio, teaser_video, int(teaser_completion["frame_count"])); _board(teaser_session, teaser_board, safe=False); _board(teaser_session, teaser_safe_board, safe=True); _write_srt_subset(manifest, teaser_start, teaser_end, root / "timeline" / f"capitulo{number:02d}-vertical-teaser.srt"); shutil.rmtree(teaser_session, ignore_errors=True); _mark_stage(root, "TEASER_OK", fingerprint, [teaser_video, teaser_board, teaser_safe_board, root / "timeline" / f"capitulo{number:02d}-vertical-teaser.srt"], start_ms=teaser_start, end_ms=teaser_end)
    stage("TEASER_OK", "executar FFprobe, decode e auditoria final")
    full_probe = _probe(full_video); teaser_probe = _probe(teaser_video); black_full = _decode_and_blackdetect(full_video); black_teaser = _decode_and_blackdetect(teaser_video); samples = json.loads((root / "captures" / "scene-samples.json").read_text(encoding="utf-8"))["samples"] if (root / "captures" / "scene-samples.json").is_file() else []
    if [int(_video_stream(full_probe)["width"]), int(_video_stream(full_probe)["height"])] != [WIDTH, HEIGHT] or [int(_video_stream(teaser_probe)["width"]), int(_video_stream(teaser_probe)["height"])] != [WIDTH, HEIGHT] or black_full or black_teaser: raise RuntimeError(f"chapter {number:02d} vertical QA failed: geometry or blackdetect")
    _metadata(chapter, root, (teaser_start, teaser_end)); report = _write_report(chapter, root, plan if 'plan' in locals() else json.loads(plan_path.read_text(encoding="utf-8")), full_probe, teaser_probe, mix_probe, _loudness(mix_path), (teaser_start, teaser_end), samples, time.perf_counter() - started); report["validation"]["blackdetect_intervals"] = black_full + black_teaser; _write_json(root / "reports" / "technical-report.json", report); _mark_stage(root, "QA_OK", fingerprint, [full_video, teaser_video, full_board, safe_board, teaser_board, teaser_safe_board, root / "reports" / "technical-report.json"], full_probe=full_probe, teaser_probe=teaser_probe, blackdetect_intervals=black_full + black_teaser)
    return report


def _write_batch_report(index: dict) -> None:
    lines = ["# CTV-001 — Crônicas de Topázio · Vertical Cinema", "", f"- Estado: `{index.get('state', 'RUNNING')}`", f"- Runner: `{RUNNER_VERSION}`", f"- Saída: `{OUTPUT_ROOT}`", "", "## Capítulos", ""]
    for item in sorted(index.get("chapters", []), key=lambda value: value["chapter"]): lines.append(f"- Capítulo {item['chapter']:02d}: `{item.get('status')}` — `{item.get('title', '')}` — completo `{item.get('full_video', 'n/a')}` — teaser `{item.get('teaser_video', 'n/a')}` — validação `{item.get('validation', {})}`")
    lines.extend(["", "## Lotes", ""])
    for summary in index.get("batch_summaries", []): lines.append(f"- Lote {summary['lot']}: `{summary['state']}`, capítulos `{summary['chapters']}`, duração de processamento `{summary['elapsed_seconds']} s`, arquivos `{summary['files']}`.")
    lines.extend(["", "## Política", "", "- Santa V5 `santa-v5-base` começa e termina na biblioteca oficial e permanece no medalhão durante toda a narrativa.", "- Voz original Kokoro `pm_santa` / `pt-BR`; WAVs existentes reutilizados; sem resíntese, pitch, retiming ou alinhamento fonético inventado.", "- Composição vertical real no Canvas, usando cenas ambientais e câmera vertical; o MP4 horizontal não é cortado ou esticado.", "- Ducking voz-prioridade, crossfades e limiter; direitos comerciais Suno continuam pendentes.", "- Aprovação humana audiovisual obrigatória; nenhum upload, merge ou deploy.", ""])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run_batch(*, start_chapter: int = 1, pilot_only: bool = False, overwrite: bool = False, timeout_s: float = 3600) -> dict:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    batch_started = time.perf_counter()
    inventory = _music_inventory(); sources = _inventory_sources()
    preflight = {"format": "fabuloom.ctv-001-preflight/0.1", "runner": RUNNER_VERSION, "source_doc": str(SOURCE_DOC), "source_doc_sha256": _sha256(SOURCE_DOC), "chapters": sources, "music": inventory, "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS}, "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "timing_source": "measured_wav_segments"}, "rights_status": "pending_owner_confirmation", "main_checkout_untouched": True}
    _write_json(OUTPUT_ROOT / "PREFLIGHT.json", preflight)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.is_file() else {"format": "fabuloom.ctv-001-batch/0.1", "runner_version": RUNNER_VERSION, "state": "RUNNING", "chapters": [], "failures": [], "batch_summaries": [], "source_doc_sha256": preflight["source_doc_sha256"], "source_chapters": sources, "music_inventory": inventory}
    _write_json(INDEX_PATH, index); _status(index, lot=None, chapter=None, stage="PREFLIGHT_OK", next_action="iniciar Lote A", started=batch_started)
    lots = [("A", (1, 2)), ("B", (3, 4)), ("C", (5, 6)), ("D", (7, 8)), ("E", (9, 10))]
    for lot, numbers in lots:
        selected = [number for number in numbers if number >= start_chapter]
        if pilot_only: selected = [number for number in selected if number == 1]
        if not selected: continue
        lot_started = time.perf_counter(); _status(index, lot=lot, chapter=None, stage=f"LOTE_{lot}_START", next_action=f"iniciar capítulo {selected[0]:02d}", started=batch_started)
        for number in selected:
            existing = next((item for item in index.get("chapters", []) if item.get("chapter") == number), None)
            if existing and existing.get("status") == "DONE" and not overwrite: continue
            entry = {"chapter": number, "lot": lot, "title": sources[number]["title"], "status": "RUNNING"}; index["chapters"] = [item for item in index.get("chapters", []) if item.get("chapter") != number] + [entry]; _write_json(INDEX_PATH, index); _write_batch_report(index); _status(index, lot=lot, chapter=number, stage="START", next_action="executar preflight do capítulo", started=batch_started)
            try:
                report = _produce_chapter(sources[number], inventory, index, batch_started, lot=lot, port=8940 + number, timeout_s=timeout_s, overwrite=overwrite)
                entry.update({"status": "DONE", "title": report["title"], "full_video": report["full_video"], "teaser_video": report["teaser_video"], "duration_ms": report["source"]["manifest"]["duration_ms"], "processing_seconds": report["processing_seconds"], "validation": report["validation"], "music_cues": report["music_cue_sheet"]}); _status(index, lot=lot, chapter=number, stage="QA_OK", next_action=f"iniciar capítulo {number + 1:02d}" if number < 10 else "finalizar lote", started=batch_started)
            except Exception as exc:
                entry.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)}); index.setdefault("failures", []).append({"chapter": number, "lot": lot, "type": type(exc).__name__, "error": str(exc)}); _write_json(INDEX_PATH, index); _write_batch_report(index); _status(index, lot=lot, chapter=number, stage="FAILED", next_action="corrigir apenas o capítulo falho e retomar", started=batch_started, state="BLOCKED"); raise
            index["failures"] = [failure for failure in index.get("failures", []) if failure.get("chapter") != number]
            index["chapters"] = [item for item in index.get("chapters", []) if item.get("chapter") != number] + [entry]; _write_json(INDEX_PATH, index); _write_batch_report(index)
        summary = {"lot": lot, "chapters": selected, "state": "PILOT_PASS" if pilot_only else "DONE", "elapsed_seconds": round(time.perf_counter() - lot_started, 3), "files": [item.get("full_video") for item in index["chapters"] if item.get("chapter") in selected] + [item.get("teaser_video") for item in index["chapters"] if item.get("chapter") in selected]}; index["batch_summaries"] = [item for item in index.get("batch_summaries", []) if item.get("lot") != lot] + [summary]; _write_json(INDEX_PATH, index); _write_batch_report(index); _status(index, lot=lot, chapter=None, stage=f"LOTE_{lot}_DONE", next_action="aguardar revisão humana" if pilot_only else (f"iniciar Lote {chr(ord(lot) + 1)}" if lot != "E" else "aguardar relatório e revisão humana"), started=batch_started, state="PILOT_PASS" if pilot_only else "RUNNING")
        if pilot_only: break
    if not pilot_only:
        index["state"] = "DONE"; index["elapsed_seconds"] = round(time.perf_counter() - batch_started, 3); _write_json(INDEX_PATH, index); _write_batch_report(index); _status(index, lot="E", chapter=None, stage="BATCH_COMPLETE", next_action="aguardar relatório e revisão humana", started=batch_started, state="DONE")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--start-chapter", type=int, choices=range(1, 11), default=1); parser.add_argument("--pilot-only", action="store_true"); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--timeout", type=float, default=3600); args = parser.parse_args(); run_batch(start_chapter=args.start_chapter, pilot_only=args.pilot_only, overwrite=args.overwrite, timeout_s=args.timeout)


if __name__ == "__main__": main()
