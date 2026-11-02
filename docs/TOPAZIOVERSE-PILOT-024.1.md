# Topazioverse — primeiro piloto cinematográfico

Esta entrega adiciona o pipeline reproduzível do piloto inicial de **O Despertar dos Cristais**, sem substituir o Narrator Mode nem alterar os packs de Dora, Alex ou Santa V5.

## Escopo

- Fonte: `workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx`.
- Intervalo usado: parágrafos do documento `3..11`, preservando o texto original.
- Voz: Kokoro `pm_santa`, português brasileiro.
- Temporização: duração real dos WAVs e pausas de composição; palavras, fonemas e visemas não são inventados.
- Cenas: cinco imagens originais coerentes, com zoom, aproximação, panorâmica, brilho e partículas determinísticas.
- Narrador: Santa V5 somente na abertura e no encerramento.
- Saída: 1920×1080, 30 FPS, H.264/yuv420p e AAC.

## Reprodução local

Com o ambiente local do projeto e os modelos Kokoro já existentes:

```powershell
$env:PYTHONPATH = 'E:\Fabuloom\studio\src'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
python E:\Fabuloom\studio\examples\topazioverse_book1_pilot_demo.py --overwrite
```

O comando grava somente em `E:\Fabuloom\workspace\exports\topazioverse-book1-episode1-pilot\`. `--reuse-manifest` e `--reuse-capture` evitam nova síntese ou nova captura quando os artefatos locais já foram validados.

## Assets e direitos

As cinco imagens foram produzidas como arte original para o piloto com a ferramenta de geração visual disponível no ambiente Codex e copiadas para o workspace; não são dependências públicas nem imagens de terceiros. A música `Apprehension.mp3` é a faixa já auditada do TopazioReader, atribuída a Kevin MacLeod sob CC BY 4.0. A chuva é uma cópia local do arquivo auditado como CC0. Os pesos Kokoro e áudios gerados permanecem fora do Git.

## Validação

O relatório gerado em `workspace/exports/topazioverse-book1-episode1-pilot/reports/technical-report.md` registra duração, codecs, hash do trecho-fonte, limites das cenas e origem temporal. A aprovação artística do piloto continua sendo uma revisão humana; testes técnicos bem-sucedidos não a substituem.

Para manter o custo de captura local viável, o Santa é capturado em todos os 30 FPS durante a abertura e o encerramento; nas cenas sem avatar, quadros intermediários são materializados por repetição determinística antes do FFmpeg. A política detalhada fica em `workspace/exports/topazioverse-book1-episode1-pilot/reports/capture-policy.md`.
