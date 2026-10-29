# Santa V5 — produção artística e rig

Mission 012 created the approved visual direction for Santa V5: a friendly
older narrator with an expressive head, gray hair, glasses, short beard and a
tailored navy/black/gold Topazioverse uniform. Mission 012.1 turns that art
direction into the first complete animation-ready layer pack without creating
a new animation engine.

## Tracked assets

The production sources are under:

```text
frontend/assets/characters/topazio-narrators-v5/santa/
```

The pack contains independent transparent PNGs for the torso, pelvis, neck,
head, front/back hair, upper arms, forearms, hands, thighs, shins, feet,
eyes, eyelids, brows, glasses, beard and mouth states. The original master,
production sheet and earlier comparison artifacts remain references; generated
media is kept in the workspace exports directory and is not committed.

## Rig integration

`frontend/src/santa-v5-pack.mjs` preserves `fabuloom.character/0.1` and uses
the `animation-ready/0.1` profile. `SantaV5Rig` and `SantaV5SceneRenderer`
reuse the deterministic V3 choreography and the same `LayeredCharacterRenderer`
used by Character Stage. The pack is available as `Santa V5 · pm_santa` in the
stage, while Santa V3 and V4 remain available for comparison.

The renderer exposes its resolved draw plan so the scene cup can follow the
actual transformed `right_hand` layer. Play, seek and offline capture remain
clock-pure. RMS controls the mouth response; word, phoneme and viseme timing
are not invented.

## Demonstration

The reusable command is:

```powershell
$env:PYTHONPATH = 'E:\Fabuloom\studio\src'
& 'E:\Fabuloom\workspace\.venv\Scripts\python.exe' .\examples\santa_v5_video_demo.py --overwrite
```

It reuses the existing measured `pm_santa` narration, captures 30 FPS frames
at 1080x1920 through `frontend/capture-santa-v5.html`, and encodes:

```text
E:\Fabuloom\workspace\exports\videos\fabuloom-santa-v5.mp4
```

The review images are `fabuloom-santa-v5-frames-comparison.png` and
`fabuloom-santa-v4-vs-v5-comparison.png` in the same directory. The generated
demonstration was checked with FFprobe as H.264 video, AAC mono audio, 24 kHz,
20.466667 seconds, 1080x1920.

## Limits

This is a first production rig pass, not a claim of finished cinematic art.
The generated layers have overlap-friendly silhouettes but still deserve human
review for long-form continuity, subtle expression quality and hand-object
contact. The character editor, external import, phonetic alignment and Animus
adapter remain outside this mission.

The artwork is original project material generated for Fabuloom from the
approved identity direction. No third-party art, model weights, personal media
or private project source is included.
