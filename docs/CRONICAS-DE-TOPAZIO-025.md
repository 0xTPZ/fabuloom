# Crônicas de Topázio — O Portal das Histórias

Este documento registra a produção do primeiro vídeo institucional do canal
ficcional **Crônicas de Topázio**. O vídeo apresenta exclusivamente o universo
de fantasia: não é uma demonstração do Fabuloom, de software ou de tecnologia.

## Produção

- Narrador: Santa V5 pelo `NarratorAvatarRenderer` oficial.
- Voz: Kokoro `pm_santa`, `pt-BR`.
- Duração medida do manifesto: `82,095 s`.
- Composição: `1920×1080`, `30 FPS`, H.264, AAC estéreo a `48 kHz`.
- Timing: intervalos medidos dos WAVs por segmento.
- Boca: envelope RMS do áudio PCM real; alinhamento fonético, palavras, fonemas e
  visemas não estão disponíveis e não são simulados.
- Revisão artística humana: obrigatória antes de qualquer publicação.

## Estrutura visual

A timeline contém 17 planos em cinco blocos editoriais: gancho, boas-vindas,
universo, histórias e convite. Santa aparece maior nas boas-vindas e no
encerramento e em medalhão discreto durante as paisagens. Os planos incluem:

1. Templo de Gaia e cristal.
2. Instante congelado.
3. Fissura luminosa.
4. Santa anfitrião.
5. Cidade de Topázio.
6. Panorama do mundo.
7. Caverna do Eco Etéreo.
8. Montanhas de Vordros.
9. Correntes e ventos.
10. Correntes Eternas.
11. Vulcão de Osai.
12. Emberion.
13. Floresta de Mirakel.
14. Guardiões reunidos.
15. Cristal elemental.
16. Santa encerrando o convite.
17. Lockup final do canal.

Movimentos de câmera, partículas, brilhos, névoa e transições são
determinísticos e aplicados sobre o renderizador Canvas existente. A prancha
de evidência inclui os 17 planos, em uma grade 4×5.

## Assets e proveniência

Dez placas novas de fantasia foram geradas localmente como arte conceitual
original para esta produção. Quatro imagens do piloto Topazioverse foram
reutilizadas por já possuírem proveniência registrada. Nenhuma dessas imagens
estabelece novos fatos canônicos sobre o manuscrito.

A trilha de referência Suno em `workspace/inputs/music/book1` foi auditada,
mas não foi usada porque as condições de publicação ainda precisam de revisão.
A produção usa música e efeitos sonoros procedurais, determinísticos e gerados
localmente para este vídeo. A liberação pública ainda requer revisão humana de
direitos e créditos.

Nenhum manuscrito, contexto privado, peso de modelo, credencial ou mídia
pessoal foi copiado para o repositório público. Os arquivos de mídia gerados
permanecem no diretório local de exports, fora do Git.

## Artefatos locais

O pipeline grava os resultados em:

`<workspace>/workspace/exports/cronicas-de-topazio-channel-intro/`

Os artefatos principais são:

- `cronicas-de-topazio-channel-intro.mp4`
- `timeline/cronicas-de-topazio-channel-intro.json`
- `timeline/cronicas-de-topazio-channel-intro.srt`
- `captures/cronicas-de-topazio-channel-intro-frames.png`
- `reports/technical-report.md`
- `reports/credits-and-provenance.md`

O script reutilizável é
`examples/cronicas_de_topazio_channel_intro_demo.py`. Ele suporta síntese,
composição de áudio, captura determinística, materialização em 30 FPS,
exportação FFmpeg e reconstrução da prancha sem nova síntese.

## Validação

- Suíte Python: `57 passed, 1 skipped, 22 subtests passed`.
- Testes específicos desta produção: `5 passed`.
- Testes frontend/Node: `143 passed`.
- Decodificação completa do MP4 com FFmpeg: aprovada.
- FFprobe: vídeo H.264 `1920×1080`, áudio AAC estéreo `48 kHz`, duração
  `82,100 s` no contêiner.
- Black-frame check com `blackdetect` para trechos contínuos de pelo menos
  `0,20 s`: nenhum trecho reportado.
- Níveis medidos da mix: pico `-7,8 dB`, média `-27,6 dB`.

O resultado está marcado como concluído tecnicamente, pendente de avaliação
humana da narrativa, continuidade visual, pronúncia, mixagem e adequação de
direitos para publicação no YouTube.
