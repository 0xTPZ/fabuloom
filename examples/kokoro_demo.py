"""Generate one real PT-BR Kokoro WAV without adding models to the repository."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.tts import SynthesisRequest, TTSError


DEFAULT_OUTPUT = Path(r"E:\Fabuloom\workspace\exports\kokoro-demo.wav")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="Era uma vez uma história contada em voz alta.")
    parser.add_argument("--voice", default="pf_dora")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    # The demonstration is intentionally offline: an existing local cache is
    # required, and no model download is attempted.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    provider = KokoroTTSProvider(output_dir=Path(r"E:\Fabuloom\workspace\exports"))
    try:
        result = provider.synthesize(
            SynthesisRequest(
                id="kokoro-demo-001",
                text=args.text,
                voice_id=args.voice,
                language="pt-BR",
            ),
            args.output,
        )
    except TTSError as exc:
        print(f"state=failed")
        print(f"error_code={exc.code}")
        print(f"error={exc}")
        return 2
    finally:
        provider.close()

    print(f"provider={result.provider_id}")
    print(f"voice={result.voice_id}")
    print(f"language={result.language}")
    print(f"duration_ms={result.duration_ms}")
    print(f"sample_rate={result.metadata['sample_rate']}")
    print(f"channels={result.metadata['channels']}")
    print(f"model_load_seconds={result.metadata['model_load_seconds']:.3f}")
    print(f"synthesis_seconds={result.metadata['synthesis_seconds']:.3f}")
    output_path = Path(result.audio_uri.removeprefix("file:///"))
    print(f"output={output_path.resolve()}")
    print("word_timing=unavailable")
    print("phoneme_timing=unavailable")
    print("viseme_timing=unavailable")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
