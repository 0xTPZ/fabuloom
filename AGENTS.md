# Agent instructions

Fabuloom is a local-first audiovisual prototype. Read `README.md`, `INSTALL.md`, `USER_GUIDE.md` and `docs/ARCHITECTURE.md` before changing code.

Use isolated worktrees for changes. Keep models, private context, production inputs, generated media and credentials outside Git. Do not modify `main`, merge unrelated PRs, or claim that an experimental narrator is approved. Santa V5 is the current production reference; Dora and Alex are gated pending artistic approval.

Run Python and Node tests after code changes. For server changes, verify loopback binding, workspace containment and missing-file behavior. Record limitations instead of masking them with local files.
