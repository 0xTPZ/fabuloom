# Crônicas de Topázio — Refinamento Cinematográfico V2

Esta entrega preserva o episódio da Missão 026 e cria uma composição V2
independente para o Capítulo 1.

## Correção visual

Na V1, o HTML de captura calculava `narratorVisible` somente quando a cena
ativa era `host`. Por isso Santa aparecia na biblioteca de abertura e
encerramento, mas desaparecia durante o bloco `STORY_CHAPTER`, embora a voz
continuasse funcionando. A V2 usa o mesmo `NarratorAvatarRenderer` Santa V5 e
desenha um medalhão menor e persistente no canto inferior esquerdo em todas as
cenas de história. A captura foi concluída com 11.684/11.684 quadros e a
prancha dos 38 planos foi inspecionada.

## Storyboard

O episódio passou de 12 cenas na V1 para 38 cenas na V2: 36 planos de história,
mais abertura e encerramento. Os cortes são derivados de limites de segmentos
de áudio medidos e usam planos gerais, médios, closes, detalhes e retratos
conceituais alinhados aos acontecimentos do DOCX. Não há mudança no texto,
ordem, duração ou IDs dos segmentos.

## Áudio

Os 102 WAVs medidos da Missão 026 foram reutilizados sem nova síntese. A música
original fornecida pelo proprietário é preservada em velocidade e tom, com
volume base V2 `0.13`, ducking sidechain voz→música ratio `5`, ataque `45 ms`,
release `650 ms`, SFX `0.12` e limiter `0.90`. A comparação PCM integral
registrou V1 `-25,6/-3,7 dB` (média/pico) e V2 `-25,3/-3,5 dB`. A avaliação de
inteligibilidade e aprovação musical continua humana.

## Saídas

- MP4: `E:/Fabuloom/workspace/exports/topazio-book1-capitulo1-cronicas-v2/videos/fabuloom-cronicas-de-topazio-livro1-capitulo1-v2.mp4`
- Manifesto: `.../manifest.json`
- Timeline: `.../timeline/topazio-book1-capitulo1-cronicas-v2.json`
- Prancha de quadros: `.../captures/chapter1-v2-frames.png`
- Comparação: `.../captures/v1-v2-comparison.png`
- Prancha de personagens: `.../captures/character-proposals-board.png`

Formato final: 1920×1080, 30 FPS, H.264, AAC estéreo 48 kHz, duração
`389,445 s`.

Timestamps de palavras, fonemas e visemas permanecem indisponíveis; a boca de
Santa continua baseada no envelope RMS real.

As novas imagens foram geradas localmente como arte conceitual original e
estão marcadas como `DRAFT` quando representam personagens não aprovados.
Direitos comerciais da faixa Suno ainda precisam ser confirmados antes de
qualquer publicação.
