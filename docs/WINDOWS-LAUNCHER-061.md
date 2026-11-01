# Windows launcher 061

Status: `PASS` for portable local startup; no release or merge performed.

## Implementation

- `Iniciar Fabuloom.bat` resolves its own directory through `%~dp0` and invokes the local PowerShell helper.
- `scripts/launch-fabuloom.ps1` prefers `.venv\Scripts\python.exe`, otherwise searches for `python.exe` on PATH.
- Python 3.11+ is checked before startup.
- The launcher validates `server.py`, checks whether `http://127.0.0.1:8765/studio.html` is a Fabuloom page, detects a conflicting listener, starts only its own server when needed, waits for the expected page, opens the browser, and stops only the process it created when the user presses Enter.
- Workspace/export variables are scoped to the launched process. No global PATH, registry, firewall, remote script, download, or administrator privilege is used.

## Verification

The launcher was executed from the repository path containing spaces-sensitive path handling. It found the local virtual environment, started the server on loopback, opened `http://127.0.0.1:8765/studio.html`, and closed the child server after Enter; the port was confirmed closed afterward.

The script also has explicit safe failure paths for a missing `server.py`, missing Python, incompatible Python, a port occupied by another process, and a server that does not return the expected Fabuloom page. Existing Fabuloom instances are reused only after page-content verification; unknown listeners are never terminated.

## Distribution

Candidate ZIP (separate from Mission 060): `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only-061.zip`.

- Included files: 338
- ZIP SHA-256: `E50197811504B4AD1C797953855876186DB2FDE5353A8F02B0D147BED316770D`
- Manifest SHA-256: `82D59B3783936815D7B783E16E4ADC2324784FE0652A7FB1AE30D2162FB80A3E`

The candidate contains the launcher, public source, Ponto, documentation, licenses, scripts, and applicable tests. It excludes `.git`, `.venv`, `workspace`, `node_modules`, caches, models, voices, FFmpeg, credentials, private contexts, and Topazioverse art. Its SHA-256 is recorded below after packaging.

## Limitations

- Python must be prepared by the user; the launcher intentionally does not install dependencies.
- Kokoro and FFmpeg remain optional external setup for narration/export.
- Closing the launcher window forcibly instead of pressing Enter can leave a server child running; normal shutdown is documented through Enter.
- The launcher does not change the system's default browser or firewall.
