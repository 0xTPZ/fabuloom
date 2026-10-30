# Visual Inspector V1.2

O Visual Inspector é uma ferramenta local de QA para o Character Engine. Ele
faz uma captura reproduzível, registra o plano de desenho resolvido, analisa
evidências estruturadas e produz imagens auxiliares para comparação. Ele não
edita código, assets, parâmetros ou relatórios anteriores automaticamente.

## Limites e arquitetura

```text
Character Stage / capture page
          |
          v
LayeredCharacterRenderer + LayeredCharacterRig
          |
          +--> frame JSON: layers, matrices, pivots, bounds, landmarks, pose
          |
          +--> PNG screenshot
                      |
                      v
               Inspector CLI
          /        |          \\
  frame QA   motion QA   PNG compare
          \\        |          /
                 report JSON + Markdown
```

`frontend/visual-inspector-capture.html` usa o mesmo caminho
`SantaV5SceneRenderer` → `LayeredCharacterRenderer` do palco e recebe apenas
requisições por HTTP de loopback. A captura não abre arquivos `file://` e não
carrega um segundo renderizador. O backend de navegador atual é o Edge
headless já instalado; nenhum pacote global é necessário.

`frontend/src/visual-inspector-core.mjs` é browser-safe e provider-neutral.
Ele diagnostica somente o que pode ser sustentado por dados: recursos e erros
de console, assets faciais duplicados, estado de piscada, regiões faciais,
lacunas entre landmark e pivô, razões de proporção, assimetria e saltos de
movimento. A severidade é `error`, `warning` ou `hypothesis`; evidência
insuficiente nunca é convertida em defeito confirmado.

O comparador local em `tools/visual-inspector/png.mjs` decodifica PNG RGBA,
usa tolerância de cor/alpha para antialiasing e gera razão de diferença,
limites suspeitos, máscara e overlay. OpenCV e Pixelmatch foram mantidos como
alternativas futuras, mas não são dependências desta V1: a implementação
embutida mantém a execução offline e não instala bibliotecas.

## Executar

De `E:\Fabuloom\studio`:

```powershell
node .\tools\visual-inspector\cli.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013"
```

Opções disponíveis:

```text
--output DIR       diretório de artefatos; o padrão fica em workspace/exports
--reference PNG    referência externa aprovada para comparação
--port PORT        porta loopback; o padrão é 8786
```

O comando grava `visual-inspection-report.json`, Markdown, PNGs capturados,
overlays e máscaras. A saída padrão inclui os estados Santa V5 neutro, rosto,
piscada, boca RMS, mãos, WAVE_HELLO, POINT_AT e pés. Os JSONs de captura
registram o tempo absoluto, estado da animação, matriz de cada camada, pivô,
dimensão intrínseca, bounds alfa e transformados, ordem Z, landmarks,
recursos carregados e erros observados.

## Interface DEV

Abra `http://127.0.0.1:8765/visual-inspector.html` depois de iniciar
`python .\frontend\server.py`. A página permite selecionar personagem e pose,
renderizar um quadro, ver landmarks e diagnósticos, carregar uma referência
PNG aprovada, exportar o JSON e rever o histórico da sessão. A página usa o
mesmo renderer do palco; é uma ferramenta de inspeção, não um editor.

## Fluxo de correção

1. Capturar e ler o relatório estruturado.
2. Formular uma hipótese com base nos landmarks, matrizes, imagens e severidade.
3. Aplicar uma correção em branch isolada, fora do Inspector.
4. Reexecutar testes, capturas e comparações.
5. Fazer revisão humana das imagens e do vídeo antes de aceitar a alteração.

O Inspector não decide qualidade artística por igualdade de pixels e não
produz timestamps fonéticos. RMS continua sendo apenas uma entrada visual de
boca. A ausência de um modelo de visão é suportada: a análise primária é
determinística e a revisão humana continua obrigatória.

## Validação de defeitos conhecidos — V1.1

O banco controlado em `tools/visual-inspector/fixtures.mjs` muta somente
frames JSON derivados de um frame conhecido-good. Ele não altera PNGs oficiais
nem o pack. As fixtures cobrem cabeça pintada com overlays, olhos fechados,
mão deslocada, mão pequena, pé deslocado, ombro desconectado, antebraço no lado
errado do torso, proporção de cabeça alterada e salto temporal de articulação.

Cada resultado registra códigos esperados, severidade, camadas/região,
evidência, falsos positivos e falsos negativos. A CLI gera um PNG full-frame
com a região suspeita destacada em `fixtures/` e o pacote
`visual-inspection-evidence.json`. O quadro conhecido-good também é medido para
falsos positivos.

Os checks de interseção usam bounds alfa transformados medidos dos assets. Eles
são evidência visual conservadora: podem confirmar uma lacuna ou uma mudança
de silhueta, mas não afirmam a interseção exata de cada pixel em uma junta
oculta por roupa. Os limiares são configuráveis por relação e personagem;
WAVE_HELLO, por exemplo, tem tolerância de ombro diferente do repouso.

## Estado da primeira inspeção Santa V5

A captura V1.1 produz quadros com o plano do personagem resolvido em
680×1550 e screenshots de apresentação full-frame em 680×1920 (close facial em
680×520), incluindo três amostras temporais de IDLE, WAVE_HELLO e POINT_AT. O
relatório terminou com zero erros, zero avisos e zero hipóteses no personagem
oficial. Isso significa
“nenhum erro verificável nos dados capturados”, não aprovação artística final.
As comparações neutro versus piscada, boca, WAVE_HELLO e POINT_AT foram
geradas como evidência visual auxiliar. As nove fixtures foram detectadas com
100% de detecção, 0 falsos positivos no frame conhecido-good e regiões
compatíveis. A análise por IA não foi executada.

## Validação em imagens históricas reais

Mission 013.2 adiciona `tools/visual-inspector/real-cli.mjs` e o módulo
browser-safe `frontend/src/real-image-inspector.mjs`. Essa trilha não usa as
fixtures JSON da V1.1: ela lê PNGs reais extraídos dos MP4s V3, V4 e V5, mais
uma captura isolada do asset histórico preservado. Cada entrada registra
origem, versão, tempo, dimensões, SHA-256 e condições de captura em
`historical-dataset-manifest.json`.

O fluxo cego é obrigatório. O analisador recebe pixels, uma região ampla de
composição e, quando disponível, uma referência geral; não recebe o rótulo ou
a localização exata do defeito. `blind-results.json` é gravado antes do
arquivo de revisão humana. A avaliação posterior separa defeito confirmado,
diferença de direção artística entre versões, amostra limpa e evidência
inconclusiva.

O analisador mede transparência, máscara de foreground, componentes conectados,
limites de silhueta, densidade de borda, regiões faciais/laterais/pés e
diferença de pixels. Frames de vídeo são opacos; portanto, a segmentação é
heurística e não confirma juntas ocultas pela roupa. Os resultados de pixels
continuam sendo hipóteses até revisão humana e não são misturados à taxa das
fixtures estruturadas.

O contrato opcional `VisualAnalysisProvider` define `analyzeImage`,
`analyzeSequence`, `capabilities` e `providerMetadata`. O provider padrão está
indisponível e offline; a execução registra `not-executed`, não inventa uma
resposta de IA e não envia imagens para serviços externos.

Para executar:

```powershell
node .\tools\visual-inspector\real-cli.mjs `
  --workspace "E:\Fabuloom" `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.2-real\real-run" `
  --review "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.2-real\historical-review.json"
```

Para inspeção manual sem o Character Stage, abra
`http://127.0.0.1:8765/visual-inspector-real.html` e selecione um PNG local.

## Visual QA Gate V1.3

Mission 013.3 adiciona `tools/visual-inspector/qa-gate.mjs` e a página DEV
`/visual-qa.html`. O gate monta um plano determinístico para Santa V5 com
início/fim, keyframes, quadros intermediários, extremos, estados faciais,
contatos e trocas de pose. Cada captura carrega o motivo de sua seleção e é
produzida pelo mesmo `LayeredCharacterRenderer` usado no palco.

Execução técnica somente:

```powershell
node .\tools\visual-inspector\qa-gate.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-qa\mission-013.3" `
  --port 8813
```

O ciclo experimental de correção histórica compara a variante preservada
`historical-head-original` com a variante de produção `production-v5`:

```powershell
node .\tools\visual-inspector\qa-gate.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-qa\mission-013.3" `
  --port 8813 --correction --max-attempts 1
```

O ciclo possui limite de tentativas, evidência antes/depois, máscara, overlay,
estado de reversão e escopo explícito `experimental-historical-replay`. Ele não
sobrescreve assets oficiais. O pacote `visual-qa-evidence.json` e a interface
DEV exibem o histórico, os frames selecionados, o gate técnico e a revisão
artística pendente. Sem um `VisualAnalysisProvider` configurado, o resultado é
`not-executed`; nenhum modelo ou serviço externo é simulado.

## Visual Quality Recovery — Mission 014

Mission 014 executou o gate sobre o Santa V5 em resolução de produção
1080×1920, com 60 capturas: repouso, rosto, fala, piscada, mãos, pés,
`WAVE_HELLO`, `POINT_AT` à direita e `POINT_AT` à esquerda. A revisão humana
das PNGs reais encontrou uma deriva de composição: clips nomeados herdavam o
`characterX` do walk-in V3. A causa foi corrigida com `SantaV5SceneRenderer.sceneAt`,
que ancora apenas os clips V5 sem alterar o rig ou os assets.

Também foi corrigido o enquadramento do alvo esquerdo de `POINT_AT`: a
composição usa uma âncora de apresentação x=180 quando o braço esquerdo está
ativo, evitando cortar a manga no limite interno do canvas. A resolução full
frame da CLI passou de 680 para 1080 pixels; close-ups faciais continuam
compactos por desenho.

O relatório e a prancha visual ficam somente no workspace:

```text
E:\Fabuloom\workspace\exports\visual-qa\mission-014\mission-014-visual-quality-report.md
E:\Fabuloom\workspace\exports\visual-qa\mission-014\santa-v5-visual-quality-board.png
```

Os vídeos de revisão são gerados pelos exemplos reais do Character Engine:
`fabuloom-santa-v5-wave-hello.mp4` e `fabuloom-santa-v5-point-at.mp4`, em
1080×1920 H.264. A inspeção multimodal realizada nesta missão foi a leitura
local das imagens geradas; nenhum provider de visão externo foi executado.
O gate técnico passou, mas a aprovação artística continua humana.
