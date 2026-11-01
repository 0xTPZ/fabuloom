# Missão 040 — Alpha 0.1.0 Final Gates

Data: 2026-11-01  
HEAD auditado: `663f124`  
Branch: `release/fabuloom-alpha-preparation`  
PR #33: Draft  
Decisão: **NO-GO para Alpha externa até fechar os gates obrigatórios**

## Gate 1 — Instalação Kokoro

**Classificação: PASS técnico / PARTIAL para experiência integralmente gráfica.**

O relatório `docs/CLEAN-USER-ACCEPTANCE-033.md` comprova checkout independente, venv novo, `HF_HOME` inicialmente vazio, instalação opcional `kokoro==0.9.4`, download oficial do `hexgrad/Kokoro-82M` e síntese real `pm_santa`. Isso prova instalação técnica independente e instalação assistida por terminal. Não prova instalação integralmente gráfica: o pacote ainda exige comandos para criar venv, instalar o extra e iniciar o servidor. Não repeti o download pesado.

## Gate 2 — Canvas × FFmpeg

**Classificação: PARTIAL.**

`docs/VISUAL-PARITY-GATE-0301.md` comprova correções matemáticas para estático, zoom, pan horizontal e pan vertical, com tolerância geométrica definida, e MP4 real com quadros FFmpeg. Porém, a própria evidência registra que a captura pixel-a-pixel do Canvas real nos cinco instantes de cada movimento não foi concluída. Os testes de contrato não substituem a prancha Canvas | FFmpeg | Diferença exigida neste gate. Não declarar paridade visual completa.

## Gate 3 — Importação nativa Windows

**Classificação: PARTIAL, não FAIL.**

A importação e exportação com assets foram comprovadas tecnicamente em missões anteriores, mas a automação CUA desta auditoria não controla o diálogo nativo. Isso não prova defeito da interface. O teste manual reproduzível é: iniciar `Iniciar Fabuloom.bat`; criar `Gate 040`; abrir Cenas; escolher `C:\Temp\fabuloom-alpha-037-audit\images\grid-landscape.png`; conferir miniatura; salvar; fechar/reabrir; exportar MP4. Falta aprovação humana ou harness Windows compatível para transformar este gate em PASS.

## Gate 4 — Licenças e proveniência

**Classificação: PARTIAL / BLOCKED para pacote redistribuível.**

O código original é MIT. O pacote Kokoro `0.9.4` e o modelo `hexgrad/Kokoro-82M` têm origem/licença Apache-2.0 identificadas para uso local. Ainda faltam notices versionados e uma proveniência fechada para vozes, PyTorch, Misaki, eSpeak-ng/phonemizer, build específico de FFmpeg e qualquer pacote futuro. Fontes Windows não são redistribuídas. O inventário completo está em `docs/THIRD-PARTY-LICENSE-INVENTORY-040.md`. Nenhum modelo, voz, runtime ou binário foi adicionado ao Git.

## Segurança

**Classificação: PASS local com ressalvas.**

O servidor restringe requisições a loopback, valida caminhos dentro do workspace, usa argumentos estruturados para subprocessos e não usa `shell=True`. O servidor não deve ser exposto à rede. O canal privado de reporte de vulnerabilidades ainda não está formalizado.

## Regressão

- Python: `46 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- Diagnóstico: Python 3.12.10, Node 24.19.0, FFmpeg/FFprobe 9.0.1.
- Timeline da Missão 038: MP4 real de 196,57 s, AAC 48 kHz, diferença áudio/vídeo de 0,003333 s.
- Nenhuma funcionalidade nova foi implementada nesta missão.

## Matriz de decisão

### OBRIGATÓRIO — bloqueia Alpha externa

- comprovar instalação Kokoro completa em checkout limpo sem depender de cache público implícito;
- concluir captura real Canvas×FFmpeg e prancha para os quatro movimentos e três proporções;
- validar importação pelo seletor nativo em Windows;
- fechar notices e proveniência de todas as dependências efetivamente redistribuídas.

### RECOMENDADO

- formalizar canal privado de segurança;
- automatizar recovery de exportação interrompida;
- reduzir passos de terminal no bootstrap do Kokoro.

### FUTURO

- novos narradores, efeitos e transições;
- editor nonlinear avançado;
- timestamps fonéticos/visemas;
- exposição fora de loopback;
- instalador/distribuição complexa.

## Conclusão

**NO-GO.** A base técnica está funcional e a timeline foi comprovada, mas quatro gates obrigatórios permanecem incompletos. A decisão pode mudar para GO após evidências finais desses gates, sem expansão de escopo.

`E:\Fabuloom\studio` e os ambientes Topazioverse permaneceram intactos.
