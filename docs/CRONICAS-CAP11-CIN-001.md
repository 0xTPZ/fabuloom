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

## Revisão R2 — transições editoriais

A revisão R2 preserva integralmente a produção R1, os WAVs Kokoro medidos e a
captura narrativa existente. A alteração é limitada à composição das
transições entre blocos:

- pausa de 1.000 ms entre a apresentação cinematográfica e a narrativa;
- pausa de 1.200 ms entre a narrativa e a despedida cinematográfica;
- dissolução de página/cristal com partículas determinísticas, sem tela preta;
- Alba continua audível nas pausas, com a mesma velocidade e o mesmo tom;
- efeitos de transição discretos, mixados abaixo da voz e da música.

O runner da revisão é
[cronicas_cap11_cin_001_r2.py](../examples/cronicas_cap11_cin_001_r2.py).
Ele reutiliza os componentes R1 e somente insere os intervalos editoriais,
os quadros de transição e a nova mixagem. Não há ressíntese, recaptura do
Canvas ou alteração nos capítulos 01–10.

Os artefatos R2 ficam fora do Git em
`E:\Fabuloom\workspace\exports\cronicas-book1-capitulo11-cinematic-r2`.
Os arquivos finais são `videos/cronicas-capitulo11-o-eco-que-nao-morre-
horizontal-r2.mp4` e `videos/cronicas-capitulo11-o-eco-que-nao-morre-
vertical-r2.mp4`, acompanhados de manifestos, SRT, timeline, pranchas e
relatório técnico. A duração do manifesto é 298.280 ms; os contêineres
medidos pelo FFprobe têm aproximadamente 298,333 s.

O QA técnico R2 passou: H.264/AAC, 30 fps, 1920×1080 e 1080×1920, áudio
estéreo a 48 kHz, decodificação FFmpeg concluída e `blackdetect` sem eventos.
A inspeção das pranchas confirma a dissolução visual nos dois formatos. A
escuta humana e a aprovação artística continuam pendentes, assim como a
confirmação dos direitos comerciais da música e dos clipes fornecidos.

