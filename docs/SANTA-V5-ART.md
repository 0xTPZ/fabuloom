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

## Mission 012.3 — rig calibration

The V5 source PNGs remain unchanged. Calibration is represented by the pack's
normalized positions, sizes and pivots, while alpha bounds are recorded as
diagnostic metadata in `frontend/src/santa-v5-calibration.mjs`. The diagnostic
checks parent references, normalized values, expected joint regions and large
transparent margins without loading model files or rewriting artwork.

The local DEV tool is `frontend/santa-v5-calibration.html`. It can inspect the
master overlay, intrinsic layer boxes and transformed pivots, switch between
neutral, walking, seated, gesture, cup and controlled-extreme poses, and export
parameter data. It is a development aid, not a public character editor.

`SantaV5Rig` remains a thin adapter over the V3 scene choreography. V5 now
limits walking, seated, reach/drink and explain amplitudes to the overlap range
of the painted parts; V3 and V4 are not changed. The same absolute-time rig is
used by the Character Stage and by
`frontend/capture-santa-v5-calibration.html`.

The technical reel is generated with:

```powershell
& 'E:\Fabuloom\workspace\.venv\Scripts\python.exe' .\examples\santa_v5_calibration_demo.py --overwrite
```

It writes the 8-second, silent visual calibration reel and report under
`E:\Fabuloom\workspace\exports\videos\`. The reel is deliberately silent: it
validates composition and deterministic poses, not Kokoro timing. The current
calibration remains subject to human visual approval, especially for long-form
hand/object contact.

## Mission 012.4 — anatomical rig calibration

The approved V5 assets were kept intact. `frontend/src/character-landmarks.mjs`
defines reusable local-intrinsic landmarks for the neck, shoulders, elbows,
wrists, hip, knees and ankles, and converts them through the resolved draw plan
to stage coordinates. Hidden joints are explicitly marked as low/medium
confidence estimates rather than exact measurements.

The DEV calibration page now draws landmark connections, compares them with
current transformed pivots, exposes movement amplitude and includes dedicated
arm, elbow, step and seated pose buttons. The eight-pose gallery is a visual
diagnostic, not a character editor.

The V5 pack now mounts upper-arm sleeves at the estimated shoulder landmarks.
The V5 adapter adds a bounded gait with modest pelvis/foot offsets and a
progressive seated pose; these are lightweight corrections at the pack/rig
boundary. The full-body coat still limits how clearly a seated knee fold can be
read, so seated motion remains a known visual limitation.
