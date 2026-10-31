"""Render Mission 017.2 with a measured framing crop and reused Mission 017 audio."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from narrator_mode_demo import FPS, HEIGHT, STUDIO_ROOT, WIDTH, _capture, _frame_board, _probe_export, _render_mp4

EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
SOURCE_ID = "fabuloom-narrator-mode-v1"
PREVIOUS_ID = "fabuloom-narrator-mode-v1.1-face-correction"
OUTPUT_ID = "fabuloom-narrator-mode-v1.2-framing"


def _face_comparison_board(before_frames: Path, after_frames: Path, output: Path) -> None:
    before = before_frames / "000240.png"
    after = after_frames / "000240.png"
    if not before.is_file() or not after.is_file():
        raise FileNotFoundError("equivalent before/after frame 240 is required")
    crop = "crop=420:420:30:630,scale=620:620:flags=lanczos"
    filters = [
        f"[0:v]{crop},drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='V1.1 · frame 240':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.86[a]",
        f"[1:v]{crop},drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='V1.2 · frame 240':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.86[b]",
        "[a][b]hstack=inputs=2[out]",
    ]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(before), "-i", str(after), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _expression_board(frames: Path, output: Path) -> None:
    samples = [(0, "neutro"), (130, "piscada"), (181, "boca aberta"), (107, "inclinação +"), (300, "inclinação -")]
    inputs = []
    filters = []
    for index, label in samples:
        path = frames / f"{index:06d}.png"
        if not path.is_file(): raise FileNotFoundError(path)
        inputs += ["-i", str(path)]
        slot = chr(97 + len(filters))
        filters.append(f"[{len(filters)}:v]crop=420:420:30:630,scale=360:360:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{label}':fontcolor=white:fontsize=24:x=16:y=16:box=1:boxcolor=0x07142A@.86[{slot}]")
    filters += ["[a][b]hstack=inputs=2[topraw]", "[topraw]pad=1080:360:0:0:color=0x061329[top]", "[c][d][e]hstack=inputs=3[bottom]", "[top][bottom]vstack=inputs=2[out]"]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], check=True, cwd=output.parent)


def _safe_area_overlay(frame: Path, output: Path) -> None:
    # The safe rectangle is the approved normalized area mapped to the 330 px
    # production avatar at (74,676): left=94, top≈688, width≈290, height≈307.
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame),
        "-vf", "drawbox=x=94:y=688:w=290:h=307:color=0x5BDDEB@0.9:t=3,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='área segura do rosto':fontcolor=0x5BDDEB:fontsize=24:x=92:y=650:box=1:boxcolor=0x07142A@.86",
        "-frames:v", "1", str(output),
    ], check=True, cwd=output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true", help="reuse an existing deterministic frame directory")
    parser.add_argument("--port", type=int, default=8784)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    video_root = export_root / "videos"
    manifest = export_root / f"{SOURCE_ID}.json"
    audio = video_root / f"{SOURCE_ID}.wav"
    previous_frames = video_root / f".{PREVIOUS_ID}-frames"
    frames = video_root / f".{OUTPUT_ID}-frames"
    output = video_root / f"{OUTPUT_ID}.mp4"
    board = video_root / f"{OUTPUT_ID}-frames.png"
    comparison = video_root / f"{OUTPUT_ID}-before-after.png"
    expressions = video_root / f"{OUTPUT_ID}-expressions.png"
    safe_area = video_root / f"{OUTPUT_ID}-safe-area.png"
    report = video_root / f"{OUTPUT_ID}-report.md"
    visual_report = video_root / f"{OUTPUT_ID}-visual-inspection.json"

    if not manifest.is_file() or not audio.is_file() or not previous_frames.is_dir():
        raise FileNotFoundError("Mission 017 manifest/WAV and Mission 017.1 frames are required; no synthesis is performed")
    if output.exists() and not args.overwrite: raise FileExistsError(f"video already exists: {output}; pass --overwrite")
    if frames.exists() and not args.reuse_capture:
        if not args.overwrite: raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    if args.reuse_capture and not frames.is_dir(): raise FileNotFoundError(f"capture directory does not exist: {frames}")
    frames.mkdir(parents=True, exist_ok=True)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    duration_ms = int(payload["duration_ms"])
    started = time.perf_counter()
    capture = {"frame_count": len(list(frames.glob("*.png"))), "fps": FPS, "reused": True} if args.reuse_capture else _capture(STUDIO_ROOT, frames, manifest, args.port, args.capture_timeout)
    if capture["frame_count"] <= 0: raise ValueError("capture has no PNG frames")
    _render_mp4(frames, audio, output, duration_ms, args.overwrite)
    _frame_board(frames, board, duration_ms)
    _face_comparison_board(previous_frames, frames, comparison)
    _expression_board(frames, expressions)
    _safe_area_overlay(frames / "000240.png", safe_area)
    probe = _probe_export(output)
    elapsed = time.perf_counter() - started
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")

    report.write_text("\n".join([
        "# Fabuloom Narrator Mode V1.2 — final avatar framing",
        "",
        f"- Áudio e manifesto reutilizados: `{audio}` / `{manifest}`.",
        "- Nova síntese Kokoro: `não executada`.",
        f"- Voz: `{payload.get('metadata', {}).get('voice_id', 'pm_santa')}` · idioma `pt-BR`.",
        f"- Duração medida: `{duration_ms} ms`; segmentos: `{len(payload['segments'])}`.",
        "- Crop V1.2: `{ x: 245, y: 35, width: 590, height: 590 }`.",
        "- Área segura normalizada: `{ left: 0.06, top: 0.035, right: 0.94, bottom: 0.965 }`.",
        f"- Frames: `{frames}` ({capture['frame_count']} em {FPS} fps).",
        f"- MP4: `{output}` ({output.stat().st_size} bytes).",
        f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']}` {video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`.",
        f"- Prancha de poses: `{board}`.",
        f"- Comparação V1.1/V1.2: `{comparison}`.",
        f"- Prancha de cinco estados faciais: `{expressions}`.",
        f"- Evidência de área segura: `{safe_area}`.",
        "- A alteração desta missão está limitada ao enquadramento; cenário, legendas, voz, áudio, rig e assets oficiais foram preservados.",
        "- Aprovação artística humana continua obrigatória.",
        "",
    ]), encoding="utf-8")
    visual_report.write_text(json.dumps({
        "format": "fabuloom.visual-inspection-narrator/0.3",
        "mode": "narrator-mode-v1.2-framing",
        "source": str(output),
        "previous_source": str(previous_frames / "000240.png"),
        "after_source": str(frames / "000240.png"),
        "crop": {"x": 245, "y": 35, "width": 590, "height": 590},
        "safe_area": {"left": 0.06, "top": 0.035, "right": 0.94, "bottom": 0.965},
        "checks": {"canvas": [WIDTH, HEIGHT], "avatar": "circular-clipped", "facial_layers_only": True, "mouth_source": "pcm16_rms_envelope", "captions": "measured_segment_ranges", "deterministic_frame_count": capture["frame_count"], "human_review_required": True},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={manifest}"); print(f"audio_reused={audio}"); print(f"frames={frames}"); print(f"video={output}"); print(f"board={board}"); print(f"comparison={comparison}"); print(f"expressions={expressions}"); print(f"safe_area={safe_area}"); print(f"report={report}"); print(f"visual_report={visual_report}"); print(f"duration_ms={duration_ms}"); print(f"processing_seconds={elapsed:.3f}"); print(f"probe={json.dumps(probe, ensure_ascii=False)}"); print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
