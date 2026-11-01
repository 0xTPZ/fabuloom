# Crônicas Breves — CB-001: O Quarto Eco

Mission 030 produz o primeiro piloto vertical da série **Lendas e Segredos de
Topázio**. O texto foi recuperado do briefing editorial privado
`editorial/cronicas-breves/CB-001-O-QUARTO-ECO.md` e usado integralmente, sem
diálogos inventados.

## Estado editorial

O briefing continua marcado como **ROTEIRO PROPOSTO**. O episódio é tratado
como folclore proposto, não como fato canônico. A direção mantém “dizem que” e
“ninguém sabe se aconteceu”, não representa Thaurion ou visitantes e bloqueia
personagens Draft. A aprovação artística e canônica pertence ao proprietário.

## Pipeline

O runner reproduz a sequência texto → Kokoro → segmentos WAV medidos →
manifesto/SRT → captura Canvas → FFmpeg. A captura usa
`NarratorAvatarRenderer`, Santa V5 e a biblioteca oficial
`santa-library-topazioverse-v1`; as cenas da história são placas de ambiente e
objetos, sem personagens embutidos.

```powershell
& 'G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe' `
  'E:\Fabuloom\studio\examples\cronicas_breves_cb001_quarto_eco_demo.py' `
  --overwrite --port 8793
```

Para reusar a narração já sintetizada e recapturar somente a composição:

```powershell
& 'G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe' `
  'E:\Fabuloom\studio\examples\cronicas_breves_cb001_quarto_eco_demo.py' `
  --reuse-manifest --overwrite --port 8793
```

O áudio de boca é envelope RMS do PCM real. Timestamps de palavras, fonemas e
visemas continuam indisponíveis e não são inventados.

## Música e mixagem

A fonte original é preservada em `audio/source-music.mp3` e também permanece
intacta em `workspace/inputs/music/book1/Os Ecos que Nunca Morrem.mp3`.
O pipeline não altera pitch ou velocidade. A voz é convertida para estéreo e
comanda `sidechaincompress` sobre a música; a música ganha presença nos
intervalos e recebe uma redução suave adicional na janela do quarto eco, com
limiter final e fade cinematográfico.

Origem declarada: Suno. A confirmação dos direitos comerciais continua
pendente antes de qualquer publicação.

## Artefatos locais

Os artefatos gerados ficam fora do Git em:

`E:\Fabuloom\workspace\exports\cronicas-breves\cb-001-o-quarto-eco\`

- `videos/fabuloom-cb001-o-quarto-eco.mp4`
- `timeline/cb-001-o-quarto-eco.srt`
- `audio/narration-manifest.json`
- `timeline/storyboard-used.json`
- `captures/cb001-storyboard-board.png`
- `metadata/shorts-tiktok-metadata.json`
- `reports/technical-report.json`

As seis placas ambientais foram criadas como conceitos originais locais com a
ferramenta de geração de imagens disponível no ambiente; não foram usados
assets de personagens, e a avaliação artística humana continua obrigatória.

## Validação

O resultado produzido nesta missão foi validado com FFprobe, decodificação
FFmpeg, `blackdetect`, contagem de segmentos/SRT e inspeção visual da prancha.
O MP4 é 1080×1920, 9:16, 30 FPS, H.264/yuv420p, AAC estéreo a 48 kHz, com
59,48 s medidos a partir do áudio Kokoro.
