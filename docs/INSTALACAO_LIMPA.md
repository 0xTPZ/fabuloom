# Instalação limpa — MISSÃO 022

## Resultado resumido

Foram usados dois clones rasos independentes do repositório público:

1. `main`, o checkout que um usuário obtém sem selecionar uma branch;
2. `mission-021-ui-reforge`, a branch que contém o Studio UI atual.

O primeiro não é uma instalação executável do Studio atual. O segundo executa
os testes offline e o servidor, mas não traz modelos, WAVs, manifestos, cenas ou
MP4s.

## Pré-requisitos observados

No computador de auditoria: Python 3.12.10, Node 24.19.0/npm 11.17.0 e
FFmpeg/FFprobe 9.0.1. Esses valores são evidência do host, não dependências
embutidas no repositório.

O checkout atual não possui `package.json` nem `requirements.txt`. O Python
core não tem dependências; Kokoro é um extra opcional de `pyproject.toml` e
requer modelo/cache que não são distribuídos.

## Procedimento documentado para a branch atual

```powershell
git clone https://github.com/0xTPZ/fabuloom.git
cd fabuloom
git switch --detach mission-021-ui-reforge

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[kokoro]"
$env:PYTHONPATH = (Resolve-Path .\src).Path
& .\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
node --test .\frontend\tests\*.mjs

$env:FABULOOM_WORKSPACE_ROOT = (Resolve-Path .).Path
$env:FABULOOM_EXPORT_ROOT = Join-Path $env:FABULOOM_WORKSPACE_ROOT 'workspace\exports'
& .\.venv\Scripts\python.exe .\frontend\server.py --port 8765
```

O comando `pip install` é opcional para os testes offline e não foi executado
nesta auditoria. Ele deve ser feito somente em ambiente local do usuário, após
revisão das licenças e da disponibilidade do modelo Kokoro.

## Resultados reproduzidos

- Clone de `main`: falha como fluxo de usuário do Studio porque não contém o
  servidor, frontend, `pyproject.toml`, exemplos ou testes.
- Branch da MISSÃO 021 sem `PYTHONPATH`: a descoberta Python falha ao importar
  `fabuloom_core`; o `Getting Started` anterior não informava esse passo.
- Branch da MISSÃO 021 com `PYTHONPATH=src`: 35 testes Python aprovados, com um
  teste Kokoro real opt-in ignorado.
- Suíte Node da branch da MISSÃO 021: 128 testes aprovados.
- Servidor: inicialização e rota raiz retornaram HTTP 200; arquivo inexistente
  retornou HTTP 404.
- Antes da correção de portabilidade, um clone limpo conseguia servir um
  manifesto encontrado no `E:\Fabuloom\workspace\exports` do desenvolvedor.
  Isso foi confirmado como dependência indevida e corrigido nesta branch por
  variáveis de workspace/export contidas.

## Conclusão

Ainda não existe uma instalação “clique e produza” nem uma distribuição de
modelos. A futura versão Alpha precisa escolher uma branch/release executável,
fornecer bootstrap reproduzível e separar claramente demonstrações com
artefatos locais de um projeto novo vazio.

