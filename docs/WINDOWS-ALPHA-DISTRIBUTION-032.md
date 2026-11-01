# Missão 032 — Windows Alpha Experience

Data: 2026-11-01  
Resultado: **PARTIAL**

## Estratégia escolhida

Para a Alpha, a menor distribuição segura é um checkout portátil com Python local e `.venv` gerenciado pelo próprio usuário. Um executável empacotado ou instalador MSI aumentaria tamanho, superfície de segurança, manutenção e complexidade de atualização sem remover a necessidade de FFmpeg/modelo externo. A estratégia pode evoluir para instalador depois da aprovação humana.

## Fluxo implementado

`Preparar Fabuloom.bat` executa somente ações fixas e locais:

1. localiza Python 3.11+;
2. cria `.venv` dentro do checkout se necessário;
3. instala o pacote Fabuloom localmente;
4. solicita confirmação explícita antes do extra Kokoro;
5. informa origem, licença e destino aproximado;
6. permite nova tentativa após erro;
7. deixa claro que o Studio continua editável sem Kokoro.

`Iniciar Fabuloom.bat` permanece responsável somente por iniciar o servidor, detectar servidor já ativo e tratar porta ocupada. Nenhum script altera PATH, registro, permissões globais ou encerra processos externos.

## Validação independente

O checkout limpo deve ser validado com um `.venv` novo e `HF_HOME` temporário antes de qualquer aprovação pública. Nesta rodada, o teste automatizado local confirmou que a instalação básica é independente do cache Kokoro e que o servidor loopback inicia sem pacote opcional. A síntese real `pm_santa` da Missão 031 usou cache público existente, portanto não é evidência de instalação limpa completa.

## Gates

| Gate | Estado |
|---|---|
| Distribuição simples e atualizável | PASS — checkout + `.venv` |
| Preparação consentida do Kokoro | PARTIAL — script fixo, download do modelo é posterior |
| Sem Kokoro | PASS — edição continua disponível |
| Sem alterações globais | PASS |
| Primeiro projeto completo independente | BLOCKED/PENDING — requer máquina/cache isolado e exportação narrada |
| Canvas × FFmpeg | PENDING conforme Missão 030.1 |
| Licenças e aprovação humana | PENDING |

Não publicar release nem declarar instalação pública aprovada nesta missão.
