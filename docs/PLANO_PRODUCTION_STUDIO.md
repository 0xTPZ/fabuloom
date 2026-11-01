# Plano Production Studio — MISSÃO 025

## Fluxo-alvo

`Criar projeto → escrever roteiro → selecionar narrador → preparar cenas →
visualizar → exportar MP4`.

## Bloqueios atuais

| Bloqueio | Componentes | Solução recomendada | Complexidade | Risco |
| --- | --- | --- | --- | --- |
| Projeto novo | `studio.html`, `studio-shell.mjs`, Core models | persistir `Project`/`Book`/`Chapter`/`Scene` em workspace local | alta | migração e perda de dados |
| Roteiro | `bindScriptDraft`, `localStorage` | editor que grava contratos versionados e IDs estáveis | média | quebra de compatibilidade |
| Narração nova | catálogo + Kokoro CLI | endpoint/job local para segmentar, sintetizar e medir WAV | alta | modelo, licenças, tempo e falhas |
| Cenas | perfis JSON somente leitura | editor de assets, intervalos, câmera e transições | alta | paths e composição |
| Imagens | ausência de importador | pipeline local de importação/validação e biblioteca | alta | segurança e arquivos grandes |
| Prévia | shared renderer facial | carregar projeto real, áudio e cenas em timeline | alta | divergência browser/FFmpeg |
| Exportação | links para arquivos existentes | job local com progresso, logs, cancelamento e FFprobe | alta | processos órfãos e espaço |
| Estado/erro | status distribuído | contrato de job e recuperação após falha | média | consistência |

## Estratégia

Implementar primeiro uma produção mínima baseada nos contratos existentes, sem
introduzir um segundo renderer. Cada job deve ser local, limitado ao workspace,
cancelável e reexecutável sem sobrescrever saída sem autorização explícita.

## Testes da MISSÃO 025

- projeto vazio e projeto inválido;
- roteiro salvo e reaberto;
- voz/idioma incompatíveis;
- modelo ausente e síntese interrompida;
- asset ausente e path fora da raiz;
- seek/pausa durante composição;
- exportação concluída, falha e cancelamento;
- MP4 validado por FFprobe e decodificação completa;
- recuperação após reiniciar o servidor.

