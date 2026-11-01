# Alpha 0.1.0 testing guide

This is an invited, source-only test of the Fabuloom Studio preparation branch. It is not a packaged installer.

1. Follow [INSTALL.md](INSTALL.md) in a clean checkout.
2. Run `scripts/diagnose.ps1` and record missing Python/Node/FFmpeg prerequisites.
3. Start the loopback Studio and create a project.
4. Save a short script, import one authorized PNG/JPEG/WebP per scene, and confirm persistence.
5. Install Kokoro only if you accept the package/model/voice terms from their official sources.
6. Generate Santa narration through the Studio button and export MP4.
7. Record the MP4 path and validate it with FFprobe/FFmpeg.

Do not upload private manuscripts, model caches, voices, production media or Topazioverse assets to issues. Report security-sensitive findings privately as described in [SECURITY.md](SECURITY.md).
