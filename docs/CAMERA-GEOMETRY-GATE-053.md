# Camera Geometry Gate 053

Data: 2026-11-01  
Base: `74cce8e`  
Resultado: **PARTIAL**

## Cobertura

O `npm run test:e2e:visual` foi expandido para 12 cenas: quatro movimentos (`static`, `zoom`, `pan-horizontal`, `pan-vertical`) combinados com três proporções (horizontal, vertical e quadrada). Cada cena possui cinco timestamps derivados da duração real do segmento: 0%, 25%, 50%, 75% e o último frame válido a 30 fps. Resultado: **60 pares Canvas × FFmpeg válidos**.

Evidência: `C:\Users\User\AppData\Local\Temp\fabuloom-visual-052-wU4bhc`.

- `metrics.json`: JSON completo com timestamps, MAE, RMSE, changed_ratio e geometria.
- `canvas/`: PNGs reais capturados pelo Canvas do Studio.
- `ffmpeg-scene-*-p*.png`: frames reais extraídos do MP4.
- `board-scene-*-p*.png`: pranchas Canvas | FFmpeg | diferença.
- MP4 final e logs do servidor isolado.

## Causa temporal corrigida no cenário

O exportador limita o MP4 à duração do manifesto. O teste deixou de assumir quatro cenas fixas de 3 s e passou a persistir cada duração conforme o segmento real de narração. Nenhum áudio foi alongado e nenhuma regra de produção foi alterada.

## Auditoria de assets

Cada cena mantém ID persistido, ordem, caminho `assets/asset-*.png`, câmera e duração. O Canvas acessa o asset pelo endpoint do projeto; o FFmpeg acessa o mesmo arquivo pelo caminho persistido. O teste registra SHA-256 dos três assets de proporção usados. Não foi observada troca arbitrária de asset no caso estático conferido.

## Geometria versus RGB

O teste detecta o marcador amarelo por cor e calcula centro, área, deslocamento e razão de escala. Marcadores ausentes/cortados retornam `inconclusive` e confiança zero; não são tratados como correspondência. O marcador vermelho é frequentemente cortado por enquadramento e permanece inconclusivo em parte da matriz.

Tolerâncias preliminares: deslocamento geométrico ≤ 1 px lógico, razão de escala ≤ 1%, confiança ≥ 0,5. MAE/RMSE e `changed_ratio` não são usados sozinhos para reprovar geometria, pois H.264, antialiasing e conversão de cor alteram pixels.

## Resultado

Os 60 pares foram capturados e extraídos com timestamps válidos. A matriz ainda é **PARTIAL** porque a comparação RGB permanece alta em vários frames e a identificação de marcadores não é confiável quando há crop. Não há evidência suficiente para declarar que toda a geometria Canvas × FFmpeg está dentro das tolerâncias.

Não foi alterada nenhuma fórmula de câmera, renderizador de personagem, Kokoro, licença ou asset autoral. A causa temporal foi corrigida somente no cenário de teste.

## Regressão

- Python: 48 passed, 1 skipped.
- Node: 160 passed.
- E2E visual: 60 pares válidos, classificação PARTIAL.
- E2E de exportação audiovisual 051.1 anterior: PASS.

Commit final: a ser registrado após esta atualização. PR #33 permanece Draft; nenhum merge ou release foi realizado.
