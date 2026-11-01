# Crônicas de Topázio — Livro 1, Capítulo 3

## Escopo

Missão 028 produz uma versão cinematográfica completa do Capítulo 3,
**Sete caminhos para Gaia**, preservando as saídas das Missões 026, 026.1 e
027.

O recorte é lido do DOCX em tempo de execução: título no parágrafo 47,
narrativa nos parágrafos 48–105, separador no 106 e título do Capítulo 4 no
107. O texto é salvo em `timeline/chapter3-source-excerpt.txt` e validado por
SHA-256:
`ec9da4e1db6bc52274562c7fc94c11e021456e6da96b0b4f228eecab563fbb3e`.

## Identidade visual autorizada

Santa V5 é a única identidade com status `APPROVED` no registry público. O
runner chama `CharacterRegistry.require_approved("santa-v5-base")` antes da
composição. Os sete conceitos de guardiões permanecem `DRAFT` e são bloqueados
pela política `approved_only`/`draft_rendering: blocked`.

As 20 cenas de história são `environment_only`: cidades, templo, cristal,
fissuras, luz, fogo, água, gelo e detritos. Nenhuma placa desenha um guardião
ou silhueta de personagem. A abertura, o encerramento e o medalhão persistente
reutilizam `santa-library-topazioverse-v1` por seu registro estável, sem
regenerar a arte aprovada.

## Áudio e tempo

- Provedor: Kokoro `hexgrad/Kokoro-82M`.
- Revisão do modelo: `f3ff3571791e39611d31c381e3a41a3af07b4987`.
- Voz: `pm_santa`, `pt-BR`.
- 153 segmentos WAV medidos; duração total do manifesto: 512.660 ms.
- Captura e legendas usam os limites reais dos segmentos.
- Timestamps de palavras, fonemas e visemas não estão disponíveis; a boca do
  Santa usa somente envelope RMS em tempo absoluto.
- Música: `workspace/inputs/music/book1/Topázio — O Despertar dos Cristais _ Tema do Despertar.mp3`.
- Mix: sidechain ducking voz→música, ratio 5, ataque 45 ms, release 650 ms,
  cama musical 0.13 e limiter final 0.90.
- A confirmação dos direitos comerciais da faixa Suno continua necessária
  antes de publicação.

## Renderização

O runner `examples/topazio_book1_chapter3_cronicas_demo.py` reutiliza os
helpers da produção do Capítulo 2 e a página determinística do Character Stage.
Ele gera 20 planos de ambiente, abertura/encerramento na biblioteca oficial,
transições de 900 ms e captura Canvas em 1920×1080/30 FPS. O FFmpeg recebe os
quadros capturados e o mix medido, produzindo H.264/AAC.

As placas ambientais foram criadas com a ferramenta imagegen disponível no
ambiente, apenas para cenários e objetos, sem geração de personagens. São
conceitos originais de produção local, ficam fora do Git em
`workspace/exports/topazio-book1-capitulo3-cronicas/assets/generated` e exigem
avaliação artística humana antes de qualquer promoção.

## Reprodução local

Com o ambiente Kokoro local disponível:

```powershell
$env:PYTHONPATH = "src;examples"
& "G:\TopazioReader\tts\kokoro-test\.venv\Scripts\python.exe" `
  examples\topazio_book1_chapter3_cronicas_demo.py --overwrite --port 8780
```

Os testes de contrato executam sem internet, GPU ou modelos reais; a produção
local acima usa o modelo Kokoro existente apenas para gerar o episódio real.

## Saídas e aprovação

Vídeo de referência:

`workspace/exports/topazio-book1-capitulo3-cronicas/videos/fabuloom-cronicas-de-topazio-livro1-capitulo3.mp4`

Prancha:

`workspace/exports/topazio-book1-capitulo3-cronicas/captures/chapter3-frames.png`

Relatórios de técnica, política de personagens, reuso da biblioteca, mixagem e
visibilidade ficam em `workspace/exports/topazio-book1-capitulo3-cronicas/reports`.
O estado é `completed_pending_human_artistic_review`; nenhum merge ou publicação
externa faz parte desta missão.
