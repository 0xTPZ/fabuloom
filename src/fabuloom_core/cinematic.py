"""Compatibility boundary for the approved Crônicas de Topázio pipeline.

The cinematic renderer remains implemented by the approved legacy components,
but execution is exposed through a hash-registered request-boundary runner.
This module deliberately does not reimplement their renderer. It discovers
the components, validates reference outputs, builds a safe production plan,
and executes only runners that can isolate their output.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable

from .paths import FabuloomPaths


CINEMATIC_FORMAT = "fabuloom.cronicas-cinematic-production/0.1"
CINEMATIC_PROFILE_ID = "cronicas-cinematic-production"
SHORTS_PROFILE_ID = "cronicas-shorts-production"
_RUNNER_NAME = re.compile(r"^cronicas_[a-z0-9_]+\.py$", re.IGNORECASE)


class CinematicCompatibilityError(RuntimeError):
    """Raised when a cinematic operation cannot be performed safely."""


@dataclass(frozen=True)
class CinematicRequest:
    """Stable request contract shared by Desktop, CLI, API and MCP."""

    chapter: int
    chapter_title: str
    source_document: str
    voice_id: str = "pm_santa"
    language: str = "pt-BR"
    music_asset_id: str | None = None
    scene_asset_ids: tuple[str, ...] = ()
    output_variants: tuple[str, ...] = ("horizontal", "vertical")
    mode: str = "plan"
    runner: str | None = None
    output_root: str | None = None

    def validate(self) -> None:
        if isinstance(self.chapter, bool) or not isinstance(self.chapter, int) or self.chapter < 1:
            raise ValueError("chapter must be a positive integer")
        if not self.chapter_title.strip():
            raise ValueError("chapter_title must be non-empty")
        if not self.source_document.strip():
            raise ValueError("source_document must be non-empty")
        if self.voice_id != "pm_santa" or self.language != "pt-BR":
            raise ValueError("the approved Crônicas production contract requires pm_santa and pt-BR")
        allowed = {"horizontal", "vertical"}
        if not self.output_variants or not set(self.output_variants).issubset(allowed):
            raise ValueError("output_variants must contain horizontal and/or vertical")
        if self.mode not in {"plan", "validate-reference", "execute"}:
            raise ValueError("mode must be plan, validate-reference or execute")
        if self.output_root is not None and not str(self.output_root).strip():
            raise ValueError("output_root must be non-empty when provided")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


class CinematicCompatibility:
    """Audit and safely execute the registered cinematic production boundary."""

    def __init__(self, paths: FabuloomPaths, *, product_root: str | Path):
        self.paths = paths
        self.product_root = Path(product_root).expanduser().resolve()

    @property
    def profile_path(self) -> Path:
        return self.product_root / "profiles" / "cronicas-cinematic-production.json"

    @property
    def runner_registry_path(self) -> Path:
        return self.product_root / "profiles" / "registries" / "cinematic-runners.json"

    @property
    def reference_root(self) -> Path:
        return self.paths.exports / "cronicas-book1-capitulo11-cinematic-r2"

    def _candidate_runners(self) -> list[tuple[Path, str]]:
        candidates: list[tuple[Path, str]] = []
        if self.runner_registry_path.is_file():
            try:
                registry = json.loads(self.runner_registry_path.read_text(encoding="utf-8"))
                for entry in registry.get("runners", []):
                    if isinstance(entry, dict) and isinstance(entry.get("script"), str):
                        candidates.append((self.product_root / entry["script"], f"registered:{entry.get('id', 'unknown')}"))
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        candidates.extend(
            [
                (self.paths.private / "productions" / "cronicas" / "examples" / "cronicas_cap11_cin_001_r2.py", "private-production-evidence"),
                (self.paths.workspace / "legacy" / "cronicas_cap11_cin_001_r2.py", "workspace-legacy-evidence"),
            ]
        )
        # Existing PR worktrees are read-only evidence. They are never
        # executable through this service.
        worktrees = self.paths.root / "worktrees"
        if worktrees.is_dir():
            candidates.extend((path, "worktree-evidence") for path in sorted(worktrees.glob("*/examples/cronicas_cap11_cin_001_r2.py")))
        unique: list[tuple[Path, str]] = []
        seen: set[str] = set()
        for path, source in candidates:
            resolved = path.expanduser().resolve()
            key = str(resolved).casefold()
            if key not in seen:
                seen.add(key)
                unique.append((resolved, source))
        return unique

    def _runner_record(self, path: Path, source: str) -> dict[str, object]:
        inside = True
        try:
            path.relative_to(self.paths.root.resolve())
        except ValueError:
            inside = False
        valid_name = bool(_RUNNER_NAME.match(path.name))
        exists = path.is_file()
        source_text = ""
        if exists and path.stat().st_size <= 2 * 1024 * 1024:
            source_text = path.read_text(encoding="utf-8", errors="replace")
        # A printed field or a hard-coded ``OUTPUT_ROOT`` is not a parameter.
        # Require the registered request boundary, not an arbitrary command.
        parametrized = "--request" in source_text and "output_root" in source_text
        registered = source.startswith("registered:")
        return {
            "path": str(path),
            "relative_path": _relative(path, self.paths.root),
            "source": source,
            "exists": exists,
            "inside_runtime_root": inside,
            "safe_name": valid_name,
            "sha256": _sha256(path) if exists else None,
            "parameterized_output": parametrized,
            "registered": registered,
            "execution_allowed": bool(exists and inside and valid_name and registered and parametrized),
            "reason": None if registered and parametrized else "runner is not a registered request-boundary runner",
        }

    def _registered_runner(self, runner_id: str) -> dict[str, object]:
        if not self.runner_registry_path.is_file():
            raise CinematicCompatibilityError(f"registered runner registry is missing: {self.runner_registry_path}")
        try:
            registry = json.loads(self.runner_registry_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CinematicCompatibilityError("registered runner registry is invalid") from exc
        entry = next((item for item in registry.get("runners", []) if isinstance(item, dict) and item.get("id") == runner_id), None)
        if not entry:
            raise CinematicCompatibilityError(f"unknown cinematic runner id: {runner_id}")
        script_value = entry.get("script")
        if not isinstance(script_value, str) or Path(script_value).is_absolute() or ".." in Path(script_value).parts:
            raise CinematicCompatibilityError("registered runner script must be product-relative")
        script = (self.product_root / script_value).resolve()
        try:
            script.relative_to(self.product_root.resolve())
        except ValueError as exc:
            raise CinematicCompatibilityError("registered runner escaped product root") from exc
        if not script.is_file() or not _RUNNER_NAME.match(script.name):
            raise CinematicCompatibilityError("registered runner script is missing or has an unsafe name")
        expected_hash = entry.get("sha256")
        actual_hash = _sha256(script)
        if not isinstance(expected_hash, str) or expected_hash != actual_hash:
            raise CinematicCompatibilityError("registered runner hash does not match the product registry")
        source = script.read_text(encoding="utf-8", errors="replace")
        if "--request" not in source or "output_root" not in source:
            raise CinematicCompatibilityError("registered runner lacks the isolated request/output contract")
        return {"id": runner_id, "script": str(script), "relative_script": script_value, "sha256": actual_hash, "capabilities": entry.get("capabilities", [])}

    def _reference_files(self) -> list[Path]:
        return [
            self.reference_root / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-horizontal-r2.mp4",
            self.reference_root / "videos" / "cronicas-capitulo11-o-eco-que-nao-morre-vertical-r2.mp4",
            self.reference_root / "manifest" / "chapter11-full-r2.json",
            self.reference_root / "timelines" / "chapter11-r2.json",
            self.reference_root / "subtitles" / "chapter11-r2.srt",
            self.reference_root / "reports" / "chapter11-r2-technical-report.json",
        ]

    def _input_records(self, *, hash_inputs: bool = False) -> list[dict[str, object]]:
        relative_paths = [
            "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
            "workspace/inputs/music/book1/Alba Quando a Luz Rasga o Céu.mp3",
            "workspace/inputs/biblioteca videos e musicas/FBS-001-INTRO-H-O-Despertar-do-Cristal.mp4",
            "workspace/inputs/biblioteca videos e musicas/FBS-001-INTRO-V-O-Despertar-do-Cristal.mp4",
            "workspace/inputs/biblioteca videos e musicas/santa-cinematic-opening-v-v1.mp4",
            "workspace/inputs/biblioteca videos e musicas/santa-cinematic-opening-v-v2.mp4",
        ]
        records: list[dict[str, object]] = []
        for relative in relative_paths:
            path = self.paths.root / Path(relative)
            records.append({
                "relative_path": relative,
                "exists": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256": _sha256(path) if hash_inputs and path.is_file() else None,
            })
        return records

    def audit(self, *, hash_inputs: bool = False) -> dict[str, object]:
        """Return a read-only compatibility report; no media is written."""

        self.paths.validate_runtime_root()
        runners = [self._runner_record(path, source) for path, source in self._candidate_runners()]
        reference = [{"relative_path": _relative(path, self.paths.root), "exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else None} for path in self._reference_files()]
        inputs = self._input_records(hash_inputs=hash_inputs)
        registry = self.product_root / "assets" / "character-registry.json"
        santa_approved = False
        if registry.is_file():
            try:
                payload = json.loads(registry.read_text(encoding="utf-8"))
                santa_approved = any(item.get("id") == "santa-v5-base" and item.get("approval_status") == "APPROVED" for item in payload.get("characters", []))
            except (OSError, ValueError, json.JSONDecodeError):
                santa_approved = False
        reference_ok = all(bool(item["exists"]) for item in reference)
        executable_runner = next((item for item in runners if item["execution_allowed"]), None)
        missing_inputs = [item["relative_path"] for item in inputs if not item["exists"]]
        blockers: list[str] = []
        if not reference_ok:
            blockers.append("chapter 11 R2 reference artifacts are incomplete")
        if not santa_approved:
            blockers.append("approved Santa V5 registry record is unavailable")
        if missing_inputs:
            blockers.append("cinematic input library is incomplete")
        if not executable_runner:
            blockers.append("no registered request-boundary cinematic runner is available")
        return {
            "format": CINEMATIC_FORMAT,
            "profile": CINEMATIC_PROFILE_ID,
            "legacy_pipeline": {
                "reference_implementation": "PR #56 / Chapter 11 R2",
                "runners": runners,
                "status": "available_for_reference_validation" if reference_ok else "incomplete",
                "execution_policy": "registered_runner_hash_and_isolated_output_only",
            },
            "reference_artifacts": {"root": str(self.reference_root), "files": reference, "complete": reference_ok},
            "inputs": inputs,
            "input_hashes": "included" if hash_inputs else "not_computed_by_default; use tools/fab_arch_003_audit.py --hash-sources",
            "approved_assets": {"character_registry": str(registry), "santa_v5_approved": santa_approved},
            "shared_engine": {
                "manifest_contract": "fabuloom.audio-manifest/0.1",
                "timeline_contract": "fabuloom.cronicas-cap11-cinematic/0.2",
                "audio": "Kokoro native WAV + FFmpeg voice-priority ducking/limiter",
                "canvas": "legacy NarratorAvatarRenderer through the registered runner",
                "export": "FFmpeg H.264/AAC horizontal and vertical",
                "status": "reference_validation_only" if not executable_runner else "ready_for_execution",
            },
            "next_chapter": {
                "source_document_present": inputs[0]["exists"],
                "official_santa_present": santa_approved,
                "production_profile_present": self.profile_path.is_file(),
                "status": "ready_to_execute" if inputs[0]["exists"] and santa_approved and self.profile_path.is_file() and executable_runner else ("ready_to_plan" if inputs[0]["exists"] and santa_approved and self.profile_path.is_file() else "blocked"),
                "constraint": "registered runner must pass source, voice, output and checkpoint validation before render",
            },
            "shorts": {
                "profile": SHORTS_PROFILE_ID,
                "status": "review_required",
                "requires_storyboard": True,
                "quality_reference": "do not use FBS-SHORT-001 as an artistic reference",
            },
            "blocking_issues": blockers,
        }

    @staticmethod
    def _probe(path: Path) -> dict[str, object]:
        if not shutil.which("ffprobe"):
            return {"path": str(path), "error": "ffprobe unavailable"}
        result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        video = next((item for item in payload.get("streams", []) if item.get("codec_type") == "video"), {})
        audio = next((item for item in payload.get("streams", []) if item.get("codec_type") == "audio"), {})
        return {
            "path": str(path),
            "duration_seconds": float(payload.get("format", {}).get("duration", 0.0)),
            "video": {key: video.get(key) for key in ("codec_name", "width", "height", "r_frame_rate", "pix_fmt")},
            "audio": {key: audio.get(key) for key in ("codec_name", "sample_rate", "channels", "channel_layout")},
        }

    def validate_reference(self, *, decode: bool = False, progress: Callable[[str], None] | None = None) -> dict[str, object]:
        """Validate the existing chapter 11 masters without recapturing them."""

        audit = self.audit()
        results: list[dict[str, object]] = []
        for path in self._reference_files()[:2]:
            if progress:
                progress(f"validating {_relative(path, self.paths.root)}")
            if not path.is_file():
                results.append({"path": str(path), "valid": False, "error": "missing"})
                continue
            probe = self._probe(path)
            video = probe.get("video", {})
            audio = probe.get("audio", {})
            expected = (1920, 1080) if "horizontal" in path.name else (1080, 1920)
            valid = (
                video.get("codec_name") == "h264"
                and int(video.get("width") or 0) == expected[0]
                and int(video.get("height") or 0) == expected[1]
                and audio.get("codec_name") == "aac"
                and int(audio.get("sample_rate") or 0) == 48000
                and int(audio.get("channels") or 0) == 2
            )
            decode_result = "not_requested"
            if decode and valid and shutil.which("ffmpeg"):
                completed = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True)
                decode_result = "passed" if completed.returncode == 0 else (completed.stderr[-1000:] or "failed")
                valid = valid and decode_result == "passed"
            results.append({"path": str(path), "probe": probe, "valid": valid, "decode": decode_result})
        report_path = self.reference_root / "reports" / "chapter11-r2-technical-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
        report_checks = {
            "voice": report.get("voice", {}).get("voice_id") == "pm_santa" and report.get("voice", {}).get("language") == "pt-BR",
            "ducking": report.get("music", {}).get("ducking") == "sidechain voice-priority",
            "blackdetect": all(not item.get("blackdetect_events") for item in report.get("validations", {}).values() if isinstance(item, dict)),
            "decode": all(item.get("decode_passed") for item in report.get("validations", {}).values() if isinstance(item, dict)),
        }
        return {
            "format": "fabuloom.cinematic-reference-validation/0.1",
            "status": "passed" if audit["reference_artifacts"]["complete"] and all(item["valid"] for item in results) and all(report_checks.values()) else "failed",
            "reference": str(self.reference_root),
            "masters": results,
            "report_checks": report_checks,
            "r1_preserved": (self.paths.exports / "cronicas-book1-capitulo11-cinematic-v1").is_dir(),
            "resynthesis": False,
            "recapture": False,
            "artistic_qa": "REVIEW_REQUIRED",
        }

    def plan(self, request: CinematicRequest) -> dict[str, object]:
        request.validate()
        audit = self.audit()
        if not audit["reference_artifacts"]["complete"] or audit["next_chapter"]["status"] == "blocked":
            plan_status = "blocked"
        elif audit["next_chapter"]["status"] == "ready_to_execute":
            plan_status = "ready_for_execution"
        else:
            plan_status = "ready_for_reference_validation"
        return {
            "format": "fabuloom.cinematic-production-plan/0.1",
            "status": plan_status,
            "request": {
                "chapter": request.chapter,
                "chapter_title": request.chapter_title,
                "source_document": request.source_document,
                "voice_id": request.voice_id,
                "language": request.language,
                "output_variants": list(request.output_variants),
                "runner": request.runner or "cronicas.chapter",
                "output_root": request.output_root,
            },
            "stages": [
                "validate source DOCX boundaries and hash",
                "reuse or synthesize measured Kokoro pm_santa segments",
                "compose Santa V5 NarratorAvatarRenderer and approved scenes",
                "mix owner-approved music with voice-priority ducking and limiter",
                "export horizontal and vertical through FFmpeg",
                "run FFprobe/decode/blackdetect and separate artistic review",
            ],
            "adapter": audit["shared_engine"],
            "safety": {
                "approved_outputs_overwrite": False,
                "external_video_audio": "discarded",
                "draft_characters": "blocked",
                "private_library": "referenced by stable catalog IDs, never copied into product",
            },
            "limitations": audit["blocking_issues"],
        }

    def _choose_output_root(self, request: CinematicRequest) -> Path:
        if request.output_root:
            candidate = Path(request.output_root)
            if not candidate.is_absolute():
                candidate = self.paths.root / candidate
            exports_root = self.paths.exports.resolve()
            resolved = candidate.resolve()
            try:
                relative = resolved.relative_to(exports_root)
            except ValueError as exc:
                raise CinematicCompatibilityError("cinematic output_root must stay inside workspace/exports") from exc
            if not relative.parts:
                raise CinematicCompatibilityError("cinematic output_root must be a child of workspace/exports")
            return resolved
        base = self.paths.exports / f"cronicas-book1-capitulo{request.chapter}-cinematic-production"
        if not base.exists():
            return base
        if (base / "CHECKPOINT.json").is_file() and not (base / "reports" / "production-result.json").is_file():
            return base
        for index in range(2, 1000):
            candidate = base.with_name(f"{base.name}-attempt-{index}")
            if not candidate.exists():
                return candidate
        raise CinematicCompatibilityError("unable to allocate a non-overwriting cinematic output root")

    def execute(self, request: CinematicRequest, *, progress: Callable[[str, float, dict[str, object] | None], None] | None = None, cancel: threading.Event | None = None) -> dict[str, object]:
        """Execute only a hash-registered runner with a workspace output root."""

        request.validate()
        if request.mode != "execute":
            raise CinematicCompatibilityError("execute requires mode=execute")
        runner_id = request.runner or "cronicas.chapter"
        runner = self._registered_runner(runner_id)
        output_root = self._choose_output_root(request)
        if output_root.is_dir() and (output_root / "reports" / "production-result.json").is_file():
            raise CinematicCompatibilityError(f"approved or completed output exists; refusing overwrite: {output_root}")
        output_root.mkdir(parents=True, exist_ok=True)
        request_file = output_root / ".engine-request.json"
        payload = {
            "chapter": request.chapter,
            "chapter_title": request.chapter_title,
            "source_document": request.source_document,
            "voice_id": request.voice_id,
            "language": request.language,
            "music_asset_id": request.music_asset_id,
            "scene_asset_ids": list(request.scene_asset_ids),
            "output_variants": list(request.output_variants),
            "output_root": str(output_root),
            "runner_id": runner_id,
        }
        if request_file.is_file():
            try:
                existing = json.loads(request_file.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise CinematicCompatibilityError("existing engine request is invalid; refusing to reuse output root") from exc
            if existing != payload:
                raise CinematicCompatibilityError("output root contains a different request; refusing to mix productions")
        else:
            request_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_path = output_root / "runner.log"
        environment = os.environ.copy()
        environment.update({"FABULOOM_ROOT": str(self.paths.root), "FABULOOM_WORKSPACE_ROOT": str(self.paths.root), "FABULOOM_EXPORT_ROOT": str(self.paths.exports), "PYTHONPATH": str(self.product_root) + os.pathsep + environment.get("PYTHONPATH", "")})
        configured_python = self.paths.root / "workspace" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python_executable = configured_python if configured_python.is_file() else Path(sys.executable)
        command = [str(python_executable), str(runner["script"]), "--request", str(request_file)]
        if progress:
            progress("cinematic-runner-start", 0.08, {"runner": runner_id, "output_root": str(output_root)})
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"event": "start", "runner": runner_id, "command": command, "output_root": str(output_root)}) + "\n")
            process = subprocess.Popen(command, cwd=str(self.product_root), env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            lines: list[str] = []
            def consume() -> None:
                assert process.stdout is not None
                for line in process.stdout:
                    lines.append(line.rstrip())
                    log.write(line)
                    log.flush()
            reader = threading.Thread(target=consume, daemon=True)
            reader.start()
            while process.poll() is None:
                if cancel and cancel.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise InterruptedError("cinematic runner cancelled")
                if progress:
                    progress("cinematic-runner", 0.10, {"runner": runner_id, "output_root": str(output_root), "checkpoint": str(output_root / "CHECKPOINT.json")})
                time.sleep(0.5)
            reader.join(timeout=5)
            return_code = process.returncode
        if return_code != 0:
            tail = "\n".join(lines[-20:])
            raise CinematicCompatibilityError(f"registered cinematic runner failed with exit code {return_code}: {tail}")
        result_path = output_root / "reports" / "production-result.json"
        if not result_path.is_file():
            raise CinematicCompatibilityError("runner completed without production-result.json")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["engine_execution"] = {"runner_id": runner_id, "runner_sha256": runner["sha256"], "output_root": str(output_root), "log": str(log_path), "request": payload}
        if progress:
            progress("cinematic-runner-complete", 1.0, {"output_root": str(output_root), "outputs": result.get("outputs", [])})
        return result


__all__ = [
    "CINEMATIC_FORMAT",
    "CINEMATIC_PROFILE_ID",
    "SHORTS_PROFILE_ID",
    "CinematicCompatibility",
    "CinematicCompatibilityError",
    "CinematicRequest",
]
