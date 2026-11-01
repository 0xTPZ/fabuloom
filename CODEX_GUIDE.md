# Using Codex with Fabuloom

Codex can operate this repository without private context when the task stays inside the documented workspace.

## Safe setup prompt

Ask Codex to: “Use a separate worktree, inspect `INSTALL.md`, run `scripts/diagnose.ps1`, keep all generated media under the configured workspace, and do not modify `main`, production inputs, exports, models or another agent's checkout.”

## Useful commands

```powershell
pwsh -File .\scripts\diagnose.ps1
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s tests -p 'test_*.py' -v
node --test .\frontend\tests\*.mjs
```

For UI work, use a separate worktree and a loopback port. For media work, use explicit `FABULOOM_WORKSPACE_ROOT` and `FABULOOM_EXPORT_ROOT` values and never infer paths from another checkout.

## Safety rules

- Never use private context, credentials, model caches or production media as missing test fixtures.
- Never run destructive Git cleanup in a shared checkout.
- Do not call a branch feature “supported” unless a clean checkout reproduces it.
- Preserve the distinction between an existing export, a demo pipeline and a new user-generated project.
