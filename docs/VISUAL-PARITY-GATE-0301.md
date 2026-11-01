# Missão 030.1 — Visual Parity Gate

Data: 2026-11-01  
Base: `bf4c85e`  
Resultado final: **PARTIAL**

## Divergências confirmadas e correções

1. O pan do Canvas terminava em 60% da cena (`progress / 0.6`), enquanto o FFmpeg usa `on/(30*20)`. Corrigido para a trajetória temporal de 20 s, usando `localMs / 20000`.
2. O Canvas usava `cover` também para `static`; o FFmpeg usa `scale ... decrease + pad`. Corrigido para `contain` em estático e `cover` somente nos movimentos.

O contrato agora é testado em `frontend/src/cinematic-composition.mjs`. Projetos existentes continuam compatíveis porque os campos persistidos não mudaram.

## Projeto de evidência

Artefatos isolados, fora do Git, em `workspace/audit-0301/`:

- `marker-wide.svg`, `marker-tall.svg`, `marker-square.svg`: referências geométricas originais.
- `visual-parity-video.mp4`: MP4 H.264 real com quatro cenas de 3 s: static, zoom, pan-horizontal e pan-vertical.
- `frames/scene-XX-t*.png`: quadros extraídos em 0, 750, 1500, 2250 e 2966 ms; no ponto final foi usado o último frame válido da cena.

FFprobe do vídeo: 1920×1080, 360 frames, 12.000000 s, 30 fps efetivos.

## Comparação matemática

| Movimento | Contrato FFmpeg | Canvas após correção | Resultado |
|---|---|---|---|
| Static 16:9 | contain + pad | contain + centralização | PASS geométrico |
| Static vertical/quadrado | contain + pad | contain + centralização | PASS geométrico |
| Zoom | cover, zoom incremental 0.0015/frame, limite 1.12 | mesma taxa/limite, centrado | PASS dentro da tolerância geométrica |
| Pan horizontal | cover, zoom 1.08, deslocamento em 20 s | cover, zoom 1.08, `localMs/20000` | PASS geométrico |
| Pan vertical | cover, zoom 1.08, deslocamento em 20 s | cover, zoom 1.08, `localMs/20000` | PASS geométrico |

Tolerância definida antes da classificação: proporção 16:9 idêntica, direção e ordem corretas; erro de enquadramento ≤1 px lógico após normalização. Diferenças de cor H.264 não são critério. O vídeo real e os quadros FFmpeg foram produzidos; a captura automatizada dos pixels do Canvas em cada um dos 20 pontos não foi possível com a superfície CUA disponível nesta execução. Portanto, não é declarado PASS absoluto.

## Navegador e regressão

O navegador confirmou os modos Cinematográfico/Narrator Mode, reprodução, pausa e canvas sem imagem demonstrativa. O Narrator Mode Santa V5 permaneceu funcional. A alteração de cena e persistência continuam cobertas pelo fluxo anterior.

Testes: **4 testes do contrato passaram**, `node --check` passou, e a suíte Python anterior permanece em **39 passed, 1 skipped**. A suíte Node existente também passou na rodada anterior; deve ser repetida no CI antes de retirar o Draft.

Conclusão: a origem das duas divergências foi corrigida e a comparação matemática é PASS para os quatro movimentos. A aceitação da missão permanece **PARTIAL** por falta de captura pixel-a-pixel do Canvas nos 20 instantes; não há evidência suficiente para declarar paridade visual completa.
