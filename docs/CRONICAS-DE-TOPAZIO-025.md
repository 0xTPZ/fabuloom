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

## MISSÃO 025.1 — trilha Suno e mix V2

A versão aprovada visualmente foi preservada em seu arquivo original. A V2
reutiliza exatamente os mesmos 2463 frames, a timeline, as legendas e a
narração, trocando somente a camada sonora.

- Música: `Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3`.
- Origem registrada: faixa original fornecida pelo proprietário e gerada com
  Suno; os direitos comerciais para publicação ainda precisam ser confirmados.
- Ducking: sidechain da voz sobre a música com ratio 8, ataque de 35 ms e
  release de 700 ms. Os SFX recebem ducking moderado separado para não competir
  com Santa.
- Controle final: fades suaves, `alimiter` com limite 0,92 e sem alteração de
  velocidade ou tom da música.
- Preservação verificada: `framemd5` com `2463` frames em cada vídeo e `0`
  diferenças entre original e V2.
- Nova saída: `<workspace>/workspace/exports/cronicas-de-topazio-channel-intro/cronicas-de-topazio-channel-intro-v2.mp4`.
- Trechos de revisão humana: `reviews/cronicas-de-topazio-channel-intro-v2-review-{inicio,meio,fim}.wav`.

A inteligibilidade subjetiva deve ser confirmada ouvindo os três trechos e o
vídeo completo antes de qualquer publicação. A mídia continua fora do Git.
