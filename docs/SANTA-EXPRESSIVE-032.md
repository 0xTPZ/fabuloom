# Missão 032 — Santa Expressive V1

## Diagnóstico

O adaptador `KokoroTTSProvider` atual carrega e reutiliza o modelo `hexgrad/Kokoro-82M`, aceita `pm_santa` em `pt-BR` e encaminha somente `speed` ao Kokoro. Pitch, volume, parâmetros extras, SSML e tags emocionais são rejeitados pelo contrato. O adaptador também mede o WAV real, mas não fornece alinhamento de palavras, fonemas ou visemas.

`synthesize_narration` separa parágrafos e pontuação, registra pausas de composição e monta o manifesto a partir das durações reais. Ele não controla entonação acústica; portanto, uma pergunta terminada em `?` não garante por si só uma curva interrogativa convincente.

## Protótipo

O laboratório está em `examples/santa_expressive_v1_lab.py`. Ele não altera nenhum episódio e não substitui as falas originais. O vocabulário de direção contém:

- `neutral`: controle, texto original, velocidade `1,00`;
- `curious`: reticência moderada, velocidade `0,97`, pausa de pergunta `320 ms`;
- `suspense`: reticência e velocidade `0,92`, pausa de pergunta `420 ms`;
- `welcoming`: contrato preparado para falas acolhedoras futuras, sem inventar diálogo do CB-002.

Foram produzidas três versões para cada uma das duas perguntas do CB-002. A versão `neutral` mantém exatamente:

`Você já reparou para onde aponta a sua sombra?`

`E você, Guardião... olharia para trás?`

As variações de pontuação e velocidade não mudam o significado, mas podem alterar a prosódia produzida pelo modelo. Isso precisa ser confirmado por audição humana.

## Amostras

Todos os arquivos estão fora do Git em:

`E:\Fabuloom\workspace\exports\voice-lab\mission-032-santa-expressive-v1\`

| Perfil | Pergunta 1 | Pergunta 2 |
|---|---|---|
| Neutro | `samples\01-neutral-q01.wav` — 3000 ms | `samples\01-neutral-q02.wav` — 2675 ms |
| Curioso | `samples\02-curious-q01.wav` — 3175 ms | `samples\02-curious-q02.wav` — 2625 ms |
| Suspense | `samples\03-suspense-q01.wav` — 3225 ms | `samples\03-suspense-q02.wav` — 2875 ms |

Cada amostra possui manifesto JSON, SRT e métricas RMS/peak correspondentes. Os WAVs são mono PCM-16 a 24 kHz. Os manifests registram `audio_duration_only`; não há timestamps inventados de palavras, fonemas ou visemas.

## Recomendação provisória

Para uma primeira avaliação de Santa conversacional, o perfil `curious` é o candidato técnico mais equilibrado: a alteração de velocidade é pequena (`0,97`), a pausa é perceptível e o texto continua natural. O perfil `suspense` deve ser reservado para momentos em que a desaceleração for desejada, pois aumenta mais a duração e pode soar excessivo.

Esta é uma recomendação técnica preliminar, não uma aprovação auditiva. O proprietário deve comparar as seis amostras e escolher a direção antes de qualquer integração em CB-002, CB-003 ou outro vídeo.

## Execução e preservação

O laboratório usa o ambiente Kokoro local já existente e não instala dependências. A branch pública é específica da missão. Os episódios aprovados, seus WAVs, manifestos, SRTs e MP4s não foram modificados.
