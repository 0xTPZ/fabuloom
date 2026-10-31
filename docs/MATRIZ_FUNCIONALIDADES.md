# Matriz de funcionalidades — MISSÃO 022

| Recurso | Interface | CLI/código | Classificação | Observação |
| --- | --- | --- | --- | --- |
| Dashboard | navegação e status local | — | funcional como shell | não cria projeto nem mede todos os componentes por conta própria |
| Projetos | lista demos e botão Novo desabilitado | contratos Core | incompleto | falta persistência de projeto e criação |
| Roteiro | campos e rascunho no navegador | `models.py`, `serialization.py` | experimental | não escreve livro/capítulo/cena no contrato |
| Cenas | leitura de perfis JSON | scripts Python de produção | experimental | não há editor de câmera, asset ou transição |
| Narradores | Santa V5, Dora e Alex | packs V2 e catálogo de vozes | parcial | Dora/Alex visuais não são a composição principal do Studio |
| Áudio | seleção de manifestos e playback | Kokoro opcional, WAVs | funcional com assets | não sintetiza a partir do texto pela interface |
| Prévia | Canvas, RMS, Play/Pause/Stop/seek | renderer compartilhado | funcional com assets | não substitui o compositor offline |
| Exportação | links para MP4 existentes | exemplos + FFmpeg | CLI/reference | não há job de renderização na interface |
| Área DEV | links para labs e Character Stage | Inspector/QA | experimental/legado | não é fluxo de produção garantido |
| Character Creator | não existe no Studio | contratos/renderer reutilizáveis | indisponível | plano separado para a MISSÃO 024 |
| Importação de mídia | não existe | validação de paths em packs | indisponível | exige política de segurança e UX |

## Classificação usada

- **Funcional:** executa uma operação real dentro dos limites declarados.
- **Experimental:** prova local ou rascunho sem contrato de produção completo.
- **CLI/reference:** existe fora da interface e requer intervenção técnica.
- **Indisponível:** não há implementação utilizável para o fluxo do usuário.

