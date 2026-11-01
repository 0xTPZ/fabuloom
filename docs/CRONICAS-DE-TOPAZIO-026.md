# Crônicas de Topázio — Livro 1, Capítulo 1

MISSÃO 026 produz o primeiro episódio cinematográfico completo de
`O Despertar dos Cristais`, preservando o texto literário e usando Santa V5
como anfitrião da abertura e do encerramento.

## Resultado local

- Branch: `mission-026-book1-chapter1`.
- Saída: `E:/Fabuloom/workspace/exports/topazio-book1-capitulo1-cronicas/videos/fabuloom-cronicas-de-topazio-livro1-capitulo1.mp4`.
- Formato: 1920×1080, 30 FPS, H.264, AAC estéreo 48 kHz.
- Duração medida: `389.445 s`.
- Manifesto: 102 segmentos Kokoro medidos.
- Cenas: 12 cenas de abertura, capítulo e encerramento.
- Texto: parágrafos DOCX `3–22`, conferidos contra a fonte sem resumo ou alteração.

Os arquivos gerados, WAVs, capturas, pranchas e relatórios ficam somente no
workspace local. O manuscrito não é copiado para o Git.

## Pipeline

1. A abertura e o encerramento editorial são sintetizados com Kokoro
   `pm_santa` / `pt-BR`.
2. Os 46 segmentos já medidos do piloto são preservados e copiados localmente;
   os parágrafos restantes do capítulo são sintetizados com o mesmo provedor.
3. A timeline registra `HOST_INTRO`, `STORY_CHAPTER` e `HOST_OUTRO`, com
   transições editoriais de 900 ms.
4. A voz é composta pelo tempo real dos WAVs. Palavras, fonemas e visemas são
   declarados indisponíveis; a boca continua usando apenas RMS no Canvas.
5. O Canvas usa `NarratorAvatarRenderer` para Santa V5 e a mesma biblioteca
   oficial `santa-library-topazioverse-v1` na abertura e no encerramento.
6. O tema Suno fornecido pelo proprietário é prolongado com loop crossfaded,
   recebe ducking sidechain sob a voz, SFX determinísticos e limiter antes do
   mux H.264/AAC.

## Cenários

As placas de Topázio, Caverna do Eco, Correntes Eternas, Vordros, mar,
Vulcão de Osai e vila em incêndio são arte conceitual original gerada
localmente para este episódio. Não são ilustrações canônicas nem substituem
uma aprovação artística humana.

A biblioteca oficial é registrada no contrato público
[`SCENE-ASSET-REGISTRY.md`](SCENE-ASSET-REGISTRY.md). O PNG-base não contém
Santa, e o personagem é aplicado pelo renderizador real.

## Verificações

- Python: `64 passed, 1 skipped, 22 subtests passed`.
- Node/frontend: `143 passed`.
- DOCX: 20 parágrafos conferidos; textos dos segmentos de história conferidos
  por parágrafo.
- FFmpeg: decodificação completa aprovada; nenhum intervalo preto contínuo foi
  detectado pelo `blackdetect` usado no gate.
- FFprobe: duração `389.445 s`, 1920×1080, H.264, AAC, 48 kHz, 2 canais.
- Amostras de nível PCM início/meio/fim: picos entre `-3.7 dB` e `-6.1 dB`,
  sem clipping técnico.
- Biblioteca: ID resolvido duas vezes na timeline, SHA-256
  `1e38477edd9e62d5aa5ae7d63d4784f3c5fd5b65a6486fbc1b187c0933395770`.

## Estado de revisão

O resultado está `completed_pending_human_artistic_review`. A origem Suno foi
registrada como fornecida pelo proprietário; a confirmação de direitos
comerciais continua obrigatória antes de qualquer publicação. Nenhum merge ou
upload automático foi realizado.
