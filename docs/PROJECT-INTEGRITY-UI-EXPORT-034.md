# Missão 034 — Project Integrity & UI Export

Data: 2026-11-01  
Base: `f483bd8`  
Resultado: **PASS técnico / PARTIAL de aceitação pública**

## Causa-raiz

`frontend/server.py::_handle_narration()` substituía as cenas do projeto pelos IDs dos segmentos medidos do áudio. Como esses IDs são temporários e mudam a cada síntese, a operação perdia imagens, movimentos, duração e identidade. O `saveProject()` do frontend também reconstruía cenas por índice e restaurava câmera/duração para defaults.

## Correção

Foi criado `_reconcile_scenes()`: segmentos de áudio são mapeados por posição para as cenas existentes, preservando `id`, `image`, `camera`, `transition`, duração, ordem e metadados. Cenas novas recebem IDs estáveis `scene-###`; IDs de manifesto permanecem restritos ao áudio. A atualização de script no frontend também preserva todos os campos editáveis da cena por índice.

## Fluxo gráfico independente

Checkout: `C:\Temp\fabuloom-alpha-033-clean`  
Workspace novo: `C:\Temp\fabuloom-alpha-034-workspace`  
Porta: `8898`

Executado exclusivamente no navegador:

1. Criar `A Jornada de uma Estrela`.
2. Escrever roteiro com três frases.
3. Salvar e criar três cenas.
4. Importar `santa.png`, `dora.png` e `alex.png` pela interface.
5. Configurar static, zoom, pan-horizontal e pan-vertical.
6. Gerar narração Santa V5 pelo botão.
7. Alterar a segunda frase e salvar.
8. Regenerar narração pelo botão.
9. Confirmar visualmente três imagens e movimentos preservados.
10. Exportar MP4 pelo botão.
11. Abrir a biblioteca, reabrir o projeto e confirmar novamente cenas/assets/movimentos.

Estado persistido após regeneração:

| ID | Asset | Movimento | Duração |
|---|---|---|---:|
| `scene-001` | `asset-5dfb1e4ecb.png` | zoom | 3600 ms |
| `scene-002` | `asset-774842cde1.png` | pan-horizontal | 3000 ms |
| `scene-003` | `asset-455a32301d.png` | pan-vertical | 3000 ms |

MP4 real produzido pela interface: `C:\Temp\fabuloom-alpha-034-workspace\workspace\exports\projects\project-f454678ec622\project-f454678ec622-1080p.mp4`. FFprobe confirmou H.264/AAC, 1920×1080, 8.900000 s, 1021803 bytes; decodificação integral FFmpeg passou.

## Testes

- Regressão Python: **43 passed, 1 skipped**.
- Node/frontend: **147 passed**.
- Novos testes: regeneração preserva identidade/assets/movimento e cenas novas não usam IDs de manifesto.
- `node --check` e `git diff --check`: PASS.

## Classificação

| Área | Resultado |
|---|---|
| Integridade após regeneração | PASS |
| Preservação de imagens e movimentos | PASS |
| Exportação real pela interface | PASS |
| Reabertura e persistência | PASS |
| Narrator Mode Santa V5 | PASS |
| Aceitação sem terminal em checkout independente | PASS técnico, PARTIAL de produto |

A classificação pública permanece PARTIAL porque o ambiente independente precisou ser preparado pelo terminal e o gate Canvas × FFmpeg continua separado. Nenhum MP4 ou modelo foi adicionado ao Git.
