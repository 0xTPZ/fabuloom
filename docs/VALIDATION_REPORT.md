# Validation report

Date: 2026-10-31 (America/Sao_Paulo)

## Automated suites

- Python: `python -m unittest discover -s tests -p 'test_*.py' -q` — 38 tests passed, 1 skipped.
- Node: `node --test frontend/tests/*.mjs` — 143 passed, 0 failed.
- Diagnostics: Python 3.12.10, Node 24.19.0, FFmpeg 9.0.1 and FFprobe 9.0.1 detected in the audit host.

## Server smoke test

With explicit workspace/export roots in the isolated worktree, `frontend/server.py --port 8876` started and returned HTTP 200 for `/`. A missing resource returned HTTP 404. The server stopped cleanly on Ctrl+C.

## Interpretation

These results validate contracts, renderer logic, diagnostics and the loopback shell. They do not prove that a clean user checkout contains a Kokoro model, a measured WAV, a manifest, a new-project workflow or a one-click export job. Those remain Alpha acceptance work.
