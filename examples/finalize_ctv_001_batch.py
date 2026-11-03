"""Create the final CTV-001 index and validate the generated deliverables."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


FABULOOM_ROOT = Path(os.environ.get("FABULOOM_ROOT", r"E:\Fabuloom")).resolve()
OUTPUT_ROOT = FABULOOM_ROOT / "workspace" / "exports" / "vertical-cinema-book1-v1"
CHAPTERS = tuple(range(1, 11))
LOTS = {"A": (1, 2), "B": (3, 4), "C": (5, 6), "D": (7, 8), "E": (9, 10)}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def stream(data: dict, kind: str) -> dict:
    return next(item for item in data["streams"] if item.get("codec_type") == kind)


def decode(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0", "-f", "null", "NUL"],
        check=True,
        capture_output=True,
        text=True,
    )


def chapter_entry(number: int) -> tuple[dict, dict]:
    root = OUTPUT_ROOT / f"capitulo-{number:02d}"
    report_path = root / "reports" / "technical-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    full = root / "videos" / f"cronicas-topazio-capitulo{number:02d}-vertical-full.mp4"
    teaser = root / "videos" / f"cronicas-topazio-capitulo{number:02d}-vertical-teaser.mp4"
    full_probe = probe(full)
    teaser_probe = probe(teaser)
    decode(full)
    decode(teaser)
    full_video = stream(full_probe, "video")
    full_audio = stream(full_probe, "audio")
    teaser_video = stream(teaser_probe, "video")
    plan = json.loads((root / "timeline" / f"capitulo{number:02d}-vertical.json").read_text(encoding="utf-8"))
    blocked_scene_paths = [str(scene.get("image", "")).replace("\\", "/") for scene in plan.get("scenes", []) if "/characters/" in str(scene.get("image", "")).replace("\\", "/").lower()]
    validation = {
        "full_ffprobe": True,
        "teaser_ffprobe": True,
        "full_ffmpeg_decode": True,
        "teaser_ffmpeg_decode": True,
        "full_dimensions": [int(full_video["width"]), int(full_video["height"])],
        "teaser_dimensions": [int(teaser_video["width"]), int(teaser_video["height"])],
        "full_fps": full_video.get("r_frame_rate"),
        "full_codec": full_video.get("codec_name"),
        "audio_codec": full_audio.get("codec_name"),
        "audio_sample_rate": full_audio.get("sample_rate"),
        "audio_channels": full_audio.get("channels"),
        "blackdetect": report.get("validation", {}).get("blackdetect_intervals", []),
        "santa_visibility": report.get("validation", {}).get("santa_visibility", False),
        "draft_characters": report.get("validation", {}).get("draft_characters", "unknown"),
        "environment_only_plan": not blocked_scene_paths,
        "blocked_scene_paths": blocked_scene_paths,
        "rights_status": report.get("validation", {}).get("rights_status", "unknown"),
    }
    expected = [1080, 1920]
    if validation["full_dimensions"] != expected or validation["teaser_dimensions"] != expected or validation["full_fps"] != "30/1" or validation["full_codec"] != "h264" or validation["audio_codec"] != "aac" or validation["audio_sample_rate"] != "48000" or validation["audio_channels"] != 2 or validation["blackdetect"] or not validation["santa_visibility"] or validation["draft_characters"] != "blocked" or not validation["environment_only_plan"]:
        raise RuntimeError(f"chapter {number:02d} final validation failed: {validation}")
    entry = {
        "chapter": number,
        "lot": next(lot for lot, numbers in LOTS.items() if number in numbers),
        "status": "DONE",
        "title": report["title"],
        "duration_ms": report["source"]["manifest"]["duration_ms"],
        "processing_seconds": report.get("processing_seconds"),
        "full_video": str(full),
        "teaser_video": str(teaser),
        "full_bytes": full.stat().st_size,
        "teaser_bytes": teaser.stat().st_size,
        "full_sha256": sha256(full),
        "teaser_sha256": sha256(teaser),
        "music_cue_sheet": str(root / "audio" / "music-cue-sheet.json"),
        "metadata": str(root / "metadata" / "tiktok-metadata.json"),
        "validation": validation,
    }
    return entry, report


def make_cover(number: int, full: Path) -> Path:
    cover = OUTPUT_ROOT / "covers" / f"capitulo-{number:02d}-cover.jpg"
    cover.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(full), "-frames:v", "1", "-q:v", "2", str(cover)], check=True, capture_output=True, text=True)
    return cover


def main() -> None:
    entries = []
    reports = {}
    for number in CHAPTERS:
        print(f"validating chapter {number:02d}/10")
        entry, report = chapter_entry(number)
        entry["cover"] = str(make_cover(number, Path(entry["full_video"])))
        entries.append(entry)
        reports[number] = report
    entries.sort(key=lambda item: item["chapter"])
    summaries = []
    for lot, numbers in LOTS.items():
        selected = [item for item in entries if item["chapter"] in numbers]
        summaries.append({
            "lot": lot,
            "chapters": list(numbers),
            "state": "DONE",
            "elapsed_seconds": round(sum(item.get("processing_seconds") or 0 for item in selected), 3),
            "files": [path for item in selected for path in (item["full_video"], item["teaser_video"])],
        })
    old_status = json.loads((OUTPUT_ROOT / "BATCH-STATUS.json").read_text(encoding="utf-8"))
    recovered_incidents = old_status.get("failures", [])
    index = {
        "format": "fabuloom.ctv-001-batch/0.1",
        "runner_version": "ctv-001-vertical-cinema-v1.1-environment-only",
        "state": "DONE",
        "canvas": {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16"},
        "voice": {"provider": "kokoro", "voice_id": "pm_santa", "language": "pt-BR", "timing_source": "measured_wav_segments"},
        "chapters": entries,
        "batch_summaries": summaries,
        "recovery_incidents": recovered_incidents,
        "failures": [],
        "rights_status": "pending_owner_confirmation",
        "published": False,
    }
    write_json(OUTPUT_ROOT / "BATCH-INDEX.json", index)
    status = {
        "format": "fabuloom.ctv-batch-status/0.1",
        "state": "DONE",
        "lot": "E",
        "chapter": None,
        "stage": "BATCH_COMPLETE",
        "completed_chapters": list(CHAPTERS),
        "failures": [],
        "recovery_incidents": recovered_incidents,
        "next_action": "aguardar revisão humana e confirmação dos direitos comerciais",
    }
    write_json(OUTPUT_ROOT / "BATCH-STATUS.json", status)
    write_json(OUTPUT_ROOT / "FINAL-VALIDATION.json", {"chapters": entries, "mp4_count": len(entries) * 2, "all_passed": True, "ffprobe_and_ffmpeg_decode": True, "blackdetect_source": "per-chapter technical reports", "rights_status": "pending_owner_confirmation"})
    write_json(OUTPUT_ROOT / "metadata" / "vertical-index.json", {"format": "fabuloom.ctv-vertical-index/0.1", "chapters": [{"chapter": item["chapter"], "title": item["title"], "full_video": item["full_video"], "teaser_video": item["teaser_video"], "cover": item["cover"], "duration_ms": item["duration_ms"], "published": False} for item in entries]})
    lines = ["# CTV-001 — Crônicas de Topázio · Vertical Cinema", "", "- Estado: `DONE`", "- Saída: `E:\\Fabuloom\\workspace\\exports\\vertical-cinema-book1-v1`", "- Entrega: 10 episódios completos + 10 teasers verticais.", "- Canvas: 1080×1920, 9:16, 30 fps; H.264/AAC estéreo.", "- Voz: Kokoro `pm_santa`, pt-BR; WAVs originais reutilizados.", "- Narrador: Santa V5 na biblioteca na abertura/encerramento e no medalhão durante a narrativa.", "- Planos: ambientes/objetos aprovados; assets em `/characters/` bloqueados.", "- Mix: músicas locais, crossfade, ducking voz-prioridade, limiter; direitos comerciais Suno pendentes.", "- Publicação: não realizada.", "", "## Capítulos", ""]
    for item in entries:
        lines.append(f"- Capítulo {item['chapter']:02d}: `{item['title']}` — full `{item['full_video']}` — teaser `{item['teaser_video']}` — duração `{item['duration_ms']} ms` — QA `PASS`.")
    lines.extend(["", "## Lotes", ""])
    for summary in summaries:
        lines.append(f"- Lote {summary['lot']}: capítulos {summary['chapters']}; estado `DONE`; {len(summary['files'])} MP4s.")
    lines.extend(["", "## Incidentes recuperados", "", "- O primeiro encoder do capítulo 04 falhou com preset `medium`; a captura foi preservada e o full foi refeito com `fast`/`threads=2`.", "- O primeiro full parcial do capítulo 10 não continha `moov`; FFprobe detectou o arquivo incompleto, o checkpoint de captura foi reutilizado e o episódio foi reencodado com sucesso.", "", "## Aprovação", "", "A validação técnica passou. A aprovação artística e a confirmação dos direitos comerciais das faixas continuam pendentes.", ""])
    (OUTPUT_ROOT / "BATCH-REPORT-FINAL.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"finalized {len(entries) * 2} MP4s")


if __name__ == "__main__":
    main()
