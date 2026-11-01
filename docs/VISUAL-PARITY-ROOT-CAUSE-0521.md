# Visual Parity Root Cause 052.1

Data: 2026-11-01  
Base: `4d6d7e4`  
Resultado: **PARTIAL**

## Causa da duração insuficiente

O exportador usa a duração do manifesto de narração como duração efetiva do MP4 (`-t target_duration`). A Missão 052 fixava quatro cenas de 3000 ms, mas a narração real durou 6915 ms. Portanto, a timeline de cenas totalizava 12000 ms enquanto o vídeo terminava em 6915 ms. Isso não é alongamento silencioso do áudio: é a regra existente de sincronização audiovisual.

O teste 052.1 foi corrigido para, após a narração real, persistir cada duração de cena igual à duração do segmento correspondente do manifesto. Assim, todos os timestamps capturados pertencem ao intervalo efetivo do MP4.

## Auditoria de assets

O projeto de evidência usa quatro cenas persistidas em ordem. Cada cena mantém ID `scene-new-001` a `scene-new-004`, um caminho `projects/<id>/assets/asset-*.png`, câmera explícita e duração derivada do segmento. O mesmo caminho persistido é usado pelo Canvas (`/api/projects/<id>/asset/...`) e pelo exportador (`_project_dir(project_id) / scene.image`). A cena estática foi visualmente conferida contra o frame FFmpeg correspondente e não mostrou troca de asset.

Evidência detalhada, incluindo JSON do projeto, PNGs, MP4, logs e métricas: `C:\Users\User\AppData\Local\Temp\fabuloom-visual-052-RP0hCU`.

## Cena estática

Cinco pares válidos foram capturados para a cena estática, com início, 25%, 50%, 75% e último frame válido. O enquadramento Canvas e FFmpeg coincide visualmente. A comparação RGB bruta apresenta MAE/RMSE sensíveis à rasterização H.264 e às bordas antialiased; por isso não foi usada isoladamente para declarar falha geométrica.

## Movimentos

Zoom, pan horizontal e pan vertical também tiveram cinco timestamps válidos por cena no reteste. A matriz executada contém 20 pares (quatro movimentos × cinco pontos), todos dentro da duração do MP4 de evidência. As métricas brutas permanecem acima da tolerância em parte dos pontos e exigem uma métrica geométrica específica de marcadores antes de PASS.

## Proporções

Foram exercitadas imagens horizontal, vertical e quadrada no cenário de quatro cenas. A matriz completa exigida de 12 combinações independentes (60 pares) ainda não foi concluída; cobertura atual: 4 combinações de movimento/proporção, 20 pares válidos.

## Correções

- Adicionado `test:e2e:visual` com captura real do Canvas.
- Hook de captura restrito a loopback e ao mesmo `renderCinematicFrame` de produção.
- Durações do cenário agora seguem os segmentos reais do manifesto, sem modificar áudio ou o exportador.
- Fronteiras temporais usam `sceneStart + 1 ms` para evitar a diferença entre o limite inclusivo do Canvas e a troca de frame do concat FFmpeg.
- Nenhuma fórmula de câmera, narrador, asset autoral ou licença foi alterada.

## Testes

- `npm run test:e2e:visual`: executado; evidência real produzida; classificação PARTIAL.
- Python: 48 passed, 1 skipped.
- Node: 160 passed.
- E2E rápido e exportação pesada permanecem separados; a exportação 051.1 anterior passou.

## Limitações e decisão

O gate não pode ser PASS: a cobertura ainda não contém os 60 pares e as métricas RGB sem normalização geométrica produzem divergências grandes em alguns frames, embora a cena estática conferida tenha enquadramento coincidente. Não há defeito de câmera comprovado que justifique alterar o renderizador. A classificação correta é **PARTIAL**.
