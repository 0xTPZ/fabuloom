# FAB-PROD-004 — produção cinematográfica pelo EngineService

Este documento registra a primeira produção cinematográfica executada pelo
motor compartilhado do Fabuloom Studio. Desktop, CLI, API loopback e MCP usam o
mesmo `EngineService`; nenhum desses controles chama um compositor paralelo.

## Boundary de execução

O contrato público é `fabuloom.cronicas-cinematic-production/0.1`. A execução
aceita apenas um runner listado em
`profiles/registries/cinematic-runners.json`. O runner é validado por caminho
relativo, nome permitido e SHA-256 antes de iniciar. Ele recebe um arquivo
`--request` com o capítulo, voz, variantes e `output_root`.

O output precisa ser um diretório filho de `workspace/exports`. A requisição é
persistida em `.engine-request.json`; uma requisição diferente não pode ser
misturada ao mesmo diretório e uma produção completa nunca é sobrescrita. O
runner grava `CHECKPOINT.json`, permitindo reutilizar etapas válidas durante a
retomada. Cancelamento é encaminhado pelo job do EngineService.

O runner validado desta missão é `cronicas.chapter`. Ele reutiliza a captura
Canvas existente, `NarratorAvatarRenderer`, Santa V5 aprovado, Kokoro `pm_santa`
em `pt-BR`, cenários ambientais aprovados, mixagem com ducking/limiter e
exportação FFmpeg horizontal e vertical. Não carrega pesos ou mídia privada no
repositório público.

## Produção executada

Foi produzida uma versão independente do Capítulo 12, `A floresta que escolhe`,
a partir dos limites do DOCX aprovado. O texto narrativo foi extraído sem
alteração; a verificação registrou 40 parágrafos, 689 palavras e o hash
`51460c39c44ed1ead7f7725a491f7d8befb5e52cf8d29e0cdd18ad8ff8ca7d3d`. A voz é
`pm_santa`/`pt-BR`, com 98 segmentos temporais medidos no WAV. Dados de palavra,
fonema e visema não foram inventados porque o provedor não os forneceu.

Os artefatos locais ficam sob o output escolhido pelo runtime:

```text
workspace/exports/cronicas-book1-capitulo12-cinematic-production-attempt-2/
```

Variantes entregues:

- `videos/cronicas-capitulo12-a-floresta-que-escolhe-horizontal.mp4` — 1920×1080;
- `videos/cronicas-capitulo12-a-floresta-que-escolhe-vertical.mp4` — 1080×1920.

Ambas têm 30 fps, H.264, AAC estéreo a 48 kHz e duração de aproximadamente
322,23 s. O relatório independente `reports/fab-prod-004-qa.json` confirmou
FFprobe, decodificação FFmpeg, ausência de eventos `blackdetect`, dimensões,
quadros, áudio, hash do texto, SRT e mixagem.

## Governança de qualidade

`technical_qa=PASS` confirma somente a integridade técnica do artefato. A
avaliação artística permanece `REVIEW_REQUIRED`. A música Alba foi preservada e
mixada com prioridade de voz, ducking e limiter; a confirmação de direitos
comerciais continua pendente antes de qualquer publicação. Nenhuma publicação,
deploy ou merge foi realizado, e os capítulos 01–11 não foram alterados.
