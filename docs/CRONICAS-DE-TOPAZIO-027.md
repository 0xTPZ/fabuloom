# Crônicas de Topázio — Livro 1, Capítulo 2

## Escopo

Missão 027 produz uma versão cinematográfica completa do Capítulo 2, **O minotauro e a cicatriz**, sem modificar as saídas das Missões 026 e 026.1.

O recorte é obtido pelo próprio DOCX em tempo de execução: título no parágrafo 24, narrativa nos parágrafos 25–46 e primeiro título do capítulo seguinte no parágrafo 47. O texto é preservado em `chapter2-source-excerpt.txt` e validado por SHA-256.

## Identidade visual autorizada

Santa V5 é a única identidade com status `APPROVED` no registry público. A produção chama `CharacterRegistry.require_approved("santa-v5-base")` e falha para qualquer identidade `DRAFT` ou `SUPERSEDED`.

As cenas da história são placas de ambiente e objetos narrativos. Não há retratos, silhuetas ou representações visuais dos guardiões conceituais DRAFT. Santa aparece como medalhão persistente no palco, usando `NarratorAvatarRenderer` e a mesma composição do Character Stage/Narrator Mode.

## Áudio e tempo

- Provedor: Kokoro `hexgrad/Kokoro-82M`.
- Voz: `pm_santa`, `pt-BR`.
- Cada segmento é um WAV medido; a duração do manifesto é composta a partir dos frames reais.
- Captions usam limites de segmentos.
- Timestamps de palavras, fonemas e visemas continuam indisponíveis; a boca usa somente RMS.
- Música: `workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3`.
- Mix: sidechain ducking voz→música, ratio 5, ataque 45 ms, release 650 ms, limiter 0.90.
- A confirmação dos direitos comerciais da faixa Suno continua pendente antes de qualquer publicação.

## Renderização

O runner `examples/topazio_book1_chapter2_cronicas_demo.py` reutiliza o limite de captura Canvas da V2, com 16 planos de ambiente, abertura/encerramento no cenário oficial `santa-library-topazioverse-v1`, transições de 900 ms e FFmpeg H.264/AAC em 1920×1080/30 FPS.

O HTML `frontend/capture-topazio-book1-chapter2.html` valida a política de personagens antes de carregar o manifesto, carrega a voz medida, usa o RMS em tempo absoluto e registra todos os quadros. Uploads de quadros possuem retry limitado para evitar que uma falha transitória invalide uma captura longa.

## Arte e aprovação

As novas placas ambientais foram geradas localmente como conceitos originais, sem personagens, e permanecem fora do Git em `workspace/exports`. Elas não constituem aprovação artística final. O MP4 deve ser avaliado humanamente antes de publicação.

## Saída de referência

`workspace/exports/topazio-book1-capitulo2-cronicas/videos/fabuloom-cronicas-de-topazio-livro1-capitulo2.mp4`

Relatórios técnicos, política de personagens, reuso da biblioteca, mixagem e visibilidade de Santa ficam em `workspace/exports/topazio-book1-capitulo2-cronicas/reports`.
