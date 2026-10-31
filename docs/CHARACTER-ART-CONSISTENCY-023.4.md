# Character Art Consistency — MISSÃO 023.4

## Estado

Implementação experimental concluída e preservada para revisão humana. O gate artístico continua `AWAITING_ART_APPROVAL`.

## Diagnóstico

Os close-ups reais dos MP4s da MISSÃO 023.3 comprovaram que o carregamento de
`facial_states` havia sido corrigido, mas a composição ainda era inadequada:
Dora e Alex usavam cabeças V4 semirrealistas com bocas roxas largas, sem a
mesma iluminação, textura ou proporção do rosto. O defeito não era mais de
disponibilidade do asset; era incompatibilidade artística e de escala.

Evidências preservadas:

- `E:\Fabuloom\workspace\exports\videos\facial-system-recovery-v1\dora-recovery-v1-facial-closeups.png`
- `E:\Fabuloom\workspace\exports\videos\facial-system-recovery-v1\alex-recovery-v1-facial-closeups.png`
- `E:\Fabuloom\workspace\exports\videos\facial-art-consistency-v1\dora-recovery-to-cartoon-comparison.png`
- `E:\Fabuloom\workspace\exports\videos\facial-art-consistency-v1\alex-recovery-to-cartoon-comparison.png`

## Estratégia V1

Dora e Alex receberam uma identidade facial cartoon original em canvas único,
com fundo transparente e base sem boca. As bocas são estados compactos no mesmo
canvas facial: `closed`, `slight`, `moderate` e `open`, com uma variante de
sorriso que reutiliza o estado fechado. Não há faixa de largura total, placa de
terço inferior, halo ou substituição do nariz/rosto/cabelo.

Os olhos e cabelos fazem parte da base de cada identidade; a piscada usa uma
camada transparente pequena e independente. O desenho continua passando por
`NarratorAvatarRenderer` e `LayeredCharacterRenderer`, sem um motor facial novo.

| Narrador | Voz | Base | Estado |
|---|---|---|---|
| Dora | `pf_dora` | `topazio-narrators-cartoon-v1/dora/head-clean.png` | experimental |
| Alex | `pm_alex` | `topazio-narrators-cartoon-v1/alex/head-clean.png` | experimental |
| Santa | `pm_santa` | pack Santa V5 preservado | referência |

## Arte e licenciamento

As bases de Dora e Alex foram geradas como arte original para esta branch,
sem imagens de terceiros e sem alteração dos assets V2/V3/V4 ou Santa V5.
Os arquivos gerados ficam versionados no pack experimental; áudios, vídeos e
pranchas ficam somente em `E:\Fabuloom\workspace\exports` e não entram no Git.

## Evidências geradas

- `facial-art-consistency-state-board.png`: cinco estados dos três narradores,
  capturados pelo renderer compartilhado.
- `dora-cartoon-v1-facial-closeups.png`: validação progressiva da Dora.
- `alex-cartoon-v1-facial-closeups.png`: validação do Alex após o método da Dora.
- `trio-cartoon-v1-comparison.png`: comparação dos três personagens.
- `fabuloom-official-narrator-dora-cartoon-v1.mp4`: narração `pf_dora` real.
- `fabuloom-official-narrator-alex-cartoon-v1.mp4`: narração `pm_alex` real.
- `fabuloom-official-narrator-santa-cartoon-v1.mp4`: referência `pm_santa`, sem alteração do pack.

O áudio foi reutilizado dos manifests locais das missões anteriores. A boca
continua sendo resposta visual à amplitude RMS; não há alinhamento de palavras,
fonemas ou visemas inventado.

## Limitações e decisão

- A aprovação artística final permanece com o proprietário.
- A arte é uma base cartoon experimental, não uma ilustração final cinematográfica.
- O recorte circular continua priorizando o rosto; corpo completo e novos gestos
  estão fora do escopo.
- Os packs Recovery V1 e V4 continuam preservados para comparação e rollback.
- Dora e Alex só devem ser promovidos a produção depois da revisão humana das
  pranchas e MP4s.
