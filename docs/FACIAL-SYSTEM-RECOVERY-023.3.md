# Facial System Recovery 023.3

Status: `AWAITING_ART_APPROVAL`

## Diagnóstico comprovado

O MP4 V4 foi recapturado e seus close-ups foram examinados. O defeito não era
apenas escala: `NarratorAvatarRenderer` selecionava estados em
`facial_states.mouth`, mas `LayeredCharacterRenderer.load()` só carregava
assets de `layers` e `expressions`. Quando o RMS escolhia `slight`, `moderate`
ou `open`, o resolver retornava um caminho que não existia em `images`; o
renderer ignorava a camada ausente e a boca desaparecia.

O diagnóstico foi confirmado pela leitura do código e por capturas reais:

- a base `head-clean.png` não fornece uma boca completa confiável;
- os estados V4 PNG eram placas realistas independentes;
- o estado fechado podia aparecer, enquanto estados não pré-carregados eram
  omitidos silenciosamente;
- a aparência sem placa era uma face neutra, mas sem uma estratégia de boca
  cartoon integrada.

## Correção estrutural

`collectCharacterAssetPaths()` agora percorre `layers`, `expressions` e mapas
aninhados de `facial_states` antes do carregamento. Assim, um resolver de
estado não pode selecionar uma imagem declarada e ainda não carregada.

Dora e Alex usam packs novos `facial-system-recovery-v1`:

- as cabeças e pálpebras V4 continuam preservadas;
- as bocas geradas V4 não foram substituídas nem apagadas;
- novas bocas vetoriais, no mesmo canvas `1145×1374`, definem fechada, leve,
  moderada, aberta e sorriso;
- a seleção permanece no `NarratorAvatarRenderer` e usa RMS real;
- Santa V5 continua sendo a referência e não foi alterado.

## Protótipo mínimo

`mouth-recovery-lab.html` usa uma cabeça frontal vetorial criada somente para o
teste, o `LayeredCharacterRenderer` compartilhado e cinco estados explícitos.
Sua captura produziu 60 quadros e mostrou todos os estados sem apagar o rosto.

## Evidências locais

Os artefatos gerados ficam fora do Git:

- `workspace/exports/videos/facial-system-recovery-v1/mouth-recovery-prototype-states.png`
- `workspace/exports/videos/facial-system-recovery-v1/mouth-recovery-prototype.mp4`
- `workspace/exports/videos/facial-system-recovery-v1/facial-recovery-state-board.png`
- `workspace/exports/videos/facial-system-recovery-v1/dora-recovery-v1-facial-closeups.png`
- `workspace/exports/videos/facial-system-recovery-v1/alex-recovery-v1-facial-closeups.png`
- `workspace/exports/videos/facial-system-recovery-v1/facial-system-recovery-v1-report.json`

Os vídeos Dora, Santa e Alex reutilizam os WAVs e manifestos medidos da missão
023.1. Não foram inventados timestamps de palavras, fonemas ou visemas.

## Limitações

- As cabeças de Dora e Alex ainda herdam a arte V4 semirrealista; esta missão
  corrige a arquitetura e a estabilidade da boca, não recria integralmente os
  rostos em estilo Santa V5.
- As bocas vetoriais são uma solução técnica/cartoon e ainda requerem avaliação
  artística quanto a escala, integração cromática e acabamento.
- A aprovação artística do proprietário continua obrigatória.
