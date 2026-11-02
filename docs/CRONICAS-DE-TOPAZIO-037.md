# Crônicas de Topázio — capítulos 05–10

## Escopo

Missão 037 produz os capítulos 05 a 10 do Livro 1 em três lotes sequenciais:

- Lote A: capítulos 05 e 06.
- Lote B: capítulos 07 e 08.
- Lote C: capítulos 09 e 10.

O texto narrativo é extraído por limites de títulos do documento editorial local. O conteúdo integral do manuscrito não é duplicado nesta documentação pública.

## Pipeline

Cada capítulo é processado individualmente pelo runner `examples/topazio_book1_chapters_05_10_batch.py`:

1. validação do documento-fonte e da fronteira do capítulo;
2. storyboard com placas ambientais aprovadas;
3. narração Kokoro `pm_santa`, `pt-BR`, com duração medida por WAV;
4. segmentação preservando a ordem do texto, pausas de frase de 180 ms, pausas de pergunta de 320 ms e pausas de parágrafo de 350 ms;
5. composição de voz, música original e efeitos com ducking de prioridade da voz;
6. captura determinística do `NarratorAvatarRenderer` em 30 fps;
7. exportação H.264/yuv420p com áudio AAC estéreo a 48 kHz;
8. FFprobe, decode completo, blackdetect, SRT e verificação de presença do Santa.

Santa V5 (`santa-v5-base`) permanece no medalhão durante abertura, planos de história e encerramento na biblioteca oficial (`santa-library-topazioverse-v1`). Personagens DRAFT são bloqueados e os planos de história usam somente ambientes.

## Artefatos locais

Os resultados ficam fora do repositório Git em:

`workspace/exports/cronicas-book1-batch-05-10/`

Cada capítulo contém `manifest.json`, WAVs, timeline JSON, SRT, storyboard, MP4, prancha, metadados e relatórios. O arquivo `BATCH-STATUS.json` registra lote, capítulo, etapa, capítulos concluídos, falhas, tempo e próxima ação. A execução pode ser retomada a partir de um capítulo com `--start-chapter N`, sem recapturar capítulos anteriores concluídos.

## Limitações e revisão

- A duração e os tempos de segmentos são medidos nos WAVs; não há timestamps inventados de palavras, fonemas ou visemas.
- A Missão 032 não comprovou controle de pitch, SSML ou entonação emocional no adaptador Kokoro. A propriedade `expressive_question_intonation` permanece `not_verified`.
- A música original é preservada e os direitos comerciais da origem Suno continuam pendentes de confirmação do proprietário.
- Os testes técnicos não substituem a aprovação artística nem a audição humana dos episódios.

## Validação

Os seis vídeos devem ser 1920×1080, 30 fps, H.264, AAC estéreo a 48 kHz, sem intervalos detectados por blackdetect e com `ffmpeg_decode`, cobertura do texto-fonte e visibilidade de Santa aprovados.
