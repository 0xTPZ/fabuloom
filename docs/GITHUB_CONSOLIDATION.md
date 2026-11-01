# GitHub consolidation map

## Selected baseline

This preparation branch starts from commit `1d60d6a` (`fix: calibrate narrator mouth anchors`), the local HEAD of `mission-024.1-topazioverse-pilot`. It includes the Studio shell and the latest narrator-anchor calibration available in the checkout. It does not include the untracked assets in the separate `studio` worktree.

## Public main

`main` remains the documentation/Core foundation (`bc23932`). It is not modified by this mission and is not represented as the Alpha product.

## Functional dependency map

```text
Core contracts / serialization
  └─ TTS boundary + measured manifests
      └─ AudioTimelinePlayer / RMS signal
          ├─ NarratorAvatarRenderer
          │   └─ Santa V5 Narrator Mode
          └─ Canvas character/stage renderers
              └─ browser capture boundary
                  └─ FFmpeg examples / existing exports

Studio shell
  └─ reads local manifests, profiles and existing exports
      └─ creates a basic project and starts a local export job; advanced editing remains out of scope
```

## Branch families

- `mission-004`–`mission-006`: Core, Kokoro and character-stage foundations.
- `mission-010`–`mission-020`: demos, deterministic capture, Narrator Mode and cinematic pipelines.
- `mission-021`: Studio UI shell.
- `mission-022`: UX/clean-install audit.
- `mission-023*`: official narrator integration and Dora/Alex art/animation recovery.
- `mission-024.1`: current local pilot base used for this preparation.

## PR handling

Open PRs were treated as evidence of work in progress, not as release components. No original PR was merged and no dependency was inferred solely from PR order. The integration branch is a separate Draft-review artifact and must be reviewed by a human before any merge or release.
