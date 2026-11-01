# Alpha Visual Diagnostics & Decision 054

Data: 2026-11-01  
Base: `7ecfd0b`  
Resultado visual: **PARTIAL**  
Recomendação source-only: **GO_WITH_LIMITATIONS**

## Diagnóstico

Foram reutilizados os 60 pares reais da evidência `C:\Users\User\AppData\Local\Temp\fabuloom-visual-052-wU4bhc`. A causa temporal foi identificada: o exportador usa a duração do manifesto (`-t target_duration`), enquanto o cenário original fixava durações independentes. O cenário passou a alinhar durações às faixas reais do manifesto.

Também foi identificada uma limitação de instrumentação: após a persistência via UI, uma captura podia ocorrer antes de o `currentProject` recarregado refletir as novas durações, fazendo o Canvas permanecer na cena anterior enquanto o FFmpeg já estava na cena seguinte. O hook foi reforçado para aguardar o projeto e os assets reais; uma tentativa posterior de 12 cenas falhou na consulta prematura do projeto, portanto não é usada como evidência de sucesso.

## Resultado quantitativo

- Pares capturados na evidência válida: 60.
- Marcadores amarelos com correspondência confiável: 5 pares na execução registrada; demais casos foram inconclusivos por crop/ausência de marcador.
- Maior deslocamento observado entre marcadores confiáveis: aproximadamente 3 px.
- Maior erro de escala observado entre marcadores confiáveis: aproximadamente 2,67%.
- Diferenças RGB: variam de aproximadamente 0,001 a valores superiores a 0,7 em cenários afetados; não são classificadas automaticamente como erro geométrico.
- Marcador vermelho: frequentemente cortado; medição inconclusiva quando ausente.

## Classificação das diferenças

- **TIMING/INSTRUMENTATION:** captura antes do reload completo do projeto, reproduzida no harness.
- **RASTERIZATION/COMPRESSION:** MAE/RMSE e `changed_ratio` elevados em imagens com linhas finas, escalas e H.264; não provam erro de câmera.
- **GEOMETRY:** nenhum defeito geométrico global foi comprovado com confiança suficiente para alterar as fórmulas.
- **ASSET:** a auditoria não mostrou troca persistida de asset no caso estático conferido; os caminhos Canvas/FFmpeg apontam para o mesmo arquivo do projeto.
- **INCONCLUSIVE:** maioria dos casos sem marcador visível confiável após crop.

## Gate visual

**PARTIAL.** Existem 60 capturas reais, mas a instrumentação e a cobertura confiável de marcadores não sustentam PASS. Não há evidência suficiente para reprovar a geometria do produto por changed_ratio isolado.

## Decisão Alpha source-only

**GO_WITH_LIMITATIONS.** A exportação E2E 051.1 foi aprovada com H.264/AAC e FFprobe/FFmpeg. Os riscos visuais conhecidos são documentados: a prévia deve ser tratada como referência aproximada em condições de crop/compressão, e o gate pixel-a-pixel completo permanece pendente. Permanecem fora desta decisão os bloqueios de distribuição empacotada, licenças de assets, dependências externas e validação humana do diálogo nativo Windows já registrados nos relatórios anteriores.

Não foram alterados personagens, licenças, pipeline de áudio ou produção. PR #33 continua Draft; nenhum merge ou release foi executado.

## Testes

Python: 48 passed, 1 skipped. Node: 160 passed. E2E exportação 051.1: PASS. E2E visual 053: 60 pares produzidos, PARTIAL.

Commit desta decisão: a ser registrado.
