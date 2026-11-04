"""Acceptance check for an agent session with no conversation history."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


REQUIRED_DOCS = ("AGENTS.md", "docs/AGENT-OPERATIONS.md")


def _cli(root: Path, product_root: Path, *arguments: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(product_root / "src")
    result = subprocess.run(
        [sys.executable, "-B", "-m", "fabuloom_core.cli", "--root", str(root), *arguments],
        cwd=product_root,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("CLI did not return a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"E:\Fabuloom"))
    parser.add_argument("--output-id", default="fab-arch-002-cold-session")
    args = parser.parse_args(argv)
    product_root = Path(__file__).resolve().parents[1]
    docs = {relative: (product_root / relative).read_text(encoding="utf-8") for relative in REQUIRED_DOCS}
    if "Bootstrap" not in docs["AGENTS.md"] or "EngineService" not in docs["docs/AGENT-OPERATIONS.md"]:
        raise RuntimeError("repository operating instructions are incomplete")
    doctor = _cli(args.root, product_root, "doctor")
    capabilities = _cli(args.root, product_root, "capabilities")
    profiles = _cli(args.root, product_root, "profiles", "list")
    plan = _cli(args.root, product_root, "render", "demo", "--dry-run", "--output-id", args.output_id)
    if plan.get("status") != "ready":
        report = {"status": "BLOCKED", "reason": "render dry-run did not pass", "doctor": doctor, "capabilities": capabilities, "profiles": profiles, "plan": plan}
    else:
        job = _cli(args.root, product_root, "render", "demo", "--provider", "simulated-audio", "--output-id", args.output_id)
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        output_root = Path(str(result.get("project", ""))).parent if result else args.root / "workspace" / "exports" / args.output_id
        required = ["project.json", "narration.json", "captions.srt", "board.png", "video.mp4", "report.json", "technical-qa.json", "CHECKPOINT.json"]
        artifacts = {name: (output_root / name).is_file() for name in required}
        report = {
            "status": "PASS" if job.get("state") == "completed" and all(artifacts.values()) and result.get("artistic_qa", {}).get("status") == "REVIEW_REQUIRED" else "FAIL",
            "session": "cold-no-conversation-history",
            "instructions": list(REQUIRED_DOCS),
            "job": job,
            "artifacts": artifacts,
            "output_root": str(output_root),
            "private_assets_used": False,
            "human_artistic_approval": False,
            "technical_qa": result.get("technical_qa"),
        }
    if plan.get("status") == "ready":
        output_root = Path(str(report.get("output_root") or args.root / "workspace" / "exports" / args.output_id))
    else:
        output_root = args.root / "workspace" / "exports" / args.output_id
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "COLD-SESSION-REPORT.json"
    report["report"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
