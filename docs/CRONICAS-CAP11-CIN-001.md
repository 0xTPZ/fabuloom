# Crônicas de Topázio — Capítulo 11 cinematográfico

Esta implementação produz o capítulo 11, **O eco que não morre**, a partir do
manuscrito integral e dos contratos já usados pelo Fabuloom.

## Pipeline

1. O DOCX é lido por faixa de headings, preservando o texto aprovado.
2. A abertura e a despedida são sintetizadas com Kokoro `pm_santa` em pt-BR.
3. Os segmentos medidos são unidos ao capítulo sem inventar timestamps de
   palavras, fonemas ou visemas.
4. A narrativa é capturada pelo `NarratorAvatarRenderer` real em Canvas, com
   Santa V5 no medalhão, RMS para a boca e placas ambientais aprovadas.
5. `Alba Quando a Luz Rasga o Céu.mp3` é mantida na velocidade e no tom
   originais, com ducking sidechain para a voz, fades e limiter.
6. A vinheta e os clipes cinematográficos são conformados sem áudio (`-an`) e
   concatenados antes da muxagem da mixagem final.

O runner é [cronicas_cap11_cin_001.py](../examples/cronicas_cap11_cin_001.py)
e a página de captura é
[capture-cronicas-cap11-narrative.html](../frontend/capture-cronicas-cap11-narrative.html).
Ambos suportam retomada por captura completa e escrevem o estado em
`BATCH-STATUS.json` no diretório de exportação.

## Saídas da produção

Os artefatos gerados ficam fora do Git, em
`E:\Fabuloom\workspace\exports\cronicas-book1-capitulo11-cinematic-v1`:

- `videos/cronicas-capitulo11-o-eco-que-nao-morre-horizontal.mp4` — 1920×1080,
  30 fps, H.264/AAC.
- `videos/cronicas-capitulo11-o-eco-que-nao-morre-vertical.mp4` — 1080×1920,
  30 fps, H.264/AAC.
- `manifest/`, `timelines/`, `subtitles/`, `boards/`, `reports/` e
  `assets-index/` — evidências, contratos, pranchas e validações.

O áudio dos MP4s cinematográficos fornecidos é sempre descartado. A
sincronização labial dos clipes cinematográficos não é declarada como precisa;
apenas a narrativa com Santa V5 usa o RMS disponível no motor atual.

## Direitos e aprovação

A música Alba é preservada como arquivo fornecido pelo proprietário. Direitos
comerciais da faixa e autorização de distribuição dos clipes cinematográficos
continuam pendentes de confirmação. A aprovação artística humana permanece
necessária; `QA_OK` significa apenas que as validações técnicas passaram.

