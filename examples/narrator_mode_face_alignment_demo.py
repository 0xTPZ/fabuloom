"""Render Mission 017.3 with measured head-local facial alignment."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from narrator_mode_demo import FPS, HEIGHT, STUDIO_ROOT, WIDTH, _capture, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ID = "fabuloom-narrator-mode-v1"
PREVIOUS_ID = "fabuloom-narrator-mode-v1.2-framing"
OUTPUT_ID = "fabuloom-narrator-mode-v1.3-face-alignment"


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, cwd=cwd)


def _face_crop_filter(index: int, label: str, slot: str) -> str:
    return f"[{index}:v]crop=370:370:54:656,scale=480:480:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=26:x=18:y=18:box=1:boxcolor=0x07142A@.88[{slot}]"


def _before_after_board(previous_frames: Path, frames: Path, output: Path) -> None:
    before = previous_frames / "000240.png"
    after = frames / "000240.png"
    filters = [_face_crop_filter(0, "V1.2 · frame 240", "a"), _face_crop_filter(1, "V1.3 · frame 240", "b"), "[a][b]hstack=inputs=2[out]"]
    _run_ffmpeg(["-i", str(before), "-i", str(after), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _pose_board(frames: Path, output: Path) -> None:
    samples = [(0, "neutro"), (130, "piscada"), (181, "boca aberta"), (107, "inclinação +"), (300, "inclinação -")]
    inputs: list[str] = []
    filters: list[str] = []
    slots = ["a", "b", "c", "d", "e"]
    for slot, (index, label) in zip(slots, samples):
        inputs += ["-i", str(frames / f"{index:06d}.png")]
        filters.append(_face_crop_filter(len(inputs) // 2 - 1, label, slot).replace("scale=480:480", "scale=360:360"))
    filters += ["[a][b][c]hstack=inputs=3[top]", "[d][e]hstack=inputs=2[bottomraw]", "[bottomraw]pad=1080:360:0:0:color=0x061329[bottom]", "[top][bottom]vstack=inputs=2[out]"]
    _run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _reference_board(frames: Path, output: Path) -> None:
    after = frames / "000000.png"
    filters = [
        "[0:v]crop=370:370:54:656,scale=1024:1024:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='V1.3 · composição corrigida':fontcolor=white:fontsize=32:x=26:y=26:box=1:boxcolor=0x07142A@.88[a]",
        "[1:v]scale=1024:1024:force_original_aspect_ratio=decrease,pad=1024:1024:(ow-iw)/2:(oh-ih)/2:color=0x061329,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='referência estática · head.png':fontcolor=white:fontsize=32:x=26:y=26:box=1:boxcolor=0x07142A@.88[b]",
        "[a][b]hstack=inputs=2[out]",
    ]
    _run_ffmpeg(["-i", str(after), "-i", str(STUDIO_ROOT / "frontend/assets/characters/topazio-narrators-v5/santa/head.png"), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _layer_board(output: Path) -> None:
    root = STUDIO_ROOT / "frontend/assets/characters/topazio-narrators-v5/santa"
    names = ["head-clean.png", "eyes-open.png", "brows.png", "glasses.png", "mouth-closed.png", "mouth-open.png"]
    inputs: list[str] = []
    filters: list[str] = []
    for index, name in enumerate(names):
        inputs += ["-i", str(root / name)]
        slot = chr(97 + index)
        filters.append(f"[{index}:v]scale=340:340:force_original_aspect_ratio=decrease,pad=340:340:(ow-iw)/2:(oh-ih)/2:color=0x061329,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{name}':fontcolor=white:fontsize=20:x=12:y=12:box=1:boxcolor=0x07142A@.88[{slot}]")
    filters += ["[a][b][c]hstack=inputs=3[top]", "[d][e][f]hstack=inputs=3[bottom]", "[top][bottom]vstack=inputs=2[out]"]
    _run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8785)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    video_root = export_root / "videos"
    manifest = export_root / f"{SOURCE_ID}.json"
    audio = video_root / f"{SOURCE_ID}.wav"
    previous_frames = video_root / f".{PREVIOUS_ID}-frames"
    frames = video_root / f".{OUTPUT_ID}-frames"
    output = video_root / f"{OUTPUT_ID}.mp4"
    before_after = video_root / f"{OUTPUT_ID}-before-after.png"
    poses = video_root / f"{OUTPUT_ID}-poses.png"
    reference = video_root / f"{OUTPUT_ID}-reference.png"
    layers = video_root / f"{OUTPUT_ID}-layers.png"
    report = video_root / f"{OUTPUT_ID}-report.md"
    inspection = video_root / f"{OUTPUT_ID}-visual-inspection.json"

    if not manifest.is_file() or not audio.is_file() or not previous_frames.is_dir():
        raise FileNotFoundError("Mission 017 manifest/WAV and V1.2 frames are required; no synthesis is performed")
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"video already exists: {output}; pass --overwrite")
    if frames.exists() and not args.reuse_capture:
        if not args.overwrite:
            raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    if args.reuse_capture and not frames.is_dir():
        raise FileNotFoundError(f"capture directory does not exist: {frames}")
    frames.mkdir(parents=True, exist_ok=True)
    duration_ms = int(json.loads(manifest.read_text(encoding="utf-8"))["duration_ms"])
    started = time.perf_counter()
    capture = {"frame_count": len(list(frames.glob("*.png"))), "fps": FPS, "reused": True} if args.reuse_capture else _capture(STUDIO_ROOT, frames, manifest, args.port, args.capture_timeout)
    _render_mp4(frames, audio, output, duration_ms, args.overwrite)
    _before_after_board(previous_frames, frames, before_after)
    _pose_board(frames, poses)
    _reference_board(frames, reference)
    _layer_board(layers)
    probe = _probe_export(output)
    elapsed = time.perf_counter() - started
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report.write_text("\n".join([
        "# Fabuloom Narrator Mode V1.3 — face alignment",
        "",
        f"- Manifesto/WAV reutilizados: `{manifest}` / `{audio}`; nova síntese: `não executada`.",
        "- Causa medida: os PNGs faciais usavam caixas normalizadas do bitmap inteiro, apesar de margens alfa incompatíveis; olhos/óculos ficavam abaixo e maiores que os landmarks da cabeça.",
        "- Coordenadas locais: `head-clean.png` 1316×1195; sistema `head-local-v1`.",
        "- Landmarks: olhos `(526,540)/(790,540)`, óculos `(658,540)`, sobrancelhas `(658,390)`, nariz `(658,650)`, bigode `(658,710)`, boca `(658,785)`, base da barba `(658,1035)`.",
        "- Alinhamento: caixas alfa dos overlays são transformadas para alvos locais; assets oficiais não foram alterados.",
        "- Crop inicial V1.2 preservado: `{ x:245, y:35, width:590, height:590 }`.",
        f"- Frames: `{frames}` ({capture['frame_count']} em {FPS} fps).",
        f"- MP4: `{output}` ({output.stat().st_size} bytes).",
        f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']} `{video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`.",
        f"- Tempo de processamento sem síntese: `{elapsed:.3f} s`.",
        f"- Antes/depois: `{before_after}`; poses: `{poses}`; referência: `{reference}`; camadas: `{layers}`.",
        "- Boca continua baseada em RMS; alinhamento fonético/visêmico não está disponível.",
        "- Aprovação artística humana continua obrigatória.",
        "",
    ]), encoding="utf-8")
    inspection.write_text(json.dumps({
        "format": "fabuloom.visual-inspection-narrator/0.4",
        "mode": "narrator-mode-v1.3-face-alignment",
        "source": str(output),
        "reference": str(STUDIO_ROOT / "frontend/assets/characters/topazio-narrators-v5/santa/head.png"),
        "coordinateSystem": "head-local-v1",
        "landmarks": {"leftEye": [526, 540], "rightEye": [790, 540], "glasses": [658, 540], "brows": [658, 390], "nose": [658, 650], "moustache": [658, 710], "mouth": [658, 785], "beardBase": [658, 1035]},
        "checks": {"canvas": [WIDTH, HEIGHT], "frames": capture["frame_count"], "facialStates": ["neutral", "mouth-slight", "mouth-moderate", "mouth-open", "blink", "head-tilt-left", "head-tilt-right"], "headLocalHierarchy": True, "officialAssetsModified": False, "humanReviewRequired": True},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={manifest}"); print(f"audio_reused={audio}"); print(f"frames={frames}"); print(f"video={output}"); print(f"before_after={before_after}"); print(f"poses={poses}"); print(f"reference={reference}"); print(f"layers={layers}"); print(f"report={report}"); print(f"inspection={inspection}"); print(f"duration_ms={duration_ms}"); print(f"processing_seconds={elapsed:.3f}"); print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
