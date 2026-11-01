# Visual Parity Gate 052

Data: 2026-11-01  
Base: `d7b3182`  
Resultado: **PARTIAL**

## Método

Foi criado `tools/e2e/visual.mjs`, executado por `npm run test:e2e:visual`. O teste usa Playwright contra o `studio.html`, cria um projeto local, importa quatro imagens PNG derivadas dos marcadores originais do pacote `workspace/audit-0301`, configura quatro cenas (`static`, `zoom`, `pan-horizontal`, `pan-vertical`), gera narração real pelo botão da interface e exporta pelo botão real.

O único mecanismo adicional no Studio é `window.__fabuloomVisualCapture`, disponível somente em loopback (`localhost`/`127.0.0.1`). Ele chama o mesmo `renderCinematicFrame` usado pela prévia e retorna o PNG real do Canvas após o decode da imagem.

## Timestamps

Foram solicitados 0, 750, 1500, 2250 e 2966 ms por cena, correspondendo a 0%, 25%, 50%, 75% e último frame válido de uma cena de 3 s a 30 fps. Nas fronteiras entre cenas foi usado `sceneStart + 1 ms`, pois o Canvas usa limite inclusivo e o FFmpeg concatena a cena seguinte no frame de fronteira.

## Evidência

Última execução: `C:\Users\User\AppData\Local\Temp\fabuloom-visual-052-uNwVug`.

- PNGs Canvas: `canvas/`.
- PNGs FFmpeg: `ffmpeg-scene-*.png`.
- Métricas: `metrics.json`.
- Relatório HTML: `report.html`.
- MP4 real: `workspace\workspace\exports\projects\project-72914380681d\project-72914380681d-1080p.mp4`.
- FFprobe: 1920×1080, 30 fps, H.264 + AAC, 6.915 s.

## Métricas e tolerância

As comparações usam RGB bruto após decodificação FFmpeg, com MAE, RMSE e proporção de pixels com diferença absoluta maior que 12. A tolerância operacional provisória é `changed_ratio < 0.08`, além de resolução e dimensões iguais. A compressão H.264 não é tratada como divergência geométrica por si só.

O cenário inicial mostrou diferenças baixas em alguns pontos (`changed_ratio` aproximadamente 0.0009–0.054), compatíveis com rasterização/compressão. Outros pontos mostraram diferenças relevantes, de aproximadamente 0.16–0.70, incompatíveis com mera compressão.

## Resultado por movimento

| Movimento | Resultado | Observação |
|---|---|---|
| Estático | PARTIAL | Alguns frames próximos; ainda há associação Canvas/FFmpeg divergente no pacote completo. |
| Zoom | PARTIAL | Captura real realizada, mas métricas acima da tolerância em parte dos frames. |
| Pan horizontal | PENDENTE | Parte dos frames ficou fora da duração do MP4 de 6.915 s. |
| Pan vertical | PENDENTE | Parte dos frames ficou fora da duração do MP4 de 6.915 s. |

## Diagnóstico

O teste confirmou que é possível capturar o Canvas real deterministically e extrair frames reais do MP4. A execução também revelou que a duração da narração (`6.915 s`) trunca um projeto com quatro cenas de 3 s; assim, os pontos das cenas posteriores não têm correspondentes válidos no vídeo final. Além disso, a associação visual de alguns assets do Canvas não coincidiu com o asset esperado pelo manifesto persistido, exigindo investigação adicional do carregamento/seleção de cena antes de qualquer correção no contrato de câmera.

Não foi feita alteração arbitrária no renderizador nem no pipeline FFmpeg. Não há base para declarar PASS.

## Regressão

O hook é loopback-only e não altera controles de produção. O harness visual é separado do E2E rápido e do export pesado. A compatibilidade Santa V5 não foi modificada. As suítes Python/Node existentes permanecem a executar na base anterior; esta missão não altera contratos de áudio ou assets autorais.

## Limitações

O gate permanece **PARTIAL** até que o cenário tenha timeline de vídeo com duração suficiente para os 20 pontos e a associação Canvas/manifesto seja comprovada nos quatro movimentos. Nenhum merge, release ou alteração em `E:\Fabuloom\studio` foi realizado.
