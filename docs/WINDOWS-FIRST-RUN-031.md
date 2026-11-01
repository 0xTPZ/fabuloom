# Missão 031 — Windows First-Run Setup

Data: 2026-11-01  
Base: `e044f00`  
Resultado: **PARTIAL**

## Diagnóstico real

O endpoint `/api/health` agora diferencia estado de pacote e estado de uso:

| Dependência | Estado observado |
|---|---|
| Python 3.12.10 | PASS — PRONTO |
| FFmpeg | PASS — PRONTO |
| FFprobe | PASS — PRONTO |
| Kokoro 0.9.4 | PASS — PRONTO |
| Cache Kokoro-82M | PASS — PRONTO |
| Voz `pm_santa` | PARTIAL — VERIFICAÇÃO NECESSÁRIA até síntese real |
| Workspace | PASS — PRONTO para leitura/escrita |
| Porta | PASS — informada pela API local |

Foi executada síntese real curta de `pm_santa` com resultado de 2650 ms, usando o ambiente virtual da release e cache público local. O WAV ficou em `workspace/exports/audit-031/pm_santa-check.wav`, fora do Git.

## Assistente e inicialização

A tela Configurações agora explica em português que edição funciona sem Kokoro, que narração exige configuração adicional e que o Fabuloom não altera PATH, registro ou baixa arquivos sem consentimento. O painel mostra Python, FFmpeg, FFprobe, Kokoro, modelo, voz, permissão do workspace e porta.

`Iniciar Fabuloom.bat` agora:

- prefere `.venv` local;
- avisa quando precisa usar Python do sistema;
- detecta servidor já ativo e apenas abre o navegador;
- identifica porta 8765 ocupada sem encerrar o processo;
- mostra erro do servidor e mantém a janela para diagnóstico;
- usa caminhos relativos ao próprio checkout, inclusive com espaços.

Não foi adicionada instalação automática. A instalação de Kokoro continua uma ação consentida do usuário, com origem/licença/destino apresentados na interface.

## Validação

- Navegador real em `http://127.0.0.1:8895/#settings`: captura confirmou o painel de primeiro acesso e a separação da narração opcional.
- Health real retornou Python, FFmpeg, FFprobe, Kokoro, modelo, workspace e porta.
- Síntese real `pm_santa`: PASS, 2650 ms.
- Suíte Python: **40 passed, 1 skipped**.
- Suíte Node: **147 passed**.
- `node --check frontend/src/studio-shell.mjs`: PASS.

## Limitações

1. A interface ainda orienta a instalação com um comando, mas não automatiza a instalação consentida; isso é intencional nesta rodada de segurança.
2. O endpoint de health não executa síntese automaticamente para evitar downloads/carga inesperados; o estado `VERIFICAÇÃO NECESSÁRIA` é honesto até uma ação explícita.
3. A instalação limpa completa com Kokoro e exportação narrada deve ser repetida em uma máquina sem cache público, pois o teste atual usou o cache público do usuário e o venv isolado da release.
4. O requisito de prancha Canvas × FFmpeg continua pendente conforme Missão 030.1.
