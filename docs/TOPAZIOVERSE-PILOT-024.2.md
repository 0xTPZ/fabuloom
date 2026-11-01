# Topazioverse — piloto V2 com trilha original e narrador permanente

Esta entrega preserva o piloto V1 e produz uma V2 usando a trilha instrumental fornecida pelo proprietário e gerada no Suno:

`Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3`

## Implementação

- O texto do livro e o manifesto Kokoro da V1 foram preservados.
- O WAV de voz já produzido para `pm_santa` foi reutilizado; não houve nova síntese.
- Santa V5 permanece visível durante toda a narrativa, com boca RMS e movimento facial discreto durante pausas.
- A legenda usa área deslocada para a direita, preservando o rosto e o medalhão.
- A música recebe fade-in/out, redução inicial, ducking por sidechain e limiter.
- A captura facial usa 15 FPS-fonte e materializa quadros adjacentes para um contêiner final de 30 FPS; isso evita manter um quadro congelado por longos períodos sem tornar a captura local inviável.

## Medições da música original

- Codec: MP3; 48 kHz; estéreo; 202,8535 s.
- Volume médio: `-15,9 dB`; pico amostrado: `-1,5 dBFS`.
- Loudness integrado: `-13,8 LUFS`; LRA: `7,4 LU`; true peak: `-1,5 dBFS`.
- A faixa é tratada como instrumental conforme fornecida pelo proprietário. FFprobe não comprova ausência de vocais; direitos de publicação continuam sujeitos à confirmação do plano e dos termos aplicáveis ao Suno.

## Saída

Os artefatos V2 ficam exclusivamente em `E:\Fabuloom\workspace\exports\topazioverse-book1-episode1-pilot-v2\`, incluindo o MP4, mix PCM, amostras, prancha V2 e comparação V1/V2. A faixa original não é copiada para o GitHub.

A validação técnica usa FFprobe e decodificação FFmpeg. A avaliação subjetiva da inteligibilidade da voz, equilíbrio musical e aprovação artística continua sendo humana.
