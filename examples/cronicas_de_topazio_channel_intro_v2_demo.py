"""Render the Crônicas de Topázio intro with the owner-provided Suno score.

The video frames are intentionally reused from the approved Mission 025
capture. This runner only builds a new audio bed and muxes a new MP4, leaving
the original procedural-score export untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import textwrap


STUDIO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(os.environ.get("FABULOOM_WORKSPACE_ROOT", STUDIO_ROOT.parent)).resolve()
EXPORT_ROOT = Path(os.environ.get("FABULOOM_EXPORT_ROOT", WORKSPACE_ROOT / "workspace" / "exports")).resolve()
PROJECT_ID = "cronicas-de-topazio-channel-intro"
PROJECT_ROOT = EXPORT_ROOT / PROJECT_ID
FPS = 30
WIDTH = 1920
HEIGHT = 1080

DEFAULT_MUSIC = (
    WORKSPACE_ROOT
    / "workspace"
    / "inputs"
    / "music"
    / "book1"
    / "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3"
)


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size:format_tags:stream=index,codec_type,codec_name,width,height,pix_fmt,sample_rate,channels",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _duration(probe: dict) -> float:
    return float(probe.get("format", {}).get("duration", 0.0))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _levels(path: Path) -> str:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return " ".join(line.strip() for line in output.splitlines() if "mean_volume" in line or "max_volume" in line)


def _latest_capture() -> Path:
    candidates = sorted(
        (path for path in (PROJECT_ROOT / "frames").glob("capture-*") if (path / "complete.json").is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("no completed Mission 025 Canvas capture was found")
    return candidates[0]


def _numeric_frames(capture: Path, duration_ms: int) -> tuple[Path, int]:
    expected = (duration_ms * FPS + 999) // 1000
    frames = sorted(capture.glob("[0-9]*.jpg"))
    if len(frames) != expected:
        raise RuntimeError(f"capture frame count mismatch: {len(frames)} != {expected}")
    if not frames or frames[0].name != "000000.jpg":
        raise RuntimeError("capture does not start at frame 000000.jpg")
    return capture, expected


def _safe_music_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    allowed = (WORKSPACE_ROOT / "workspace" / "inputs" / "music").resolve()
    if not resolved.is_relative_to(allowed):
        raise ValueError("music input must remain under workspace/inputs/music")
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def build_ducked_mix(voice: Path, music: Path, sfx: Path, output: Path, duration_ms: int, *, overwrite: bool) -> dict:
    duration = duration_ms / 1000
    fade_out_start = max(0.0, duration - 3.5)
    # Voice is the sidechain for both score and transitions. The score is
    # louder in genuine gaps, but is continuously reduced while Santa speaks.
    graph = textwrap.dedent(
        f"""
        [0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duration:.3f},asetpts=N/SR/TB[voice];
        [1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duration:.3f},asetpts=N/SR/TB,volume=0.28,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start:.3f}:d=3.5[music];
        [2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duration:.3f},asetpts=N/SR/TB,volume=0.52[sfx];
        [music][voice]sidechaincompress=threshold=0.030:ratio=8:attack=35:release=700:makeup=1:link=average[ducked_music];
        [sfx][voice]sidechaincompress=threshold=0.040:ratio=3:attack=15:release=300:makeup=1:link=average[ducked_sfx];
        [voice][ducked_music][ducked_sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.92:attack=5:release=500[out]
        """
    ).replace("\n", "")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n",
            "-i", str(voice), "-i", str(music), "-i", str(sfx),
            "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
        ],
        check=True,
        cwd=output.parent,
    )
    return {"filter": graph, "duration_seconds": duration, "levels": _levels(output)}


def _make_review_snippets(video: Path, review_dir: Path, duration: float, *, overwrite: bool) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    window = min(10.0, max(4.0, duration / 5))
    starts = {"inicio": 0.0, "meio": max(0.0, duration / 2 - window / 2), "fim": max(0.0, duration - window)}
    results = []
    for label, start in starts.items():
        target = review_dir / f"cronicas-de-topazio-channel-intro-v2-review-{label}.wav"
        if overwrite or not target.is_file():
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{window:.3f}", "-vn", "-c:a", "pcm_s16le", str(target)],
                check=True,
            )
        results.append({"label": label, "start_seconds": round(start, 3), "duration_seconds": round(window, 3), "path": str(target)})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--music-file", type=Path, default=DEFAULT_MUSIC)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    manifest_path = PROJECT_ROOT / "manifest.json"
    voice = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-voice.wav"
    sfx = PROJECT_ROOT / "audio" / "cronicas-procedural-sfx.wav"
    output = PROJECT_ROOT / f"{PROJECT_ID}-v2.mp4"
    mix = PROJECT_ROOT / "audio" / f"{PROJECT_ID}-v2-suno-ducked-mix.wav"
    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duration_ms = int(manifest["duration_ms"])
    duration = duration_ms / 1000
    music = _safe_music_path(args.music_file)
    for required in (voice, sfx):
        if not required.is_file():
            raise FileNotFoundError(required)
    music_probe = _probe(music)
    voice_probe = _probe(voice)
    sfx_probe = _probe(sfx)
    if _duration(music_probe) < duration:
        raise ValueError("music is shorter than the measured narration")
    capture, frame_count = _numeric_frames(_latest_capture(), duration_ms)
    mix_info = build_ducked_mix(voice, music, sfx, mix, duration_ms, overwrite=args.overwrite)
    if args.overwrite or not output.is_file():
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if args.overwrite else "-n",
                "-framerate", str(FPS), "-i", str(capture / "%06d.jpg"), "-i", str(mix), "-t", f"{duration:.3f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-s", f"{WIDTH}x{HEIGHT}",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output),
            ],
            check=True,
            cwd=output.parent,
        )
    output_probe = _probe(output)
    snippets = _make_review_snippets(output, PROJECT_ROOT / "reviews", _duration(output_probe), overwrite=args.overwrite)
    music_tags = music_probe.get("format", {}).get("tags", {})
    report = {
        "project": PROJECT_ID,
        "source_video_preserved": str(PROJECT_ROOT / f"{PROJECT_ID}.mp4"),
        "video": str(output),
        "mix": str(mix),
        "music": {"filename": music.name, "sha256": _sha256(music), "probe": music_probe, "tags": music_tags, "origin": "owner-provided original score generated with Suno; commercial publication rights require confirmation"},
        "voice": {"probe": voice_probe, "levels": _levels(voice)},
        "sfx": {"probe": sfx_probe},
        "duration_ms": duration_ms,
        "frame_count": frame_count,
        "video_probe": output_probe,
        "mix_info": mix_info,
        "review_snippets": snippets,
        "ducking": {"score_sidechain": "voice -> music, ratio 8, attack 35 ms, release 700 ms", "sfx_sidechain": "voice -> SFX, ratio 3, attack 15 ms, release 300 ms", "limiter": "alimiter limit 0.92", "music_speed_and_pitch_changed": False},
        "preserved": ["17 scenes", "Canvas frames", "Santa V5 renderer capture", "RMS mouth animation", "captions", "timeline", "original MP4"],
        "rights_review_required": True,
    }
    _json(report_dir / "cronicas-de-topazio-channel-intro-v2-suno.json", report)
    (report_dir / "cronicas-de-topazio-channel-intro-v2-suno.md").write_text(
        "# Crônicas de Topázio — trilha Suno V2\n\n"
        f"- Vídeo: `{output}`\n"
        f"- Duração medida: `{duration_ms} ms`; contêiner: `{_duration(output_probe):.3f} s`.\n"
        f"- Música: `{music.name}`; SHA-256: `{_sha256(music)}`.\n"
        "- Origem registrada: faixa original fornecida pelo proprietário, gerada com Suno; confirmação de direitos comerciais ainda é obrigatória.\n"
        "- A narração permanece em primeiro plano por ducking sidechain da música e dos SFX, com limiter final e fades suaves.\n"
        "- Velocidade e tom da música não foram alterados; somente volume, recorte temporal e fades foram aplicados.\n"
        "- Os 17 planos, frames, animações, legendas, Santa V5 e RMS foram preservados.\n"
        "- Trechos para audição humana ficam em `reviews/`; a aprovação final de inteligibilidade e mixagem permanece humana.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
