# Missão 036 — Long-Form Endurance & Data Integrity

Data: 2026-11-01  
Base verificada: `9a5aaba`  
Branch: `release/fabuloom-alpha-preparation`  
Resultado: **PASS para integridade/reconciliação; PARTIAL para endurance operacional**

## Correção e causa-raiz

A auditoria encontrou um risco residual no fallback posicional. Quando mais de uma cena não tinha correspondência textual inequívoca, a posição podia transferir imagem, câmera, duração ou outro ajuste manual para outro trecho. Isso era especialmente perigoso em textos duplicados e substituições estruturais completas.

O frontend e o backend agora aplicam a mesma regra: correspondência textual normalizada e única primeiro; fallback posicional somente quando resta exatamente uma cena antiga e um novo trecho; em ambiguidade, a nova cena recebe identidade/configuração novas e nenhum asset antigo é redistribuído.

## Endurance observada

No navegador local, foram criados projetos descartáveis `Endurance 10`, `Endurance 30` e `Endurance 60` por roteiro e botão de salvar. O projeto ativo `Endurance 60` mostrou **60 cartões de cena**, todos persistidos, com 3 s por cena. A captura de evidência foi feita na rota Cenas, com Santa V5/`pm_santa` visível no palco.

O benchmark puro de reconciliação da Missão 035 permanece: 10 cenas 0,0173 ms, 30 cenas 0,0274 ms e 60 cenas 0,0503 ms por iteração média em 1000 iterações. Esses números medem o algoritmo, não toda a interação do navegador. A UI de 60 cenas permaneceu responsiva e não houve perda de cenas; não foi feita alegação de suporte a projetos de 20 minutos.

Não foi executada uma exportação nova de 3–5 minutos nesta missão: o ambiente disponível não permitia concluir esse teste com segurança dentro do ciclo sem repetir uma síntese longa. Portanto, a endurance de exportação permanece **PARTIAL**, não PASS.

## Casos de integridade

| Caso | Resultado |
|---|---|
| Regeneração sem mudança | PASS — identidade e configuração preservadas |
| Edição textual | PASS — correspondência segura quando há um único restante |
| Inserção, remoção, split/join | PASS — cobertos pelo frontend |
| Textos duplicados | PASS — nenhum asset é redistribuído |
| Substituição completa | PASS — novas cenas não herdam assets/configuração |
| Falha/transação de exportação longa | PARTIAL — requer nova execução operacional prolongada |

## Verificação

- Python: `45 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- `node --check frontend/src/studio-shell.mjs`: PASS.
- `git diff --check`: PASS.
- Worktree `E:\Fabuloom\studio`: não modificada.
- Nenhum modelo, vídeo ou mídia privada foi adicionado ao Git.

## Classificação final

**PARTIAL.** A integridade de dados para projetos longos está protegida e coberta por testes; a criação de 60 cenas foi comprovada no navegador. A exportação narrada de 3–5 minutos e a medição prolongada de recursos continuam pendentes antes de declarar endurance completa.
