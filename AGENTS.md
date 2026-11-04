# Fabuloom Studio — instruções para agentes

## Bootstrap

Este repositório é o produto público. A biblioteca privada fica fora dele.
Use um worktree isolado e configure a raiz runtime antes de operar:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -B -m fabuloom_core.cli --root E:\Fabuloom doctor
python -B -m fabuloom_core.cli --root E:\Fabuloom capabilities
```

Não use `C:` como fallback para workspace, cache, modelos ou renderizações.
Se `doctor` indicar `status=blocked`, pare e corrija a configuração ou o
espaço livre antes de executar jobs pesados.

## Fontes de verdade

- Motor compartilhado: `src/fabuloom_core/engine.py`.
- Contratos de projeto: `src/fabuloom_core/project_store.py`.
- Catálogo de assets: `src/fabuloom_core/asset_catalog.py`.
- Produção Canvas + FFmpeg: `src/fabuloom_core/production.py`.
- Interfaces: `src/fabuloom_core/cli.py`, `src/fabuloom_core/api.py` e
  `src/fabuloom_core/mcp.py`.
- Perfis: `profiles/*.json`.
- Procedimento operacional: `docs/AGENT-OPERATIONS.md`.
- Compatibilidade cinematográfica: `docs/FAB-ARCH-003-COMPATIBILITY.md`.

Desktop, CLI, API, MCP e o Stage devem usar os mesmos serviços. Não crie uma
segunda implementação de TTS, timeline, renderização ou catálogo.

## Segurança e preservação

- Trabalhe em `E:\Fabuloom` e preserve os checkouts principais.
- Trate `G:\TopazioReader`, `E:\CardGameStudio` e bibliotecas privadas como
  somente leitura, salvo autorização explícita.
- Não publique mídias, modelos, credenciais, contextos privados ou exports.
- Assets devem ser referenciados por IDs de catálogo e estado de direitos;
  personagens `DRAFT` não entram em produção.
- Migração de biblioteca começa em `dry-run`; execute cópias somente com
  checkpoint e hash verificado. Nunca remova a fonte.
- QA técnico não é aprovação artística. Entregas ficam `REVIEW_REQUIRED` até
  revisão humana.

## Operação cinematográfica

Crônicas de Topázio usa o contrato `cronicas-cinematic-production`. Preserve
manuscrito integral, Kokoro `pm_santa`/pt-BR, Santa V5 aprovado, medalhão,
abertura/despedida, música com ducking, legendas medidas, transições,
checkpoints e masters horizontal/vertical. Não promova personagens DRAFT.

O capítulo 11 R2 é referência de validação. A produção pelo motor usa somente
runners registrados em `profiles/registries/cinematic-runners.json`, com
SHA-256 verificado, contrato `--request` e `output_root` isolado. Runners com
caminhos fixos são reportados, mas recusados para evitar sobrescrever capítulos
aprovados. O runner `cronicas.chapter` é a implementação validada para a
produção parametrizada do capítulo 12.

Para executar uma produção, use `render cinematic --mode execute` ou o job/API/
MCP equivalente. O motor escolhe ou valida um diretório filho de
`workspace/exports`, grava a requisição, acompanha `CHECKPOINT.json` e preserva
saídas completas. O mesmo pedido não pode ser reutilizado em outro output.

## Worktrees e histórico

Antes de editar, confira `git status --short --branch` e use uma branch própria.
Não faça merge, deploy, publicação ou exclusões irreversíveis.
