# TopazioVerse — trailer oficial do canal (Missão 024.4)

Status: renderização local concluída, aguardando revisão audiovisual e aprovação artística humana.

## Entregas

O pipeline produz dois formatos a partir do mesmo contrato de timeline e do
mesmo `NarratorAvatarRenderer` real usado no Narrator Mode:

- `E:\Fabuloom\workspace\exports\topazioverse-channel-trailer\topazioverse-channel-trailer-1080p.mp4`
- `E:\Fabuloom\workspace\exports\topazioverse-channel-trailer\topazioverse-channel-trailer-short-vertical.mp4`

O trailer horizontal usa o roteiro completo fornecido na missão e tem duração
medida de 96,835 s. O vertical é um teaser condensado do mesmo posicionamento,
com narração independente de 41,815 s — não é um simples recorte do trailer.

## Pipeline

```text
roteiro pt-BR
  -> Kokoro pm_santa
  -> manifestos com segmentos medidos
  -> mix de voz + trilha procedural local
  -> Canvas/NarratorAvatarRenderer + RMS
  -> JPEGs determinísticos a 15 fps
  -> materialização a 30 fps
  -> FFmpeg H.264/AAC
```

Os tempos de cena e legendas vêm dos limites reais dos segmentos WAV. A boca
usa o envelope RMS do áudio. Timestamps de palavras, fonemas e visemas não
estão disponíveis e não são inventados.

## Conteúdo e autenticidade

| Elemento | Origem / tratamento |
| --- | --- |
| Santa | Santa V5 pelo caminho real do Narrator Mode; permanece visível durante todo o programa |
| Voz | Kokoro `pm_santa`, `pt-BR` |
| Cenas de fantasia | Cinco imagens locais autorizadas/reutilizadas do piloto do Livro 1 |
| Fabuloom Studio | Captura real local preservada para demonstração |
| Narrator Mode | Captura real local preservada para demonstração |
| Música | Composição procedural local já existente, sem samples comerciais registrados |
| Jogos, laboratório, comunidade e playlists | Painéis conceituais identificados em tela; não representam produtos operacionais |
| Blockchain/eletrônica | Não há demonstração operacional nem alegação de produto concluído |

As imagens, áudio e vídeos gerados ficam em `workspace/exports` e não fazem
parte do repositório público. A política final de publicação da trilha e das
imagens deve ser confirmada antes de qualquer distribuição externa.

## Arquivos de controle

- `examples/topazioverse_channel_trailer_demo.py`: pipeline reproduzível.
- `frontend/capture-topazioverse-channel-trailer.html`: captura Canvas usando o renderizador real.
- `workspace/exports/topazioverse-channel-trailer/manifest.json`: manifesto horizontal.
- `workspace/exports/topazioverse-channel-trailer/vertical-manifest.json`: manifesto vertical.
- `workspace/exports/topazioverse-channel-trailer/timeline/`: timelines, SRTs e roteiros.
- `workspace/exports/topazioverse-channel-trailer/assets.json`: proveniência e classificação dos visuais.
- `workspace/exports/topazioverse-channel-trailer/captures/`: pranchas horizontal e vertical.
- `workspace/exports/topazioverse-channel-trailer/reports/`: relatório técnico e evidência do resultado.

Execução local, com os modelos disponíveis no ambiente Kokoro:

```powershell
$env:PYTHONPATH = 'E:\Fabuloom\studio\src'
& 'G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe' `
  'E:\Fabuloom\studio\examples\topazioverse_channel_trailer_demo.py' `
  --overwrite --capture-timeout 1200
```

Para reutilizar a captura determinística existente e apenas recodificar os
artefatos derivados, use `--reuse-capture`. A opção `--overwrite` força nova
síntese e sobrescrita dos derivados no workspace de exportação.

## Validação

- Python: `52 passed, 1 skipped, 22 subtests passed`.
- Frontend: `143 passed`.
- Trailer: `1920x1080`, 30 fps, H.264, AAC estéreo 48 kHz, 96,835 s.
- Teaser: `1080x1920`, 30 fps, H.264, AAC estéreo 48 kHz, 41,815 s.
- FFmpeg decodificou ambos sem erro.
- `blackdetect` não encontrou intervalos pretos contínuos de 0,20 s ou mais.
- A inspeção visual das pranchas confirma a presença do Santa, das cenas e da
  diferenciação entre capturas reais e painéis conceituais.

O resultado ainda requer revisão humana do áudio, legibilidade em dispositivo
móvel, continuidade das transições e aprovação artística antes de publicação.
