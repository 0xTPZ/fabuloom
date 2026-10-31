# Visual Inspector — Narradores V4

Status: `AWAITING_ART_APPROVAL`

Este relatório registra a inspeção dos quadros exportados pela mesma rota de
renderização usada pelos vídeos V4. A inspeção artística foi feita sobre PNGs
gerados e close-ups ampliados; os testes automatizados são evidência auxiliar,
não aprovação visual.

## Evidências

- `narrators-trio-v4-comparison.png`: Santa V5, Dora V4 e Alex V4 em estados comparáveis.
- `dora-v3-v4-comparison.png`: comparação do board anterior com Dora V4.
- `alex-v3-v4-comparison.png`: comparação do board anterior com Alex V4.
- `dora-v4-facial-closeups.png`: neutro, fala, fala/piscada e final.
- `alex-v4-facial-closeups.png`: neutro, fala, fala/piscada e final.
- `fabuloom-official-narrator-{dora,santa,alex}-v4-frames.png`: pranchas dos vídeos individuais.

## Resultado observado

1. As bases V4 de Dora e Alex são frontais, com enquadramento de busto e moldura
   compatível com Santa V5.
2. Os estados de boca ficaram legíveis sem substituir o rosto inteiro. A primeira
   tentativa com placas grandes e realistas foi rejeitada e não integra os assets finais.
3. Olhos, cabelo, sobrancelhas e contorno facial permanecem estáveis entre os estados.
4. A troca entre silêncio, RMS suave e RMS forte é visível, mas deliberadamente
   coarse: não representa alinhamento fonético.
5. Santa V5 foi apenas reutilizado como referência e continua sendo a fonte oficial;
   seus assets não foram alterados.

## Limitações e decisão

- A inspeção não substitui a aprovação artística do proprietário.
- Dora V4 e Alex V4 permanecem experimentais.
- Timestamps de palavras, fonemas e visemas não estão disponíveis.
- Os vídeos usam manifestos e WAVs locais já medidos na missão 023.1; nenhuma nova
  síntese foi necessária.

O relatório JSON correspondente é gerado ao lado dos vídeos como
`narrators-animation-reforge-v4-report.json` e contém as dimensões, codecs,
contagem de quadros, fontes de timing e estado do gate.
