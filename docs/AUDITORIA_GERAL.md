# Auditoria geral — MISSÃO 022

Status: **não pronto para divulgação pública**.

Esta auditoria avaliou o checkout público, a branch `mission-021-ui-reforge`,
o Studio em loopback, os contratos, os packs de personagens e os comandos
documentados. Nenhuma PR anterior foi mesclada.

## Linha de base

O `main` público ainda aponta para `bc239320` e contém somente a fundação
documental/contratual. A UI da MISSÃO 021 está em `mission-021-ui-reforge`,
commit `cee6d93`, e não é obtida por um clone padrão de `main`.

## Achados principais

| ID | Severidade | Achado | Estado |
| --- | --- | --- | --- |
| AUD-01 | bloqueador | Clone padrão de `main` não contém frontend, servidor, `pyproject.toml` ou testes executáveis. | Documentado; lançamento depende de uma decisão de branch/release. |
| AUD-02 | alta | A documentação inicial não informava `PYTHONPATH=src` para a descoberta Python. | Corrigido na documentação desta branch. |
| AUD-03 | alta | O servidor fixava `E:\Fabuloom` e uma instalação clonada acessava os exports do desenvolvedor. | Corrigido com `FABULOOM_WORKSPACE_ROOT`/`FABULOOM_EXPORT_ROOT`. |
| AUD-04 | alta | A UI organiza produções existentes, mas não cria projeto, cena, importação de imagem ou job de exportação. | Mantido explícito; planejado para a MISSÃO 025. |
| AUD-05 | média | Dora e Alex têm packs técnicos V2 no Character Stage, mas a prévia oficial do Studio mantém Santa V5 como visual e troca apenas a voz. | Documentado para a MISSÃO 023. |
| AUD-06 | média | Kokoro, WAVs, manifestos, cenas e MP4s não são distribuídos no repositório. | Correto para modelos/mídia; exige bootstrap documentado. |
| AUD-07 | média | A matriz visual e a validação de interface não equivalem a aprovação artística ou a um editor de produção. | Mantido como limite explícito. |

## Correções desta missão

- resolução portátil do workspace/export root no servidor;
- rótulos do dashboard que distinguem capacidades locais, renderer de browser e
  exportação via CLI, sem afirmar `4/4 OK` sem verificação;
- foco de teclado visível e suporte CSS a `prefers-reduced-motion`;
- documentação de instalação limpa, fluxo de usuário e roadmap comunitário.

## Limites

O teste de Kokoro real não foi executado no clean-room, porque pesos, cache e
dependências opcionais não fazem parte do clone. Os testes offline passaram com
um skip opt-in para o modelo real. Nenhum arquivo externo, modelo ou mídia
privada foi publicado.

