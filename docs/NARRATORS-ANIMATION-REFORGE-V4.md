# Narrators Animation Reforge V4 — MISSÃO 023.2

Esta etapa substitui a aparência oficial experimental de Dora e Alex no
`NarratorAvatarRenderer` por bases frontais em estilo cartoon estilizado,
mantendo Santa V5 intacto. A direção visual usa Santa V5 como referência de
acabamento Topazioverse, não como fonte de características físicas.

## Diagnóstico da V3

- Dora V3 tinha acabamento próximo de retrato ilustrado e pouca leitura de
  boca em escala de avatar.
- Alex V3 mantinha perspectiva de três quartos, dificultando a troca estável
  de expressões e a leitura dos dois cantos da boca.
- As placas V3 eram corretas como prova de integração, mas ainda pareciam
  overlays aplicados a retratos, e não arte planejada para animação.

## Contrato visual comum

`frontend/src/topazio-narrator-packs-v4.mjs` define o contrato
`fabuloom.narrator-visual-contract/0.1`:

- canvas de origem `1145×1374`;
- busto frontal, cabeça e ombros centralizados;
- moldura circular azul/dourada do Narrator Mode;
- base de cabeça sem boca, para não duplicar a região facial;
- placas transparentes de pálpebras e boca no mesmo canvas;
- estados `closed`, `slight`, `moderate`, `open` e `smile`;
- `pt-BR`, RMS medido e tempos de segmentos reais;
- palavras, fonemas e visemas continuam indisponíveis;
- estado artístico `AWAITING_ART_APPROVAL`.

Os transforms de boca e pálpebras são explícitos por personagem. Isso evita
heurísticas históricas de alinhamento baseadas em nomes de arquivos e mantém
o contrato compatível com `fabuloom.character/0.1`.

## Packs e vozes

| Personagem | Pack | Voz | Estado |
|---|---|---|---|
| Santa | Santa V5 preservado | `pm_santa` | referência aprovada |
| Dora | `topazio-narrator-dora-v4` | `pf_dora` | aguardando aprovação artística |
| Alex | `topazio-narrator-alex-v4` | `pm_alex` | aguardando aprovação artística |

Os assets V4 ficam em:

- `frontend/assets/characters/topazio-narrators-v4/dora/`
- `frontend/assets/characters/topazio-narrators-v4/alex/`

Cada diretório contém uma base `head-clean.png`, uma placa de piscada e
quatro variantes de boca. V2 e V3 permanecem disponíveis para referência e
compatibilidade; não foram apagados nem sobrescritos.

## Renderização e RMS

`NarratorAvatarRenderer` continua sendo o único caminho de composição. Em
V4, o resolver escolhe a placa conforme `mouthStateAt()`:

```text
RMS < 0.12  → closed
RMS < 0.34  → slight
RMS < 0.68  → moderate
RMS ≥ 0.68  → open
```

O estado `smile` é uma expressão explícita do pack. A cabeça, piscada,
respiração, inclinação e relógio continuam vindo do `NarratorFacialRig` e do
`LayeredCharacterRenderer`; não há um segundo motor de animação.

## Laboratório e validação

`frontend/official-narrators-board.html` agora compara Santa V5, Dora V4 e
Alex V4 em neutro, sorriso, fala suave, fala forte, piscada e movimento de
cabeça usando o mesmo renderer dos vídeos.

A captura de MP4 deve reutilizar os manifestos locais de Dora, Santa e Alex,
sem inventar sincronização fonética. A aprovação visual final permanece com o
proprietário e não é inferida pelos testes automatizados.

## Limitações

- Dora V4 e Alex V4 são narradores faciais de busto; ainda não são rigs
  corporais completos.
- As placas são experimentais e aguardam avaliação humana em MP4.
- RMS fornece uma aproximação visual de fala, não alinhamento fonético.
- A promoção automática para `ART_APPROVED` está proibida.
- Character Creator V2 e importação externa continuam fora do escopo.
