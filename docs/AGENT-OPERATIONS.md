# Operação do Fabuloom por agentes

Este guia descreve apenas comandos implementados e validados. Todos usam o
mesmo `EngineService` utilizado pelo Desktop.

## 1. Preflight

Na raiz do worktree:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$fabRoot = 'E:\Fabuloom'
python -B -m fabuloom_core.cli --root $fabRoot doctor
python -B -m fabuloom_core.cli --root $fabRoot capabilities
python -B -m fabuloom_core.cli --root $fabRoot profiles list
# diagnóstico do shell Desktop, sem abrir uma janela
python -B desktop/fabuloom_desktop.py --root $fabRoot --check
```

O preflight confirma FFmpeg, FFprobe, navegador Canvas, Kokoro opcional,
espaço livre em C:/E:, raiz configurada, biblioteca montada e perfis prontos.
O perfil `cinematic-trailer` permanece `review_required`; não deve ser tratado
como pronto apenas por existir.

## 2. Biblioteca e assets

Consultar sem copiar ou alterar arquivos:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot assets search cristal
python -B -m fabuloom_core.cli --root $fabRoot job create catalog-scan --no-wait
```

O catálogo preserva tags, referências de projetos, estado de aprovação,
origem e direitos durante uma nova varredura. A busca é por metadados e IDs
estáveis, não por nomes usados diretamente no roteiro.

Para planejar uma migração legada:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot job create library-migration
```

O padrão é `dry_run=true`. O resultado contém o checkpoint em
`E:\Fabuloom\workspace\migrations\`. Uma execução real exige um payload
estruturado pela API/MCP com `dry_run=false`; as fontes continuam preservadas
e cada cópia é verificada por SHA-256. Rollback só remove cópias cujo hash não
mudou desde a migração.

## 3. Projetos e edição

Criar e consultar projetos:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot project create "Demonstração local" --id demo-local
python -B -m fabuloom_core.cli --root $fabRoot project list
python -B -m fabuloom_core.cli --root $fabRoot project show demo-local
```

Atualizações usam JSON e revisão otimista:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot project update demo-local --json-file .\project-update.json --revision 1
```

O Desktop e o agente devem editar o mesmo `project.json` através desse
contrato, sem manter cópias paralelas em memória.

Para iniciar a interface gráfica depois do preflight:

```powershell
python -B desktop/fabuloom_desktop.py --root $fabRoot
```

Fechar a janela não interrompe jobs já executados pelo motor headless; consulte
`job list` ou `/api/v1/jobs` para acompanhar o estado.

## 4. Preview, narração e render

Antes do render, planejar sem escrever mídia:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot render demo --dry-run
```

O render genérico validado usa o perfil `cinematic-short`, a captura de
`frontend/capture-music-studio.html` e `frontend/src/music-studio-renderer.mjs`,
gera manifesto de narração, WAV, SRT, frames, MP4, prancha, checkpoint e QA.
O perfil mantém `capture_fps=5` como modo econômico de demonstração, mas aceita
`capture_fps=24` ou `30` para capturar quadros reais do Canvas. O QA registra a
quantidade de quadros capturados, quadros únicos, mudanças adjacentes e deixa
explícito quando a fluidez não foi comprovada. A taxa do vídeo pode ser 24 ou
30 fps, independentemente da taxa de captura.
O áudio dos provedores permanece na taxa nativa durante a composição; a
exportação AAC padrão é estéreo a 48 kHz (`audio_sample_rate=48000`,
`audio_channels=2`).
Para a produção de aceitação sem acervo privado:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot render demo --provider simulated-audio --output-id cold-demo
python -B -m fabuloom_core.cli --root $fabRoot job list
```

Para validar fluidez real em uma saída nova, use um identificador novo e uma
captura de 30 fps:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot render demo --provider simulated-audio --capture-fps 30 --output-fps 30 --audio-sample-rate 48000 --audio-channels 2 --output-id real-canvas-30fps-r1
```

O áudio `simulated-audio` é um tom determinístico audível para teste de
pipeline; não é voz humana e não deve ser publicado como narração. Para usar
Kokoro, selecione `--provider kokoro --voice-id pf_dora|pm_alex|pm_santa` somente
quando a dependência, modelo, licença e saída local estiverem validados.

O arquivo `CHECKPOINT.json` permite retomar uma solicitação com o mesmo
fingerprint. Uma solicitação diferente não sobrescreve um export existente.
O job também aceita `--music-path` para uma faixa sob a raiz configurada; a
fonte é preservada e a mixagem usa ducking sidechain da voz, fades e limiter.
Projetos podem referenciar um `music_asset_id` catalogado pela API/MCP para
evitar caminhos editoriais embutidos no roteiro.

## 5. API e MCP

API loopback:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot api --port 8790
```

Endpoints implementados: `/api/v1/status`, `/api/v1/doctor`, `/api/v1/cinematic`,
`/api/v1/capabilities`, `/api/v1/profiles`, `/api/v1/projects`,
`/api/v1/library`, `/api/v1/jobs`, `/api/v1/render`, `/api/v1/render/cinematic` e
`/api/v1/library/migration`.

MCP local por stdio:

```powershell
python -B -m fabuloom_core.mcp --root $fabRoot
```

O MCP expõe status, diagnóstico, capacidades, perfis, projetos, catálogo,
jobs, render dry-run, render demo e migração. Ele traduz JSON-RPC para o mesmo motor; não
executa código arbitrário, plugins desconhecidos ou coordenadas de mouse.

## 6. QA e retomada

Cada render produz QA técnico com FFprobe, decodificação FFmpeg, blackdetect,
resolução, codecs, duração e tamanho. Também produz um estado separado:
`artistic_qa.status=REVIEW_REQUIRED`.

Em caso de interrupção, consulte o job e o checkpoint:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot job list
python -B -m fabuloom_core.cli --root $fabRoot job show JOB_ID
```

Jobs `queued`/`running` encontrados após encerramento de processo são marcados
como `interrupted`; trabalho arbitrário não é retomado silenciosamente.

## 7. Linha cinematográfica de Crônicas de Topázio

O diagnóstico cinematográfico é separado do demo genérico:

```powershell
python -B -m fabuloom_core.cli --root $fabRoot doctor
python -B -m fabuloom_core.cli --root $fabRoot render cinematic --mode plan --chapter 11 --chapter-title 'O eco que não morre'
python -B -m fabuloom_core.cli --root $fabRoot render cinematic --mode validate-reference --chapter 11 --chapter-title 'O eco que não morre' --decode
```

O perfil `cronicas-cinematic-production` exige fonte DOCX, segmentos Kokoro
medidos, Santa V5 aprovado, cenas por IDs, música autorizada, ducking,
transições, SRT, checkpoints e QA dos dois formatos. A validação do capítulo
11 R2 reutiliza os masters existentes sem ressíntese ou recaptura.

Os runners da PR #56 permanecem a referência legada. Eles só podem ser
executados pelo adaptador quando `FABULOOM_CINEMATIC_RUNNER` selecionar um
runner que declare saída isolada (`--output-root` ou equivalente). Runners com
caminhos fixos são reportados, mas recusados para evitar sobrescrever capítulos
aprovados.

Para o próximo capítulo, produza primeiro um plano e storyboard, valide fonte
e direitos, selecione output novo e só então execute o runner parametrizado.
`technical_qa=PASS` não equivale a aprovação artística. Para Shorts, use
`cronicas-shorts-production`; o storyboard e a aprovação artística continuam
obrigatórios.

## 8. Limites atuais

- O editor visual completo ainda não está integrado ao armazenamento de
  projetos; o Desktop é uma superfície de controle funcional e o Stage é uma
  view compatível.
- O render compartilhado validado é o perfil de curta genérico e a captura
  Music Studio; capítulos privados e o pipeline Kokoro real exigem assets,
  modelos e direitos previamente montados.
- Alinhamento de palavras, fonemas e visemas continua indisponível quando o
  provedor não o fornece.
- Nenhum QA técnico substitui aprovação artística humana.
- O teste `tools/cold_agent_session.py` inicia um subprocesso limpo sem
  histórico de conversa, lê somente os documentos versionados, descobre
  capacidades e seleciona um perfil renderizável. Ele não é um agente LLM
  autônomo; quando não há runtime de agente disponível, essa limitação fica
  registrada no relatório em vez de ser mascarada como autonomia.
