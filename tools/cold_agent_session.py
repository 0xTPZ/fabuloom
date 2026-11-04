"""Repository-instructions-only cold-session validation.

This is deliberately not presented as an autonomous language-model agent. It
starts a clean subprocess with no conversation variables, reads the versioned
agent instructions, discovers the available capabilities and renderable
profile, then invokes only the discovered shared CLI operation. A real agent
runtime can use the same protocol; this harness makes the boundary explicit.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


REQUIRED_DOCS = ("AGENTS.md", "docs/AGENT-OPERATIONS.md")


def _clean_environment(root: Path, product_root: Path) -> dict[str, str]:
    # Keep Windows runtime configuration intact (notably Winsock/Edge), but
    # remove likely credentials and conversation/agent state before spawning
    # the cold subprocess. Values are never printed or written to the report.
    blocked_markers = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "CONVERSATION", "CHAT_HISTORY", "CODEX", "OPENAI", "GH_TOKEN")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in blocked_markers)
    }
    environment.update(
        {
            "PYTHONPATH": str(product_root / "src"),
            "FABULOOM_ROOT": str(root),
            "FABULOOM_AGENT_COLD_SESSION": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return environment


def _cli(root: Path, product_root: Path, environment: dict[str, str], *arguments: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "fabuloom_core.cli", "--root", str(root), *arguments],
        cwd=product_root,
        env=environment,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cold CLI failed ({result.returncode}) for {' '.join(arguments)}: {result.stderr[-2000:]}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("cold CLI did not return an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"E:\Fabuloom"))
    parser.add_argument("--output-id", default="fab-arch-002-cold-agent-r1")
    args = parser.parse_args(argv)
    product_root = Path(__file__).resolve().parents[1]
    environment = _clean_environment(args.root, product_root)
    docs = {relative: (product_root / relative).read_text(encoding="utf-8") for relative in REQUIRED_DOCS}
    if "Bootstrap" not in docs["AGENTS.md"] or "EngineService" not in docs["docs/AGENT-OPERATIONS.md"]:
        raise RuntimeError("repository operating instructions are incomplete")

    doctor = _cli(args.root, product_root, environment, "doctor")
    capabilities = _cli(args.root, product_root, environment, "capabilities")
    profiles = _cli(args.root, product_root, environment, "profiles", "list")
    operations = capabilities.get("operations") if isinstance(capabilities.get("operations"), dict) else {}
    if "render.demo" not in operations:
        raise RuntimeError("cold session could not discover render.demo")
    renderable = [item for item in profiles.get("profiles", []) if isinstance(item, dict) and item.get("renderable")]
    if not renderable:
        raise RuntimeError("cold session found no renderable profile")
    profile_id = str(renderable[0]["id"])
    provider = "simulated-audio" if "simulated-audio" in json.dumps(capabilities, ensure_ascii=False) else "kokoro"
    plan = _cli(args.root, product_root, environment, "render", "demo", "--profile", profile_id, "--provider", provider, "--output-id", args.output_id, "--dry-run")
    if plan.get("status") != "ready":
        report = {
            "status": "BLOCKED",
            "validation_kind": "repository-instructions-only-subprocess",
            "independent_model_agent": False,
            "reason": "discovered render dry-run did not pass",
            "doctor": doctor,
            "capabilities": capabilities,
            "profiles": profiles,
            "plan": plan,
        }
    else:
        job = _cli(args.root, product_root, environment, "render", "demo", "--profile", profile_id, "--provider", provider, "--output-id", args.output_id)
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        output_root = Path(str(result.get("project", ""))).parent if result else args.root / "workspace" / "exports" / args.output_id
        required = ["project.json", "narration.json", "captions.srt", "board.png", "video.mp4", "report.json", "technical-qa.json", "CHECKPOINT.json"]
        artifacts = {name: (output_root / name).is_file() for name in required}
        report = {
            "status": "PASS" if job.get("state") == "completed" and all(artifacts.values()) and result.get("artistic_qa", {}).get("status") == "REVIEW_REQUIRED" else "FAIL",
            "validation_kind": "repository-instructions-only-subprocess",
            "independent_model_agent": False,
            "session": "cold-no-conversation-history",
            "instructions": list(REQUIRED_DOCS),
            "discovered_operation": "render.demo",
            "discovered_profile": profile_id,
            "selected_provider": provider,
            "job": job,
            "artifacts": artifacts,
            "output_root": str(output_root),
            "private_assets_used": False,
            "human_artistic_approval": False,
            "technical_qa": result.get("technical_qa"),
            "limitation": "No independent LLM-agent runtime was available inside this local validation; this proves the repository-instructions-only protocol, not autonomous reasoning.",
        }
    output_root = Path(str(report.get("output_root") or args.root / "workspace" / "exports" / args.output_id))
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "COLD-AGENT-REPORT.json"
    report["report"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
