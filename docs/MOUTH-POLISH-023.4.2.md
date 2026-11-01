# Mouth Polish — MISSÃO 023.4.2

## Estado

Calibração artística experimental concluída na branch
`mission-023.4.2-mouth-polish`. O gate permanece
`AWAITING_ART_APPROVAL`.

## Diagnóstico

Os vídeos da 023.4.1 mostraram que o framing estava correto, mas Dora e Alex
ainda usavam estados de boca com contornos escuros, largura excessiva e uma
abertura `open` com massa visual grande de dentes/língua. O resultado parecia
uma peça sobreposta, apesar de a boca estar tecnicamente na hierarquia da
cabeça.

Santa V5 não foi alterado. As bocas originais da 023.4 também foram preservadas
para comparação e rollback.

## Solução adotada

Foi escolhida a abordagem de estados discretos redesenhados, mantendo o contrato
e o renderer existentes:

- bocas novas e compactas no mesmo canvas 1254×1254;
- largura menor e contorno com menor contraste;
- gradientes e sombras mais suaves;
- linha de lábios consistente entre os estados;
- dentes e língua reduzidos nos estados `moderate` e `open`;
- centro e baseline constantes;
- `parent: "head"` preservado;
- mapeamento RMS e thresholds inalterados.

Os novos arquivos são `mouth-polish-closed.svg`, `mouth-polish-slight.svg`,
`mouth-polish-moderate.svg` e `mouth-polish-open.svg` para Dora e Alex. O pack
registra `mouth_polish_status: v1.1-experimental-awaiting-art-approval`.

## Evidências

- `workspace/exports/videos/facial-mouth-polish-v1/mouth-polish-state-board.png`
- `workspace/exports/videos/facial-mouth-polish-v1/mouth-before-after-board.png`
- `workspace/exports/videos/facial-mouth-polish-v1/dora-mouth-polish-v1-facial-closeups.png`
- `workspace/exports/videos/facial-mouth-polish-v1/alex-mouth-polish-v1-facial-closeups.png`
- `workspace/exports/videos/facial-mouth-polish-v1/mouth-polish-v1-report.json`

As imagens foram capturadas pelo `NarratorAvatarRenderer` real. A inspeção
multimodal confirmou a redução da aparência de adesivo; isso é evidência para
revisão humana, não aprovação artística automática.

## Vídeos

- `fabuloom-dora-mouth-polish-v1.mp4` — 6,233 s, 1920×1080, H.264/yuv420p,
  AAC mono 24 kHz.
- `fabuloom-alex-mouth-polish-v1.mp4` — 6,367 s, 1920×1080, H.264/yuv420p,
  AAC mono 24 kHz.
- `fabuloom-narrators-mouth-polish-trio-v1.mp4` — composição vertical de
  referência com os três narradores.

O áudio Kokoro existente foi reutilizado. Não foram criadas novas vozes,
manifests ou timestamps fonéticos.

## Limitações

O sistema ainda usa estados discretos selecionados pela amplitude RMS, não
visemas ou alinhamento fonético. Os novos SVGs são polish experimental e ainda
dependem de aprovação artística do proprietário em vídeo real.
