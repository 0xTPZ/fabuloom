# Narrators Art Reforge V3 — MISSÃO 023.1

Status: `AWAITING_ART_APPROVAL`

Esta etapa cria uma geração artística própria para Dora e Alex sem modificar a
arte aprovada do Santa V5. O objetivo é substituir os packs técnicos V2 como
demonstradores faciais do Narrator Mode, mantendo um único caminho de
renderização.

## Contrato visual

Cada personagem V3 possui um canvas de arte `1145×1374` com:

- `head-clean.png`: busto ilustrado com a área da boca limpa;
- `eyelids-closed-v3.png`: overlay transparente recortado de uma piscada da
  mesma identidade;
- `mouth-closed-v3.png`: boca fechada extraída da referência original;
- `mouth-open-v3c.png`: boca aberta extraída de uma variante de fala da mesma
  personagem.

Os três overlays usam o mesmo frame local da base. O sufixo V3 é deliberado:
ele impede que a tabela de alinhamento dos plates do Santa V5 seja aplicada por
engano aos assets de Dora ou Alex.

## Runtime

`topazio-narrator-packs-v3.mjs` expõe os packs `animation-ready/0.1` de Dora e
Alex. `narrator-mode.mjs` os seleciona por `characterId`; o Santa continua
resolvendo `SANTA_V5_PACK`. `NarratorAvatarRenderer` permanece responsável por
carregar assets, aplicar a hierarquia head-local, esconder pálpebras no estado
aberto, trocar a boca conforme o RMS e renderizar o círculo.

Não existe um segundo motor de animação. A boca continua sendo uma aproximação
por amplitude RMS; tempos de palavras, fonemas e visemas permanecem
indisponíveis e não são inventados.

## Evidência local

As capturas de validação foram produzidas pelo `capture-narrator-mode.html` e
pelo mesmo caminho do exportador, usando manifests Kokoro já existentes:

`E:\Fabuloom\workspace\exports\videos\narrators-art-reforge-v1`

Foram inspecionados frames neutros, fala, piscada e close-ups ampliados. O
ajuste rastreável desta missão corrigiu a colisão de nomes com o alinhamento
Santa V5 e depois reduziu a escala inicial da boca aberta; a variante final foi
extraída de uma edição de fala da própria referência de cada personagem.

## Limites

Esta não é ainda a arte final corporal nem um Character Creator. Dora e Alex
V3 continuam com um busto facial preparado para o Narrator Mode, sem novo rig
corporal, sem nova implementação de áudio e sem alteração do Santa V5. A
aprovação artística do proprietário permanece necessária.
