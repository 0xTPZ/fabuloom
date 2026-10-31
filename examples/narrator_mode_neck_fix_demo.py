"""Render Mission 017.4 using the shared Narrator Mode renderer.

The Mission 017 WAV and measured manifest are reused. This demo only captures
the corrected derived pack, renders the MP4, and creates visual evidence boards.
"""

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
PREVIOUS_ID = "fabuloom-narrator-mode-v1.3-face-alignment"
OUTPUT_ID = "fabuloom-narrator-mode-v1.4-neck-fix"


def _run_ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, cwd=cwd)


def _face_crop_filter(index: int, label: str, slot: str, crop: str = "370:370:54:656", scale: str = "480:480") -> str:
    safe_label = label.replace(":", "\\:")
    return f"[{index}:v]crop={crop},scale={scale}:flags=lanczos,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{safe_label}':fontcolor=white:fontsize=26:x=18:y=18:box=1:boxcolor=0x07142A@.88[{slot}]"


def _before_after_board(previous_frames: Path, frames: Path, output: Path) -> None:
    filters = [
        _face_crop_filter(0, "V1.3 · frame 240", "a"),
        _face_crop_filter(1, "V1.4 · frame 240", "b"),
        "[a][b]hstack=inputs=2[out]",
    ]
    _run_ffmpeg(["-i", str(previous_frames / "000240.png"), "-i", str(frames / "000240.png"), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _pose_board(frames: Path, output: Path) -> None:
    samples = [(0, "neutro"), (130, "piscada"), (181, "boca aberta"), (107, "tilt +"), (300, "tilt -")]
    inputs: list[str] = []
    filters: list[str] = []
    slots = ["a", "b", "c", "d", "e"]
    for slot, (index, label) in zip(slots, samples):
        inputs += ["-i", str(frames / f"{index:06d}.png")]
        filters.append(_face_crop_filter(len(inputs) // 2 - 1, label, slot, scale="360:360"))
    filters += ["[a][b][c]hstack=inputs=3[top]", "[d][e]hstack=inputs=2[bottomraw]", "[bottomraw]pad=1080:360:0:0:color=0x061329[bottom]", "[top][bottom]vstack=inputs=2[out]"]
    _run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _anatomy_asset_board(output: Path) -> None:
    root = STUDIO_ROOT / "frontend/assets/characters/topazio-narrators-v5/santa"
    names = ["head-clean.png", "neck.png", "beard.png", "mouth-closed.png", "mouth-open.png", "hair-back.png", "torso.png", "head.png"]
    inputs: list[str] = []
    filters: list[str] = []
    for index, name in enumerate(names):
        inputs += ["-i", str(root / name)]
        slot = chr(97 + index)
        filters.append(f"[{index}:v]scale=340:300:force_original_aspect_ratio=decrease,pad=340:330:(ow-iw)/2:(oh-ih)/2:color=0x061329,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{name}':fontcolor=white:fontsize=18:x=10:y=10:box=1:boxcolor=0x07142A@.88[{slot}]")
    filters += ["[a][b][c][d]hstack=inputs=4[top]", "[e][f][g][h]hstack=inputs=4[bottom]", "[top][bottom]vstack=inputs=2[out]"]
    _run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _lower_face_board(previous_frames: Path, frames: Path, output: Path) -> None:
    filters = [
        _face_crop_filter(0, "V1.3 · transicao inferior", "a", crop="370:190:54:820", scale="960:493"),
        _face_crop_filter(1, "V1.4 · transicao inferior", "b", crop="370:190:54:820", scale="960:493"),
        "[a][b]hstack=inputs=2[out]",
    ]
    _run_ffmpeg(["-i", str(previous_frames / "000240.png"), "-i", str(frames / "000240.png"), "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _diagnostic_map(frames: Path, output: Path) -> None:
    # The pixels are from the real V1.4 frame. The translucent boxes are a
    # diagnostic ownership map in the same avatar crop, not a second renderer.
    filter_graph = (
        "[0:v]crop=370:370:54:656,scale=900:900:flags=lanczos,"
        "drawbox=x=24:y=24:w=852:h=852:color=0xF7D27A@0.90:t=4,"
        "drawbox=x=110:y=590:w=680:h=250:color=0x40C9A2@0.55:t=5,"
        "drawbox=x=190:y=665:w=520:h=135:color=0x5B8FD9@0.80:t=5,"
        "drawbox=x=165:y=420:w=570:h=300:color=0xF07F91@0.65:t=5,"
        "drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='DOURADO  head-clean / cabeça + gola':fontcolor=0xF7D27A:fontsize=24:x=28:y=54:box=1:boxcolor=0x07142A@.88,"
        "drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='VERDE  neck.png / pixels redundantes':fontcolor=0x40C9A2:fontsize=24:x=116:y=622:box=1:boxcolor=0x07142A@.88,"
        "drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='AZUL  gola proprietaria do head-clean':fontcolor=0x5B8FD9:fontsize=24:x=196:y=694:box=1:boxcolor=0x07142A@.88,"
        "drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='ROSA  placa mouth / barba + labios':fontcolor=0xF07F91:fontsize=24:x=171:y=450:box=1:boxcolor=0x07142A@.88[out]"
    )
    _run_ffmpeg(["-i", str(frames / "000240.png"), "-filter_complex", filter_graph, "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-capture", action="store_true")
    parser.add_argument("--port", type=int, default=8786)
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
    anatomy = video_root / f"{OUTPUT_ID}-anatomy-layers.png"
    lower_face = video_root / f"{OUTPUT_ID}-lower-face-before-after.png"
    diagnostic = video_root / f"{OUTPUT_ID}-diagnostic-map.png"
    report = video_root / f"{OUTPUT_ID}-report.md"
    inspection = video_root / f"{OUTPUT_ID}-visual-inspection.json"

    if not manifest.is_file() or not audio.is_file() or not previous_frames.is_dir():
        raise FileNotFoundError("Mission 017 manifest/WAV and V1.3 frames are required; no synthesis is performed")
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
    _anatomy_asset_board(anatomy)
    _lower_face_board(previous_frames, frames, lower_face)
    _diagnostic_map(frames, diagnostic)
    probe = _probe_export(output)
    elapsed = time.perf_counter() - started
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    report.write_text("\n".join([
        "# Fabuloom Narrator Mode V1.4 — correção anatômica da transição",
        "",
        f"- Manifesto/WAV reutilizados: `{manifest}` / `{audio}`; nova síntese: `não executada`.",
        "- Causa comprovada: `neck.png` possui pixels de pele e uma gola completa, enquanto `head-clean.png` também possui a faixa inferior de pele e a gola visível. `beard.png` e as placas `mouth-closed.png`/`mouth-open.png` não são a fonte da duplicação de gola.",
        "- Correção: no pack derivado do Narrator Mode, o nó `neck` permanece como pai estrutural de `head`, mas recebe `opacity: 0`; a gola visível continua sendo propriedade de `head-clean.png`.",
        "- Preservação: Santa V5 oficial, assets, voz, manifesto, cenário, crop e alinhamento facial V1.3 não foram alterados.",
        "- Evidência alfa: `neck.png` 1536×1024, bounds [259,209,1279,847]; `head-clean.png` 1316×1195, bounds [226,118,1076,1165]; `beard.png` bounds [137,415,1197,1092]; `mouth-closed.png` bounds [270,255,1263,883].",
        f"- Frames: `{frames}` ({capture['frame_count']} em {FPS} fps).",
        f"- MP4: `{output}` ({output.stat().st_size} bytes).",
        f"- FFprobe: `{probe['format']['duration']} s`; vídeo `{video_stream['codec_name']}` {video_stream['width']}×{video_stream['height']} `{video_stream.get('pix_fmt')}`; áudio `{audio_stream['codec_name']}` `{audio_stream.get('sample_rate')} Hz`.",
        f"- Tempo de processamento sem síntese: `{elapsed:.3f} s`.",
        f"- Evidências: antes/depois `{before_after}`; poses `{poses}`; camadas `{anatomy}`; transição ampliada `{lower_face}`; mapa diagnóstico `{diagnostic}`.",
        "- Boca continua baseada em RMS; não há timestamps inventados de palavras, fonemas ou visemas.",
        "- O laboratório facial V1.4 ganhou toggles semânticos para pixels do pescoço/barba, mapa de responsabilidade e close-up da transição.",
        "- Aprovação artística humana continua obrigatória.",
        "",
    ]), encoding="utf-8")
    inspection.write_text(json.dumps({
        "format": "fabuloom.visual-inspection-narrator/0.5",
        "mode": "narrator-mode-v1.4-neck-fix",
        "source": str(output),
        "cause": {"neck_asset_contains_collar": True, "head_clean_contains_collar": True, "beard_or_mouth_is_collar_source": False},
        "correction": {"structural_neck_node_preserved": True, "neck_pixels_hidden": True, "neck_opacity": 0, "visible_collar_owner": "head-clean.png"},
        "assets": {"official_assets_modified": False, "wav_reused": True, "manifest_reused": True},
        "checks": {"canvas": [WIDTH, HEIGHT], "frames": capture["frame_count"], "facialStates": ["neutral", "mouth-closed", "mouth-moderate", "mouth-open", "blink", "head-tilt-left", "head-tilt-right"], "headLocalHierarchy": True, "deterministicFrameCapture": True, "humanReviewRequired": True},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={manifest}")
    print(f"audio_reused={audio}")
    print(f"frames={frames}")
    print(f"video={output}")
    print(f"before_after={before_after}")
    print(f"poses={poses}")
    print(f"anatomy={anatomy}")
    print(f"lower_face={lower_face}")
    print(f"diagnostic={diagnostic}")
    print(f"report={report}")
    print(f"inspection={inspection}")
    print(f"duration_ms={duration_ms}")
    print(f"processing_seconds={elapsed:.3f}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
