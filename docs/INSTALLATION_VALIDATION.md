# Clean installation validation

## Scope

Validation is split between the dependency-free core and the Studio shell. A clean checkout may start the shell, but a full media production still needs local manifests, audio/model inputs and FFmpeg.

## Checks

| Check | Expected result | Status for this preparation |
|---|---|---|
| Python 3.11+ | `pyproject.toml` requirement | Available in audit host |
| Project-local venv | No global Python package required | Supported |
| Core unit tests | `python -m unittest discover ...` | Must run in CI/review |
| Node renderer tests | `node --test frontend/tests/*.mjs` | Must run in CI/review |
| Loopback server | HTTP root response | Supported by `frontend/server.py` |
| Workspace containment | Export root inside workspace | Enforced by server |
| Kokoro | Optional provider/model | Not bundled; license/model gate remains |
| New project | UI button | Implemented and persisted under the configured workspace |
| New MP4 from UI | Export action | Implemented as an asynchronous local FFmpeg job |

## Acceptance rule

Do not call the Alpha install complete until a machine without the developer workspace can clone this branch, run the checks, open the shell, and receive an explicit empty-state explanation instead of silently reading developer files. Do not call video production complete until a separate test supplies approved fixtures and reproduces an MP4 from scratch.
