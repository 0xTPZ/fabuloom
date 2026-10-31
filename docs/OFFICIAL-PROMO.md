# Official Promo V1

Mission 020 adds a reproducible promotional export for Fabuloom Studio. It
uses the real Narrator Mode V1.4 `NarratorAvatarRenderer`, the local Kokoro
`pm_santa` voice, measured WAV segment timing, a real loopback capture of the
current Character Stage, and FFmpeg. It does not create a second character
renderer or fabricate word, phoneme, or viseme timing.

## Reproduction

Run from `E:\Fabuloom\studio` with the existing local environment:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
python .\examples\official_promo_demo.py --reuse-manifest --overwrite
```

`--reuse-manifest` reuses the already measured `pm_santa` narration when the
same text and voice are available. Without it, the script uses the local
Kokoro integration and writes a new measured manifest. No model weights are
stored in this repository.

The pipeline writes generated media only under
`E:\Fabuloom\workspace\exports`:

- `videos/fabuloom-official-promo-v1.mp4`: narration, original procedural
  music, and original procedural SFX;
- `videos/fabuloom-official-promo-v1-tiktok-ready.mp4`: narration and SFX,
  intentionally without music so a platform-licensed track can be added;
- `videos/fabuloom-official-promo-v1-frames.png`: human-review frame board;
- `videos/fabuloom-official-promo-v1-report.md/.json`: measured duration,
  probes, audio levels, evidence and limitations;
- `official-promo-v1/`: profile, timeline, measured manifest, segment audio,
  mixes, credits and descriptions.

The generated exports are 1080×1920 at 30 FPS, H.264/yuv420p video and AAC
stereo audio at 24 kHz. Scene boundaries and captions come from the measured
WAV segments. The capture writes every subtitle line after wrapping; it does
not drop words to fit a fixed line count.

## Evidence and claims

The `screen` scene uses a real local browser capture of the Fabuloom Character
Stage, not a fabricated terminal or a static mockup. A Codex desktop screen
recording was not available in the environment, so the trailer does not claim
to show such a recording. The profile and report record this limitation
explicitly.

The promo states that the project is free/open source, in its first public
phase, actively evolving, open to community contributions, and created by
`0xTPZ`. It does not state that unfinished features or Codex/external services
are free. The code license for original Fabuloom code is MIT; voice/model
distribution remains governed by the local Kokoro setup and its dependencies.

The music and SFX are deterministic procedural compositions generated locally
for this promo. No commercial samples, personal media, model weights, or
third-party images are published. RMS mouth motion is amplitude-based and is
not phonetic lip-sync. Human review of the MP4 and frame board remains
required; the Visual Inspector is evidence-only.

## Inspection

After capture, run the existing evidence report:

```powershell
node .\tools\visual-inspector\vertical-story-report.mjs `
  --profile "E:\Fabuloom\workspace\exports\official-promo-v1\fabuloom-official-promo-v1-profile.json" `
  --frames "E:\Fabuloom\workspace\exports\official-promo-v1\.frames" `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-020-official-promo\official-promo-inspection.json"
```

The report records frame dimensions, timing source and representative pixel
evidence. It cannot certify artistic quality, scene intent, phonetic timing or
human approval.
