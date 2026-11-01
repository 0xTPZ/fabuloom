# Experiência de usuário iniciante — MISSÃO 022

## Cenário avaliado

“Sou um escritor que encontrei o Fabuloom no GitHub. Quero instalar a
ferramenta, escrever uma história, selecionar uma voz, adicionar imagens e
exportar meu primeiro vídeo.”

## Resultado por etapa

| Etapa | Resultado atual | Fricção |
| --- | --- | --- |
| Encontrar a versão certa | bloqueada | `main` não contém a UI da MISSÃO 021; é necessário conhecer a branch. |
| Instalar Python | possível | versão mínima e criação de ambiente precisam ser documentadas como passos de usuário. |
| Instalar JavaScript | parcial | não há `package.json`; o frontend roda sem bundler, mas isso não é explicado como decisão de produto. |
| Detectar FFmpeg | manual | o Studio não verifica ou orienta a instalação dentro da UI. |
| Configurar Kokoro | avançado | extra, modelo, cache e licenças ficam fora do clone. |
| Abrir o Studio | possível na branch correta | depende do servidor Python e do workspace de exports. |
| Criar projeto | indisponível | botão desabilitado e sem contrato persistido atrás da UI. |
| Escrever roteiro | experimental | rascunho salvo em `localStorage`, não em um projeto versionado. |
| Selecionar voz | possível para manifestos existentes | Dora, Santa e Alex carregam áudio local; isso não sintetiza texto novo. |
| Adicionar imagens | indisponível na UI | cenas são perfis/arquivos preparados por CLI ou desenvolvimento. |
| Visualizar | funcional com recursos existentes | preview usa Santa V5 visual e pode trocar a voz. |
| Exportar MP4 | indisponível na UI | a tela abre arquivos antigos; o pipeline completo é CLI e depende de artefatos. |

## O que um usuário comum conclui incorretamente

Sem a leitura cuidadosa dos avisos, “Narradores”, “Cenas” e “Exportação” podem
parecer editores completos. O Studio agora marca Roteiro/Cenas como beta e
explica a ausência de job de exportação, mas o produto ainda é uma casca de
orquestração sobre demonstrações existentes.

## Recomendações

1. Publicar uma release/branch executável, não apenas `main` contratual.
2. Criar um bootstrap que valide Python, FFmpeg, permissões, modelos e espaço.
3. Transformar o projeto atual em um contrato persistido antes de ampliar a UI.
4. Expor estados vazios e erros de dependência no primeiro acesso.
5. Reservar “produção” para personagens visuais que realmente estejam
   integrados ao preview, sem confundir identidade visual e voz.

