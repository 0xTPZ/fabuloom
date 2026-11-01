# Missão 038 — Audio Timeline & Sync Integrity

Data: 2026-11-01  
Base: `d02bc32`  
Branch: `release/fabuloom-alpha-preparation`  
Resultado: **PASS para a timeline de exportação corrigida**

## Causa-raiz

O exportador criava `voice.wav` com o concat demuxer, encadeando os WAVs sem respeitar `start_ms`, `end_ms` ou a duração do manifesto. Os intervalos de 180 ms entre segmentos eram removidos. Como o mux usava `-shortest`, a faixa resultante também podia cortar a duração temporal prevista. O vídeo ainda acumulava pequenas diferenças de arredondamento por cena.

## Correção

`frontend/server.py` agora materializa a faixa de voz a partir do manifesto:

- lê os timestamps medidos de cada segmento;
- escreve silêncio PCM somente nos intervalos necessários;
- preserva o silêncio final até `manifest.duration_ms`;
- rejeita segmentos fora de ordem ou WAVs com formato incompatível;
- mantém os WAVs originais sem alteração;
- codifica o AAC final explicitamente em 48 kHz mono;
- limita o mux à duração do manifesto, evitando excedente de vídeo.

Não foram inventados timestamps de palavras, fonemas ou visemas.

## Evidência temporal

Projeto descartável reutilizando os WAVs Kokoro autorizados da Missão 037, sem nova síntese: 60 segmentos, manifesto de `196.570 s`. Os gaps entre segmentos somam `10.620 s` em 59 intervalos, com máximo individual de `180 ms`. A faixa intermediária corrigida `voice.wav` foi medida em `196.570 s` a 24 kHz mono.

MP4 final gerado novamente pelo botão da interface em:

`C:\Temp\fabuloom-alpha-037-audit\exports-038b\projects\project-c983655bb1b1\project-c983655bb1b1-1080p.mp4`

FFprobe:

- vídeo H.264, 1920×1080, 30 fps, 5.897 frames, `196.566667 s`;
- áudio AAC mono, 48 kHz, `196.570000 s`, 9.214 frames;
- duração do container: `196.570000 s`;
- tamanho: `4.812.045 bytes`.

A diferença entre áudio e vídeo é `0,003333 s` — uma fração de um frame a 30 fps e dentro da tolerância definida de 1 frame. `ffmpeg -v error -i ... -f null -` concluiu sem erro. Quadros do início, meio e fim foram extraídos para `C:\Temp\Fabuloom-alpha-038b-evidence-frames`.

## Testes

- Regressão unitária do builder PCM: gap de 100 ms e cauda preservados por contagem real de frames.
- Python: `46 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- `node --check frontend/src/studio-shell.mjs`: PASS.
- `git diff --check`: PASS.

## Limitações restantes

O arquivo final preserva a timeline de áudio e a duração do manifesto. A inspeção de palavras/fonemas/visemas continua indisponível por contrato do Kokoro usado pelo Studio; a sincronização validada é de segmentos, pausas e cenas, não fonética.

Nenhum vídeo ou modelo foi adicionado ao Git. `E:\Fabuloom\studio` permaneceu intacto. PR #33 continua Draft, sem merge ou release.
