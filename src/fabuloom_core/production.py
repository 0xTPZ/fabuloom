"""Reusable production adapter for narration, Canvas capture and FFmpeg export.

This module is intentionally an orchestration boundary. TTS segmentation and
manifest composition stay in ``narration.py``; Canvas effects stay in the
existing browser renderer; FFmpeg remains the media encoder. The service adds
shared jobs, checkpoints, reports and safe workspace handling around them.
"""

from __future__ import annotations

from array import array
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import time
from typing import Any, Callable
import uuid
import wave
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlparse

from .kokoro import KokoroTTSProvider
from .narration import synthesize_narration
from .paths import FabuloomPaths
from .profiles import ProfileRegistry
from .serialization import serialize_manifest
from .tts import SynthesisRequest, SynthesisResult, TTSError


PRODUCTION_FORMAT = "fabuloom.production-project/0.1"
ECONOMY_CAPTURE_FPS = 5
REAL_CAPTURE_FPS = (24, 30)
DEFAULT_OUTPUT_FPS = 30
DEFAULT_AUDIO_SAMPLE_RATE = 48_000
DEFAULT_AUDIO_CHANNELS = 2
DEMO_TEXT = (
    "Esta é uma demonstração pública do Fabuloom Studio. "
    "O mesmo motor organiza o projeto, prepara a narração e controla a linha do tempo. "
    "O Canvas cria os movimentos e os efeitos. "
    "O FFmpeg entrega o vídeo final para revisão humana."
)


class ProductionError(RuntimeError):
    """Raised when a shared production operation cannot continue safely."""


class DeterministicAudioProvider:
    """Offline WAV provider for generic, redistributable acceptance tests.

    It deliberately produces an audible synthetic tone bed rather than
    pretending to be human speech. Real projects may select Kokoro through the
    same narration service without changing the manifest or job boundary.
    """

    provider_id = "simulated-audio"

    def __init__(self, output_dir: str | Path, *, sample_rate: int = 24_000):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.sample_rate = sample_rate

    def synthesize(self, request: SynthesisRequest, output_path: str | Path | None = None) -> SynthesisResult:
        request.validate()
        if request.voice_id not in {"sim-narrator", "sim-character"}:
            raise TTSError("UNSUPPORTED_VOICE", f"synthetic provider does not expose {request.voice_id!r}")
        output = Path(output_path or self.output_dir / f"{request.id}.wav")
        output = output if output.is_absolute() else self.output_dir / output
        output = output.resolve()
        try:
            output.relative_to(self.output_dir)
        except ValueError as exc:
            raise TTSError("INVALID_OUTPUT_PATH", "synthetic WAV must remain inside the production directory") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise TTSError("OUTPUT_EXISTS", f"WAV already exists: {output}")
        words = len(request.text.split())
        duration_ms = max(3_700, round(words * 210 / request.parameters.speed))
        digest = hashlib.sha256(request.text.encode("utf-8")).digest()
        base_frequency = 210 + digest[0] % 110
        frames = round(duration_ms * self.sample_rate / 1000)
        with wave.open(str(output), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(self.sample_rate)
            samples = array("h")
            for index in range(frames):
                time_s = index / self.sample_rate
                envelope = min(1.0, index / max(1, self.sample_rate * 0.08), (frames - index) / max(1, self.sample_rate * 0.12))
                sample = (0.16 * math.sin(2 * math.pi * base_frequency * time_s) + 0.05 * math.sin(2 * math.pi * (base_frequency * 1.5) * time_s)) * envelope
                samples.append(max(-32767, min(32767, round(sample * 32767))))
            stream.writeframes(samples.tobytes())
        return SynthesisResult(
            request_id=request.id,
            provider_id=self.provider_id,
            voice_id=request.voice_id,
            language=request.language,
            audio_uri=output.as_uri(),
            duration_ms=duration_ms,
            metadata={"simulated": True, "audio_kind": "deterministic_tone_bed", "timing_source": "audio_duration_only", "sample_rate": self.sample_rate},
        )


class ProductionService:
    """Shared orchestration for a small, resumable audiovisual production."""

    def __init__(self, paths: FabuloomPaths, *, product_root: str | Path | None = None, profiles_root: str | Path | None = None):
        self.paths = paths
        self.product_root = Path(product_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
        self.profiles = ProfileRegistry(profiles_root or self.product_root / "profiles")

    def dry_run(self, payload: dict[str, object] | None = None) -> dict[str, object]:
        request = payload or {}
        profile_id = str(request.get("profile") or "cinematic-short")
        profile = self.profiles.get(profile_id)
        export_settings = self._export_settings(profile, request)
        dependencies = self._dependency_report()
        return {
            "format": "fabuloom.render-plan/0.1",
            "status": "ready" if profile["status"] == "ready_for_technical_test" and dependencies["ffmpeg"] and dependencies["ffprobe"] else "blocked",
            "profile": {"id": profile["id"], "version": profile["version"], "status": profile["status"]},
            "provider": str(request.get("provider") or "simulated-audio"),
            "canvas": {"renderer": "frontend/src/music-studio-renderer.mjs", "capture": "frontend/capture-music-studio.html"},
            "audio": {"manifest": "fabuloom.audio-manifest/0.1", "subtitles": "SRT from measured segment boundaries", "mix": "optional FFmpeg voice-priority ducking when music_path is supplied", "export_sample_rate": export_settings["audio_sample_rate"], "export_channels": export_settings["audio_channels"], "source_rate_policy": "preserve native provider WAV until FFmpeg export"},
            "export": export_settings,
            "dependencies": dependencies,
            "storage": self.paths.storage_report(),
            "limits": ["generic acceptance audio is synthetic tone bed", "human artistic review remains required"],
        }

    def render_demo(self, payload: dict[str, object] | None = None, *, progress: Callable[[str, float, dict[str, object] | None], None] | None = None) -> dict[str, object]:
        request = payload or {}
        profile_id = str(request.get("profile") or "cinematic-short")
        profile = self.profiles.get(profile_id)
        if profile["status"] != "ready_for_technical_test":
            raise ProductionError(f"profile is not technically ready: {profile_id}")
        self.paths.validate_runtime_root()
        self.paths.ensure_runtime_directories()
        export_settings = self._export_settings(profile, request)
        self.paths.require_free_space(64 * 1024 * 1024, operation="generic production render")
        output_id = str(request.get("output_id") or "fab-arch-002-cold-demo")
        if not output_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in output_id):
            raise ProductionError("output_id contains unsafe characters")
        root = (self.paths.exports / output_id).resolve()
        root.relative_to(self.paths.exports.resolve())
        root.mkdir(parents=True, exist_ok=True)
        checkpoint_path = root / "CHECKPOINT.json"
        music_path = self._resolve_music_path(request.get("music_path"))
        fingerprint_payload: dict[str, object] = {"text": str(request.get("text") or DEMO_TEXT), "profile": profile_id, "provider": str(request.get("provider") or "simulated-audio"), "duration_policy": "synthetic-segment-minimum-3700ms", "capture_fps": export_settings["capture_fps"], "output_fps": export_settings["output_fps"], "audio_sample_rate": export_settings["audio_sample_rate"], "audio_channels": export_settings["audio_channels"]}
        if music_path is not None:
            fingerprint_payload["music_path"] = str(music_path)
            fingerprint_payload["music_sha256"] = self._sha256(music_path)
        fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")).hexdigest()
        checkpoint = self._load_checkpoint(checkpoint_path)
        if checkpoint and checkpoint.get("fingerprint") != fingerprint:
            raise ProductionError(f"existing output has a different request fingerprint: {root}")
        checkpoint = checkpoint or {"format": "fabuloom.production-checkpoint/0.1", "id": output_id, "fingerprint": fingerprint, "status": "running", "stages": {}}

        def mark(stage: str, value: float, **extra: object) -> None:
            checkpoint["stages"][stage] = {"progress": value, "updated_at": time.time(), **extra}
            checkpoint["last_stage"] = stage
            self._write_json(checkpoint_path, checkpoint)
            if progress:
                progress(stage, value, extra)

        project_path = root / "project.json"
        asset_path = root / "assets" / "generic-scene.svg"
        manifest_path = root / "narration.json"
        voice_path = root / "voice.wav"
        audio_path = root / "audio.wav"
        captions_path = root / "captions.srt"
        video_path = root / "video.mp4"
        board_path = root / "board.png"
        text = str(request.get("text") or DEMO_TEXT)
        provider_name = str(request.get("provider") or "simulated-audio")
        mark("planning", 0.05, output=str(root))
        self._write_generic_scene(asset_path)

        if not manifest_path.is_file() or not audio_path.is_file():
            mark("narration", 0.15, provider=provider_name)
            provider = self._provider(provider_name, root / "segments")
            try:
                run = synthesize_narration(provider, text, narration_id=output_id, manifest_id=output_id, voice_id=str(request.get("voice_id") or "sim-narrator"), language=str(request.get("language") or "pt-BR"), output_dir=root / "segments", max_chars=360)
            finally:
                close = getattr(provider, "close", None)
                if callable(close):
                    close()
            self._write_json(manifest_path, json.loads(serialize_manifest(run.manifest)))
            self._compose_audio(run.manifest, voice_path)
            self._write_srt(run.manifest, captions_path)
            manifest = json.loads(serialize_manifest(run.manifest))
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            mark("narration-reused", 0.22, manifest=str(manifest_path))
        duration_ms = int(manifest["duration_ms"])
        if not voice_path.is_file():
            self._compose_audio(manifest, voice_path)
        mix_info = self._prepare_audio(voice_path, audio_path, music_path, duration_ms, mark)
        project = self._write_canvas_project(project_path, output_id, root, manifest, duration_ms, profile_id, output_fps=int(export_settings["output_fps"]), audio_sample_rate=int(export_settings["audio_sample_rate"]), audio_channels=int(export_settings["audio_channels"]))
        mark("timeline", 0.28, duration_ms=duration_ms, segments=len(manifest.get("segments", [])))

        capture_summary: dict[str, object]
        if not video_path.is_file():
            mark("canvas-capture", 0.35, renderer="frontend/src/music-studio-renderer.mjs", capture_fps=export_settings["capture_fps"], output_fps=export_settings["output_fps"])
            frames, capture_summary = self._capture_canvas(root, duration_ms, capture_fps=int(export_settings["capture_fps"]), output_fps=int(export_settings["output_fps"]))
            mark("canvas-captured", 0.62, **capture_summary)
            self._render_mp4(frames, audio_path, captions_path, video_path, duration_ms, output_fps=int(export_settings["output_fps"]), audio_sample_rate=int(export_settings["audio_sample_rate"]), audio_channels=int(export_settings["audio_channels"]))
            mark("encoded", 0.82, video=str(video_path))
            self._make_board(video_path, board_path, duration_ms, output_fps=int(export_settings["output_fps"]))
        else:
            mark("encode-reused", 0.82, video=str(video_path))
            capture_summary = dict(checkpoint.get("stages", {}).get("canvas-captured", {}))
        qa = self._validate_output(video_path, duration_ms, expected_fps=int(export_settings["output_fps"]), expected_audio_sample_rate=int(export_settings["audio_sample_rate"]), expected_audio_channels=int(export_settings["audio_channels"]))
        qa["capture"] = capture_summary
        qa["fluency_claim"] = "real_canvas_capture_validated" if capture_summary.get("real_capture_validated") else "economy_capture_or_reused_output_requires_motion_review"
        self._write_json(root / "technical-qa.json", qa)
        report = {
            "format": "fabuloom.production-report/0.1",
            "project": str(project_path),
            "manifest": str(manifest_path),
            "audio": str(audio_path),
            "captions": str(captions_path),
            "video": str(video_path),
            "board": str(board_path),
            "profile": profile_id,
            "provider": provider_name,
            "audio_mix": mix_info,
            "export": export_settings,
            "duration_ms": duration_ms,
            "backend": "Canvas music-studio-renderer + FFmpeg",
            "technical_qa": qa,
            "artistic_qa": {"status": "REVIEW_REQUIRED", "human_approval": False, "checklist": ["hook", "continuity", "safe area", "rhythm", "voice/music", "identity"]},
            "source_policy": "generic redistributable generated SVG only; no private library assets",
        }
        self._write_json(root / "report.json", report)
        (root / "report.md").write_text(self._report_markdown(report), encoding="utf-8")
        checkpoint["status"] = "completed"
        checkpoint["completed_at"] = time.time()
        self._write_json(checkpoint_path, checkpoint)
        mark("completed", 1.0, qa=qa)
        return report

    def _provider(self, name: str, output_dir: Path) -> object:
        if name == "simulated-audio":
            return DeterministicAudioProvider(output_dir)
        if name == "kokoro":
            return KokoroTTSProvider(output_dir=output_dir)
        raise ProductionError(f"unsupported production provider: {name}")

    def _resolve_music_path(self, value: object) -> Path | None:
        if value in (None, ""):
            return None
        candidate = Path(str(value)).expanduser()
        if not candidate.is_absolute():
            candidate = self.paths.root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.paths.root.resolve())
        except ValueError as exc:
            raise ProductionError("music_path must remain inside the configured Fabuloom root") from exc
        if candidate.suffix.lower() not in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}:
            raise ProductionError("music_path must reference a supported audio file")
        if not candidate.is_file():
            raise ProductionError(f"music asset does not exist: {candidate}")
        return candidate

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _prepare_audio(self, voice: Path, output: Path, music: Path | None, duration_ms: int, mark: Callable[..., None]) -> dict[str, object]:
        if music is None:
            if not output.is_file():
                shutil.copy2(voice, output)
            mark("audio-ready", 0.30, mode="voice-only")
            return {"mode": "voice-only", "music_used": False, "timing_source": "measured_voice_manifest"}
        if output.is_file():
            mark("audio-mix-reused", 0.30, mode="voice-priority-ducking", music=music.name)
            return {"mode": "voice-priority-ducking", "music_used": True, "music_name": music.name, "music_sha256": self._sha256(music), "timing_source": "measured_voice_manifest", "reused": True}
        duration = duration_ms / 1000
        fade_out = max(0.0, duration - 3.5)
        graph = (
            f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration:.3f},asetpts=N/SR/TB[voice];"
            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duration:.3f},volume=0.18,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out:.3f}:d=3.5[music];"
            "[music][voice]sidechaincompress=threshold=0.025:ratio=8:attack=35:release=700:makeup=1:link=average[ducked];"
            "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.92:attack=5:release=500[out]"
        )
        mark("audio-mix", 0.30, mode="voice-priority-ducking", music=music.name)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}", "-ar", "24000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True, cwd=str(output.parent), capture_output=True, text=True)
        return {"mode": "voice-priority-ducking", "music_used": True, "music_name": music.name, "music_sha256": self._sha256(music), "timing_source": "measured_voice_manifest", "ducking": {"threshold": 0.025, "ratio": 8, "attack_ms": 35, "release_ms": 700}, "limiter": {"limit": 0.92}, "music_speed_and_pitch_changed": False, "reused": False}

    def _dependency_report(self) -> dict[str, object]:
        edge = self._find_edge(required=False)
        return {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")), "canvas_browser": bool(edge), "kokoro_import": self._module_available("kokoro")}

    @classmethod
    def _export_settings(cls, profile: dict[str, object], request: dict[str, object]) -> dict[str, object]:
        configured = profile.get("export") if isinstance(profile.get("export"), dict) else {}
        configured = configured if isinstance(configured, dict) else {}
        capture_fps = cls._positive_int(request.get("capture_fps", configured.get("capture_fps", ECONOMY_CAPTURE_FPS)), "capture_fps", allowed={ECONOMY_CAPTURE_FPS, *REAL_CAPTURE_FPS})
        output_fps = cls._positive_int(request.get("output_fps", configured.get("video_fps", DEFAULT_OUTPUT_FPS)), "output_fps", allowed={24, 30})
        audio_sample_rate = cls._positive_int(request.get("audio_sample_rate", configured.get("audio_sample_rate", DEFAULT_AUDIO_SAMPLE_RATE)), "audio_sample_rate", minimum=8_000, maximum=192_000)
        audio_channels = cls._positive_int(request.get("audio_channels", configured.get("audio_channels", DEFAULT_AUDIO_CHANNELS)), "audio_channels", allowed={1, 2})
        return {
            "capture_fps": capture_fps,
            "output_fps": output_fps,
            "audio_sample_rate": audio_sample_rate,
            "audio_channels": audio_channels,
            "audio_codec": "aac",
            "capture_quality": "economy" if capture_fps == ECONOMY_CAPTURE_FPS else "real_canvas_capture",
        }

    @staticmethod
    def _positive_int(value: object, name: str, *, minimum: int = 1, maximum: int | None = None, allowed: set[int] | None = None) -> int:
        if isinstance(value, bool):
            raise ProductionError(f"{name} must be an integer, not a boolean")
        if isinstance(value, float) and not value.is_integer():
            raise ProductionError(f"{name} must be an integer")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ProductionError(f"{name} must be an integer") from exc
        if parsed < minimum or (maximum is not None and parsed > maximum):
            raise ProductionError(f"{name} must be between {minimum} and {maximum or 'unbounded'}")
        if allowed is not None and parsed not in allowed:
            choices = ", ".join(str(item) for item in sorted(allowed))
            raise ProductionError(f"{name} must be one of: {choices}")
        return parsed

    @staticmethod
    def _module_available(name: str) -> bool:
        # Discovery must not import optional runtimes merely to render a
        # doctor/capabilities response. Importing Kokoro can initialize torch,
        # loguru and asyncio on Windows; actual provider initialization remains
        # responsible for reporting dependency/runtime failures.
        return importlib.util.find_spec(name) is not None

    @staticmethod
    def _find_edge(*, required: bool = True) -> str | None:
        candidates = [shutil.which("msedge"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.name.lower() == "msedge.exe" and path.is_file():
                return str(path)
            for nested in (path / "Microsoft" / "Edge" / "Application" / "msedge.exe", path / "msedge.exe"):
                if nested.is_file():
                    return str(nested)
        if required:
            raise ProductionError("Microsoft Edge is required for the shared Canvas capture path")
        return None

    def _capture_canvas(self, project_root: Path, duration_ms: int, *, capture_fps: int = ECONOMY_CAPTURE_FPS, output_fps: int = DEFAULT_OUTPUT_FPS) -> tuple[Path, dict[str, object]]:
        capture_fps = self._positive_int(capture_fps, "capture_fps", allowed={ECONOMY_CAPTURE_FPS, *REAL_CAPTURE_FPS})
        output_fps = self._positive_int(output_fps, "output_fps", allowed={24, 30})
        edge = self._find_edge()
        capture_root = project_root / "captures"
        capture_root.mkdir(parents=True, exist_ok=True)
        session = f"engine-{uuid.uuid4().hex[:10]}"
        session_root = capture_root / session
        session_root.mkdir(parents=True, exist_ok=True)
        profile = Path(tempfile.mkdtemp(prefix=".edge-profile-", dir=self.paths.staging))
        port = 8890 + int(uuid.uuid4().hex[:3], 16) % 300
        environment = os.environ.copy()
        environment.update({"FABULOOM_ROOT": str(self.paths.root), "FABULOOM_WORKSPACE_ROOT": str(self.paths.root), "FABULOOM_EXPORT_ROOT": str(self.paths.exports), "FABULOOM_CAPTURE_DIR": str(capture_root), "FABULOOM_NO_JOB_RECOVERY": "1"})
        server = subprocess.Popen([os.environ.get("PYTHON", os.sys.executable), str(self.product_root / "frontend" / "server.py"), "--port", str(port)], cwd=str(self.product_root), env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        browser: subprocess.Popen[bytes] | None = None
        try:
            self._wait_http(f"http://127.0.0.1:{port}/capture-music-studio.html", 25)
            relative = project_root.relative_to(self.paths.exports).as_posix()
            url = f"http://127.0.0.1:{port}/capture-music-studio.html?session={session}&project=/exports/{relative}/project.json&mode=short&fps={capture_fps}&output_fps={output_fps}"
            browser = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--disable-gpu-compositing", "--disable-background-networking", "--hide-scrollbars", "--window-size=1080,1920", f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            complete = session_root / "complete.json"
            error = session_root / "error.json"
            # Uploading a full-resolution JPEG per Canvas frame is deliberately
            # conservative. Keep the economical mode bounded, but give real
            # 24/30 fps captures a budget proportional to their frame count so
            # a slow local browser cannot be mistaken for a render failure.
            capture_timeout_seconds = max(180.0, min(900.0, duration_ms / 1000 * capture_fps * 0.75 + 60.0))
            deadline = time.monotonic() + capture_timeout_seconds
            while not complete.exists() and not error.exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            if error.exists():
                raise ProductionError(error.read_text(encoding="utf-8"))
            if not complete.exists():
                raise ProductionError(f"Canvas capture timed out: {session_root}")
            completion = json.loads(complete.read_text(encoding="utf-8"))
            source_frames = sorted(session_root.glob("src-*.jpg"))
            if len(source_frames) != int(completion["frame_count"]):
                raise ProductionError("Canvas capture frame count mismatch")
            expected_source_count = max(1, math.ceil(duration_ms * capture_fps / 1000))
            if len(source_frames) != expected_source_count:
                raise ProductionError(f"Canvas capture produced {len(source_frames)} source frames; expected {expected_source_count} at {capture_fps} fps")
            source_hashes = [self._sha256(frame) for frame in source_frames]
            unique_source_hashes = len(set(source_hashes))
            output_count = max(1, math.ceil(duration_ms * output_fps / 1000))
            output_hashes: list[str] = []
            for index in range(output_count):
                source_index = min(len(source_frames) - 1, round(index * capture_fps / output_fps))
                target = session_root / f"{index:06d}.jpg"
                if not target.exists():
                    try:
                        os.link(session_root / f"src-{source_index:06d}.jpg", target)
                    except OSError:
                        shutil.copyfile(session_root / f"src-{source_index:06d}.jpg", target)
                output_hashes.append(source_hashes[source_index])
            adjacent_source_changes = sum(1 for previous, current in zip(source_hashes, source_hashes[1:]) if previous != current)
            unique_output_hashes = len(set(output_hashes))
            real_capture_validated = capture_fps in REAL_CAPTURE_FPS and unique_source_hashes >= 2 and adjacent_source_changes > 0
            completion.update({"capture_fps": capture_fps, "output_fps": output_fps, "source_frame_count": len(source_frames), "unique_source_frame_count": unique_source_hashes, "output_frame_count": output_count, "unique_output_frame_count": unique_output_hashes})
            return session_root, {
                "frame_count": len(source_frames),
                "fps": capture_fps,
                "duration_ms": duration_ms,
                "capture_fps": capture_fps,
                "output_fps": output_fps,
                "source_frame_count": len(source_frames),
                "expected_source_frame_count": expected_source_count,
                "unique_capture_frame_count": unique_source_hashes,
                "output_frame_count": output_count,
                "unique_output_frame_count": unique_output_hashes,
                "duplicate_output_frame_count": output_count - unique_output_hashes,
                "unique_capture_frame_ratio": round(unique_source_hashes / max(1, len(source_frames)), 4),
                "adjacent_source_changes": adjacent_source_changes,
                "continuity_validated": len(source_frames) == expected_source_count and adjacent_source_changes > 0,
                "real_capture_validated": real_capture_validated,
                "quality": "real_canvas_capture" if capture_fps in REAL_CAPTURE_FPS else "economy_repeated_frames",
                "timing_source": "Canvas frame timestamps from deterministic browser capture",
            }
        finally:
            if browser is not None and browser.poll() is None:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
            shutil.rmtree(profile, ignore_errors=True)

    @staticmethod
    def _wait_http(url: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urlopen(url, timeout=1) as response:
                    if response.status < 500:
                        return
            except (OSError, URLError):
                time.sleep(0.15)
        raise ProductionError(f"local HTTP endpoint did not start: {url}")

    @staticmethod
    def _render_mp4(frames: Path, audio: Path, captions: Path, output: Path, duration_ms: int, *, output_fps: int = DEFAULT_OUTPUT_FPS, audio_sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE, audio_channels: int = DEFAULT_AUDIO_CHANNELS) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = duration_ms / 1000
        subtitle = captions.name.replace("'", "\\'")
        filter_graph = f"subtitles='{subtitle}':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=100'"
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(output_fps), "-i", str(frames / "%06d.jpg"), "-i", str(audio), "-vf", filter_graph, "-map", "0:v:0", "-map", "1:a:0", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-r", str(output_fps), "-c:a", "aac", "-b:a", "128k", "-ar", str(audio_sample_rate), "-ac", str(audio_channels), "-movflags", "+faststart", str(output)]
        subprocess.run(command, check=True, cwd=str(output.parent), capture_output=True, text=True)

    @staticmethod
    def _make_board(video: Path, output: Path, duration_ms: int, *, output_fps: int = DEFAULT_OUTPUT_FPS) -> None:
        duration = max(0.1, duration_ms / 1000)
        times = [0.05 * duration, 0.33 * duration, 0.66 * duration, 0.92 * duration]
        select = "+".join(f"eq(n,{round(time_value * output_fps)})" for time_value in times)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vf", f"select='{select}',scale=270:480,tile=2x2", "-frames:v", "1", str(output)], check=True, capture_output=True, text=True)

    @staticmethod
    def _validate_output(video: Path, duration_ms: int, *, expected_fps: int = DEFAULT_OUTPUT_FPS, expected_audio_sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE, expected_audio_channels: int = DEFAULT_AUDIO_CHANNELS) -> dict[str, object]:
        probe_run = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,channels,channel_layout,sample_rate", "-of", "json", str(video)], check=True, capture_output=True, text=True)
        probe = json.loads(probe_run.stdout)
        decode = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], capture_output=True, text=True)
        black = subprocess.run(["ffmpeg", "-hide_banner", "-vf", "blackdetect=d=0.15:pic_th=0.98", "-an", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        streams = probe.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        actual_ms = round(float(probe.get("format", {}).get("duration") or 0) * 1000)
        frame_rate = video_stream.get("r_frame_rate") or "0/1"
        try:
            numerator, denominator = frame_rate.split("/", 1)
            actual_fps = float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            actual_fps = 0.0
        audio_sample_rate = int(audio_stream.get("sample_rate") or 0)
        audio_channels = int(audio_stream.get("channels") or 0)
        return {
            "ffprobe_ok": True,
            "decode_ok": decode.returncode == 0,
            "no_black_frames": "black_start:" not in black.stderr,
            "duration_ms": actual_ms,
            "duration_delta_ms": actual_ms - duration_ms,
            "resolution": [video_stream.get("width"), video_stream.get("height")],
            "video_codec": video_stream.get("codec_name"),
            "video_fps": actual_fps,
            "video_fps_expected": expected_fps,
            "video_fps_ok": abs(actual_fps - expected_fps) < 0.01,
            "audio_codec": audio_stream.get("codec_name"),
            "audio_sample_rate": audio_sample_rate,
            "audio_sample_rate_expected": expected_audio_sample_rate,
            "audio_sample_rate_ok": audio_sample_rate == expected_audio_sample_rate,
            "audio_channels": audio_channels,
            "audio_channels_expected": expected_audio_channels,
            "audio_channels_ok": audio_channels == expected_audio_channels,
            "audio_channel_layout": audio_stream.get("channel_layout"),
            "file_size_bytes": video.stat().st_size,
        }

    @staticmethod
    def _compose_audio(manifest: object, output: Path) -> None:
        segments = getattr(manifest, "segments", None) or manifest["segments"]
        first = segments[0]
        first_uri = getattr(first, "audio_uri", None) or first["audio_uri"]
        first_path = Path(urlparse(first_uri).path.lstrip("/"))
        with wave.open(str(first_path), "rb") as stream:
            sample_rate = stream.getframerate()
        combined = array("h")
        written = 0
        duration_ms = getattr(manifest, "duration_ms", None) or manifest["duration_ms"]
        for segment in segments:
            uri = getattr(segment, "audio_uri", None) or segment["audio_uri"]
            path = Path(urlparse(uri).path.lstrip("/"))
            start_ms = getattr(segment, "start_ms", None)
            if start_ms is None:
                start_ms = segment["start_ms"]
            with wave.open(str(path), "rb") as stream:
                if stream.getframerate() != sample_rate or stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                    raise ProductionError("narration WAV segments have incompatible formats")
                start = round(int(start_ms) * sample_rate / 1000)
                combined.extend([0] * max(0, start - written))
                raw = stream.readframes(stream.getnframes())
                combined.frombytes(raw)
                written = start + stream.getnframes()
        target = round(int(duration_ms) * sample_rate / 1000)
        combined.extend([0] * max(0, target - written))
        with wave.open(str(output), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(sample_rate); stream.writeframes(combined.tobytes())

    @staticmethod
    def _write_srt(manifest: object, path: Path) -> None:
        segments = getattr(manifest, "segments", None) or manifest["segments"]
        blocks = []
        for index, segment in enumerate(segments, start=1):
            start = getattr(segment, "start_ms", None) if hasattr(segment, "start_ms") else segment["start_ms"]
            end = getattr(segment, "end_ms", None) if hasattr(segment, "end_ms") else segment["end_ms"]
            text = getattr(segment, "text", None) if hasattr(segment, "text") else segment["text"]
            blocks.append(f"{index}\n{ProductionService._srt_time(int(start))} --> {ProductionService._srt_time(int(end))}\n{textwrap.fill(text, 58)}\n")
        path.write_text("\n".join(blocks), encoding="utf-8")

    @staticmethod
    def _srt_time(milliseconds: int) -> str:
        hours, remainder = divmod(milliseconds, 3_600_000); minutes, remainder = divmod(remainder, 60_000); seconds, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @staticmethod
    def _write_generic_scene(path: Path) -> None:
        if path.is_file():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1600\" height=\"900\" viewBox=\"0 0 1600 900\"><defs><linearGradient id=\"sky\" x2=\"0\" y2=\"1\"><stop stop-color=\"#07152f\"/><stop offset=\"1\" stop-color=\"#183e62\"/></linearGradient><radialGradient id=\"orb\"><stop stop-color=\"#f6d98b\" stop-opacity=\".9\"/><stop offset=\"1\" stop-color=\"#6aa9d8\" stop-opacity=\"0\"/></radialGradient></defs><rect width=\"1600\" height=\"900\" fill=\"url(#sky)\"/><circle cx=\"1190\" cy=\"220\" r=\"210\" fill=\"url(#orb)\"/><path d=\"M0 700 Q300 540 580 690 T1100 640 T1600 680 V900 H0Z\" fill=\"#071226\"/><path d=\"M0 770 Q330 650 680 760 T1300 730 T1600 760\" fill=\"none\" stroke=\"#e6c77a\" stroke-opacity=\".35\" stroke-width=\"5\"/><g fill=\"#f5d98a\" opacity=\".8\"><circle cx=\"170\" cy=\"160\" r=\"4\"/><circle cx=\"390\" cy=\"250\" r=\"3\"/><circle cx=\"720\" cy=\"130\" r=\"5\"/><circle cx=\"960\" cy=\"300\" r=\"3\"/><circle cx=\"1410\" cy=\"120\" r=\"4\"/></g></svg>""", encoding="utf-8")

    @staticmethod
    def _write_canvas_project(path: Path, output_id: str, root: Path, manifest: dict[str, object], duration_ms: int, profile_id: str, *, output_fps: int = DEFAULT_OUTPUT_FPS, audio_sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE, audio_channels: int = DEFAULT_AUDIO_CHANNELS) -> dict[str, object]:
        project = {
            "format": "fabuloom.music-studio-project/0.1",
            "id": output_id,
            "title": "Fabuloom Generic Engine Demo",
            "display_title": "Fabuloom Engine Demo",
            "asset_root": root.relative_to(root.parents[1] / "exports").as_posix() if "exports" in root.parents[1].parts else output_id,
            "renderer_version": "music-studio-v1.1",
            "style": {"id": "crystal-dawn", "palette": {"deep": "#07152f", "mid": "#183e62", "accent": "#6aa9d8", "gold": "#e6c77a", "mist": "#c7e5ff", "fog": "#8cc3d8", "spark": "#f5d98a", "reflection": "#86c4e3"}},
            "source": {"filename": "generic-deterministic-narration.wav", "display_title": "Fabuloom Engine Demo", "analysis": {"duration_ms": duration_ms, "duration_seconds": duration_ms / 1000}},
            "analysis": {"waveform": {"values": [0.35 + 0.2 * math.sin(index / 7) for index in range(120)], "bars": 120}},
            "visual_policy": {"mode": "generic-redistributable", "narrator": None, "characters": [], "narration": "simulated-audio", "lip_sync": False, "captions": True, "assets_are_environmental_only": True},
            "assets": [{"id": "generic-scene", "path": "assets/generic-scene.svg"}],
            "export": {"video_fps": output_fps, "audio_codec": "aac", "audio_sample_rate": audio_sample_rate, "audio_channels": audio_channels, "source_audio_policy": "preserve_native_Kokoro_rate_until_export"},
            "full": {"width": 1920, "height": 1080, "fps": output_fps, "duration_ms": duration_ms, "audio_start_ms": 0, "audio_end_ms": duration_ms, "scenes": [{"id": "scene-01", "asset_id": "generic-scene", "start_ms": 0, "end_ms": duration_ms, "camera": {"zoom": 1.0, "pan_x": 0, "pan_y": 0}}]},
            "short": {"width": 1080, "height": 1920, "fps": output_fps, "duration_ms": duration_ms, "audio_start_ms": 0, "audio_end_ms": duration_ms, "scenes": [{"id": "scene-01", "asset_id": "generic-scene", "start_ms": 0, "end_ms": duration_ms, "camera": {"zoom": 1.0, "pan_x": 0, "pan_y": 0}}]},
            "short_selection": {"start_ms": 0, "end_ms": duration_ms, "duration_ms": duration_ms},
            "production_profile": profile_id,
            "narration_manifest": "narration.json",
            "captions": "captions.srt",
        }
        ProductionService._write_json(path, project)
        return project

    @staticmethod
    def _load_checkpoint(path: Path) -> dict[str, object] | None:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def _report_markdown(report: dict[str, object]) -> str:
        qa = report["technical_qa"]
        artistic = report["artistic_qa"]
        return "\n".join([
            "# Fabuloom Generic Production Report",
            "",
            f"- Profile: `{report['profile']}`",
            f"- Backend: `{report['backend']}`",
            f"- Video: `{report['video']}`",
            f"- Duration: `{report['duration_ms']} ms`",
            f"- Resolution: `{qa['resolution']}`",
            f"- Codecs: video `{qa['video_codec']}`, audio `{qa['audio_codec']}`",
            f"- Video rate: `{qa['video_fps']} fps` (expected `{qa['video_fps_expected']}`, verified `{qa['video_fps_ok']}`)",
            f"- Audio export: `{qa['audio_sample_rate']} Hz`, `{qa['audio_channels']} channels` (rate verified `{qa['audio_sample_rate_ok']}`)",
            f"- Technical QA: decode `{qa['decode_ok']}`, blackdetect `{qa['no_black_frames']}`, duration delta `{qa['duration_delta_ms']} ms`",
            f"- Capture QA: `{qa.get('fluency_claim')}`, unique source frames `{qa.get('capture', {}).get('unique_capture_frame_count')}`",
            f"- Artistic QA: `{artistic['status']}`; human approval remains pending.",
            "- This acceptance production uses generated generic SVG and deterministic synthetic audio; it contains no private Topazioverse material.",
            "",
        ])


__all__ = ["DEMO_TEXT", "DeterministicAudioProvider", "ProductionError", "ProductionService", "PRODUCTION_FORMAT"]
