"""Render Mission 023.4.2 mouth-polish videos from existing local audio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

STUDIO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
from facial_system_recovery_demo import _capture, _facial_closeups, _frame_board, _probe_export, _render_mp4, _comparison

NARRATORS = {"dora": ("pf_dora", "Dora Mouth Polish"), "alex": ("pm_alex", "Alex Mouth Polish"), "santa": ("pm_santa", "Santa V5 reference")}


def _ffmpeg(args: list[str], cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


def _stack(paths: list[Path], output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n"]
    args.extend(item for path in paths for item in ("-i", str(path)))
    labels = [f"v{i}" for i in range(len(paths))]
    filters = [f"[{i}:v]scale=760:-1[{label}]" for i, label in enumerate(labels)]
    filters.append("".join(f"[{label}]" for label in labels) + f"vstack=inputs={len(labels)}[out]")
    _ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", str(output)], output.parent)


def _trio(videos: list[Path], audio: Path, output: Path, overwrite: bool) -> None:
    args = ["-y" if overwrite else "-n", *[item for path in videos for item in ("-i", str(path))], "-i", str(audio)]
    filters = [f"[{i}:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]" for i in range(3)]
    filters.append("[v0][v1][v2]vstack=inputs=3[outv]")
    _ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "3:a:0", "-shortest", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(output)], output.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--port", type=int, default=8817)
    parser.add_argument("--capture-timeout", type=float, default=600)
    args = parser.parse_args()
    export_root = args.export_dir.resolve(); source_root = export_root / "videos" / "official-narrators-v1"; output_root = export_root / "videos" / "facial-mouth-polish-v1"; output_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter(); results=[]; videos=[]
    for character_id,(voice_id,name) in NARRATORS.items():
        source_id=f"fabuloom-official-narrator-{character_id}-v1"; manifest_path=export_root/f"{source_id}.json"; audio_path=source_root/f"{source_id}.wav"; video_path=output_root/f"fabuloom-{character_id}-mouth-polish-v1.mp4"; board_path=output_root/f"{character_id}-mouth-polish-v1-frames.png"; closeup_path=output_root/f"{character_id}-mouth-polish-v1-facial-closeups.png"; frames_path=output_root/f".fabuloom-{character_id}-mouth-polish-v1-frames"
        for path in (manifest_path,audio_path):
            if not path.is_file(): raise FileNotFoundError(path)
        if frames_path.exists():
            if not args.overwrite: raise FileExistsError(f"frames exist: {frames_path}; pass --overwrite")
            import shutil; shutil.rmtree(frames_path)
        frames_path.mkdir(parents=True,exist_ok=True); manifest=json.loads(manifest_path.read_text(encoding="utf-8")); capture=_capture(STUDIO_ROOT,frames_path,manifest_path,args.port,args.capture_timeout,character_id=character_id); _render_mp4(frames_path,audio_path,video_path,int(manifest["duration_ms"]),args.overwrite); _frame_board(frames_path,board_path,int(manifest["duration_ms"])); _facial_closeups(frames_path,closeup_path,args.overwrite); videos.append(video_path)
        results.append({"character_id":character_id,"name":name,"voice_id":voice_id,"language":"pt-BR","audio_reused":str(audio_path),"video":str(video_path),"facial_closeups":str(closeup_path),"duration_ms":manifest["duration_ms"],"frame_count":capture["frame_count"],"probe":_probe_export(video_path)})
    comparisons={}
    for character_id in ("dora","alex"):
        old=EXPORT_ROOT/"videos"/"facial-framing-v1"/f"{character_id}-framing-v1-facial-closeups.png"; new=output_root/f"{character_id}-mouth-polish-v1-facial-closeups.png"; target=output_root/f"{character_id}-mouth-before-after.png"
        if old.is_file() and new.is_file(): _comparison(old,new,target,args.overwrite); comparisons[character_id]=str(target)
    before_after=output_root/"mouth-before-after-board.png"
    if len(comparisons)==2: _stack([Path(comparisons["dora"]),Path(comparisons["alex"])],before_after,args.overwrite)
    trio_path=output_root/"fabuloom-narrators-mouth-polish-trio-v1.mp4"; _trio(videos,source_root/"fabuloom-official-narrator-dora-v1.wav",trio_path,args.overwrite)
    report_path=output_root/"mouth-polish-v1-report.json"; report_path.write_text(json.dumps({"format":"fabuloom.mouth-polish-report/0.1","mission":"023.4.2","diagnosis":{"cause":"existing lips had a strong dark outline, broad horizontal width and an open state with an oversized smile/teeth mass","preserved":["Santa V5","Dora/Alex head-clean.png","previous mouth SVG states","global narrator renderer","framing profiles"]},"solution":{"approach":"discrete compact painted SVG states","states":["closed","slight","moderate","open"],"visual_rules":["smaller width","soft outline","consistent center and baseline","restrained teeth/tongue shapes","same-canvas head-local children"],"rms_mapping":"unchanged thresholds and RMS source","renderer_changed":False},"results":results,"trio_video":str(trio_path),"comparisons":comparisons,"before_after_board":str(before_after),"art_gate":"AWAITING_ART_APPROVAL","processing_seconds":round(time.perf_counter()-started,3)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"report={report_path}"); [print(f"{r['character_id']}: video={r['video']} duration_ms={r['duration_ms']} frames={r['frame_count']}") for r in results]; print(f"trio={trio_path}"); print("state=completed"); return 0


if __name__ == "__main__": raise SystemExit(main())
