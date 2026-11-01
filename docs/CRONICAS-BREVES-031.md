# Missão 031 — Crônicas Breves: episódios 002 e 003

Esta missão adiciona o pipeline independente dos pilotos propostos:

- `CB-002 — A Sombra que Olhava para o Sol`
- `CB-003 — A Luz do Último Viajante`

Os dois roteiros são reproduzidos exatamente a partir do briefing editorial recuperado do repositório privado. Eles continuam propostos, não canônicos e pendentes de aprovação artística.

## Estado dos episódios

### CB-002

O texto foi sintetizado com Kokoro `pm_santa` em português brasileiro e os artefatos de pré-produção foram preparados, mas o MP4 foi bloqueado porque a trilha obrigatória não foi encontrada em:

`E:\Fabuloom\workspace\inputs\music\book1\A Sombra que Olhava para o Sol.mp3`

Nenhuma música substituta foi usada. O episódio deve ser retomado somente quando o arquivo proprietário estiver disponível e sua origem/direitos comerciais forem confirmados.

### CB-003

O MP4 foi exportado com a trilha proprietária encontrada em:

`E:\Fabuloom\workspace\inputs\music\book1\A Luz do Último Viajante.mp3`

O resultado tem 52 segundos, 1080×1920, 30 FPS, H.264 e AAC estéreo. A música foi preservada sem alteração de velocidade ou tom, com ducking sidechain da voz e limiter. A aprovação artística e a confirmação dos direitos comerciais da faixa permanecem pendentes.

## Pipeline

O exemplo executável é:

`E:\Fabuloom\studio\examples\cronicas_breves_cb002_cb003_demo.py`

Ele reutiliza `NarratorAvatarRenderer`, Santa V5 da biblioteca oficial, captions baseadas nos segmentos medidos, RMS para a boca e placas ambientais verticais. Personagens Draft, pessoas, rostos e silhuetas são bloqueados nas cenas. Não há timestamps inventados de palavras, fonemas ou visemas.

Execução local, usando o ambiente Kokoro já existente:

```powershell
& 'G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe' `
  'E:\Fabuloom\studio\examples\cronicas_breves_cb002_cb003_demo.py' `
  --episode all --overwrite --port 8794 --capture-timeout 1800
```

As exportações ficam fora do Git em:

`E:\Fabuloom\workspace\exports\cronicas-breves\cb-002-a-sombra-que-olhava-para-o-sol\`

`E:\Fabuloom\workspace\exports\cronicas-breves\cb-003-a-luz-do-ultimo-viajante\`

## Evidências locais da execução

CB-003:

- MP4: `videos\fabuloom-cb-003-a-luz-do-ultimo-viajante.mp4`
- SRT: `timeline\cb-003-a-luz-do-ultimo-viajante.srt`
- Manifesto: `audio\narration-manifest.json`
- Prancha: `captures\storyboard-board.png`
- Relatório técnico: `reports\technical-report.md`
- Validação: `reports\validation.json`

Validações concluídas: FFprobe, decodificação FFmpeg, `blackdetect`, coerência de duração, sincronismo de SRT, área segura, presença do Santa e bloqueio de personagens Draft. A revisão humana do vídeo e a escuta crítica continuam sendo a etapa de aprovação.

As placas de ambiente foram geradas como conceitos originais para esta pré-produção. Nenhum asset de personagem foi gerado ou substituído por imagem sintética.
