# FAB-ARCH-003 — compatibilidade cinematográfica e continuidade

Este documento registra o estado da consolidação sem afirmar equivalência que
ainda não foi demonstrada. O produto continua sendo uma única aplicação: o
Desktop, a CLI, a API loopback e o MCP chamam o mesmo `EngineService`.

## Matriz de compatibilidade

| Capacidade | Pipeline aprovada do capítulo 11 | EngineService | Estado FAB-ARCH-003 |
| --- | --- | --- | --- |
| Kokoro `pm_santa` / pt-BR | Sim, WAV medido | Sim no `render-demo` quando disponível | Contrato compatível; referência validada |
| Santa V5 + RMS | Sim, `NarratorAvatarRenderer` | Canvas genérico compartilhado | Adaptador de referência; sem duplicar renderer |
| DOCX integral | Sim, limites de capítulo | Sim no runner registrado | Capítulo 12 executado com validação dos limites do DOCX |
| Medalhão e abertura/despedida | Sim, PR #56 R2 | Não no demo genérico | Preservados pelo runner legado |
| Música e ducking | Sim, sidechain e limiter | Sim no mix genérico | Contratos compatíveis; direitos pendentes |
| Transições mágicas | Sim, determinísticas | Não no demo genérico | Validadas nos masters R2 |
| Legendas medidas | Sim, SRT por segmentos | Sim no demo | Contrato de manifesto reutilizado |
| Horizontal/vertical | Sim, 1920×1080 e 1080×1920 | Sim no demo | Dois masters R2 validados |
| Checkpoints/retomada | Sim, `BATCH-STATUS.json` | Sim, jobs/checkpoints | Runner registrado retoma etapas válidas por `CHECKPOINT.json` |
| Biblioteca privada | IDs, hashes e direitos | Catálogo SQLite/migração dry-run | Externa ao produto; sem migração destrutiva |

Os estados são deliberadamente separados: `legacy_validated`,
`shared_validated` e `adapter_reference_only`. Um demo genérico com SVG e
áudio sintético não comprova uma produção de capítulo.

## Contrato `cronicas-cinematic-production`

O perfil em `profiles/cronicas-cinematic-production.json` representa a linha
aprovada: manuscrito integral, `pm_santa`, Santa V5 aprovado, abertura e
despedida cinematográficas, medalhão, cenários aprovados, música por projeto,
ducking, transições, SRT, manifestos, checkpoints e os dois formatos.

O contrato não copia mídia particular para o repositório público. Projetos
referenciam IDs estáveis do catálogo e registram direitos. Personagens `DRAFT`
continuam bloqueados.

## Segurança do adaptador

`fabuloom_core.cinematic.CinematicCompatibility` faz descoberta, planejamento,
validação e execução controlada. Ele valida os masters R2 com FFprobe, codec,
dimensão, áudio, relatório de voz, ducking, decode e blackdetect.

Execução só é habilitada para um runner registrado em
`profiles/registries/cinematic-runners.json`, com SHA-256, contrato `--request`
e output novo dentro de `workspace/exports`. O runner `cronicas.chapter` foi
validado na produção independente do capítulo 12. Runners legados com caminhos
fixos continuam somente como evidência e não podem sobrescrever capítulos
aprovados. PR #56, R1/R2 e fontes permanecem preservados.

## Diagnóstico

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$fabRoot = 'E:\Fabuloom'
python -B -m fabuloom_core.cli --root $fabRoot doctor
python -B -m fabuloom_core.cli --root $fabRoot capabilities
python -B -m fabuloom_core.cli --root $fabRoot render cinematic --mode plan --chapter 11 --chapter-title 'O eco que não morre'
python -B -m fabuloom_core.cli --root $fabRoot render cinematic --mode validate-reference --chapter 11 --chapter-title 'O eco que não morre' --decode
```

Também estão disponíveis `GET /api/v1/cinematic`, o MCP
`fabuloom_cinematic_diagnose` e o job `cinematic-audit`. A validação de
referência não ressintetiza, não recaptura e não escreve nos masters aprovados.

## Biblioteca e migração

A fonte legada é inventariada sem cópia pelo catálogo. O procedimento continua
dry-run-first:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot job create library-migration
```

Cada plano guarda IDs, hashes, direitos e estado. Uma migração real exige
payload explícito, espaço livre e verificação SHA-256; a origem nunca é
removida. Arquivos desconhecidos, exports aprovados, worktrees e ambientes
virtuais permanecem preservados.

## Próximo capítulo e Shorts

O ambiente fica `ready_to_execute` quando DOCX, catálogo de Santa V5, perfil e
runner registrado estão presentes. A execução do capítulo 12 validou limites,
reutilização de assets aprovados, WAV Kokoro, os dois formatos e
FFprobe/decode/blackdetect/SRT/ducking. `technical_qa=PASS` continua separado
de `artistic_qa=REVIEW_REQUIRED`.

`profiles/cronicas-shorts-production.json` prepara Shorts sem gerar um novo
vídeo nesta missão. Cada Short exige storyboard com justificativa semântica,
início/desenvolvimento/gancho, legendas em área segura, trilha com ducking e
revisão artística. FBS-SHORT-001 é regressão, não referência estética.

## Pendências

- conexão do pack privado Santa V5 ao catálogo de produção;
- edição de timeline cinematográfica no Desktop;
- sessão fria com runtime LLM independente;
- confirmação de direitos comerciais de músicas e clipes.

Enquanto existirem, use o runner registrado para novas produções e o
EngineService para diagnósticos, projetos, catálogo, jobs, render genérico e
validação de referência. Não substitua a pipeline cinematográfica por um demo.
