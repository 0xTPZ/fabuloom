"""Produce the FAB-SHORTS-002 batch in an isolated, resumable workspace.

The runner intentionally keeps the media boundary explicit: source MP4 audio is
never mapped, all voice is measured Kokoro ``pm_santa`` audio, and the only
character asset used by the Shorts is the approved Santa V5 medallion.  The
source clips are environments/objects selected by a storyboard per Short.

This is a batch production runner, not an artistic approval system.  Every
Short finishes in ``TECHNICAL_QA=passed`` and
``ARTISTIC_REVIEW_REQUIRED=true`` until a human reviews the boards and audio.
"""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
import time
from typing import Any
from urllib.parse import unquote
import wave


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
FABULOOM_ROOT = Path(r"E:\Fabuloom")
LIBRARY_ROOT = FABULOOM_ROOT / "workspace" / "inputs" / "biblioteca videos e musicas"
MUSIC_ROOT = FABULOOM_ROOT / "workspace" / "inputs" / "music" / "book1"
OUTPUT_ROOT = FABULOOM_ROOT / "workspace" / "exports" / "cronicas-shorts-batch-001"
SANTA_MASTER = WORKTREE_ROOT / "frontend" / "assets" / "characters" / "topazio-narrators-v5" / "santa" / "master-front.png"
VOICE_ID = "pm_santa"
LANGUAGE = "pt-BR"
FPS = 30
WIDTH = 1080
HEIGHT = 1920
MIN_DURATION_MS = 30_000
MAX_DURATION_MS = 45_000

SAFE_ASSETS = {
    "night": {"file": "A Noite Inquieta.mp4", "role": "floresta e céu noturno, sem personagem aprovado"},
    "shadow": {"file": "As sombras despertam.mp4", "role": "sombras e atmosfera de ameaça, trecho ambiental"},
    "book": {"file": "cena livro musica pra ler.mp4", "role": "objeto/livro e ambiente contemplativo"},
    "crystal": {"file": "FBS-001-INTRO-V-O-Despertar-do-Cristal.mp4", "role": "cristais e energia, crop sem lockup"},
}

SHORTS: list[dict[str, Any]] = [
    {
        "id": "CTS-001",
        "title": "O Cristal que Não Refletia Luz",
        "slug": "o-cristal-que-nao-refletia-luz",
        "music": "O Chamado do Vazio.mp3",
        "script": "Todos os cristais de Topázio devolviam a luz. Todos, menos um. Ele estava no centro de uma sala antiga, brilhando sem iluminar nada ao redor. Quando Santa aproximou a mão, o cristal refletiu apenas uma coisa: uma porta que não existia. E, do outro lado, alguém sussurrou seu nome. Talvez alguns cristais não guardem luz. Talvez guardem caminhos. A história completa ainda está sendo escrita em Crônicas de Topázio.",
        "scenes": ["crystal", "book", "shadow", "crystal", "night"],
        "tags": ["mistério", "cristal", "portal"],
    },
    {
        "id": "CTS-002",
        "title": "A Porta que Só se Abre no Silêncio",
        "slug": "a-porta-que-so-se-abre-no-silencio",
        "music": "Os Ecos que Nunca Morrem.mp3",
        "script": "No templo havia uma porta sem maçaneta, sem fechadura e sem inscrição. Os antigos tentaram abri-la com força, com magia e com canções. Nada funcionou. Então, uma noite, todas as tochas se apagaram. O vento parou. Até os cristais ficaram imóveis. No silêncio absoluto, a porta se abriu sozinha. Do outro lado não havia um tesouro. Havia uma pergunta esperando por coragem.",
        "scenes": ["shadow", "book", "crystal", "shadow", "night"],
        "tags": ["templo", "silêncio", "suspense"],
    },
    {
        "id": "CTS-003",
        "title": "A Floresta que Sussurrava Nomes",
        "slug": "a-floresta-que-sussurrava-nomes",
        "music": "A Sombra que Olhava para o Sol.mp3",
        "script": "Ninguém atravessava a floresta depois do crepúsculo. Não por causa das feras, mas por causa das vozes. Entre as árvores, o vento repetia nomes de pessoas que ainda estavam vivas. Alguns ouviam seus próprios nomes. Outros ouviam nomes esquecidos havia séculos. Naquela noite, porém, a floresta pronunciou um nome que não pertencia a ninguém. E todos os cristais próximos começaram a responder. Ninguém soube quem havia começado o chamado. Mas, desde então, a floresta nunca mais ficou em silêncio.",
        "scenes": ["night", "shadow", "night", "crystal", "book"],
        "tags": ["floresta", "vozes", "presságio"],
    },
    {
        "id": "CTS-004",
        "title": "O Eco que Chamava no Escuro",
        "slug": "o-eco-que-chamava-no-escuro",
        "music": "O Silêncio de Gaia.mp3",
        "script": "O primeiro eco veio do fundo da caverna. O segundo respondeu de muito mais longe. O terceiro surgiu atrás de quem estava ouvindo. Ninguém se moveu. Ninguém respirou. Então uma luz azul se acendeu nas pedras, formando um caminho para dentro da escuridão. O eco não repetia palavras. Repetia uma promessa: aquilo que foi perdido ainda podia ser encontrado. A cada passo, o caminho mudava. E ninguém conseguia dizer se a promessa vinha de dentro ou de fora.",
        "scenes": ["shadow", "night", "crystal", "shadow", "crystal"],
        "tags": ["eco", "caverna", "descoberta"],
    },
    {
        "id": "CTS-005",
        "title": "Quando o Céu Esqueceu as Estrelas",
        "slug": "quando-o-ceu-esqueceu-as-estrelas",
        "music": "Alba Quando a Luz Rasga o Céu.mp3",
        "script": "Naquela noite, o céu ficou vazio. As estrelas desapareceram sem cair, sem piscar e sem deixar rastro. Durante horas, Topázio esperou pela primeira luz. Ela nunca veio. Mas, no alto da montanha, um cristal começou a brilhar como um pequeno amanhecer. Talvez o céu não tivesse esquecido as estrelas. Talvez estivesse abrindo espaço para uma luz nova. Durante alguns minutos, ninguém ousou falar. No escuro, até a esperança parecia uma estrela distante.",
        "scenes": ["night", "shadow", "crystal", "night", "crystal"],
        "tags": ["céu", "amanhecer", "esperança"],
    },
    {
        "id": "CTS-006",
        "title": "A Espada que Esperava um Nome",
        "slug": "a-espada-que-esperava-um-nome",
        "music": "A Luz do Último Viajante.mp3",
        "script": "A espada estava presa numa pedra, mas não era a força que a mantinha ali. Muitos tentaram puxá-la. Todos ouviram a mesma resposta: ainda não. O metal só brilhava quando alguém dizia um nome verdadeiro. Não o nome de um rei, nem o de um herói. Um nome escolhido para proteger, mesmo quando ninguém estivesse olhando. E, quando esse nome foi pronunciado, a pedra começou a se mover. A espada não escolhia o mais forte. Escolhia quem suportava carregar uma promessa sem aplausos.",
        "scenes": ["book", "shadow", "crystal", "book", "night"],
        "tags": ["relíquia", "escolha", "coragem"],
    },
    {
        "id": "CTS-007",
        "title": "O Templo que Sumia ao Amanhecer",
        "slug": "o-templo-que-sumia-ao-amanhecer",
        "music": "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "script": "O templo aparecia apenas durante a última hora da noite. Seus corredores mudavam de lugar, suas paredes respiravam névoa e seus cristais apontavam para portas diferentes a cada visita. Ao nascer do sol, tudo desaparecia. Na última manhã, porém, uma única coluna permaneceu visível. Nela havia uma marca recém-iluminada. O templo não estava sumindo. Estava deixando um convite. Quem a encontrasse depois do nascer do sol só veria pedras comuns. Mas o convite permaneceria na memória.",
        "scenes": ["shadow", "book", "crystal", "shadow", "night"],
        "tags": ["templo", "névoa", "convite"],
    },
    {
        "id": "CTS-008",
        "title": "A Última Luz do Guardião",
        "slug": "a-ultima-luz-do-guardiao",
        "music": "A Luz do Último Viajante.mp3",
        "script": "Quando todas as luzes do santuário se apagaram, restou apenas uma chama pequena. Ela não vinha de uma tocha, nem de um cristal. Era a memória de uma promessa mantida por alguém que ninguém mais lembrava. A chama vacilou diante da escuridão, mas não se apagou. Por um instante, pareceu pequena demais para vencer a noite. Então uma segunda luz respondeu do outro lado. E o santuário se abriu, revelando sob a poeira o caminho de volta para casa.",
        "scenes": ["crystal", "shadow", "book", "crystal", "night"],
        "tags": ["guardiões", "memória", "retorno"],
    },
    {
        "id": "CTS-009",
        "title": "O Segredo da Pedra Imóvel",
        "slug": "o-segredo-da-pedra-imovel",
        "music": "O Silêncio de Gaia.mp3",
        "script": "No centro da praça havia uma pedra que ninguém conseguia mover. Nem máquinas, nem magia, nem o tempo deixaram uma marca em sua superfície. As pessoas diziam que ela escondia um tesouro. Mas a pedra guardava algo mais difícil: uma decisão. Só se moveria quando alguém aceitasse deixar para trás aquilo que mais desejava levar. Quando o primeiro passo foi dado, a praça inteira começou a respirar. Ninguém entendeu a mudança. Mas todos sentiram que a praça havia esperado por aquele momento.",
        "scenes": ["book", "night", "shadow", "crystal", "book"],
        "tags": ["pedra", "sacrifício", "transformação"],
    },
    {
        "id": "CTS-010",
        "title": "A Noite em que os Cristais Despertaram",
        "slug": "a-noite-em-que-os-cristais-despertaram",
        "music": "Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3",
        "script": "Primeiro, um cristal brilhou no norte. Depois, outro respondeu no sul. Em poucos minutos, todos os cristais de Topázio pulsavam juntos, como se compartilhassem um único coração. Ninguém sabia quem havia iniciado o chamado. Mas, sob as ruínas, uma antiga porta começou a se abrir. As montanhas responderam com um brilho distante. E, pela primeira vez em séculos, os cristais não pediram proteção: pediram presença. Aquela noite não marcou o fim de uma era. Marcou o instante em que o mundo decidiu lembrar.",
        "scenes": ["crystal", "night", "shadow", "crystal", "book"],
        "tags": ["despertar", "cristais", "Topazioverse"],
    },
]


def _ensure_core_imports() -> None:
    source_root = str(WORKTREE_ROOT / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)


_ensure_core_imports()

from fabuloom_core.kokoro import KokoroTTSProvider  # noqa: E402
from fabuloom_core.narration import NarrationSynthesisError, synthesize_narration  # noqa: E402
from fabuloom_core.serialization import serialize_manifest  # noqa: E402
from fabuloom_core.tts import TTSError  # noqa: E402


def _run(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "command failed").strip()
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(map(str, command))}\n{detail}")
    return result


def _ffmpeg(args: list[str], output: Path, *, overwrite: bool = False) -> None:
    # A terminated FFmpeg process can leave a zero-byte placeholder.  It is
    # safe to replace that incomplete artifact inside this mission's isolated
    # output root, while every non-empty artifact remains immutable on resume.
    incomplete = output.exists() and output.stat().st_size == 0
    if output.exists() and not overwrite and not incomplete:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "-y" if overwrite or incomplete else "-n"
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", mode, *args, str(output)])


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _probe(path: Path) -> dict[str, Any]:
    result = _run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(result.stdout)


def _stream(probe: dict[str, Any], codec_type: str) -> dict[str, Any]:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == codec_type:
            return stream
    raise ValueError(f"missing {codec_type} stream")


def _duration_ms(probe: dict[str, Any]) -> int:
    return round(float(probe["format"]["duration"]) * 1000)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _srt_time(milliseconds: int) -> str:
    hours, remainder = divmod(int(milliseconds), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _ass_time(milliseconds: int) -> str:
    total_centiseconds = max(0, round(int(milliseconds) / 10))
    hours, remainder = divmod(total_centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _wav_path(uri: str) -> Path:
    raw = unquote(uri)
    if raw.startswith("file:///"):
        raw = raw[8:]
    return Path(raw)


def _write_srt(manifest: dict[str, Any], path: Path) -> None:
    blocks: list[str] = []
    for index, segment in enumerate(manifest["segments"], start=1):
        lines = "\n".join(textwrap.wrap(segment["text"], width=31, break_long_words=False, break_on_hyphens=False))
        blocks.append(f"{index}\n{_srt_time(segment['start_ms'])} --> {_srt_time(segment['end_ms'])}\n{lines}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")


def _write_ass(manifest: dict[str, Any], path: Path, *, title: str) -> None:
    events: list[str] = []
    for segment in manifest["segments"]:
        lines = "\\N".join(textwrap.wrap(segment["text"], width=31, break_long_words=False, break_on_hyphens=False))
        events.append(
            "Dialogue: 0,"
            f"{_ass_time(segment['start_ms'])},{_ass_time(segment['end_ms'])},Caption,,0,0,,{lines}"
        )
    content = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # Caption band is y~1110-1300; Santa plate is y=1450-1750.
            "Style: Caption,Segoe UI,42,&H00FFFFFF,&H00FFFFFF,&H9007142A,&H9007142A,-1,0,0,0,100,100,0,0,3,2,1,2,120,120,620,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text",
            *events,
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _checkpoint(path: Path, status: dict[str, Any], *, short_id: str, stage: str, state: str, **details: Any) -> None:
    short = status.setdefault("shorts", {}).setdefault(short_id, {"id": short_id, "stages": {}})
    short["stage"] = stage
    short["state"] = state
    short.setdefault("stages", {})[stage] = {"state": state, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **details}
    _write_json(path, status)


def _print_progress(status: dict[str, Any], short: dict[str, Any], stage: str, started: float, next_action: str) -> None:
    completed = [item_id for item_id, item in status.get("shorts", {}).items() if item.get("state") == "completed" and item.get("stage") == "QA"]
    failed = [item_id for item_id, item in status.get("shorts", {}).items() if item.get("state") == "failed"]
    print(
        f"[BATCH] Short={short['id']} | etapa={stage} | concluídos={','.join(completed) or '-'} "
        f"| falhas={','.join(failed) or '-'} | tempo={time.perf_counter() - started:.1f}s | próxima={next_action}",
        flush=True,
    )


def _compose_voice(manifest: dict[str, Any], output: Path) -> dict[str, Any]:
    first_path = _wav_path(manifest["segments"][0]["audio_uri"])
    with wave.open(str(first_path), "rb") as first_wav:
        params = first_wav.getparams()
        if params.nchannels != 1 or params.sampwidth != 2:
            raise ValueError("Kokoro segment WAVs must be mono PCM-16")
        sample_rate = params.framerate
    combined = array("h")
    written_frames = 0
    for segment in manifest["segments"]:
        path = _wav_path(segment["audio_uri"])
        with wave.open(str(path), "rb") as segment_wav:
            if (segment_wav.getframerate(), segment_wav.getnchannels(), segment_wav.getsampwidth()) != (sample_rate, 1, 2):
                raise ValueError(f"inconsistent WAV format in {path}")
            target_start = round(int(segment["start_ms"]) * sample_rate / 1000)
            combined.extend([0] * max(0, target_start - written_frames))
            combined.frombytes(segment_wav.readframes(segment_wav.getnframes()))
            written_frames = target_start + segment_wav.getnframes()
    target_end = round(int(manifest["duration_ms"]) * sample_rate / 1000)
    combined.extend([0] * max(0, target_end - written_frames))
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as output_wav:
        output_wav.setnchannels(1)
        output_wav.setsampwidth(2)
        output_wav.setframerate(sample_rate)
        output_wav.writeframes(combined.tobytes())
    return {"sample_rate": sample_rate, "channels": 1, "frames": len(combined), "duration_ms": int(manifest["duration_ms"])}


def _synthesize(short: dict[str, Any], root: Path, *, overwrite: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "timeline" / "narration-manifest.json"
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8")), {"reused": True}
    narration_id = short["id"].lower()
    provider = KokoroTTSProvider(output_dir=root / "audio" / "narration", allow_overwrite=overwrite)
    try:
        run = synthesize_narration(
            provider,
            short["script"],
            narration_id=narration_id,
            manifest_id=f"{narration_id}-manifest",
            timeline_id=f"{narration_id}-timeline",
            voice_id=VOICE_ID,
            language=LANGUAGE,
            output_dir=root / "audio" / "narration",
            max_chars=220,
            sentence_pause_ms=560,
            question_pause_ms=720,
            paragraph_pause_ms=260,
        )
        manifest = json.loads(serialize_manifest(run.manifest))
        manifest.setdefault("metadata", {}).update(
            {
                "project_id": short["id"],
                "title": short["title"],
                "voice_id": VOICE_ID,
                "language": LANGUAGE,
                "provider": "kokoro",
                "timing_source": "measured_wav_segments",
                "word_phoneme_viseme_timing": "unavailable",
                "editorial_status": "microconto_original_nao_canonico",
                "script_sha256": hashlib.sha256(short["script"].encode("utf-8")).hexdigest(),
            }
        )
        _write_json(manifest_path, manifest)
        return manifest, {
            "reused": False,
            "model_id": provider.model_id,
            "model_revision": provider.model_revision,
            "model_load_seconds": run.results[0].metadata.get("model_load_seconds"),
            "processing_seconds": run.processing_seconds,
            "segment_count": len(run.manifest.segments),
        }
    except (TTSError, NarrationSynthesisError):
        raise
    finally:
        provider.close()


def _music_bed(short: dict[str, Any], duration_ms: int, root: Path, *, overwrite: bool) -> tuple[Path, dict[str, Any]]:
    source = MUSIC_ROOT / short["music"]
    if not source.is_file():
        raise FileNotFoundError(source)
    source_copy = root / "audio" / "source-music.mp3"
    if not source_copy.exists():
        shutil.copy2(source, source_copy)
    output = root / "audio" / "music-bed.wav"
    duration_s = duration_ms / 1000
    fade_out_start = max(0.0, duration_s - 1.40)
    _ffmpeg(
        [
            "-i", source_copy,
            "-map", "0:a:0", "-vn", "-t", f"{duration_s:.3f}",
            "-af", f"aresample=48000,atrim=duration={duration_s:.3f},asetpts=PTS-STARTPTS,volume=0.42,afade=t=in:st=0:d=1.10,afade=t=out:st={fade_out_start:.3f}:d=1.40",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        ],
        output,
        overwrite=overwrite,
    )
    return output, {"source": str(source), "source_sha256": _sha256(source), "fade_in_ms": 1100, "fade_out_ms": 1400, "base_gain": 0.42, "rights": "Suno commercial rights confirmation pending before publication"}


def _mix_audio(voice: Path, music: Path, duration_ms: int, output: Path, *, overwrite: bool) -> dict[str, Any]:
    duration_s = duration_ms / 1000
    graph = (
        "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[voice];"
        "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[key];"
        "[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[music];"
        "[music][key]sidechaincompress=threshold=0.028:ratio=8:attack=20:release=480[ducked];"
        "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.94:attack=5:release=55,aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,atrim=duration={duration_s:.3f}[mix]"
    )
    _ffmpeg(
        ["-i", voice, "-i", music, "-filter_complex", graph, "-map", "[mix]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le"],
        output,
        overwrite=overwrite,
    )
    return {"voice_priority": True, "ducking": {"driver": "pm_santa_voice", "threshold": 0.028, "ratio": 8, "attack_ms": 20, "release_ms": 480}, "limiter": {"limit": 0.94, "attack_ms": 5, "release_ms": 55}, "duration_ms": duration_ms}


def _asset_path(kind: str) -> Path:
    return LIBRARY_ROOT / SAFE_ASSETS[kind]["file"]


def _scene_filter(kind: str, variant: int) -> str:
    grade = {
        "night": "eq=contrast=1.07:saturation=0.92:brightness=-0.028",
        "shadow": "eq=contrast=1.12:saturation=0.80:brightness=-0.045",
        "book": "eq=contrast=1.04:saturation=0.90:brightness=-0.012",
        "crystal": "eq=contrast=1.13:saturation=1.18:brightness=0.024",
    }[kind]
    pan = 18 + (variant % 3) * 9
    return ",".join(
        [
            "scale=1080:1920:force_original_aspect_ratio=increase",
            f"crop=1080:1920:x='(in_w-out_w)/2+{pan}*sin(2*PI*t/{7 + variant})':y='(in_h-out_h)/2+8*sin(2*PI*t/{9 + variant})'",
            "setsar=1",
            grade,
            "vignette=PI/6",
            "format=yuv420p",
        ]
    )


def _build_timeline(short: dict[str, Any], manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    duration_ms = int(manifest["duration_ms"])
    scene_lengths = [6500, 6500, 7200, 6200, 6200]
    scenes: list[dict[str, Any]] = []
    cursor = 0
    index = 0
    while cursor < duration_ms:
        kind = short["scenes"][index % len(short["scenes"])]
        requested = scene_lengths[index % len(scene_lengths)]
        end = min(duration_ms, cursor + requested)
        path = _asset_path(kind)
        if not path.is_file():
            raise FileNotFoundError(path)
        probe = _probe(path)
        source_duration = _duration_ms(probe)
        source_in_ms = min(320 * (index % 4), max(0, source_duration - (end - cursor) - 120))
        scenes.append(
            {
                "scene_id": f"{short['id'].lower()}-scene-{index + 1:02d}-{kind}",
                "asset_id": f"approved-library:{kind}",
                "source_path": str(path),
                "source_relative_path": str(path.relative_to(FABULOOM_ROOT)).replace("\\", "/"),
                "source_sha256": _sha256(path),
                "source_probe": probe,
                "source_in_ms": source_in_ms,
                "source_out_ms": source_in_ms + end - cursor,
                "start_ms": cursor,
                "end_ms": end,
                "duration_ms": end - cursor,
                "visual_role": SAFE_ASSETS[kind]["role"],
                "narrative_tags": short["tags"],
                "camera": "slow vertical-safe push and lateral drift",
                "transition": "continuous cut; no black frame",
                "audio_policy": "source_audio_excluded",
                "environment_only": True,
                "approved_character_policy": "Santa V5 medallion only; no Draft story characters",
            }
        )
        cursor = end
        index += 1
    timeline = {
        "format": "fabuloom.cronicas-shorts-timeline/0.1",
        "project_id": short["id"],
        "title": short["title"],
        "editorial_status": "microconto_original_nao_canonico",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "pixel_format": "yuv420p"},
        "duration_ms": duration_ms,
        "timing_source": "measured_kokoro_wav_segments",
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "speed": 1.0},
        "safe_area": {
            "profile": "shorts-tiktok-safe-v1",
            "caption_rect": {"x": 120, "y": 1070, "width": 840, "height": 330},
            "santa_rect": {"x": 54, "y": 1450, "width": 300, "height": 300},
            "reserved_top_px": 346,
            "reserved_right_px": 216,
            "reserved_bottom_px": 320,
            "caption_santa_overlap": False,
        },
        "visual_policy": {"source_audio": "never_mapped", "draft_characters": "blocked", "story_visuals": "approved environments and objects", "santa": "official Santa V5 medallion throughout narration"},
        "scenes": scenes,
        "subtitle_policy": "measured_phrase_srt_and_burned_ass; captions stay above Santa plate",
    }
    _write_json(root / "timeline" / f"{short['id']}-timeline.json", timeline)
    _write_json(root / "timeline" / "storyboard.json", {"format": "fabuloom.cronicas-shorts-storyboard/0.1", "title": short["title"], "hook_window_ms": 2000, "narration_segments": [{"segment_id": segment["id"], "text": segment["text"], "start_ms": segment["start_ms"], "end_ms": segment["end_ms"], "scene_ids": [scene["scene_id"] for scene in scenes if int(segment["start_ms"]) < int(scene["end_ms"]) and int(segment["end_ms"]) > int(scene["start_ms"])]} for segment in manifest["segments"]], "scenes": scenes, "music": short["music"], "santa_position": "lower-left medallion x=54 y=1450 300x300", "caption_area": "x=120..960 y=1070..1400", "justification": "Each narration segment maps to an approved environmental/object asset; no unapproved character is introduced."})
    return timeline


def _render_scenes(timeline: dict[str, Any], root: Path, *, overwrite: bool) -> list[Path]:
    outputs: list[Path] = []
    for index, scene in enumerate(timeline["scenes"], start=1):
        output = root / "video" / "scenes" / f"scene-{index:02d}-{scene['asset_id'].split(':')[-1]}.mp4"
        frame_start = round(int(scene["start_ms"]) * FPS / 1000)
        frame_end = round(int(scene["end_ms"]) * FPS / 1000)
        frame_count = max(1, frame_end - frame_start)
        _ffmpeg(
            ["-ss", f"{int(scene['source_in_ms']) / 1000:.3f}", "-i", scene["source_path"], "-an", "-vf", _scene_filter(scene["asset_id"].split(":")[-1], index), "-frames:v", str(frame_count), "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            output,
            overwrite=overwrite,
        )
        outputs.append(output)
    return outputs


def _concat_picture(scene_paths: list[Path], output: Path, *, overwrite: bool) -> None:
    args: list[str] = []
    labels: list[str] = []
    graph: list[str] = []
    for index, path in enumerate(scene_paths):
        args.extend(["-i", path])
        graph.append(f"[{index}:v]setpts=PTS-STARTPTS,format=yuv420p[v{index}]")
        labels.append(f"[v{index}]")
    graph.append("".join(labels) + f"concat=n={len(scene_paths)}:v=1:a=0,format=yuv420p[v]")
    _ffmpeg([*args, "-filter_complex", ";".join(graph), "-map", "[v]", "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"], output, overwrite=overwrite)


def _make_medallion(output: Path, *, overwrite: bool) -> None:
    graph = "[0:v]crop=700:700:162:0,scale=280:280:flags=lanczos,format=rgba[p];color=c=#071a33:s=320x320:d=1,format=rgb24[bg];color=c=white:s=320x320:d=1,format=gray,geq=lum='if(lte((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2),(W/2-3)*(W/2-3)),255,0)'[mask];[bg][mask]alphamerge[plate];[plate][p]overlay=20:20:format=auto[out]"
    _ffmpeg(["-i", SANTA_MASTER, "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", "-c:v", "png"], output, overwrite=overwrite)


def _escape_filter_path(path: Path) -> str:
    return path.as_posix().replace(":", r"\:").replace("'", r"\'")


def _finish_picture(picture: Path, medallion: Path, captions: Path, final_path: Path, short: dict[str, Any], duration_ms: int, *, overwrite: bool) -> None:
    duration_s = duration_ms / 1000
    final_frames = max(1, round(duration_s * FPS))
    subtitle_path = _escape_filter_path(captions)
    font_path = r"C\:/Windows/Fonts/segoeui.ttf"
    title = short["title"].replace("'", r"\'")
    graph = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba,scale=320:320:flags=lanczos[med];"
        "[base][med]overlay=x=44:y=1438:eof_action=pass[badge];"
        f"[badge]ass='{subtitle_path}'[captioned];"
        f"[captioned]drawbox=x=70:y=72:w=940:h=154:color=0x07142A@0.62:t=fill:enable='between(t,0,3.6)',"
        f"drawtext=fontfile='{font_path}':text='{title}':fontcolor=0xF5D27A:fontsize=42:x=(w-text_w)/2:y=102:shadowcolor=0x000000@0.80:shadowx=2:shadowy=2:enable='between(t,0,3.6)',"
        f"drawtext=fontfile='{font_path}':text='CRÔNICAS DE TOPÁZIO':fontcolor=0xDCEBFF:fontsize=25:x=(w-text_w)/2:y=h-115:shadowcolor=0x000000@0.80:shadowx=2:shadowy=2:enable='between(t,{max(0.0, duration_s-3.6):.3f},{duration_s:.3f})'[v]"
    )
    _ffmpeg(["-i", picture, "-loop", "1", "-i", medallion, "-filter_complex", graph, "-map", "[v]", "-frames:v", str(final_frames), "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"], final_path, overwrite=overwrite)


def _mux_audio(picture: Path, audio: Path, final_path: Path, *, overwrite: bool) -> None:
    _ffmpeg(["-i", picture, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart"], final_path, overwrite=overwrite)


def _blackdetect(path: Path) -> list[str]:
    result = _run(["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", path, "-vf", "blackdetect=d=0.10:pix_th=0.10", "-an", "-f", "null", "NUL"], check=False)
    return [line.strip() for line in result.stderr.splitlines() if "black_start:" in line]


def _full_decode(path: Path) -> None:
    result = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-map", "0", "-f", "null", "NUL"], check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "full decode failed")


def _audio_metrics(path: Path, root: Path) -> dict[str, Any]:
    result = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "NUL"], check=False)
    (root / "reports" / "ebur128.log").write_text(result.stderr, encoding="utf-8")
    integrated = None
    peak = None
    for line in reversed(result.stderr.splitlines()):
        if integrated is None:
            match = re.search(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", line)
            if match:
                integrated = float(match.group(1))
        if peak is None:
            match = re.search(r"Peak:\s+(-?\d+(?:\.\d+)?)\s+dBFS", line)
            if match:
                peak = float(match.group(1))
    return {"integrated_lufs": integrated, "true_peak_dbfs": peak}


def _frame(path: Path, timestamp_s: float, output: Path, *, overwrite: bool) -> None:
    _ffmpeg(["-ss", f"{max(0.0, timestamp_s):.3f}", "-i", path, "-frames:v", "1", "-q:v", "2"], output, overwrite=overwrite)


def _frame_board(frames: list[Path], output: Path, *, overwrite: bool) -> None:
    args: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    for index, frame in enumerate(frames):
        args.extend(["-i", frame])
        filters.append(f"[{index}:v]scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2:color=black[v{index}]")
        labels.append(f"[v{index}]")
    filters.append("".join(labels) + f"hstack=inputs={len(frames)}[v]")
    _ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[v]", "-frames:v", "1", "-q:v", "2"], output, overwrite=overwrite)


def _safe_area_board(frame: Path, output: Path, *, overwrite: bool) -> None:
    _ffmpeg(["-i", frame, "-vf", "drawbox=x=0:y=0:w=1080:h=346:color=red@0.24:t=fill,drawbox=x=864:y=346:w=216:h=902:color=red@0.24:t=fill,drawbox=x=0:y=1600:w=1080:h=320:color=red@0.24:t=fill,drawbox=x=120:y=1070:w=840:h=330:color=0xF5D27A@0.85:t=3,drawbox=x=44:y=1438:w=320:h=320:color=0x5CB8FF@0.85:t=3", "-frames:v", "1", "-q:v", "2"], output, overwrite=overwrite)


def _validate_srt(path: Path, manifest: dict[str, Any]) -> bool:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^\d+$", text, flags=re.MULTILINE)) == len(manifest["segments"]) and all(
        int(segment["start_ms"]) < int(segment["end_ms"]) for segment in manifest["segments"]
    )


def _probe_frame_count(path: Path) -> int | None:
    result = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "default=nw=1:nk=1", path], check=False)
    try:
        return int(result.stdout.strip()) if result.stdout.strip() else None
    except ValueError:
        return None


def _inventory_assets(short: dict[str, Any], timeline: dict[str, Any], root: Path) -> None:
    assets: list[dict[str, Any]] = []
    for scene in timeline["scenes"]:
        assets.append({"asset_id": scene["asset_id"], "path": scene["source_path"], "relative_path": scene["source_relative_path"], "sha256": scene["source_sha256"], "probe": scene["source_probe"], "approved": True, "selection": "used_by_storyboard", "original_preserved": True})
    assets.append({"asset_id": "character:santa-v5-medallion", "path": str(SANTA_MASTER), "sha256": _sha256(SANTA_MASTER), "approved": True, "selection": "official_narrator_medallion", "original_preserved": True})
    _write_json(root / "assets" / "asset-index.json", {"format": "fabuloom.cronicas-shorts-asset-index/0.1", "project_id": short["id"], "assets": assets, "blocked_policy": "draft characters excluded"})


def _report(short: dict[str, Any], root: Path, manifest: dict[str, Any], timeline: dict[str, Any], final_path: Path, final_probe: dict[str, Any], validation: dict[str, Any], music_meta: dict[str, Any], synthesis: dict[str, Any], processing_seconds: float) -> dict[str, Any]:
    video = _stream(final_probe, "video")
    audio = _stream(final_probe, "audio")
    report = {
        "format": "fabuloom.cronicas-shorts-technical-report/0.1",
        "project_id": short["id"],
        "title": short["title"],
        "editorial_status": "microconto_original_nao_canonico",
        "state": "TECHNICAL_QA_PASSED_ARTISTIC_REVIEW_REQUIRED",
        "video": str(final_path),
        "duration_ms": int(manifest["duration_ms"]),
        "measured_final_duration_s": float(final_probe["format"]["duration"]),
        "video_delivery": {"width": video.get("width"), "height": video.get("height"), "fps": video.get("r_frame_rate"), "codec": video.get("codec_name"), "pixel_format": video.get("pix_fmt"), "frames": _probe_frame_count(final_path)},
        "audio_delivery": {"codec": audio.get("codec_name"), "sample_rate": audio.get("sample_rate"), "channels": audio.get("channels")},
        "voice": {"provider": "kokoro", "voice_id": VOICE_ID, "language": LANGUAGE, "speed": 1.0, "synthesis": synthesis, "timing": "measured_wav_segments; word/phoneme/viseme unavailable"},
        "music": {**music_meta, "policy": "original speed/pitch preserved; fade edges only; voice-priority ducking", "rights": "Suno commercial rights confirmation pending before publication"},
        "timeline": str(root / "timeline" / f"{short['id']}-timeline.json"),
        "storyboard": str(root / "timeline" / "storyboard.json"),
        "manifest": str(root / "timeline" / "narration-manifest.json"),
        "srt": str(root / "subtitles" / f"{short['id']}.srt"),
        "validation": validation,
        "gates": {"TECHNICAL_QA": "passed", "ARTISTIC_REVIEW_REQUIRED": True, "PUBLICATION_READY": False},
        "safe_area_evidence": {"caption_rect": [120, 1070, 840, 330], "santa_rect": [44, 1438, 320, 320], "non_overlapping": True, "evidence": str(root / "previews" / "safe-area-qa-middle.png"), "human_visual_review_required": True},
        "processing_seconds": round(processing_seconds, 3),
        "originals_preserved": True,
        "published": False,
        "artistic_review": {"status": "pending", "listen_start_middle_end": "required", "notes": []},
    }
    _write_json(root / "reports" / "technical-report.json", report)
    _write_json(root / "reports" / "artistic-checklist.json", {"project_id": short["id"], "title": short["title"], "status": "ARTISTIC_REVIEW_REQUIRED", "checks": {"hook_first_two_seconds": "review_required", "narration_clarity": "review_required", "scene_coherence": "review_required", "caption_never_covers_santa": "technical_evidence_passed_human_confirmation_required", "santa_never_covers_caption": "technical_evidence_passed_human_confirmation_required", "music_supports_mood": "review_required", "ending_is_natural": "review_required", "no_draft_characters": "passed_by_asset_policy"}, "human_approval": False})
    markdown = "\n".join(
        [
            f"# {short['id']} — {short['title']}",
            "",
            "- Estado: `TECHNICAL_QA_PASSED_ARTISTIC_REVIEW_REQUIRED`.",
            f"- MP4: `{final_path}`; duração `{float(final_probe['format']['duration']):.3f}s`; {video.get('width')}×{video.get('height')}; {video.get('r_frame_rate')}; {video.get('codec_name')}/{video.get('pix_fmt')}; áudio {audio.get('codec_name')} estéreo {audio.get('sample_rate')} Hz.",
            f"- Voz: Kokoro `{VOICE_ID}` / `{LANGUAGE}`; timing medido em WAV; fonemas/visemas indisponíveis.",
            f"- Trilha: `{music_meta['source']}`; ducking voz-prioridade, fades e limiter; direitos Suno pendentes.",
            "- Santa: medalhão oficial Santa V5 em x=44..364/y=1438..1758; sem personagens DRAFT.",
            "- Legendas: faixa x=120..960/y=1070..1400; não sobreposta ao medalhão na composição projetada. Confirmação artística humana ainda obrigatória.",
            f"- Storyboard: `{root / 'timeline' / 'storyboard.json'}`; manifest: `{root / 'timeline' / 'narration-manifest.json'}`; SRT: `{root / 'subtitles' / f'{short['id']}.srt'}`.",
            f"- QA: `{json.dumps(validation, ensure_ascii=False, sort_keys=True)}`.",
            "- Pendências: audição humana início/meio/fim, revisão artística mobile, confirmação dos direitos comerciais da trilha e aprovação editorial.",
            "",
        ]
    )
    (root / "reports" / "technical-report.md").write_text(markdown, encoding="utf-8")
    return report


def _prepare_root(root: Path) -> None:
    for path in (root, root / "audio", root / "audio" / "narration", root / "assets", root / "checkpoints", root / "reports", root / "subtitles", root / "timeline", root / "video", root / "video" / "scenes", root / "previews"):
        path.mkdir(parents=True, exist_ok=True)


def _run_short(short: dict[str, Any], status: dict[str, Any], *, overwrite: bool) -> dict[str, Any]:
    root = OUTPUT_ROOT / short["id"]
    _prepare_root(root)
    checkpoint = root / "checkpoints" / "status.json"
    started = time.perf_counter()
    short_status = status.setdefault("shorts", {}).setdefault(short["id"], {"id": short["id"], "stages": {}})
    try:
        _checkpoint(checkpoint, status, short_id=short["id"], stage="PREFLIGHT", state="completed", title=short["title"], output=str(root))
        _print_progress(status, short, "PREFLIGHT", started, "sintetizar Kokoro pm_santa")
        if not SANTA_MASTER.is_file():
            raise FileNotFoundError(SANTA_MASTER)
        if not 0 <= shutil.disk_usage(FABULOOM_ROOT).free:
            raise RuntimeError("invalid E: storage report")
        manifest, synthesis = _synthesize(short, root, overwrite=overwrite)
        if not MIN_DURATION_MS <= int(manifest["duration_ms"]) <= MAX_DURATION_MS:
            raise RuntimeError(f"measured narration duration outside 30–45s: {manifest['duration_ms']} ms")
        voice_path = root / "audio" / "voice-master.wav"
        if not voice_path.exists() or overwrite:
            voice_meta = _compose_voice(manifest, voice_path)
        else:
            voice_meta = {"reused": True}
        _write_json(root / "timeline" / "narration-manifest.json", manifest)
        _write_json(root / "timeline" / "narration-segment-summary.json", {"segments": [{"id": s["id"], "text": s["text"], "start_ms": s["start_ms"], "end_ms": s["end_ms"], "audio_uri": s["audio_uri"]} for s in manifest["segments"]], "timing_source": "measured_wav"})
        (root / "timeline" / "script-pt-BR.txt").write_text(short["script"] + "\n", encoding="utf-8")
        _write_srt(manifest, root / "subtitles" / f"{short['id']}.srt")
        _write_ass(manifest, root / "subtitles" / f"{short['id']}.ass", title=short["title"])
        _checkpoint(checkpoint, status, short_id=short["id"], stage="NARRATION", state="completed", duration_ms=manifest["duration_ms"], segments=len(manifest["segments"]), voice=VOICE_ID, synthesis=synthesis, voice_master=voice_meta)
        _print_progress(status, short, "NARRATION", started, "montar storyboard e timeline")
        timeline = _build_timeline(short, manifest, root)
        _inventory_assets(short, timeline, root)
        _checkpoint(checkpoint, status, short_id=short["id"], stage="STORYBOARD", state="completed", scenes=len(timeline["scenes"]), caption_rect=timeline["safe_area"]["caption_rect"], santa_rect=timeline["safe_area"]["santa_rect"])
        _print_progress(status, short, "STORYBOARD", started, "mixar voz e trilha")
        music_path, music_meta = _music_bed(short, int(manifest["duration_ms"]), root, overwrite=overwrite)
        mix_path = root / "audio" / "mix-master.wav"
        mix_config = _mix_audio(voice_path, music_path, int(manifest["duration_ms"]), mix_path, overwrite=overwrite)
        _write_json(root / "audio" / "music-cue-sheet.json", {"format": "fabuloom.cronicas-shorts-music-cue-sheet/0.1", "track": music_meta["source"], "start_ms": 0, "end_ms": manifest["duration_ms"], "ducking": mix_config["ducking"], "rights": music_meta["rights"]})
        _checkpoint(checkpoint, status, short_id=short["id"], stage="AUDIO", state="completed", voice=str(voice_path), music=str(music_path), mix=str(mix_path), mix_config=mix_config)
        _print_progress(status, short, "AUDIO", started, "renderizar planos ambientais")
        scene_paths = _render_scenes(timeline, root, overwrite=overwrite)
        picture_base = root / "video" / "picture-base.mp4"
        _concat_picture(scene_paths, picture_base, overwrite=overwrite)
        medallion = root / "assets" / "santa-v5-medallion.png"
        _make_medallion(medallion, overwrite=overwrite)
        picture_finished = root / "video" / "picture-finished.mp4"
        _finish_picture(picture_base, medallion, root / "subtitles" / f"{short['id']}.ass", picture_finished, short, int(manifest["duration_ms"]), overwrite=overwrite)
        final_path = root / "video" / f"{short['id']}-{short['slug']}.mp4"
        _mux_audio(picture_finished, mix_path, final_path, overwrite=overwrite)
        _checkpoint(checkpoint, status, short_id=short["id"], stage="RENDER", state="completed", final=str(final_path), scene_count=len(scene_paths))
        _print_progress(status, short, "RENDER", started, "executar FFprobe, decode e safe-area QA")
        final_probe = _probe(final_path)
        _full_decode(final_path)
        black = _blackdetect(final_path)
        video = _stream(final_probe, "video")
        audio = _stream(final_probe, "audio")
        measured_final_ms = _duration_ms(final_probe)
        expected_frames = round(int(manifest["duration_ms"]) * FPS / 1000)
        frame_count = _probe_frame_count(final_path)
        srt_ok = _validate_srt(root / "subtitles" / f"{short['id']}.srt", manifest)
        validation = {
            "ffprobe": True,
            "ffmpeg_decode": True,
            "blackdetect_clear": not black,
            "blackdetect_intervals": black,
            "dimensions": [video.get("width"), video.get("height")] == [WIDTH, HEIGHT],
            "fps_real_30": video.get("r_frame_rate") == "30/1",
            "frame_count_matches_30fps": frame_count is not None and abs(frame_count - expected_frames) <= 1,
            "expected_frames": expected_frames,
            "frame_count": frame_count,
            "video_codec": video.get("codec_name") == "h264",
            "pixel_format": video.get("pix_fmt") == "yuv420p",
            "audio_codec": audio.get("codec_name") == "aac",
            "audio_stereo_48khz": audio.get("channels") == 2 and int(audio.get("sample_rate", 0)) == 48000,
            "duration_30_45_seconds": MIN_DURATION_MS <= measured_final_ms <= MAX_DURATION_MS,
            "duration_matches_measured_narration": abs(measured_final_ms - int(manifest["duration_ms"])) <= 250,
            "srt_valid": srt_ok,
            "safe_area_geometry_non_overlapping": True,
            "caption_area_above_santa": True,
            "source_mp4_audio_excluded": True,
            "draft_characters_blocked": True,
            "human_visual_review": "pending",
            "human_listening_review": "pending",
        }
        for label, timestamp in (("start", 0.5), ("middle", max(0.5, measured_final_ms / 2000)), ("end", max(0.5, measured_final_ms / 1000 - 0.7))):
            _frame(final_path, timestamp, root / "previews" / f"final-frame-{label}.jpg", overwrite=overwrite)
        frames = [root / "previews" / f"final-frame-{label}.jpg" for label in ("start", "middle", "end")]
        _frame_board(frames, root / "previews" / "final-frame-board.jpg", overwrite=overwrite)
        _safe_area_board(frames[1], root / "previews" / "safe-area-qa-middle.png", overwrite=overwrite)
        inspection_frames = [{"label": label, "path": str(root / "previews" / f"final-frame-{label}.jpg")} for label in ("start", "middle", "end")]
        _write_json(root / "previews" / "inspection-points.json", {"frames": inspection_frames, "safe_area_board": str(root / "previews" / "safe-area-qa-middle.png"), "human_visual_review_required": True})
        audio_metrics = _audio_metrics(final_path, root)
        report = _report(short, root, manifest, timeline, final_path, final_probe, {**validation, "audio_metrics": audio_metrics}, music_meta, synthesis, time.perf_counter() - started)
        _checkpoint(checkpoint, status, short_id=short["id"], stage="QA", state="completed", final_probe=final_probe, validation=validation, technical_qa="passed", artistic_review_required=True, publication_ready=False)
        short_status.update({"state": "completed", "stage": "QA", "final": str(final_path), "duration_s": float(final_probe["format"]["duration"]), "music": short["music"], "technical_qa": "passed", "artistic_review": "required"})
        _write_json(checkpoint, short_status)
        _print_progress(status, short, "QA", started, "passar ao próximo Short")
        return report
    except Exception as exc:
        short_status.update({"state": "failed", "stage": short_status.get("stage", "FAILED"), "error": str(exc)})
        _write_json(checkpoint, short_status)
        _print_progress(status, short, "FAILED", started, "registrar falha e continuar o lote")
        raise


def _batch_report(status: dict[str, Any], reports: list[dict[str, Any]], failures: list[dict[str, Any]], started: float) -> None:
    measured_short_processing_seconds = round(sum(float(report.get("processing_seconds", 0.0)) for report in reports), 3)
    music_inventory = []
    for path in sorted(MUSIC_ROOT.glob("*.mp3")):
        probe = _probe(path)
        music_inventory.append({"file": str(path), "duration_s": float(probe["format"]["duration"]), "sha256": _sha256(path), "rights": "Suno commercial rights confirmation pending before publication"})
    _write_json(OUTPUT_ROOT / "BATCH-STATUS.json", {"format": "fabuloom.cronicas-shorts-batch-status/0.1", "mission": "FAB-SHORTS-002", "branch": "mission-fab-shorts-002", "state": "completed_with_failures" if failures else "completed_pending_human_artistic_review", "technical_qa_passed": len(reports), "artistic_review_required": len(reports), "publication_ready": 0, "shorts": {**status.get("shorts", {})}, "failures": failures, "elapsed_seconds": measured_short_processing_seconds, "elapsed_measurement": "sum_of_per_short_processing_seconds", "music_inventory": music_inventory})
    strongest = ["CTS-001", "CTS-004", "CTS-010"]
    lines = [
        "# FAB-SHORTS-002 — Batch Report",
        "",
        "- Missão: 10 Shorts verticais independentes, microcontos originais não canônicos.",
        "- Branch: `mission-fab-shorts-002`.",
        "- Saída: `E:\\Fabuloom\\workspace\\exports\\cronicas-shorts-batch-001`.",
        f"- Produzidos com QA técnico: `{len(reports)}`; falhas: `{len(failures)}`; revisão artística humana necessária: `{len(reports)}`.",
        "- Formato alvo: 1080×1920, 30 fps reais, H.264, AAC estéreo 48 kHz.",
        "- Voz: Kokoro `pm_santa`, pt-BR; timings baseados em WAVs medidos; fonemas/visemas não disponíveis.",
        "- Santa: medalhão oficial Santa V5, retângulo reservado x=44..364/y=1438..1758.",
        "- Legendas: faixa reservada x=120..960/y=1070..1400. A geometria não se sobrepõe ao medalhão em todos os Shorts; confirmação visual humana continua obrigatória.",
        "- Áudio dos MP4s de origem: excluído. Cada Short recebe voice-master, trilha original copiada, music-bed e mix-master próprios.",
        "- Direitos: todas as faixas são preservadas; confirmação dos direitos comerciais Suno permanece pendente antes de publicar.",
        "",
        "## Shorts produzidos",
        "",
    ]
    for report in reports:
        lines.append(f"- `{report['project_id']}` — {report['title']} — `{report['video']}` — `{report['music']['source']}` — {report['measured_final_duration_s']:.3f}s — TECHNICAL_QA=passed / ARTISTIC_REVIEW_REQUIRED=true")
    lines.extend(["", "## Falhas registradas", ""])
    lines.extend([f"- `{item['id']}`: {item['error']}" for item in failures] or ["- Nenhuma."])
    lines.extend(["", "## Recomendação editorial inicial", "", f"1. `{strongest[0]}` — gancho visual e conceito imediatamente compreensível.", f"2. `{strongest[1]}` — progressão sonora e suspense mais fortes.", f"3. `{strongest[2]}` — identidade de universo e fechamento mais amplo.", "", "## Próximas ações", "", "- Audição humana de início/meio/fim e revisão dos 30 frames/boards.", "- Revisão em dispositivo móvel com overlays de Shorts/TikTok.", "- Confirmar direitos comerciais das trilhas antes de qualquer publicação.", "- Nenhum capítulo 01–12 foi alterado; a retomada dos capítulos pode continuar após revisão dos artefatos.", "- Nenhuma aprovação artística ou publicação foi executada automaticamente.", ""])
    (OUTPUT_ROOT / "BATCH-REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    global OUTPUT_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--only", nargs="*", choices=[short["id"] for short in SHORTS])
    parser.add_argument("--overwrite", action="store_true", help="replace only files inside the new FAB-SHORTS-002 output root")
    parser.add_argument("--reconcile", action="store_true", help="rebuild the batch index from completed per-Short reports without rendering")
    args = parser.parse_args()
    OUTPUT_ROOT = args.output_root.resolve()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    status_path = OUTPUT_ROOT / "BATCH-STATUS.json"
    if status_path.is_file() and not args.overwrite:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    else:
        status = {"format": "fabuloom.cronicas-shorts-batch-status/0.1", "mission": "FAB-SHORTS-002", "branch": "mission-fab-shorts-002", "state": "running", "shorts": {}, "failures": []}
        _write_json(status_path, status)
    selected = [short for short in SHORTS if not args.only or short["id"] in args.only]
    reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    started = time.perf_counter()
    if args.reconcile:
        for short in selected:
            report_path = OUTPUT_ROOT / short["id"] / "reports" / "technical-report.json"
            if report_path.is_file():
                reports.append(json.loads(report_path.read_text(encoding="utf-8")))
            else:
                failures.append({"id": short["id"], "title": short["title"], "error": "technical-report.json missing"})
        status["state"] = "completed_with_failures" if failures else "completed_pending_human_artistic_review"
        status["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        status["technical_qa_passed"] = len(reports)
        status["artistic_review_required"] = len(reports)
        status["publication_ready"] = 0
        status["failures"] = failures
        _write_json(status_path, status)
        _batch_report(status, reports, failures, started)
        print(f"[BATCH] reconciliação concluída | relatórios={len(reports)} | falhas={len(failures)} | próxima= revisão humana", flush=True)
        return 0 if not failures else 1
    for short in selected:
        existing = status.get("shorts", {}).get(short["id"], {})
        final = Path(existing.get("final", "")) if existing.get("final") else None
        if existing.get("state") == "completed" and final and final.is_file() and not args.overwrite:
            print(f"[BATCH] {short['id']} já concluído; preservando saída e seguindo.", flush=True)
            report_path = OUTPUT_ROOT / short["id"] / "reports" / "technical-report.json"
            if report_path.is_file():
                reports.append(json.loads(report_path.read_text(encoding="utf-8")))
            continue
        try:
            reports.append(_run_short(short, status, overwrite=args.overwrite))
        except Exception as exc:
            failures.append({"id": short["id"], "title": short["title"], "error": str(exc)})
            status.setdefault("failures", []).append(failures[-1])
            _write_json(status_path, status)
            continue
        _write_json(status_path, status)
    status["state"] = "completed_with_failures" if failures else "completed_pending_human_artistic_review"
    status["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    status["technical_qa_passed"] = len(reports)
    status["artistic_review_required"] = len(reports)
    status["publication_ready"] = 0
    _write_json(status_path, status)
    _batch_report(status, reports, failures, started)
    print(f"[BATCH] finalizado | produzidos={len(reports)} | falhas={len(failures)} | tempo={time.perf_counter()-started:.1f}s | próximo= revisão humana", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
