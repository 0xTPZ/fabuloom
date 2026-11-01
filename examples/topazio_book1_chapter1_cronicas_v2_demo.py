"""Render Mission 026.1 without changing the approved Mission 026 episode.

The V2 reuses the measured Mission 026 manifest and WAVs, keeps the official
Santa renderer, makes Santa a persistent story medalion, increases the visual
storyboard to 36 purposeful shots, registers reusable character identities, and
raises the musical presence with a new sidechain mix.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

import topazio_book1_chapter1_cronicas_demo as v1

from fabuloom_core.character_registry import CharacterRegistry
from fabuloom_core.scene_assets import SceneAssetRegistry


FABULOOM_ROOT = Path(r"E:\Fabuloom")
EXPORT_ROOT = FABULOOM_ROOT / "workspace" / "exports"
V1_PROJECT_ROOT = EXPORT_ROOT / "topazio-book1-capitulo1-cronicas"
PROJECT_ID = "topazio-book1-capitulo1-cronicas-v2"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
MUSIC = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1" / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "scene-registry.json"
CHARACTER_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "character-registry.json"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
TRANSITION_MS = 900


# These are editorially ordered shots.  They are assigned to measured story
# segments in order, so no visual cut is inserted in the middle of an audio
# segment.  Repeated plates use a different crop/camera treatment, not a new
# story event.
SHOT_SPECS = (
    ("shot-001-topazio-wide", "01-topazio-nightwide-v2.png", "topazio-wide", None),
    ("shot-002-rivers-suspended", "02-river-detail-v2.png", "river-drift", None),
    ("shot-003-river-city-reaction", "02-vila-rios-suspensos.png", "frozen-river", None),
    ("shot-004-flames-frozen", "04-flame-detail-v2.png", "flame-detail", None),
    ("shot-005-temple-approach", "03-templo-gaia-crack.png", "temple-approach", None),
    ("shot-006-temple-crack", "03-templo-gaia-crack.png", "crystal_approach", None),
    ("shot-007-crystal-altar", "06-temple-altar-v2.png", "altar-push", None),
    ("shot-008-crystal-close", "06-temple-altar-v2.png", "crystal_pulse", None),
    ("shot-009-echo-entrance", "04-caverna-do-eco.png", "cave_push", "thaurion-v1-base"),
    ("shot-010-memory-pillars", "09-echo-pillars-v2.png", "memory-drift", "thaurion-v1-base"),
    ("shot-011-thaurion-awakens", "thaurion-v1-base.png", "portrait-breathe", "thaurion-v1-base"),
    ("shot-012-currents-wide", "05-correntes-eternas.png", "wind_lateral", None),
    ("shot-013-zephirion", "zephirion-v1-base.png", "portrait-pan", "zephirion-v1-base"),
    ("shot-014-wind-stops", "05-correntes-eternas.png", "wind-stop", None),
    ("shot-015-vordros-wide", "06-vordros-frozen.png", "snow_breath", None),
    ("shot-016-snowflake", "15-vordros-close-v2.png", "snowflake-close", None),
    ("shot-017-glaciron", "glaciron-v1-base.png", "portrait-breathe", "glaciron-v1-base"),
    ("shot-018-sea-nym-wide", "07-sea-corals.png", "water_drift", None),
    ("shot-019-inverted-current", "18-nym-abyssal-v2.png", "water-invert", None),
    ("shot-020-abyssal", "abyssal-v1-base.png", "portrait-pan", "abyssal-v1-base"),
    ("shot-021-osai-volcano", "08-vulcao-osai.png", "ember_pulse", None),
    ("shot-022-emberion", "emberion-v1-base.png", "portrait-breathe", "emberion-v1-base"),
    ("shot-023-ember-detail", "08-vulcao-osai.png", "ember-detail", None),
    ("shot-024-village-wide", "09-vila-incendio.png", "fire_pan", None),
    ("shot-025-aurelion", "aurelion-v1-base.png", "portrait-pan", "aurelion-v1-base"),
    ("shot-026-village-ash", "09-vila-incendio.png", "ash_pull", None),
    ("shot-027-luminor-temple", "27-luminor-temple-v2.png", "luminor-rise", "luminor-v1-base"),
    ("shot-028-light-failure", "27-luminor-temple-v2.png", "light-failure", None),
    ("shot-029-crystal-pulse-one", "06-temple-altar-v2.png", "crystal_pulse", None),
    ("shot-030-crystal-pulse-two", "03-templo-gaia-crack.png", "crystal-pulse-wide", None),
    ("shot-031-fissure-close", "03-templo-gaia-crack.png", "fissure-close", None),
    ("shot-032-fissure-reflection", "06-temple-altar-v2.png", "fissure-reflection", None),
    ("shot-033-final-atmosphere", "01-topazio-nightwide-v2.png", "topazio-return", None),
    ("shot-034-final-crystal", "06-temple-altar-v2.png", "crystal_final", None),
    ("shot-035-final-pulse", "03-templo-gaia-crack.png", "crystal-pulse-wide", None),
    ("shot-036-story-to-library", "01-topazio-nightwide-v2.png", "story-fade", None),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _copy_visual_assets() -> None:
    target = PROJECT_ROOT / "assets" / "generated"
    source = V1_PROJECT_ROOT / "assets" / "generated"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("02-vila-rios-suspensos.png", "03-templo-gaia-crack.png", "04-caverna-do-eco.png", "05-correntes-eternas.png", "06-vordros-frozen.png", "07-sea-corals.png", "08-vulcao-osai.png", "09-vila-incendio.png"):
        source_path = source / name
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        shutil.copyfile(source_path, target / name)


def _copy_measured_audio(source_manifest: dict) -> dict:
    copied = copy.deepcopy(source_manifest)
    copied["id"] = PROJECT_ID
    copied["timeline_id"] = f"{PROJECT_ID}-timeline"
    copied["metadata"] = dict(copied.get("metadata", {}))
    copied["metadata"].update({"visual_revision": "026.1-v2", "audio_reused_from": "topazio-book1-capitulo1-cronicas"})
    target_dir = PROJECT_ROOT / "audio" / "voice-segments"
    target_dir.mkdir(parents=True, exist_ok=True)
    for index, segment in enumerate(copied["segments"]):
        source_path = v1._local_audio_path(segment["audio_uri"])
        target_path = target_dir / f"{index:04d}.wav"
        shutil.copyfile(source_path, target_path)
        segment["audio_uri"] = v1._audio_uri(target_path)
    return copied


def _split_evenly(items: list[dict], count: int) -> list[list[dict]]:
    if len(items) < count:
        raise ValueError(f"cannot create {count} shots from {len(items)} measured segments")
    quotient, remainder = divmod(len(items), count)
    groups: list[list[dict]] = []
    cursor = 0
    for index in range(count):
        size = quotient + (1 if index < remainder else 0)
        groups.append(items[cursor:cursor + size])
        cursor += size
    return groups


def _shot_image(filename: str) -> str:
    if filename.endswith(".png") and filename.split(".")[0].split("-")[-1].isdigit():
        return f"{PROJECT_ID}/assets/generated/{filename}"
    if filename in {"01-topazio-nightwide-v2.png", "02-river-detail-v2.png", "04-flame-detail-v2.png", "06-temple-altar-v2.png", "09-echo-pillars-v2.png", "15-vordros-close-v2.png", "18-nym-abyssal-v2.png", "27-luminor-temple-v2.png"}:
        return f"{PROJECT_ID}/assets/generated/{filename}"
    if filename.endswith("-v1-base.png"):
        return f"{PROJECT_ID}/assets/characters/{filename}"
    return f"{PROJECT_ID}/assets/generated/{filename}"


def build_scene_schedule(manifest: dict) -> tuple[dict, ...]:
    blocks = manifest["metadata"]["editorial_blocks"]
    intro = next(item for item in blocks if item["type"] == "HOST_INTRO")
    outro = next(item for item in blocks if item["type"] == "HOST_OUTRO")
    scenes: list[dict] = [
        {"id": "host-library-opening", "kind": "host", "asset_id": "santa-library-topazioverse-v1", "image": "official-scenes/santa-library-topazioverse-v1/library-base.png", "camera": "host_wide", "start_ms": intro["start_ms"], "end_ms": intro["end_ms"], "source_paragraphs": []}
    ]
    story_segments = [segment for segment in manifest["segments"] if segment.get("metadata", {}).get("editorial_block") == "STORY_CHAPTER"]
    groups = _split_evenly(story_segments, len(SHOT_SPECS))
    for (shot_id, filename, camera, character_id), group in zip(SHOT_SPECS, groups, strict=True):
        metadata = [segment.get("metadata", {}) for segment in group]
        source_paragraphs = sorted({int(item["source_paragraph"]) for item in metadata if "source_paragraph" in item})
        scenes.append({
            "id": shot_id,
            "kind": "story",
            "image": _shot_image(filename),
            "camera": camera,
            "start_ms": int(group[0]["start_ms"]),
            "end_ms": int(group[-1]["end_ms"]) + int(group[-1].get("metadata", {}).get("pause_after_ms", 0)),
            "source_paragraphs": source_paragraphs,
            "character_registry_id": character_id,
        })
    scenes.append({"id": "host-library-closing", "kind": "host", "asset_id": "santa-library-topazioverse-v1", "image": "official-scenes/santa-library-topazioverse-v1/library-base.png", "camera": "host_closing", "start_ms": outro["start_ms"], "end_ms": outro["end_ms"], "source_paragraphs": []})
    scenes.sort(key=lambda item: (item["start_ms"], item["id"]))
    scenes[-1]["end_ms"] = int(manifest["duration_ms"])
    if scenes[0]["start_ms"] != 0 or scenes[-1]["end_ms"] != manifest["duration_ms"]:
        raise ValueError("scene schedule does not cover the measured episode")
    return tuple(scenes)


def mix_audio_v2(voice: Path, music_loop: Path, sfx: Path, output: Path, duration_ms: int) -> None:
    duration = duration_ms / 1000
    graph = (
        "[0:a]aresample=48000,pan=mono|c0=c0,asplit=2[voice][det];"
        "[voice]pan=stereo|c0=c0|c1=c0[voice_st];"
        f"[1:a]aresample=48000,volume=0.13,atrim=duration={duration:.3f},afade=t=in:st=0:d=2,afade=t=out:st={max(0, duration - 5):.3f}:d=5[music];"
        "[music][det]sidechaincompress=threshold=0.020:ratio=5:attack=45:release=650:makeup=1:link=average[ducked];"
        f"[2:a]aresample=48000,volume=0.12,atrim=duration={duration:.3f}[sfx];"
        "[voice_st][ducked][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.90:attack=5:release=500[out]"
    )
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(voice), "-i", str(music_loop), "-i", str(sfx),
        "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)
    ], check=True)


def _capture_frames(timeline_path: Path, frames_root: Path, *, port: int, timeout_seconds: float) -> tuple[Path, dict]:
    edge = v1._find_edge()
    frames_root.mkdir(parents=True, exist_ok=True)
    session = f"capture-{int(time.time())}"
    session_dir = frames_root / session
    session_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=frames_root))
    env = os.environ.copy()
    env.update({"FABULOOM_WORKSPACE_ROOT": str(FABULOOM_ROOT), "FABULOOM_EXPORT_ROOT": str(EXPORT_ROOT)})
    server = subprocess.Popen([
        sys.executable, str(Path(__file__).resolve().parents[1] / "frontend" / "server.py"), "--port", str(port), "--capture-dir", str(frames_root)
    ], cwd=str(Path(__file__).resolve().parents[1]), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        v1._wait_for_http(f"http://127.0.0.1:{port}/capture-topazio-book1-chapter1-v2.html", 20)
        relative = timeline_path.relative_to(EXPORT_ROOT).as_posix()
        url = f"http://127.0.0.1:{port}/capture-topazio-book1-chapter1-v2.html?session={session}&timeline=/exports/{relative}&fps={FPS}"
        command = [edge, "--headless=new", "--disable-gpu", "--dump-dom", "--hide-scrollbars", "--window-size=1920,1080", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3600000", f"--user-data-dir={profile_dir}", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session_dir / "complete.json"
        error = session_dir / "error.json"
        deadline = time.monotonic() + timeout_seconds
        try:
            while not complete.exists() and not error.exists() and time.monotonic() < deadline:
                time.sleep(0.25)
            if error.exists():
                raise RuntimeError(error.read_text(encoding="utf-8"))
            if not complete.exists():
                raise TimeoutError(f"Canvas capture did not complete: {session_dir}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            frames = v1._materialize_frames(session_dir, completion)
            expected = int(completion["frame_count"])
            if len(frames) != expected:
                raise RuntimeError(f"capture incomplete: expected {expected} frames, found {len(frames)}")
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


def _measure_levels(path: Path) -> dict[str, str]:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"], capture_output=True, text=True, check=True)
    text = result.stderr
    values: dict[str, str] = {}
    for key in ("mean_volume", "max_volume"):
        for line in text.splitlines():
            if key in line:
                values[key] = line.split(":", 1)[1].strip()
    return values


def audit_santa_visibility(session_dir: Path, scenes: list[dict], *, frame_count: int) -> dict:
    """Inspect the rendered JPEG crop where Santa must appear for every scene."""
    samples = []
    for scene in scenes:
        timestamp_ms = int((int(scene["start_ms"]) + int(scene["end_ms"])) / 2)
        frame_index = min(frame_count - 1, max(0, round(timestamp_ms / 1000 * FPS)))
        frame = session_dir / f"{frame_index:06d}.jpg"
        if not frame.is_file():
            raise RuntimeError(f"missing rendered sample frame for {scene['id']}: {frame}")
        if scene.get("kind") == "host":
            crop = "crop=560:560:20:480"
        else:
            crop = "crop=340:340:20:720"
        result = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(frame), "-vf", f"{crop},signalstats,metadata=print:file=-", "-frames:v", "1", "-f", "null", "NUL"
        ], capture_output=True, text=True, check=True)
        output = result.stdout + result.stderr
        yavg_match = re.search(r"lavfi\.signalstats\.YAVG=([0-9.]+)", output)
        satavg_match = re.search(r"lavfi\.signalstats\.SATAVG=([0-9.]+)", output)
        if not yavg_match or not satavg_match:
            raise RuntimeError(f"signalstats did not produce a luminance sample for {scene['id']}")
        samples.append({
            "scene_id": scene["id"],
            "timestamp_ms": timestamp_ms,
            "frame_index": frame_index,
            "crop": crop,
            "yavg": float(yavg_match.group(1)),
            "satavg": float(satavg_match.group(1)),
            "rendered_frame": str(frame),
        })
    return {
        "policy": "all_scenes_medallion",
        "renderer": "NarratorAvatarRenderer",
        "sample_count": len(samples),
        "passed": all(item["yavg"] > 5.0 for item in samples),
        "method": "signalstats on rendered JPEG crops plus human inspection of shot board",
        "samples": samples,
    }


def _extract_comparison(v1_video: Path, v2_video: Path) -> Path:
    target = PROJECT_ROOT / "captures" / "v1-v2-comparison.png"
    times = (0, 194, 375)
    with tempfile.TemporaryDirectory(prefix="v1-v2-comparison-") as directory:
        sample_paths: list[Path] = []
        for video_index, video in enumerate((v1_video, v2_video)):
            for time_index, seconds in enumerate(times):
                sample = Path(directory) / f"sample-{video_index}-{time_index}.png"
                subprocess.run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(seconds), "-i", str(video), "-frames:v", "1", str(sample)
                ], check=True)
                sample_paths.append(sample)
        inputs: list[str] = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for sample in sample_paths:
            inputs.extend(["-i", str(sample)])
        filters = []
        for index in range(6):
            filters.append(f"[{index}:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:black[v{index}]")
        filters.extend(["[v0][v3]hstack=inputs=2[r0]", "[v1][v4]hstack=inputs=2[r1]", "[v2][v5]hstack=inputs=2[r2]", "[r0][r1][r2]vstack=inputs=3[out]"])
        subprocess.run(inputs + ["-filter_complex", ";".join(filters), "-map", "[out]", str(target)], check=True)
    return target


def _write_reports(manifest: dict, timeline: dict, video_probe: dict, mix_probe: dict, *, comparison: Path, registry: CharacterRegistry, v1_levels: dict[str, str], v2_levels: dict[str, str], processing_seconds: float, visibility: dict) -> None:
    reports = PROJECT_ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"- `{scene['id']}`: `{scene['start_ms']}–{scene['end_ms']} ms`, `{scene['camera']}`, parágrafos `{scene['source_paragraphs']}`" for scene in timeline["scenes"])
    (reports / "technical-report.md").write_text(
        "# Missão 026.1 — Refinamento cinematográfico\n\n"
        "A V2 é uma composição independente; a produção da Missão 026 permanece intacta.\n\n"
        f"- Duração: `{manifest['duration_ms']} ms`\n- Segmentos preservados: `{len(manifest['segments'])}`\n- Planos visuais: `{len(timeline['scenes'])}` (`{len(SHOT_SPECS)}` planos de história + abertura/encerramento)\n"
        f"- Processamento local: `{processing_seconds:.2f} s`\n- Vídeo: `{json.dumps(video_probe, ensure_ascii=False, sort_keys=True)}`\n- Comparação V1/V2: `{comparison}`\n"
        "- Santa V5: medalhão persistente em todas as cenas, desenhado pelo NarratorAvatarRenderer oficial; RMS continua sendo a fonte da boca.\n"
        "- Timestamps de palavras, fonemas e visemas: indisponíveis.\n\n## Planos\n\n" + lines + "\n",
        encoding="utf-8",
    )
    (reports / "mix-report-v2.md").write_text(
        "# Comparação de mixagem V1/V2\n\n"
        "A voz Kokoro e os WAVs medidos foram reutilizados sem nova síntese. A V2 aumenta a presença musical somente na música e mantém ducking sidechain.\n\n"
        f"- V1 mean/max: `{v1_levels}`\n- V2 mean/max: `{v2_levels}`\n- V2 música base: `0.13`\n- Ducking voz→música: ratio `5`, ataque `45 ms`, release `650 ms`.\n- SFX: `0.12`; limiter final: `0.90`.\n- Música: `{MUSIC}`; velocidade e tom preservados.\n- Direitos comerciais Suno: confirmação necessária antes de publicação.\n- FFprobe mix V2: `{json.dumps(mix_probe, ensure_ascii=False, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (reports / "character-registry-report.md").write_text(
        "# Character Registry — Capítulo 1\n\n"
        f"- Registry: `assets/character-registry.json`\n- Identidades registradas: `{len(registry.ids())}`\n- Aprovadas: `{registry.approved_ids()}`\n- DRAFT: `{tuple(item for item in registry.ids() if item not in registry.approved_ids())}`\n\n"
        "As sete propostas de guardiões são referências conceituais `DRAFT`; não foram promovidas ao cânone. Santa V5 é a única identidade aprovada neste registro.\n\n"
        "- Prancha: `captures/character-proposals-board.png`\n- Imagens-base locais: `assets/characters/`\n- Hashes SHA-256 verificados durante a renderização.\n- Consistência entre capítulos: mecanismo de reutilização por ID/hash implementado; continuidade artística ainda exige aprovação humana e não é garantida apenas por prompt.\n",
        encoding="utf-8",
    )
    visibility_report = dict(visibility)
    visibility_report.update({
        "scene_count": len(timeline["scenes"]),
        "host_mode": "large_library_avatar",
        "story_mode": "persistent_lower_left_medallion",
    })
    (reports / "santa-visibility-report.json").write_text(json.dumps(visibility_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8776)
    parser.add_argument("--capture-timeout", type=float, default=1800)
    args = parser.parse_args()
    for path in (MUSIC, V1_PROJECT_ROOT / "manifest.json", V1_PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo1.mp4"):
        if not path.is_file():
            raise FileNotFoundError(path)
    started = time.perf_counter()
    for directory in (PROJECT_ROOT / "audio", PROJECT_ROOT / "timeline", PROJECT_ROOT / "captures", PROJECT_ROOT / "reports", PROJECT_ROOT / "videos", PROJECT_ROOT / ".frames", PROJECT_ROOT / "assets" / "generated", PROJECT_ROOT / "assets" / "characters"):
        directory.mkdir(parents=True, exist_ok=True)
    _copy_visual_assets()
    scene_registry = SceneAssetRegistry.from_json(REGISTRY, workspace_root=FABULOOM_ROOT)
    library_path = scene_registry.resolve("santa-library-topazioverse-v1")
    character_registry = CharacterRegistry.from_json(CHARACTER_REGISTRY_PATH, workspace_root=FABULOOM_ROOT)
    for character_id in character_registry.ids():
        character_registry.resolve(character_id)
    source_manifest = json.loads((V1_PROJECT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest = _copy_measured_audio(source_manifest)
    manifest_path = PROJECT_ROOT / "manifest.json"
    _write_json(manifest_path, manifest)
    timeline_path = PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.json"
    timeline = {
        "format": "fabuloom.topazioverse-chapter/0.2",
        "title": "Crônicas de Topázio — Livro 1 — Capítulo 1: A noite em que Topázio parou",
        "manifest": f"{PROJECT_ID}/manifest.json",
        "duration_ms": manifest["duration_ms"],
        "transition_ms": TRANSITION_MS,
        "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
        "source_paragraphs": list(range(3, 23)),
        "music_asset": "workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "scene_registry": "assets/scene-registry.json",
        "character_registry": "assets/character-registry.json",
        "library_asset_id": "santa-library-topazioverse-v1",
        "narrator": "Santa V5",
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "timing_source": "measured_wav_segments_reused_from_mission_026",
        "word_phoneme_viseme_timing": "unavailable",
        "santa_visibility_policy": "all_scenes_medallion",
        "scenes": list(build_scene_schedule(manifest)),
    }
    _write_json(timeline_path, timeline)
    v1.write_srt(manifest, PROJECT_ROOT / "timeline" / f"{PROJECT_ID}.srt")
    voice_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-voice.wav"
    sample_rate, _ = v1.compose_voice(manifest, voice_path)
    sfx_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-sfx-bed.wav"
    v1._write_sfx_bed(sfx_path, int(manifest["duration_ms"]))
    music_loop_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-music-loop.wav"
    v1.make_crossfaded_music_loop(MUSIC, music_loop_path, int(manifest["duration_ms"]), overwrite=True)
    mix_path = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-mix.wav"
    mix_audio_v2(voice_path, music_loop_path, sfx_path, mix_path, int(manifest["duration_ms"]))
    session_dir, completion = _capture_frames(timeline_path, PROJECT_ROOT / ".frames", port=args.port, timeout_seconds=args.capture_timeout)
    visibility = audit_santa_visibility(session_dir, timeline["scenes"], frame_count=int(completion["frame_count"]))
    video_path = PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo1-v2.mp4"
    v1.render_mp4(session_dir, mix_path, video_path, int(manifest["duration_ms"]), overwrite=True)
    board_path = PROJECT_ROOT / "captures" / "chapter1-v2-frames.png"
    v1.frame_board(session_dir, board_path, int(completion["frame_count"]), overwrite=True)
    comparison = _extract_comparison(V1_PROJECT_ROOT / "videos" / "fabuloom-cronicas-de-topazio-livro1-capitulo1.mp4", video_path)
    video_probe = v1.probe(video_path)
    mix_probe = v1.probe(mix_path)
    v1_levels = _measure_levels(V1_PROJECT_ROOT / "audio" / "topazio-book1-capitulo1-cronicas-mix.wav")
    v2_levels = _measure_levels(mix_path)
    _write_reports(manifest, timeline, video_probe, mix_probe, comparison=comparison, registry=character_registry, v1_levels=v1_levels, v2_levels=v2_levels, processing_seconds=time.perf_counter() - started, visibility=visibility)
    report = {
        "project": PROJECT_ID,
        "video": str(video_path),
        "duration_ms": manifest["duration_ms"],
        "segments_preserved": len(manifest["segments"]),
        "visual_shots": len(SHOT_SPECS),
        "scenes": len(timeline["scenes"]),
        "frame_count": completion["frame_count"],
        "video_probe": video_probe,
        "mix_probe": mix_probe,
        "v1_audio_levels": v1_levels,
        "v2_audio_levels": v2_levels,
        "comparison": str(comparison),
        "library_id": "santa-library-topazioverse-v1",
        "character_registry_ids": character_registry.ids(),
        "character_registry_approved_ids": character_registry.approved_ids(),
        "santa_visibility": "all_scenes_medallion",
        "santa_visibility_audit": visibility,
        "timing_source": "measured_wav_segments_reused_from_mission_026",
        "mouth_source": "pcm16_rms_envelope",
        "word_phoneme_viseme_timing": "unavailable",
        "state": "completed_pending_human_artistic_review",
    }
    _write_json(PROJECT_ROOT / "reports" / "episode-result-v2.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
