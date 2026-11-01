# Missão 041 — Alpha Final Evidence

Data: 2026-11-01  
HEAD de entrada: `711a6d2`  
Branch: `release/fabuloom-alpha-preparation`  
PR #33: Draft  
Decisão: **NO-GO neste ciclo**

## 1. Canvas real × FFmpeg

**Resultado: PARTIAL.**

Foi aberto o Studio real em loopback com o workspace de auditoria e acessada a rota Prévia. O DOM confirmou o Canvas real:

`<canvas id="studio-preview" width="1920" height="1080" aria-label="Prévia do Narrator Mode com Santa V5">`

O Canvas foi trazido para o viewport por locator e capturado por screenshot; a captura exibiu a grade horizontal original `LANDSCAPE 037` no palco. Isso comprova que a prévia usa um bitmap real do projeto, não somente o cálculo matemático.

O bloqueio restante é técnico da superfície de automação: o avaliador de página expõe o elemento Canvas e suas dimensões, mas remove métodos de protótipo como `toDataURL`; a captura por screenshot não foi exportada pelo ambiente para um arquivo local comparável automaticamente. Por isso, não é possível produzir honestamente a prancha pixel-a-pixel dos 20 pontos nesta execução.

Evidências anteriores continuam válidas para os quadros FFmpeg, o MP4 real e os contratos geométricos de estático, zoom, pan horizontal e pan vertical. A alternativa executável é: abrir a rota Prévia com um Playwright/Chromium que permita `locator('canvas').screenshot()` ou `canvas.toDataURL()`, capturar 0/25/50/75/último frame para cada cena, extrair os mesmos timestamps com FFmpeg e comparar bordas/marcadores com tolerância de 1 px lógico. A matriz 030.1 permanece PARTIAL até essa captura ser realizada.

## 2. Escopo de distribuição e licenças

**Resultado: PASS para a modalidade source-only; BLOCKED para pacote empacotado futuro.**

A Alpha avaliada publica somente:

- código original Fabuloom sob MIT;
- documentação, testes e assets originais versionados;
- nenhum modelo, voz, WAV, MP4, cache, runtime Python, FFmpeg, fonte Windows ou binário externo.

O usuário instala dependências separadamente a partir de suas fontes oficiais. Kokoro 0.9.4 e o modelo `hexgrad/Kokoro-82M` foram identificados como Apache-2.0 para uso local; isso não autoriza empacotar vozes, PyTorch, eSpeak-ng, FFmpeg ou transitivas sem notices e revisão própria.

`git ls-files` não encontrou arquivos de modelo, áudio, vídeo, fonte, executável ou DLL. O inventário detalhado está em `docs/THIRD-PARTY-LICENSE-INVENTORY-040.md`.

## 3. Kokoro

**Resultado: PASS técnico independente / PARTIAL na preparação assistida / NOT IMPLEMENTED graficamente.**

O relatório 033 comprova checkout independente, venv novo, HF_HOME inicialmente vazio, instalação opcional, download oficial do Kokoro-82M e síntese real `pm_santa`. Não foi repetido download pesado. A instalação totalmente gráfica não faz parte da modalidade source-only aprovada e continua explicitamente documentada como inexistente.

## 4. Importação Windows

**Resultado: PARTIAL, pendente de validação humana.**

A tentativa de evento `filechooser` no navegador in-app expirou; isso demonstra uma limitação da superfície de automação, não um defeito confirmado do seletor. O roteiro manual permanece: iniciar `Iniciar Fabuloom.bat`, criar projeto, abrir Cenas, selecionar `C:\Temp\fabuloom-alpha-037-audit\images\grid-landscape.png`, conferir miniatura, salvar, reabrir e exportar. A aprovação do proprietário continua necessária.

## 5. Testes consolidados

- Python: `46 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- Diagnóstico Windows: Python 3.12.10, Node 24.19.0, FFmpeg/FFprobe 9.0.1.
- Timeline 038: MP4 real de 196,57 s, AAC 48 kHz, diferença áudio/vídeo de 0,003333 s.
- Segurança: loopback-only, containment de paths, subprocessos sem `shell=True`.

## 6. Decisão

**NO-GO para declarar a Alpha pronta para testadores externos neste ciclo.**

A modalidade source-only está juridicamente delimitada e o núcleo técnico funciona, mas dois gates de evidência permanecem incompletos: captura pixel-a-pixel Canvas×FFmpeg e aprovação do seletor nativo Windows. O proprietário pode usar o roteiro manual para decidir uma Alpha experimental restrita, mas esta auditoria não pode converter esses gates pendentes em GO.

Nenhuma funcionalidade nova foi criada. `E:\Fabuloom\studio` permaneceu intacto. Não houve merge nem release.
