# Visual Inspector V1.1

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
