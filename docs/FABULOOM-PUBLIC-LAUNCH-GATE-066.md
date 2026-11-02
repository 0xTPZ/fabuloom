# Fabuloom Public Launch & Alpha Final Gate — Mission 066

Data da validação: 2026-11-02. Nenhuma publicação, merge, tag ou ativação de GitHub Pages foi realizada.

## Estado inicial

- Alpha: `release/fabuloom-alpha-preparation`, HEAD inicial `a2a8bf4`.
- PR #33 e PR #49 permanecem Draft.
- `E:\Fabuloom\studio` permaneceu intocado.
- O ZIP 065 tinha o SHA esperado `6EF3ECEF36EF4A92859CD3EBAB85023AA441B64ABBE3457B41DBB4778D8C0900`, mas a auditoria encontrou `.pytest_cache` gerado após sua criação. Ele não foi aprovado nem substituído.

## Gate A — site institucional

Classificação: **SITE_READY_WITH_WARNINGS**.

PR #49 está no commit `5177aa6`. A landing page é estática, relativa, sem backend, fontes externas, trackers ou dependências externas. A seção de demonstração usa três capturas reais verificadas:

| Arquivo | Resultado |
|---|---|
| `studio-ponto-dashboard.png` | PASS — Studio principal real, Ponto visível, sem personagens proprietários |
| `studio-scenes.png` | PASS — tela real de cenas, conteúdo demonstrativo neutro |
| `studio-preview.png` | PASS — tela real de prévia, sem credenciais ou manuscritos privados |

As imagens foram inspecionadas visualmente e não exibem Santa V5, Dora, Alex, caminhos pessoais ou dados de produção. Foram capturadas fora do repositório e copiadas somente após inspeção.

Foram geradas capturas Edge em 1920×1080, 1366×768, 768×1024, 390×844 e 320×568. A visualização de 320px não apresentou overflow horizontal observável. Navegação, foco visível, imagens, botões e textos foram verificados; a acessibilidade não é declarada como integral. O idioma inicial PT-BR foi confirmado pelo navegador local; a landing possui alternância completa, preferência persistente, metadados e alt text localizados. A preferência sem `localStorage` é tratada defensivamente pelo código.

## Gate B — distribuição Alpha

Classificação: **ALPHA_READY_WITH_WARNINGS**.

Foi criado um novo candidato, sem alterar os anteriores:

- ZIP: `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only-066.zip`
- Arquivos: 326
- SHA-256 do ZIP: `BFD2185BE378BA6BBE067DFB50E8D0CCF3E62F09BF97D4E10289B8A142BDA27A`
- Manifesto: `E:\Fabuloom\alpha-testers\MANIFEST-066.json`
- SHA-256 do manifesto: `F4751AC93823FED9BA7CB7B4C9F04B2B5C2D80D98A8C38715E34C8CF671E7EE9`
- Extração auditada: `C:\Users\User\AppData\Local\Temp\fabuloom-066-verify`

A extração não contém assets Topazioverse, modelos, vozes, caches, virtualenv, `node_modules`, bytecode Python, workspace ou credenciais. O módulo de contrato `fantasy-narrator-pack.mjs` foi mantido porque é código necessário à suíte pública; nenhum asset correspondente foi incluído.

## Instalação e E2E real

O harness Playwright foi executado a partir do candidato extraído. A dependência Playwright foi instalada somente no diretório temporário de teste; o ZIP permanece sem dependências instaladas. O Python usado foi o `.venv` autorizado externamente, via `PATH`, sem copiá-lo para o candidato.

Fluxos PASS:

- criação de projeto, roteiro, cena, imagem neutra e movimento;
- seleção do Ponto e expressão `smile`;
- persistência após novo contexto de navegador;
- restauração do pack e expressão pelo backend;
- geração de narração pelo botão real do Studio usando Kokoro;
- exportação MP4 pela interface;
- FFprobe e decodificação integral FFmpeg.

Evidência E2E: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-mFthJc`.

## MP4 real

- Caminho: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-mFthJc\workspace\workspace\exports\projects\project-8105ea91f0d4\project-8105ea91f0d4-1080p.mp4`
- Tamanho: 37.281 bytes
- SHA-256: `04FA876EB17D6F5FE17F5608814E12468E24550B2EB5032B2DDB98F894DA0484`
- Vídeo: H.264, 1920×1080, 30 FPS, 87 frames
- Áudio: AAC LC, mono, 48 kHz
- Duração: 2,900 s em ambos os streams
- Decodificação FFmpeg: PASS
- Frames inicial, intermediário e final: extraídos pelo harness

O projeto exportado contém Ponto e imagem neutra. O narrador persistido no manifesto interno continua `pm_santa` por compatibilidade do pipeline de áudio, mas nenhuma arte Santa foi usada no projeto visual; a voz é uma dependência externa opcional e não está no ZIP.

## Regressão

- Python no candidato extraído: **48 passed, 1 skipped, 22 subtests passed**.
- Node público no candidato extraído: **128 passed, 0 failed**.
- Playwright E2E com exportação: **PASS**.
- FFmpeg/FFprobe: **PASS**.
- Gate Canvas × FFmpeg: permanece **PARTIAL**, sem alteração artificial.

## Decisão final

O site está tecnicamente pronto para revisão do proprietário, com ressalvas de acessibilidade formal. A Alpha source-only está pronta para testadores controlados porque a evidência obrigatória de síntese Kokoro e exportação real foi obtida a partir do código do candidato 066 usando runtime externo autorizado.

Recomendação: **aprovar para revisão/entrega experimental limitada**, sem GitHub Release ou publicação automática. Permanecem obrigatórios: aprovação final do proprietário, comunicação da limitação visual Canvas × FFmpeg, preparação externa de Kokoro/FFmpeg e validação humana do seletor nativo Windows.

Commits relevantes: Alpha `17d52fd`, relatório anterior `a2a8bf4`; PR #49 `5177aa6`. Nenhuma PR foi merged nesta missão.
