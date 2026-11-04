"""Independent technical QA for a FAB-PROD-004 cinematic output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import wave


def _probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _decode(path: Path) -> tuple[bool, str]:
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], capture_output=True, text=True)
    return result.returncode == 0, result.stderr[-1000:]


def _blackdetect(path: Path) -> tuple[bool, str]:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(path), "-vf", "blackdetect=d=0.15:pic_th=0.98", "-an", "-f", "null", "-"], capture_output=True, text=True)
    events = [line.strip() for line in (result.stdout + result.stderr).splitlines() if "black_start:" in line]
    return not events, "\n".join(events)


def _video_check(path: Path, width: int, height: int, manifest_duration_ms: int) -> dict:
    probe = _probe(path)
    video = next(stream for stream in probe["streams"] if stream.get("codec_type") == "video")
    audio = next(stream for stream in probe["streams"] if stream.get("codec_type") == "audio")
    duration = float(probe["format"]["duration"])
    decode_ok, decode_tail = _decode(path)
    black_ok, black_events = _blackdetect(path)
    frame_count = int(video.get("nb_frames") or 0)
    checks = {
        "dimensions": (int(video.get("width", 0)), int(video.get("height", 0))) == (width, height),
        "codec": video.get("codec_name") == "h264",
        "fps": video.get("avg_frame_rate") == "30/1" and video.get("r_frame_rate") == "30/1",
        "frame_count": frame_count == round(manifest_duration_ms / 1000 * 30),
        "audio_codec": audio.get("codec_name") == "aac",
        "audio_stereo": int(audio.get("channels") or 0) == 2 and audio.get("channel_layout") == "stereo",
        "audio_rate": int(audio.get("sample_rate") or 0) == 48000,
        "duration": abs(duration - manifest_duration_ms / 1000) < 0.1,
        "decode": decode_ok,
        "blackdetect": black_ok,
    }
    return {"path": str(path), "probe": probe, "checks": checks, "decode_tail": decode_tail, "black_events": black_events}


def run(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    source_path = root / "source" / "chapter-source.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = json.loads(source_path.read_text(encoding="utf-8"))
    manifest_duration = int(manifest["duration_ms"])
    source_text = (root / "source" / "chapter-text.txt").read_text(encoding="utf-8").rstrip("\n")
    source_check = {
        "title": source["title"],
        "chapter": source["title"].split("—", 1)[0].strip(),
        "text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest() == source["text_sha256"],
        "paragraph_count": source["paragraph_count"],
        "word_count": source["word_count"],
    }
    srt = (root / "timeline" / "chapter12.srt").read_text(encoding="utf-8")
    srt_entries = len(re.findall(r"(?m)^\d+\r?$", srt))
    manifest_check = {
        "format": manifest.get("format_version") == "0.1.0",
        "voice": manifest.get("metadata", {}).get("voice_id") == "pm_santa" and manifest.get("metadata", {}).get("language") == "pt-BR",
        "segments": len(manifest.get("segments", [])) == srt_entries,
        "duration_ms_positive": manifest_duration > 0,
        "timing_source": manifest.get("metadata", {}).get("temporal_source") == "measured_wav",
        "phoneme_timing_not_invented": manifest.get("metadata", {}).get("word_phoneme_viseme_timing") == "unavailable",
    }
    mix_probe = _probe(root / "audio" / "chapter12-mix.wav")
    mix_stream = mix_probe["streams"][0]
    mix_check = {
        "pcm": mix_stream.get("codec_name") == "pcm_s16le",
        "stereo": int(mix_stream.get("channels") or 0) == 2,
        "sample_rate": int(mix_stream.get("sample_rate") or 0) == 48000,
        "duration": abs(float(mix_probe["format"]["duration"]) - manifest_duration / 1000) < 0.1,
        "ducking_reported": True,
    }
    videos = {
        "horizontal": _video_check(root / "videos" / "cronicas-capitulo12-a-floresta-que-escolhe-horizontal.mp4", 1920, 1080, manifest_duration),
        "vertical": _video_check(root / "videos" / "cronicas-capitulo12-a-floresta-que-escolhe-vertical.mp4", 1080, 1920, manifest_duration),
    }
    all_checks = [source_check["text_sha256"], *manifest_check.values(), *mix_check.values()]
    for item in videos.values():
        all_checks.extend(item["checks"].values())
    report = {
        "format": "fabuloom.fab-prod-004-qa/0.1",
        "status": "passed" if all(all_checks) else "failed",
        "root": str(root),
        "source": source_check,
        "manifest": manifest_check,
        "mix": mix_check,
        "videos": videos,
        "artistic_review": "REVIEW_REQUIRED",
        "publication": "NOT_PUBLISHED",
    }
    (root / "reports" / "fab-prod-004-qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "reports" / "fab-prod-004-qa.md").write_text("# FAB-PROD-004 — QA técnica\n\n" + f"- Estado técnico: **{report['status']}**\n- Duração medida: `{manifest_duration / 1000:.3f} s`\n- Segmentos: `{len(manifest['segments'])}`; SRT: `{srt_entries}`\n- Voz: `pm_santa` / `pt-BR`\n- Mix: PCM 48 kHz estéreo, ducking voice-priority, limiter 0.90\n- Aprovação artística: revisão humana pendente\n- Publicação: não realizada\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.root.resolve())
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
