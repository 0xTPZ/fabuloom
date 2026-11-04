# FAB-PROD-004-R1 — runner cinematográfico reutilizável

Esta revisão mantém os masters do capítulo 12 intactos e torna a fronteira de
produção reutilizável para capítulos posteriores.

## Contrato de produção

Uma requisição `mode=execute` precisa informar:

- `chapter`, `chapter_title` e `source_document`;
- `scene_asset_ids`, contendo apenas IDs de placas ambientais aprovadas;
- `storyboard`, com entradas `{asset_id, story_segment_start, story_segment_end}`.
  Os intervalos são inteiros, semiabertos `[início, fim)`, e precisam cobrir
  todos os segmentos narrativos sem lacunas ou sobreposição;
- `host_intro` e `host_outro`, fornecidos pelo documento/contrato editorial;
- voz `pm_santa` em `pt-BR` e as variantes de saída.

O runner copia somente os assets selecionados para o diretório isolado da
produção. O mesmo ID pode ser reutilizado em várias entradas do storyboard,
mas nenhum asset é escolhido por uma lista fixa de outro capítulo. A validação
rejeita placas não aprovadas, assets que contenham personagens e qualquer
referência que não esteja na lista solicitada.

Os nomes de timeline, SRT, WAV, relatório, captura e MP4 derivam do número e
do título da requisição. A página Canvas recebe `chapterLabel` e
`chapterNumber` pela URL de captura; os defaults são genéricos e não apontam
para um capítulo específico.

## Recuperação e concorrência

O EngineService persiste o PID e o fingerprint do runner em
`runner-process.json`, registra o mesmo estado no job e usa uma árvore de
processos isolada. Cancelamento encerra a árvore inteira. Um lock por
`workspace/exports` impede duas execuções no mesmo diretório. Um lock stale só
é removido depois de confirmar que o PID registrado não está vivo; se a
reivindicação do lock falhar, a execução é recusada sem tocar na produção.

Após reinicialização, jobs são reconciliados por resultado final, checkpoint e
PID. Um filho ainda vivo permanece marcado como ativo; um job sem filho vivo e
sem `production-result.json` vira `interrupted`. Isso evita declarar abandono
enquanto uma captura ainda está em execução e evita retomar silenciosamente
uma produção incompleta.

## Validação R1

Os testes simulam requisições independentes para os capítulos 12 e 13 com
diretórios de saída distintos. A simulação não sintetiza áudio, não recaptura
quadros e não inicia produção completa. Ela verifica que título, número,
storyboard, paths de saída e contrato de host permanecem isolados.

A produção aprovada em `workspace/exports/cronicas-book1-capitulo12-cinematic-production-attempt-2`
não é entrada de escrita desta revisão.
