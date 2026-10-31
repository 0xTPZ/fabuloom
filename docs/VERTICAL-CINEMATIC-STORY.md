# Vertical Cinematic Story V1

Mission 019 adds a profile-driven vertical export path for a 9:16 story. It
reuses the Narrator Mode V1.4 `NarratorAvatarRenderer`, measured Kokoro
segments, the existing local capture server and FFmpeg. It does not create a
second character renderer or invent word, phoneme or viseme timing.

## Reproduction

From `E:\Fabuloom\studio` with the existing local environment:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
python .\examples\vertical_story_demo.py --overwrite
```

The command writes all generated media under `E:\Fabuloom\workspace\exports`:

- `vertical-story-v1/`: measured manifest, segment WAVs, composed voice WAV,
  original local procedural music, voice-priority mixed WAV, versioned profile,
  timeline and deterministic PNG frames;
- `videos/fabuloom-vertical-story-test-v1.mp4`: 1080×1920, 30 FPS, H.264/AAC;
- `videos/fabuloom-vertical-story-test-v1-frames.png`: human-review frame board;
- `videos/fabuloom-vertical-story-test-v1-report.md/.json`: probe and mix report.

Use `--reuse-manifest` to avoid a second Kokoro synthesis for the same text and
voice. The browser capture is loopback-only and accepts only the PNG/JSON
payloads needed for the caller-owned frame sequence.

## Profile contract

`frontend/src/vertical-story-profile.mjs` defines
`fabuloom.vertical-story/0.1`. A profile fixes 1080×1920, 30 FPS, 9:16,
safe-relative asset paths, measured scene intervals, the Santa V5 narrator
bounds, subtitle safe area, explicit codecs and the absence of technical
metadata in the public video. It is intended to be reused by another story by
changing the text, measured manifest and scene schedule rather than editing the
capture renderer.

The five Mission 019 scene images are original assets generated with the
Codex-built-in image generation tool and copied into the workspace only. Their
prompts and provenance are recorded in the profile. No model weights, personal
media or third-party images are published.

The soundtrack is an original deterministic local procedural composition. It
is mixed below the voice, faded at the boundaries, and ducked by the narration
when the local FFmpeg build supports the configured `sidechaincompress` graph.
The report records the measured audio levels; the voice remains the priority.

## Inspection and limitations

Run the generic Mission 019 pixel-evidence report after capture:

```powershell
node .\tools\visual-inspector\vertical-story-report.mjs `
  --profile "E:\Fabuloom\workspace\exports\vertical-story-v1\fabuloom-vertical-story-v1-profile.json" `
  --frames "E:\Fabuloom\workspace\exports\vertical-story-v1\.frames" `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-019-vertical\vertical-story-inspection.json"
```

The inspector reports dimensions, alpha/foreground evidence and representative
scene frames. It is not an artistic approval, does not prove phonetic
alignment, and cannot decide whether a composition is cinematic or whether a
character is anatomically correct. Human review of the MP4 and frame board is
required.

The current profile-driven capture is the reusable integration point for a
future Studio UI. A full story editor, word/phoneme alignment, adaptive music
system and platform-specific UI remain outside this mission.
