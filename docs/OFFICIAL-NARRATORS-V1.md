# Official Narrators V1 — MISSÃO 023

Status: `AWAITING_ART_APPROVAL`

Esta missão conecta Dora, Santa V5 e Alex ao mesmo caminho de renderização facial
do Narrator Mode, mantendo a identidade visual e a voz como uma seleção única.
Nenhum merge automático foi realizado.

## Auditoria dos assets

Foram encontrados três níveis para Dora e Alex:

- `frontend/assets/characters/topazio-narrators/dora.png` e `alex.png`: retratos
  V1 transparentes, visualmente consistentes com o uniforme azul-marinho, azul
  profundo e dourado. São referências de identidade, não rigs articuláveis.
- `frontend/assets/characters/topazio-narrators-v2/`: packs `animation-ready/0.1`
  com camadas SVG locais para cabeça, cabelo, olhos, pálpebras, sobrancelhas,
  boca, tronco, braços, antebraços, mãos e acessório. São uma base técnica
  reutilizável, ainda não arte final cinematográfica.
- `frontend/assets/characters/topazio-narrators-v3/`: bases ilustradas refeitas
  para Dora e Alex, com o mesmo acabamento semi-realista, uniforme Topazioverse,
  proporções faciais preservadas e placas transparentes de pálpebras e boca
  alinhadas ao mesmo canvas. São uma geração experimental pronta para o
  Narrator Mode, ainda sujeita à aprovação artística humana.

Os assets são registrados no repositório como material original local do
Fabuloom; não foi encontrada fonte externa por arquivo ou licença de terceiros
nos diretórios auditados. A confirmação final de autoria artística continua
sendo responsabilidade do proprietário antes de promover Dora ou Alex para
produção.

Santa V5 permanece usando `frontend/src/santa-v5-pack.mjs` e os assets oficiais
em `frontend/assets/characters/topazio-narrators-v5/santa/`. Eles não foram
substituídos nem reescritos.

## Contrato de seleção

| personagem | voz | idioma | pack visual atual | estado |
| --- | --- | --- | --- | --- |
| Santa V5 | `pm_santa` | `pt-BR` | V5 facial corrigido | produção |
| Dora | `pf_dora` | `pt-BR` | V3 artístico experimental próprio | aguardando aprovação artística |
| Alex | `pm_alex` | `pt-BR` | V3 artístico experimental próprio | aguardando aprovação artística |

`NarratorAvatarRenderer` agora aceita a identidade visual por `characterId` e
troca o pack por `setPack()` no mesmo renderer. O `AudioTimelinePlayer` continua
independente. A troca somente é confirmada depois de o manifesto, o `voice_id`
real e o pack visual terem sido carregados; respostas obsoletas são descartadas
por token de carregamento.

O `NarratorSceneRenderer` recebe o nome e a voz efetivamente selecionados. A
boca continua sendo uma aproximação por amplitude RMS do áudio real. Não são
inventados tempos de palavras, fonemas ou visemas.

## Prancha e demonstração

A prancha executável usa o mesmo `NarratorAvatarRenderer` do Studio e exibe
Santa, Dora e Alex em estados neutro, fala RMS, piscada e movimento de cabeça:

`frontend/official-narrators-board.html`

Ela usa o mesmo renderer para estados neutro, sorriso, boca aberta por RMS,
piscada e movimento de cabeça, com capturas ampliadas de Dora V3 e Alex V3; a
referência Santa V5 permanece preservada. A página informa explicitamente
`AWAITING_ART_APPROVAL`. Os arquivos de áudio, manifests, frames,
MP4s e relatórios da execução ficam exclusivamente em
`E:\Fabuloom\workspace\exports\videos\official-narrators-v1` e não entram no
Git. A execução produziu: Dora `6,230 ms`, Santa `6,380 ms` e Alex `6,355 ms`;
todos em 1920×1080, H.264/yuv420p, AAC mono 24 kHz. Os WAVs e manifests medidos
ficam no diretório de exports local.

O exemplo reprodutível é:

```powershell
E:\Fabuloom\workspace\.venv\Scripts\python.exe examples\official_narrators_v1_demo.py
```

Ele usa o texto curto original definido na missão, as vozes `pf_dora`,
`pm_santa` e `pm_alex`, o áudio medido, o envelope RMS e a captura determinística
do Canvas. A página de captura aceita `character=dora|santa|alex` e continua
reutilizando o mesmo renderer, sem uma implementação paralela dentro do FFmpeg.

## Resultado da Missão 023.1

- Dora e Alex agora usam bases V3 geradas como identidade artística própria,
  separadas de Santa V5 e sem alterar seus assets oficiais.
- A boca fechada é extraída da referência da própria personagem; a boca aberta
  e as pálpebras usam overlays no mesmo canvas e são resolvidas pelo
  `NarratorAvatarRenderer` conforme RMS e relógio facial.
- Capturas locais de 30 FPS confirmaram estado neutro, fala, piscada e troca de
  identidade para `pf_dora`/`pm_alex` sem regressão do caminho Santa V5.

## Limitações conhecidas

- Dora e Alex ainda não têm um rig corporal V3 completo com braços, mãos e
  acessórios independentes; esta missão concentra-se no Narrator Mode facial.
- A base ilustrada e as placas faciais são experimentais e aguardam revisão
  artística do proprietário; não são declaradas como arte final aprovada.
- O RMS indica abertura aproximada da boca; não é lip-sync fonético.
- Os manifestos locais existentes continuam sendo a fonte de reprodução no
  Studio; a demonstração curta só deve ser considerada nova quando o comando
  de síntese for executado e o relatório correspondente existir.
- O Character Creator V2 permanece fora do escopo.

## Segurança e preservação

Não foram tocados TopazioReader, Card Game Studio, modelos, caches antigos,
ambientes virtuais ou arquivos fora de `E:\Fabuloom`. Nenhum peso, áudio pessoal,
credencial ou contexto privado é publicado. O carregamento continua limitado a
assets locais validados pelo contrato de character pack.
