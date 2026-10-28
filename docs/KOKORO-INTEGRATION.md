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
