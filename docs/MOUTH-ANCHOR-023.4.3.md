# Mouth Anchor Recovery — MISSÃO 023.4.3

## Estado

Calibração geométrica experimental concluída na branch
`mission-023.4.3-mouth-anchor-recovery`. O gate permanece
`AWAITING_ART_APPROVAL`.

## Diagnóstico comprovado

Foram extraídos quadros reais dos MP4s da 023.4.2. A boca de Dora e Alex
estava centrada no canvas transparente da boca, mas não em landmarks próprios
da identidade facial. O resultado colocava a linha labial alta demais em
relação ao nariz e deixava a integração com o queixo menos natural no avatar
reduzido. Santa V5 permaneceu estável e não foi alterado.

Não foi encontrado motivo para alterar crop, enquadramento geral, RMS ou o
`NarratorAvatarRenderer` global.

## Contrato e valores

Foi adicionado o contrato versionado
`fabuloom.narrator-mouth-anchor/0.1` ao pack cartoon. Os parâmetros são
persistidos em `TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES`:

| personagem | anchor | posição base | offset local | posição efetiva | escala |
|---|---:|---:|---:|---:|---:|
| Dora | `[0.5, 0.5]` | `[0.5, 0.5]` | `[0, 0.04]` | `[0.5, 0.54]` | `[1, 1]` |
| Alex | `[0.5, 0.5]` | `[0.5, 0.5]` | `[0, 0.036]` | `[0.5, 0.536]` | `[1, 1]` |

Os offsets são específicos por personagem. A boca continua filha da cabeça,
portanto acompanha rotação, piscada, seek e demais transformações herdadas.
Os quatro estados RMS usam a mesma ancoragem.

Landmarks locais registrados:

- Dora: nariz `[627,565]`, centro da boca `[627,665]`, cantos
  `[552,665]`–`[702,665]`, limite superior do queixo `[627,775]`.
- Alex: nariz `[627,580]`, centro da boca `[627,666]`, cantos
  `[548,666]`–`[706,666]`, limite superior do queixo `[627,810]`.

Na pose neutra, a projeção do centro esperado para o canvas final 1920×1080
passa de aproximadamente `y=888,5` para `y=905,0` em Dora e de `y=888,8`
para `y=903,6` em Alex. O deslocamento é exclusivamente local e não altera o
enquadramento do avatar.

## Laboratório

`frontend/mouth-anchor-calibration-lab.html` reutiliza o
`NarratorAvatarRenderer` real e mostra os estados `closed`, `slight`,
`moderate` e `open`, com landmarks, linha entre os cantos, centro da boca e
limite do queixo.

## Evidências workspace-only

Os artefatos estão em:
`workspace/exports/videos/mouth-anchor-recovery-v1/`

- `mouth-anchor-calibration-board.png` — laboratório com landmarks.
- `mouth-anchor-before-after-board.png` — 023.4.2 versus 023.4.3.
- `dora-mouth-anchor-v1-facial-closeups.png` — quadros reais de Dora.
- `alex-mouth-anchor-v1-facial-closeups.png` — quadros reais de Alex.
- `santa-mouth-anchor-v1-facial-closeups.png` — referência Santa V5.
- `mouth-anchor-recovery-v1-report.json` — relatório técnico.
- `reference-frames/` — quadros extraídos dos MP4s anteriores para diagnóstico.

## Vídeos

- `fabuloom-dora-mouth-anchor-v1.mp4` — 6,233 s, 1920×1080, 30 FPS,
  H.264/yuv420p e AAC mono 24 kHz.
- `fabuloom-alex-mouth-anchor-v1.mp4` — 6,367 s, 1920×1080, 30 FPS,
  H.264/yuv420p e AAC mono 24 kHz.
- `fabuloom-narrators-mouth-anchor-trio-v1.mp4` — composição de comparação.

Os WAVs e manifestos Kokoro existentes foram reutilizados. Não foram criados
timestamps de palavras, fonemas ou visemas.

## Validação

O laboratório e os vídeos foram produzidos em navegador local pelo mesmo
caminho de renderização usado no Narrator Mode. Node, Python, FFprobe e
decodificação completa FFmpeg foram executados. A aprovação artística final
continua pertencendo ao proprietário.
