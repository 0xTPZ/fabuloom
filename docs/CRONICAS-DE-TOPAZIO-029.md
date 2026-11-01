# Crônicas de Topázio — Livro 1, Capítulo 4

## Escopo

Missão 029 produz a versão cinematográfica do Capítulo 4, **O círculo dos
ausentes**, preservando as saídas das Missões 026–028 e usando o mesmo limite
real do DOCX. O título está no parágrafo 107; a narrativa ocupa os parágrafos
108–178; o parágrafo 179 é o separador; e o próximo título está no parágrafo
180. São 71 parágrafos narrativos, 1.026 palavras e 5.913 caracteres. O
SHA-256 do texto narrativo normalizado é
`8b8b293aa0ef990d70607e7d69f71513a273d609140d4976e0fe136f1ffdcd48`.

## Política visual e identidade

Santa V5 é a única identidade aprovada utilizada pela produção, com o ID
`santa-v5-base`. A biblioteca oficial `santa-library-topazioverse-v1` é
reutilizada sem regenerar a arte do personagem; seu SHA-256 é
`1e38477edd9e62d5aa5ae7d63d4784f3c5fd5b65a6486fbc1b187c0933395770`.
As cenas da história são `environment_only`, e o render de personagens em
estado `DRAFT` permanece bloqueado por `approved_only`/`draft_rendering:
blocked`.

Foram preparadas 20 cenas ambientais, usando placas originais de cidade,
templo, cristal, gelo, fogo, água, observatório, mapa e tempestade. As placas
foram geradas com imagegen apenas para ambientes e objetos; nenhum asset de
personagem foi gerado ou substituído. Elas são conceitos de produção e exigem
aprovação artística humana antes de qualquer promoção.

## Áudio e tempo

- Provedor: Kokoro `hexgrad/Kokoro-82M`.
- Voz: `pm_santa`, idioma `pt-BR`.
- 153 segmentos WAV medidos; o manifesto registra 482.445 ms.
- Captura e legendas usam os intervalos reais dos WAVs.
- Timestamps de palavras, fonemas e visemas não estão disponíveis; a boca usa
  somente o envelope RMS em tempo absoluto.
- Música: `workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3`,
  com ducking voz→música, compressão/limiter no mix reutilizado e confirmação
  de direitos comerciais Suno ainda pendente.

## Renderização e saídas

O runner `examples/topazio_book1_chapter4_cronicas_demo.py` lê o DOCX,
reutiliza o pipeline determinístico do Capítulo 3, captura o Canvas em
1920×1080/30 FPS, compõe o medalhão persistente do Santa e codifica H.264/AAC
com FFmpeg. Os artefatos completos ficam fora do Git:

`workspace/exports/topazio-book1-capitulo4-cronicas/`

Saídas principais:

- MP4: `videos/fabuloom-cronicas-de-topazio-livro1-capitulo4.mp4`.
- Prancha: `captures/chapter4-frames.png`.
- SRT e timeline: `timeline/`.
- Relatórios: `reports/`.
- Metadados de YouTube, sem publicação automática:
  `metadata/youtube-metadata.json`.

## Reprodução e aprovação

```powershell
$env:PYTHONPATH = "src;examples"
& "G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe" `
  examples\topazio_book1_chapter4_cronicas_demo.py --overwrite --port 8781
```

O runner exige `santa-v5-base` aprovado, registra o texto fonte e bloqueia
identidades DRAFT. A produção não faz merge, não publica no YouTube e não
constitui aprovação artística: a revisão humana do vídeo, das placas e da
mixagem continua obrigatória.
