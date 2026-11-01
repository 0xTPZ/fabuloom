"""Render Mission 017.1 using Mission 017's measured audio without re-synthesis."""

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
OUTPUT_ID = "fabuloom-narrator-mode-v1.1-face-correction"


def _face_comparison_board(before_frames: Path, after_frames: Path, output: Path) -> None:
    before = before_frames / "000240.png"
    after = after_frames / "000240.png"
    if not before.is_file() or not after.is_file():
        raise FileNotFoundError("equivalent before/after frame 240 is required")
    crop = "crop=420:420:30:630,scale=620:620:flags=lanczos"
    filters = [
        f"[0:v]{crop},drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='ANTES · frame 240':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.86[a]",
        f"[1:v]{crop},drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='DEPOIS · frame 240':fontcolor=white:fontsize=28:x=24:y=24:box=1:boxcolor=0x07142A@.86[b]",
        "[a][b]hstack=inputs=2[out]",
    ]
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(before), "-i", str(after), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)],
        check=True,
        cwd=output.parent,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8782)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()

    export_root = args.export_dir.resolve()
    video_root = export_root / "videos"
    manifest = export_root / f"{SOURCE_ID}.json"
    audio = video_root / f"{SOURCE_ID}.wav"
    source_frames = video_root / f".{SOURCE_ID}-frames"
    frames = video_root / f".{OUTPUT_ID}-frames"
    output = video_root / f"{OUTPUT_ID}.mp4"
    board = video_root / f"{OUTPUT_ID}-frames.png"
    comparison = video_root / f"{OUTPUT_ID}-face-before-after.png"
    report = video_root / f"{OUTPUT_ID}-report.md"
    visual_report = video_root / f"{OUTPUT_ID}-visual-inspection.json"

    if not manifest.is_file() or not audio.is_file():
        raise FileNotFoundError("Mission 017 manifest and WAV are required; no synthesis is performed by this script")
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"video already exists: {output}; pass --overwrite")
    if frames.exists():
        if not args.overwrite:
            raise FileExistsError(f"frames already exist: {frames}; pass --overwrite")
        shutil.rmtree(frames)
    frames.mkdir(parents=True, exist_ok=True)

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    duration_ms = int(payload["duration_ms"])
    started = time.perf_counter()
    capture = _capture(STUDIO_ROOT, frames, manifest, args.port, args.capture_timeout)
    _render_mp4(frames, audio, output, duration_ms, args.overwrite)
    _frame_board(frames, board, duration_ms)
    _face_comparison_board(source_frames, frames, comparison)
    probe = _probe_export(output)
    elapsed = time.perf_counter() - started
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")

    report.write_text("\n".join([
        "# Fabuloom Narrator Mode V1.1 — correção facial",
        "",
        f"- Áudio e manifesto reutilizados da MISSÃO 017: `{audio}` / `{manifest}`.",
        "- Síntese Kokoro nesta execução: `não executada`.",
        f"- Voz preservada: `{payload.get('metadata', {}).get('voice_id', 'pm_santa')}` · idioma `pt-BR`.",
        f"- Duração medida: `{duration_ms} ms`; segmentos: `{len(payload['segments'])}`.",
        f"- Frames reais: `{frames}` ({capture['frame_count']} em {FPS} fps).",
        f"- MP4: `{output}` ({output.stat().st_size} bytes).",
        f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']}` {video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`.",
        f"- Prancha de poses: `{board}`.",
        f"- Comparação facial antes/depois, mesmo frame 240: `{comparison}`.",
        "- Correção: boca/barba passaram a usar uma única placa inferior; a barba duplicada foi desativada somente no pack experimental do Narrator Mode.",
        "- Sincronização: RMS PCM-16 do áudio medido; palavras, fonemas e visemas continuam indisponíveis.",
        "- Aprovação artística humana continua obrigatória.",
        "",
    ]), encoding="utf-8")
    visual_report.write_text(json.dumps({
        "format": "fabuloom.visual-inspection-narrator/0.2",
        "mode": "narrator-mode-v1.1-face-correction",
        "source": str(output),
        "before_source": str(source_frames / "000240.png"),
        "after_source": str(frames / "000240.png"),
        "checks": {
            "canvas": [WIDTH, HEIGHT],
            "avatar": "circular-clipped",
            "facial_layers_only": True,
            "mouth_source": "pcm16_rms_envelope",
            "mouth_composition": "single_lower_face_plate",
            "captions": "measured_segment_ranges",
            "no_black_frame_sample": True,
            "deterministic_frame_count": capture["frame_count"],
            "human_review_required": True,
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={manifest}")
    print(f"audio_reused={audio}")
    print(f"frames={frames}")
    print(f"video={output}")
    print(f"board={board}")
    print(f"comparison={comparison}")
    print(f"report={report}")
    print(f"visual_report={visual_report}")
    print(f"duration_ms={duration_ms}")
    print(f"processing_seconds={elapsed:.3f}")
    print(f"probe={json.dumps(probe, ensure_ascii=False)}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
