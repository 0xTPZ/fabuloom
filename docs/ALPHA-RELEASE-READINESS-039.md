# Missão 039 — Alpha 0.1.0 Release Readiness Audit

Data: 2026-11-01  
HEAD auditado: `f9ec56b`  
Branch: `release/fabuloom-alpha-preparation`  
PR: #33 Draft  
Recomendação: **NO-GO para distribuição externa ampla**

## Matriz funcional

| Área | Estado | Evidência / limite |
|---|---|---|
| Instalação Windows básica | PASS | `INSTALL.md`, venv local, diagnóstico Python 3.12.10/Node 24.19.0/FFmpeg 9.0.1 |
| Kokoro em instalação limpa | PARTIAL | extra opcional e modelo não distribuído; clean-room completo sem cache público ainda não é prova de instalação independente |
| Primeiro acesso sem Kokoro | PASS | shell loopback inicia e oferece estado vazio |
| Criação de projeto | PASS | fluxo real e persistência comprovados nas Missões 034/037 |
| Edição de roteiro e cenas | PASS | 60 cenas persistidas e reabertas |
| Importação de imagens | PARTIAL | pipeline validado; seletor nativo não foi exercitado por automação compatível nesta auditoria |
| Movimentos de câmera | PASS técnico | estático/zoom/pans exportados e cobertos por testes |
| Persistência/reconciliação | PASS | IDs, assets e configurações protegidos; regressões cobertas |
| Kokoro `pm_santa` | PASS condicionado | síntese real e 60 segmentos comprovados quando runtime/modelo estão configurados |
| Santa V5/Narrator Mode | PASS técnico | pack e reprodução local cobertos pelas suítes/evidências anteriores |
| Prévia cinematográfica | PARTIAL | renderer determinístico; gate completo Canvas×FFmpeg da Missão 030.1 não está fechado com prancha real para todos os movimentos/proporções |
| Timeline audiovisual | PASS | Missão 038: gaps preservados, AAC 48 kHz, diferença de 0,003333 s |
| Exportação MP4 curta/longa | PASS condicionado | MP4 real de 196,57 s validado; depende de assets, FFmpeg e Kokoro locais |
| Falhas/recuperação | PARTIAL | mensagens e validações existem; matriz completa de interrupção/recovery em máquina limpa ainda pendente |

## Gates obrigatórios

1. **Instalação externa reproduzível — PARTIAL/BLOQUEADOR.** O clone básico inicia, mas a produção com Kokoro exige instalar o extra, baixar modelo e aceitar seus termos. A documentação ainda não comprova a sequência completa em uma máquina sem cache público.
2. **Fidelidade visual — PARTIAL/BLOQUEADOR.** Há testes matemáticos e renderer determinístico, mas não há evidência final suficiente de comparação de quadros Canvas×FFmpeg para todas as proporções e movimentos exigidos.
3. **Importação nativa — PARTIAL.** A limitação encontrada foi da automação usada; não prova defeito do seletor. Ainda falta uma execução humana ou harness Windows compatível que selecione arquivos e confirme o vínculo na UI.
4. **Licenciamento/proveniência — PARTIAL/BLOQUEADOR.** O código Fabuloom é MIT e o modelo `hexgrad/Kokoro-82M` é indicado como Apache-2.0 na página oficial do modelo, mas o repositório ainda não mantém um inventário versionado completo de pacote Kokoro, PyTorch, eSpeak-ng, vozes, fontes e assets demonstrativos. Não distribuir modelo/vozes até fechar esse registro.
5. **Segurança operacional — PASS com ressalvas.** O servidor aceita apenas loopback, valida containment e usa listas de argumentos sem `shell=True`. A superfície é apropriada para uso local; não deve ser exposta à rede. O canal privado de reporte de vulnerabilidades ainda não está formalizado.

## Evidências de estabilidade

- Python: `46 passed, 1 skipped, 22 subtests`.
- Node: `154 passed`.
- Diagnóstico: Python 3.12.10, Node 24.19.0, FFmpeg/FFprobe 9.0.1.
- Missão 038: MP4 H.264/AAC de 196,57 s, 1920×1080, áudio 48 kHz mono, decode integral e sincronização dentro de 1 frame.
- Worktree pública limpa em `f9ec56b` antes da auditoria; `E:\Fabuloom\studio` não foi alterado.

## Classificação de release

### OBRIGATÓRIO — bloqueia Alpha externa

- repetir instalação Kokoro completa em checkout limpo e documentar cada dependência/modelo;
- concluir gate Canvas×FFmpeg com quadros reais e tolerâncias publicadas;
- confirmar importação pelo seletor nativo em Windows;
- fechar inventário de licenças e proveniência para código, modelo, runtime, vozes, fontes e mídia.

### RECOMENDADO — pode ocorrer durante teste controlado

- adicionar teste automatizado de falha/interrupção e recovery após exportação;
- formalizar canal privado de segurança;
- reduzir a dependência de intervenção técnica no bootstrap do Kokoro.

### FUTURO — fora da Alpha 0.1.0

- novos narradores e efeitos;
- editor nonlinear avançado;
- distribuição/release automática;
- timestamps fonéticos, visemas e word alignment;
- exposição do servidor fora de loopback.

## Decisão

**NO-GO para disponibilização a usuários externos neste momento.** O núcleo audiovisual é funcional e a timeline foi corrigida, mas os quatro gates obrigatórios acima ainda não possuem comprovação suficiente para uma Alpha externa responsável. A recomendação pode mudar para GO após um ciclo curto focado exclusivamente nesses gates, sem expansão de funcionalidades.
