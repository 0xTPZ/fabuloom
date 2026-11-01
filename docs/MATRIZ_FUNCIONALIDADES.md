# Matriz de funcionalidades — MISSÃO 027

| Recurso | Interface | CLI/código | Classificação | Observação |
| --- | --- | --- | --- | --- |
| Dashboard | navegação, orientação e status local | — | funcional como shell | diagnóstico completo depende do ambiente local |
| Projetos | criação, persistência e reabertura | API local + `project.json` | funcional Alpha | edição avançada ainda não existe |
| Roteiro | texto persistente e segmentação por sentença | modelos/serialização | funcional Alpha | não é editor nonlinear completo |
| Cenas | importação de imagens e associação por cena | validação de paths | funcional Alpha | câmera avançada permanece limitada |
| Narradores | Santa V5, Dora e Alex | packs V2 e catálogo de vozes | parcial | Dora/Alex visuais não são a composição principal do Studio |
| Áudio | geração Santa, manifesto medido e playback | Kokoro opcional, WAVs | funcional Alpha | requer pacote/modelo Kokoro para síntese |
| Prévia | Canvas, RMS, Play/Pause/Stop/seek | renderer compartilhado | funcional Alpha | não substitui o compositor offline |
| Exportação | job assíncrono, progresso e link MP4 | FFmpeg local | funcional Alpha | horizontal 1920×1080 nesta UI |
| Área DEV | links para labs e Character Stage | Inspector/QA | experimental/legado | não é fluxo de produção garantido |
| Character Creator | não existe no Studio | contratos/renderer reutilizáveis | indisponível | plano separado para a MISSÃO 024 |
| Importação de mídia | imagens e trilha opcional por projeto | validação de MIME/tamanho/path | funcional Alpha | formatos deliberadamente limitados |

## Classificação usada

- **Funcional:** executa uma operação real dentro dos limites declarados.
- **Experimental:** prova local ou rascunho sem contrato de produção completo.
- **CLI/reference:** existe fora da interface e requer intervenção técnica.
- **Indisponível:** não há implementação utilizável para o fluxo do usuário.

