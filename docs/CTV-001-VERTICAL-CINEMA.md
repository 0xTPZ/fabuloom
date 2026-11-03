# CTV-001 — Vertical Cinema do Livro 1

CTV-001 produz versões verticais para TikTok/Shorts a partir dos manifests,
WAVs medidos e assets locais aprovados dos capítulos 01–10.

## Contrato de saída

- Canvas: `1080×1920`, `9:16`, `30 fps`.
- Vídeo: H.264, pixel format `yuv420p`.
- Áudio: AAC estéreo, `48 kHz`.
- Voz: Kokoro `pm_santa`, `pt-BR`; os WAVs existentes são reutilizados.
- Santa V5 começa e termina na biblioteca oficial e permanece no medalhão nas
  cenas narrativas.
- Os planos verticais são compostos no Canvas com câmera cover, movimento
  atmosférico e legendas em área segura. O MP4 horizontal não é cortado,
  esticado ou usado como fundo.
- Assets de história sob `/characters/` são bloqueados; os planos usam apenas
  ambientes/objetos aprovados. A voz não recebe pitch, retiming, SSML,
  alinhamento fonético ou visemas inventados.

## Áudio e música

Cada capítulo recebe um `audio/music-cue-sheet.json` com a faixa, hash,
intervalo, crossfade, ducking e status de direitos. A mixagem usa a voz como
fonte prioritária, crossfades, compressor sidechain e limiter. Os direitos
comerciais das faixas Suno continuam pendentes de confirmação do proprietário.

## Execução e retomada

No worktree isolado:

```powershell
python examples/ctv_001_vertical_cinema.py --pilot-only --timeout 3600
python examples/ctv_001_vertical_cinema.py --start-chapter 2 --timeout 3600
```

O resultado fica em `E:\Fabuloom\workspace\exports\vertical-cinema-book1-v1`.
Cada capítulo possui `BATCH-STATUS`/stages, timeline vertical, SRT full e
teaser, cue sheet, pranchas, metadados, relatório e dois MP4s. A produção é
serializada por capítulo e não sobrescreve os exports históricos.

O `examples/finalize_ctv_001_batch.py` consolida o índice após uma retomada,
revalida os 20 MP4s com FFprobe/FFmpeg, gera capas e mantém incidentes
recuperados separados de falhas finais.

## Teasers e revisão

Cada teaser é um intervalo contínuo da narração original, com 25–45 segundos;
não há montagem de frases artificiais nem CTA falado. As pranchas de área
segura mostram as zonas reservadas para controles do TikTok, mas não são
inseridas no MP4.

A validação técnica não substitui a avaliação humana de enquadramento,
legibilidade, mixagem e aprovação artística. Nenhum vídeo é publicado
automaticamente.
