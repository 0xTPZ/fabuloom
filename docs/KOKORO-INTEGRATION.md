# Kokoro integration

The optional `KokoroTTSProvider` adapts the local Kokoro pipeline to the
provider-neutral `TTSProvider` contract. It is lazy: importing Fabuloom Core
does not import Kokoro, NumPy, or SoundFile; the model is initialized on the
first synthesis request and reused until `close()` is called.

## Supported behavior

- Language: Portuguese (Brazil), represented by the contract value `pt-BR` and
  Kokoro language code `p`.
- Voices prioritized by this integration: `pf_dora`, `pm_alex`, and `pm_santa`.
- Output: PCM 16-bit WAV, measured after writing with the standard WAV reader.
- Default sample rate: 24,000 Hz, reported from the generated file.
- Supported generic parameter: positive `speed`.
- Explicitly unsupported by this adapter: `pitch`, `volume`, and arbitrary
  provider extras. They fail with a stable `UNSUPPORTED_PARAMETER` error
  instead of being silently ignored.
- Word, phoneme, and viseme timings are not invented. The result reports
  `timing_source=audio_duration_only` and leaves timing arrays empty.

The output path must be a `.wav` file inside
`E:\Fabuloom\workspace\exports`. Model weights, caches, generated audio, and
virtual environments are external to this repository and are not published.
Existing output files are protected by default. Replacing one requires the
explicit `allow_overwrite=True` provider option or the `--overwrite` demo flag.

Kokoro 0.9.x accepts a model repository identifier but not a revision argument
on `KPipeline`. The adapter therefore passes the pinned model ID and records
the validated local snapshot revision `f3ff3571791e39611d31c381e3a41a3af07b4987`
in result metadata. A future runtime that supports revision pinning should make
that pin explicit at pipeline construction.

## Local demonstration

Use an environment that already contains the optional dependencies. The
demonstration sets Hugging Face offline flags and therefore does not download
weights:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python E:\Fabuloom\studio\examples\kokoro_demo.py `
  --text "Esta é uma demonstração de narração em português brasileiro." `
  --voice pf_dora
```

The command prints the provider, voice, language, measured duration, WAV
format, model-load time, synthesis time, output path, and the explicit
unavailability of word/phoneme/viseme timing.

For a multi-segment original short story, run:

```powershell
python E:\Fabuloom\studio\examples\kokoro_story_demo.py --voice pf_dora
```

This writes one WAV per ordered sentence/paragraph fragment and a JSON
manifest in the same export directory. Segment start/end values use measured
WAV durations; punctuation and paragraph gaps are explicit composition pauses,
not invented speech timestamps. Re-running the same demo requires
`--overwrite`.

Mission 009.1 provides one pre-generated local narration for each official
stage narrator. Generate all three with one reused Kokoro pipeline:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python E:\Fabuloom\studio\examples\kokoro_narrator_trio_demo.py --overwrite
```

The command writes only to `E:\Fabuloom\workspace\exports`:
`kokoro-story-demo-0091-dora.json` with `pf_dora`,
`kokoro-story-demo-0091-santa.json` with `pm_santa`, and
`kokoro-story-demo-0091-alex.json` with `pm_alex`, plus their measured WAV
segments. The Character Stage selects the matching existing manifest; changing
characters never invokes synthesis again. A failed or missing manifest is
shown as a voice-specific loading error and the previous player is disposed
before the next one is loaded.

## Mission 010 first video

`examples/first_video_demo.py` demonstrates the complete first local path from
the original story text *A Última Luz* to a vertical MP4. It uses Dora and
`pf_dora`, composes the five measured narration segments, derives the mouth
signal from the audio RMS envelope, and uses the measured segment boundaries
for SRT captions. It does not invent word, phoneme, or viseme timestamps.

The first reference export is intentionally small and reusable: a portrait,
an original night-temple background, FFmpeg composition, and a Fabuloom /
Topazioverse outro. It is a demonstration exporter rather than the final
editor or cinematic compositor. The generated WAV, JSON manifest, SRT, and MP4
stay in the local workspace export directory and are not published with the
source repository.

## Dependencies and licensing

The tested optional environment used Kokoro 0.9.4, SoundFile 0.14.0,
Transformers 5.17.0, and a local PyTorch installation. The optional package
extra declares Kokoro, NumPy, and SoundFile; the Kokoro package brings its
runtime dependencies. Versions and licenses must be rechecked when changing
the environment.

The Kokoro-82M model page identifies the model as Apache-2.0. SoundFile is
BSD-3-Clause. PyTorch is distributed under a BSD-style license with additional
third-party notices that must be preserved by any redistribution. Fabuloom
does not redistribute weights or model caches; users remain responsible for
reviewing the exact artifacts in their environment.
