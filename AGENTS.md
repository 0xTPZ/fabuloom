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

## Worktrees e histórico

Antes de editar, confira `git status --short --branch` e use uma branch própria.
Não faça merge, deploy, publicação ou exclusões irreversíveis.
