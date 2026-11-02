# Fabuloom — Website Launch 067

**Classificação:** `PUBLISHED_WITH_WARNINGS`

## Escopo

Esta missão publicou somente o site institucional estático do Fabuloom. A Alpha 0.1.0, seus artefatos de distribuição e a PR #33 não foram publicados nem mesclados.

## Estado Git e PRs

- Repositório: `0xTPZ/fabuloom`
- Branch de publicação: `main`
- Merge normal da PR #49: `52379c683d03f6a6bea90f2a3a07374b71cccb3b`
- Correção do workflow: `5515520`
- PR #49: `MERGED`, sem alterações no motor do Studio
- PR #33: `OPEN`, `Draft`, head `6cfe75cb58f4df83562a30d45bbe59a7f9eabd69`
- Produção em `E:\Fabuloom\studio`: preservada e não modificada

## Publicação

- URL: <https://0xtpz.github.io/fabuloom/>
- Método: GitHub Pages por GitHub Actions, a partir de `docs/site`
- Execução bem-sucedida: [workflow 41368738582](https://github.com/0xTPZ/fabuloom/actions/runs/41368738582)
- Validação HTTP: `200 OK`
- Pages: público, HTTPS obrigatório, build por workflow

O primeiro workflow falhou porque não fazia checkout do repositório. A causa foi corrigida em `5515520`; a execução seguinte concluiu com checkout, configuração, upload e deploy bem-sucedidos.

## Conteúdo auditado

O site publicado contém somente a apresentação institucional em `docs/site`:

- `index.html`, `styles.css`, `app.js` e `README.md`;
- três capturas neutras do Studio em `media/`;
- nenhum ZIP da Alpha, modelo, voz, FFmpeg, cache, credencial ou contexto privado;
- nenhum asset proprietário do Topazioverse.

As capturas exibidas foram auditadas individualmente: dashboard com Ponto, editor de cenas neutro e tela de prévia. A página declara corretamente que a Alpha ainda está em preparação e não foi lançada oficialmente.

## Verificação visual e responsiva

Validações locais realizadas nas dimensões `1920×1080`, `1366×768`, `768×1024`, `390×844` e `320×568`. As versões tablet e mobile foram inspecionadas sem overflow horizontal observado.

No navegador público, a inspeção confirmou:

- título e conteúdo principal carregados;
- links para a branch Alpha e PR #33;
- botão de idioma e conteúdo PT-BR;
- seção “STUDIO REAL · DEMO PONTO”;
- três imagens com textos alternativos descritivos;
- informações de licença e limites de distribuição.

## Segurança e licenciamento

O site é estático, sem backend, trackers, fontes externas ou execução de código fornecido por usuários. O código original permanece sob MIT; imagens, packs, modelos, vozes e demais dependências conservam licenças próprias. A publicação não afirma autorização para redistribuir assets do Topazioverse.

## Avisos residuais

- A validação de acessibilidade é funcional/visual, não substitui uma auditoria formal completa.
- O workflow registra avisos de manutenção futura para Node 20 e `ubuntu-latest`; não impediram o deploy.
- A Alpha source-only continua separada, em revisão e sem release público.

## Decisão

**Site institucional:** publicado e verificável, com os avisos acima.

**Alpha 0.1.0:** permanece fora do escopo de publicação desta missão; PR #33 continua Draft.

Não houve merge da PR #33, criação de tag, GitHub Release, alteração de visibilidade ou publicação de domínio customizado.
