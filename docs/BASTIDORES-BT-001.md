# BT-001 — Por Trás das Crônicas de Topázio

BT-001 é um piloto horizontal de bastidores que conecta o Livro I, o Fabuloom Studio e o Atlas Literário. A produção usa o roteiro editorial aprovado em `fabuloom-internal/editorial/bastidores/BT-001-POR-TRAS-DAS-CRONICAS.md` sem acrescentar diálogos.

## Pipeline

- `examples/bastidores_bt001_demo.py` sintetiza a narração com Kokoro `pm_santa` em `pt-BR`, grava o manifesto medido e gera o SRT por segmentos.
- `frontend/capture-bastidores-bt001.html` captura frames determinísticos do Canvas com o `NarratorAvatarRenderer` oficial do Santa V5.
- As telas do portal são capturas reais verificadas em home → biblioteca → Livro I → capítulo 1 → ferramentas de leitura em Sépia.
- As telas do Fabuloom e as pranchas de CB-001/002/003 são reutilizadas como fontes locais autenticadas; os capítulos anteriores não são alterados.
- A música original fornecida pelo proprietário é preservada como stem e recebe ducking por sidechain durante a narração. Direitos comerciais devem ser confirmados antes de qualquer publicação.

## Execução local

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\examples;E:\Fabuloom\studio\src"
& "G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe" `
  "E:\Fabuloom\studio\examples\bastidores_bt001_demo.py" `
  --recapture
```

O runner escreve somente em `workspace/exports/bastidores/bt-001-por-tras-das-cronicas/`. O manifesto registra duração real da fala; palavras, fonemas e visemas são marcados como indisponíveis. O CTA possui uma cauda editorial de 7 segundos após a despedida falada para manter a URL legível.

## Entregas locais

- `videos/fabuloom-bt-001-bastidores-topazio.mp4`
- `fabuloom-bt-001-bastidores-topazio.srt`
- `narration-manifest.json` e `timeline/bt-001-por-tras-das-cronicas.json`
- `storyboard-used.json` e `captures/bt-001-capture-board.png`
- `reports/technical-report.*`, `source-capture-report.md`, `music-report.md` e `youtube-metadata.json`

O MP4 não é publicado automaticamente. A aprovação artística e a confirmação dos direitos comerciais da música continuam pendentes do proprietário.
