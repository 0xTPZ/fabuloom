# Character Registry V0.1

O Fabuloom agora mantém identidades visuais reutilizáveis por IDs estáveis,
separadas do texto literário e dos arquivos grandes de produção. O contrato
público é `assets/character-registry.json` e a implementação está em
`src/fabuloom_core/character_registry.py`.

## Estados de aprovação

- `DRAFT`: proposta conceitual ainda não aprovada.
- `APPROVED`: identidade aprovada pelo proprietário.
- `SUPERSEDED`: versão substituída por outra identidade aprovada.

Nenhuma proposta conceitual é promovida automaticamente. Cada registro guarda
nome canônico, versão, descrição visual, paleta, características físicas,
estrutura facial, traje, proporções, origem, SHA-256 e histórico de variações.

## Capítulo 1

O Capítulo 1 registra `santa-v5-base` como a única identidade `APPROVED`. As
propostas `thaurion-v1-base`, `aurelion-v1-base`, `zephirion-v1-base`,
`glaciron-v1-base`, `abyssal-v1-base`, `emberion-v1-base` e `luminor-v1-base`
são `DRAFT` e existem apenas como referências conceituais locais para o
storyboard. A prancha fica em:

`E:/Fabuloom/workspace/exports/topazio-book1-capitulo1-cronicas-v2/captures/character-proposals-board.png`

As placas não são cânone literário nem arte final. A consistência entre
capítulos é garantida pelo mecanismo de ID/hash e pelo reuso do asset, mas a
continuidade artística precisa de aprovação humana; o mesmo prompt não prova
identidade visual.

## Resolução segura

Os caminhos são relativos ao workspace `E:/Fabuloom`. A resolução rejeita
travessia de diretórios, arquivos ausentes e hashes divergentes. Os assets
gerados permanecem no workspace e não são publicados no GitHub.
