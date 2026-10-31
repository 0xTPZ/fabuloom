# Plano de narradores Dora e Alex — MISSÃO 023

Santa V5 permanece intacto e continua sendo a referência aprovada do Narrator
Mode. Dora e Alex não devem ser apresentados como concluídos no Studio até que
tenham identidade visual própria integrada ao mesmo caminho de renderização.

## Estado auditado

- `pf_dora` e `pm_alex` possuem manifestos de voz no catálogo local quando os
  exports estão presentes.
- `topazio-narrator-packs.mjs` possui packs V1 de retrato e packs V2
  animation-ready com camadas SVG, expressões e bindings.
- O Character Stage legado consegue preparar os packs V2.
- O Studio agora troca visual e voz coordenadamente: Santa usa o V5 facial
  corrigido; Dora e Alex usam seus packs V2 técnicos e seus manifestos Kokoro
  correspondentes. O contrato da UI marca ambos como `awaiting-art-approval`.

## Contrato da MISSÃO 023

Cada narrador deverá ter:

1. pack visual próprio, com `fabuloom.character/0.1` e
   `animation-ready/0.1`;
2. cabeça, cabelo, olhos, pálpebras, sobrancelhas, boca, tronco, braços e
   acessórios com pivôs independentes;
3. expressões neutra, sorriso e fala, sem duplicar placas faciais;
4. piscada e movimento de cabeça determinísticos;
5. boca controlada por RMS, identificada como aproximação de amplitude;
6. associação explícita entre `character_id`, `voice_id` e idioma;
7. manifesto e áudio selecionáveis sem re-síntese automática;
8. fallback compreensível quando asset, manifesto ou WAV estiver ausente.

## Integração recomendada

Generalizar `NarratorAvatarRenderer` para receber um pack validado e manter o
`AudioTimelinePlayer` independente. O preview deverá trocar visual e voz como
duas operações coordenadas, verificando que o `voice_id` efetivamente carregado
corresponde ao narrador selecionado. Testes devem cobrir troca durante parado,
pausado e reproduzindo, seek, ausência de assets e determinismo.

Não copiar arte privada nem redesenhar Santa V5 nesta missão. A prancha de gate
artístico está em `frontend/official-narrators-board.html`; a promoção de Dora e
Alex para produção depende de revisão humana.

