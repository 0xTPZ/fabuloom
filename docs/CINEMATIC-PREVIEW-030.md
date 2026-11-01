# Missão 030 — Cinematic Preview Parity

Data: 2026-11-01  
Commit base: `8c663a8`  
Status: **PARTIAL aprovado para alpha**

## Diagnóstico

Antes desta missão, `studio-shell.mjs` sempre inicializava `NarratorSceneRenderer` com a arte fixa do escritório. O editor e `server.py` persistiam `image`, `duration_ms` e `camera`, mas somente o exportador FFmpeg aplicava esses dados. Isso produzia a divergência P1 registrada em `docs/UX-AUDIT-029.md`.

## Arquitetura adotada

Foi adicionado `frontend/src/cinematic-composition.mjs`, com a transformação pura de enquadramento usada pela prévia. Ela recebe os campos persistidos da cena e calcula escala, deslocamento e progresso para `static`, `zoom`, `pan-horizontal` e `pan-vertical`. O canvas usa a URL real do asset da cena e cacheia cada imagem por URL; não há imagem demonstrativa substituta.

O canvas agora possui dois modos explícitos:

- Cinematográfico: composição das cenas do projeto, com ordem, duração, imagens e câmera.
- Narrator Mode: palco e rig Santa V5 existentes, preservados sem alteração de identidade.

A equivalência ainda não é declarada como pixel-perfect: o FFmpeg usa `zoompan` a 30 fps e o browser usa `requestAnimationFrame`. A tolerância de aceitação desta missão é geométrica: mesma proporção 16:9, mesma direção de deslocamento, mesmo estado de câmera e erro de enquadramento esperado inferior a um pixel lógico após normalização; diferenças de codec não são consideradas. Uma prancha final com os cinco pontos por movimento depende de um projeto com quatro imagens de referência e exportação real na próxima rodada de evidências.

## Evidência real

No navegador local (`127.0.0.1:8894`), a rota `#preview` exibiu os controles “Cinematográfico” e “Narrator Mode”. Com o workspace sem projeto, o canvas cinematográfico mostrou a mensagem de estado “Crie um projeto para visualizar as cenas”, confirmando que não recorre à arte fixa do escritório. O Narrator Mode permaneceu visível no dock e os controles de reprodução continuaram funcionais.

## Testes

- Novo teste de contrato: `frontend/tests/test_cinematic_composition.mjs` — **2 passed**.
- Python: **39 passed, 1 skipped**.
- Suíte Node existente: passou; `studio-shell.mjs` passou `node --check`.
- `git diff --check`: passou.

## Limitações restantes

1. A sobreposição do Narrator Mode sobre imagens de cena ainda não é suportada; os modos permanecem corretamente separados.
2. Para PASS completo, falta a prancha Canvas × MP4 com projeto de teste contendo marcadores visuais e capturas em início/25/50/75/fim para os quatro movimentos.
3. Recomendado para a próxima iteração: extrator de frames automatizado e comparação geométrica baseada em bordas/quadros, não em uma única métrica de pixels.
