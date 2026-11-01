"""Generate an original short Portuguese story and its measured audio manifest."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
import time

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration
from fabuloom_core.serialization import serialize_manifest
from fabuloom_core.tts import TTSError


EXPORT_DIR = Path(r"E:\Fabuloom\workspace\exports")
STORY_ID = "kokoro-story-demo-0051"
STORY_TEXT = """Na pequena vila de Vale Claro, Lia guardava uma lanterna azul que só acendia quando alguém precisava de coragem. Certa manhã, uma névoa cobriu a ponte e os moradores perderam o caminho para casa. Lia respirou fundo, ergueu a lanterna e seguiu pela estrada silenciosa.

Cada passo revelava uma pedrinha brilhante, como se a própria vila deixasse sinais para ela. No meio da ponte, Lia encontrou um filhote assustado, preso entre duas tábuas. Ela o libertou, e a luz azul ficou mais forte. Juntos, os dois continuaram até o outro lado.

Quando a névoa desapareceu, os moradores perceberam que a coragem de Lia não tinha afastado a escuridão; tinha mostrado como atravessá-la. Naquela noite, a lanterna voltou a ser pequena, mas nunca mais pareceu fraca. E o filhote ganhou um nome: Brilho.

Desde então, Lia e Brilho caminhavam ao entardecer, levando a lanterna para quem encontrasse uma ponte difícil, uma pergunta sem resposta ou um medo grande demais para atravessar sozinho."""


def _memory_mb() -> float | None:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def _write_manifest(path: Path, payload: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise TTSError("OUTPUT_EXISTS", "manifest already exists; pass --overwrite explicitly")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}-",
        suffix=".json",
        dir=path.parent,
        text=True,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(payload, encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="pf_dora")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    manifest_path = EXPORT_DIR / f"{STORY_ID}.json"
    provider = KokoroTTSProvider(output_dir=EXPORT_DIR, allow_overwrite=args.overwrite)
    memory_before = _memory_mb()
    started = time.perf_counter()
    try:
        run = synthesize_narration(
            provider,
            STORY_TEXT,
            narration_id=STORY_ID,
            manifest_id=STORY_ID,
            voice_id=args.voice,
            output_dir=EXPORT_DIR,
            max_chars=360,
        )
        _write_manifest(
            manifest_path,
            serialize_manifest(run.manifest),
            overwrite=args.overwrite,
        )
    except (TTSError, NarrationSynthesisError) as exc:
        print("state=failed")
        print(f"error_code={exc.code}")
        print(f"error={exc}")
        return 2
    finally:
        provider.close()

    memory_after = _memory_mb()
    print("provider=kokoro")
    print(f"model_id={provider.model_id}")
    print(f"model_revision={provider.model_revision}")
    print(f"model_load_count={provider.model_load_count}")
    print(f"voice={args.voice}")
    print("language=pt-BR")
    print("voice_consistent=True")
    print(f"segment_count={len(run.manifest.segments)}")
    print(f"duration_ms={run.manifest.duration_ms}")
    print(f"processing_seconds={run.processing_seconds:.3f}")
    print(f"model_load_seconds={run.results[0].metadata['model_load_seconds']:.3f}")
    print(f"synthesis_seconds_sum={sum(result.metadata['synthesis_seconds'] for result in run.results):.3f}")
    if memory_before is None or memory_after is None:
        print("memory_delta_mb=unavailable")
    else:
        print(f"memory_delta_mb={memory_after - memory_before:.1f}")
    print(f"manifest={manifest_path.resolve()}")
    for segment in run.manifest.segments:
        print(
            f"segment={segment.id} start_ms={segment.start_ms} "
            f"end_ms={segment.end_ms} duration_ms={segment.duration_ms} "
            f"audio={segment.audio_uri}"
        )
    print("word_timing=unavailable")
    print("phoneme_timing=unavailable")
    print("viseme_timing=unavailable")
    print(f"elapsed_wall_seconds={time.perf_counter() - started:.3f}")
    print("state=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
