# FAB-SHORTS-002 — Batch de Shorts verticais

Esta missão produz dez microcontos verticais independentes para revisão humana
do canal Crônicas de Topázio. Eles não são capítulos canônicos e não alteram os
capítulos 01–12 nem as produções aprovadas.

## Runner

O runner é `examples/fab_shorts_002_batch.py`. Ele deve ser executado com um
ambiente Python que já contenha o provedor Kokoro validado; não instala
dependências e mantém o modo offline do Hugging Face. A saída é configurável e,
por padrão, fica em `workspace/exports/cronicas-shorts-batch-001`.

```text
python examples/fab_shorts_002_batch.py
python examples/fab_shorts_002_batch.py --only CTS-001 CTS-002
python examples/fab_shorts_002_batch.py --reconcile
```

O processo é sequencial, grava `BATCH-STATUS.json` em cada etapa e preserva
artefatos não vazios ao retomar. Um placeholder zero-byte deixado por uma
interrupção do FFmpeg pode ser regenerado dentro da saída isolada; nenhum
arquivo-fonte ou produção anterior é substituído.

## Contratos de cada Short

Cada diretório `CTS-001`–`CTS-010` contém:

- MP4 vertical 1080×1920, 30 fps, H.264, AAC estéreo 48 kHz;
- WAVs segmentados, `voice-master.wav`, `music-bed.wav` e `mix-master.wav`;
- manifesto de narração com duração medida, SRT e ASS;
- storyboard com associação dos segmentos aos assets;
- índice de assets com hashes e política de bloqueio de personagens Draft;
- pranchas de quadros e prancha de safe area;
- relatório técnico e checklist artístico.

A voz é Kokoro `pm_santa` em `pt-BR`. Os tempos são derivados dos WAVs reais;
word/phoneme/viseme timing permanece indisponível. O áudio dos MP4s de origem é
sempre descartado (`-an`) e a mix final usa apenas a voz, a trilha escolhida,
ducking side-chain voz-prioridade e limiter.

## Safe area

A composição usa uma faixa de legendas em `x=120..960, y=1070..1400` e o
medalhão Santa V5 em `x=44..364, y=1438..1758`. Esses retângulos são registrados
no timeline, no relatório e na prancha visual. A separação geométrica é uma
verificação técnica; não substitui a inspeção humana em celular com os overlays
do TikTok/Shorts.

## Assets e direitos

O storyboard usa somente ambientes/objetos aprovados da biblioteca local e o
medalhão oficial Santa V5. Clips com personagens não aprovados não entram no
lote. As sete músicas existentes são inventariadas; a faixa selecionada é
copiada sem alterar velocidade ou tom, com fades nas extremidades. A confirmação
dos direitos comerciais das faixas de origem Suno continua pendente antes de
qualquer publicação.

## Gates

O batch marca cada item como `TECHNICAL_QA=passed` somente após FFprobe, decode
FFmpeg, blackdetect, contagem de frames, codec, resolução, áudio, duração, SRT e
geometria da safe area. Todos os itens permanecem
`ARTISTIC_REVIEW_REQUIRED=true` e `PUBLICATION_READY=false` até audição e
avaliação visual humana.

Artefatos da execução ficam fora do Git em
`workspace/exports/cronicas-shorts-batch-001`. O relatório consolidado é
`BATCH-REPORT.md`, acompanhado por `BATCH-STATUS.json`.
