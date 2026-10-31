# Facial Framing — MISSÃO 023.4.1

## Estado

Calibração experimental concluída em `mission-023.4.1-facial-framing`. O
renderer global, o crop de Narrator Mode e os assets oficiais não foram
alterados. O gate artístico permanece `AWAITING_ART_APPROVAL`.

## Diagnóstico comprovado

Os MP4s da MISSÃO 023.4 mostravam Dora e Alex com cabelo e queixo muito
próximos do aro circular. A causa não era somente escala visual: os assets
`head-clean.png` são quadrados (1254×1254), mas os packs desenhavam a raiz no
canvas-fonte 1080×1920 com `size: [0.68, 0.68]`. Isso aplicava escalas físicas
de largura e altura diferentes e alongava o rosto. A boca era filha da cabeça,
mas herdava esse enquadramento comprimido.

As capturas anteriores estão preservadas em
`workspace/exports/videos/facial-art-consistency-v1/`. A auditoria desta
missão também extraiu quadros em `facial-framing-v1/audit-before/`.

## Correção pack-local

`frontend/src/topazio-narrator-packs-cartoon-v1.mjs` agora expõe perfis
versionados por personagem em `TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES`:

| Campo | Antes | Dora/Alex V1.1 |
|---|---:|---:|
| `base_size` | `[0.68, 0.68]` | `[0.68, 0.3825]` |
| `base_position` | `[0.5, 0.32]` | `[0.5, 0.205]` |
| `mouth_size` | `[0.9, 0.9]` | `[1, 1]` |

`0.3825 = 0.68 × 1080 / 1920`, preservando a proporção física do asset
quadrado. A posição foi ajustada para manter cabelo, rosto, boca, gola e
ombros dentro do recorte existente. Boca e pálpebras continuam com
`parent: "head"`, portanto rotação, respiração, piscada e estados RMS usam a
mesma transformação facial. Santa V5 continua com seu perfil original.

Os valores são registrados também em `pack.framing`, com contrato
`fabuloom.narrator-cartoon-framing/0.1`, pivô, centro da boca, escala da boca,
canvas-fonte e referência explícita a `NARRATOR_FACE_CROP`.

## Laboratório e evidências

- `frontend/facial-framing-lab.html`: laboratório DEV com controles de escala,
  posição, escala/centro da boca e visualização dos quatro estados.
- `frontend/facial-framing-state-board.html`: prancha capturada pelo mesmo
  `NarratorAvatarRenderer` usado na exportação.
- `workspace/exports/videos/facial-framing-v1/facial-framing-state-board.png`:
  Santa V5, Dora e Alex lado a lado em estados fechada, leve, moderada e aberta.
- `workspace/exports/videos/facial-framing-v1/before-after-framing-board.png`:
  comparação equivalente antes/depois.
- `workspace/exports/videos/facial-framing-v1/dora-framing-v1-facial-closeups.png`
  e `alex-framing-v1-facial-closeups.png`: close-ups reais extraídos do pipeline.

Nenhuma imagem nova foi criada nesta missão; somente parâmetros dos packs foram
calibrados e os assets existentes foram reutilizados.

## Vídeos

O áudio Kokoro local das missões anteriores foi reutilizado, sem nova síntese:

- `workspace/exports/videos/facial-framing-v1/fabuloom-dora-framing-v1.mp4`
- `workspace/exports/videos/facial-framing-v1/fabuloom-alex-framing-v1.mp4`
- `workspace/exports/videos/facial-framing-v1/fabuloom-narrators-framing-trio-v1.mp4`

Dora, Alex e Santa foram renderizados pelo mesmo caminho de captura de quadros.
Os dois vídeos individuais são 1920×1080, 30 FPS, H.264/yuv420p e AAC. O trio
é uma prancha audiovisual vertical 640×1080, com os três vídeos empilhados e
áudio Dora como referência de reprodução.

## Validação

Foram validados:

- bounds normalizados dos perfis e proporção física do asset;
- parentagem da boca e das pálpebras à cabeça;
- estados fechada, leve, moderada e aberta;
- determinismo do renderer e manutenção de RMS/timing;
- captura real do navegador e decodificação FFmpeg/FFprobe;
- preservação do pack Santa V5 e dos assets anteriores.

Não há timestamps de palavras, fonemas ou visemas inventados. A boca continua
sendo uma aproximação por amplitude RMS.

## Limitações e decisão

A correção melhora demonstravelmente o enquadramento e elimina a distorção
vertical do pack, mas não substitui uma aprovação artística humana. O recorte
circular ainda é um compromisso de Narrator Mode e a avaliação de produção de
Dora/Alex continua pendente.
