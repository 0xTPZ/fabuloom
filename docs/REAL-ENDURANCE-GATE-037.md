# Missão 037 — Real Endurance Gate

Data: 2026-11-01  
Base: `79a3f16`  
Branch: `release/fabuloom-alpha-preparation`  
Classificação: **PARTIAL**

## Ambiente e orçamento

Workspace descartável: `C:\Temp\fabuloom-alpha-037-audit`  
Projeto: `project-c983655bb1b1` / `Endurance Gate 037`  
Armazenamento livre no início: aproximadamente 756,9 GB no volume E. Ao final, aproximadamente 746,7 GB. Artefatos do audit: 29,3 MB; exports: 19,8 MB.

O processo Kokoro atingiu aproximadamente 1,24 GB de working set observado. Não foram encerrados processos externos nem tocados caches ou worktrees de produção.

## Produção real

- Projeto e roteiro de 60 cenas criados pela interface.
- Botão `Gerar narração Santa` executou Kokoro real com `pm_santa`.
- Primeira síntese: 391,72 s; descartada como teste de duração incompatível com o alvo.
- Segunda síntese, com roteiro original mais curto: 196,57 s, 60 segmentos, executada pela interface.
- Exportação MP4 iniciada pelo botão da interface e concluída após correções de duração.
- A associação dos três PNGs próprios e dos movimentos foi feita via API local, pois o seletor de arquivos nativo não aceitou esta automação. Portanto, isso é evidência de pipeline local instrumentado, não PASS integral da UX de importação.
- Movimentos distribuídos: 15 estáticos, 15 zoom, 15 pan horizontal e 15 pan vertical.

## Resultado do MP4 final

Caminho: `C:\Temp\fabuloom-alpha-037-audit\exports\projects\project-c983655bb1b1\project-c983655bb1b1-1080p.mp4`

FFprobe:

- vídeo H.264, 1920×1080, 30 fps, 5.641 frames, 188,033 s;
- áudio AAC mono, 96 kHz, 186,000 s, 17.434 frames;
- tamanho: 4.536.011 bytes.

`ffmpeg -v error -i ... -f null -` concluiu sem erro. Quadros de início, meio e fim foram extraídos para `evidence-frames-final` e inspecionados. O MP4 é real, tem mais de 180 s e decodifica integralmente.

## Divergência encontrada

O manifesto Kokoro mede 196,57 s porque contém intervalos temporais entre segmentos. O pipeline atual concatena os WAVs sem esses silêncios e o mux final produziu 186,00 s de áudio e 188,03 s de vídeo. Assim, há uma diferença aproximada de 2,03 s no arquivo final e não é correto declarar sincronização perfeita de toda a linha do tempo.

Esse comportamento é um limite real do pipeline atual, não foi mascarado com áudio silencioso ou MP4 prévio. A exportação curta anterior também foi repetida após a produção longa; a aplicação permaneceu íntegra e reabriu 60 cenas no navegador.

## Regressão

- Python: `45 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- `node --check frontend/src/studio-shell.mjs`: PASS.
- `git diff --check`: PASS.

## Decisão

**PARTIAL**, não PASS: o Fabuloom concluiu uma produção real de 60 cenas com 188 s de vídeo H.264/AAC, Kokoro `pm_santa`, quatro movimentos e decodificação completa. Permanecem duas limitações comprovadas: importação de arquivos não foi concluída exclusivamente pela UX automatizada e o pipeline concatena áudio sem preservar os gaps do manifesto, gerando diferença final de aproximadamente 2 s.

Nenhum vídeo ou modelo foi adicionado ao Git. `E:\Fabuloom\studio` permaneceu intacto. PR #33 continua Draft, sem merge ou release.
