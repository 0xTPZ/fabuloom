# Missão 035 — Long-Form Project Integrity

Data: 2026-11-01  
Base: `fecaa44`  
Commit da correção: `a5cd761`  
Resultado: **PASS para reconciliação / PARTIAL para long-form completo**

## Auditoria antes da correção

O fluxo anterior usava posição como fallback em todas as situações. Após inserir uma frase no meio, a cena nova podia herdar a imagem/configuração da antiga posição 2. Split e join também podiam redistribuir ou remover vínculos sem distinguir correspondência inequívoca.

## Estratégia adotada

`frontend/src/scene-reconciliation.mjs` agora:

1. normaliza texto e procura correspondência exata única;
2. preserva identidade, asset e configuração dessa cena;
3. usa posição apenas quando a quantidade de cenas não mudou, tratando como edição textual;
4. cria uma cena sem asset para novos trechos ambíguos;
5. retorna cenas removidas para que o frontend peça confirmação quando havia configuração ou imagem;
6. mantém IDs persistentes independentes dos IDs temporários do áudio.

O backend usa a mesma regra de texto exato durante regeneração. Não há redistribuição arbitrária de imagens.

## Casos cobertos

| Caso | Resultado |
|---|---|
| Inserção no início/meio/fim | PASS — textos existentes preservam IDs/assets |
| Exclusão | PASS — cena removida é reportada; assets não migram |
| Reordenação | PASS — correspondência textual preserva identidade |
| Alteração textual | PASS — mesma cardinalidade mantém configuração por posição |
| Split | PASS — novas cenas ficam sem asset e exigem revisão |
| Join | PASS — correspondência ambígua não herda assets |
| Regeneração sem alteração | PASS |
| Falha de correspondência | PASS seguro — revisão/confirmção no UI |

## Desempenho

Benchmark da função pura, 1000 reconciliações por tamanho, no host Windows:

| Cenas | Total | Média |
|---:|---:|---:|
| 10 | 17.284 ms | 0.0173 ms |
| 30 | 27.393 ms | 0.0274 ms |
| 60 | 50.275 ms | 0.0503 ms |

Essas medidas são do algoritmo, não do tempo de renderização do navegador, upload, Kokoro ou FFmpeg. Não constituem promessa de suporte a vídeos de 20 minutos.

## Regressão

- Python: **43 passed, 1 skipped**.
- Node completo: **151 passed**.
- Novos testes de reconciliação: inserção, edição, exclusão, split e join.
- `node --check` e `git diff --check`: PASS.

## Limitações

Projetos com frases idênticas repetidas continuam ambíguos; o algoritmo não pode inferir intenção sem confirmação humana. A missão não executou uma exportação de vários minutos nem uma bateria de 10/30/60 cenas pela interface completa; o gate de long-form operacional permanece **PARTIAL**. Santa V5, Kokoro, Narrator Mode, preview e FFmpeg não foram reconstruídos.
