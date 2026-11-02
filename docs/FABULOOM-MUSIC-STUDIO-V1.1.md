# Fabuloom Music Studio V1.1 — refinamento visual e lote Book 1

V1.1 preserva o contrato e o fluxo do Music Studio V1, mas remove elementos decorativos que competiam com as paisagens e acrescenta uma execução de lote retomável para todas as faixas diretamente presentes em `workspace/inputs/music/book1`.

## Alterações visuais

- removida a fileira repetitiva de polígonos/cristais planos do rodapé;
- removida a faixa roxa artificial sobre o ambiente;
- adicionadas névoa em camadas, partículas com profundidade, reflexos curvos e fragmentos luminosos orgânicos;
- intensidade dos efeitos reage discretamente ao envelope RMS real;
- paletas adaptadas por estilo: `Obsidian Void`, `Crystal Dawn`, `Gaia Contemplative` e `Topazioverse Living Worlds`;
- o título é derivado do nome real da faixa/projeto, com quebra limitada e sem texto permanente grande;
- nenhuma faixa usa Santa, narrador, personagens DRAFT, legenda de fala ou lip-sync.

## Lote

O comando é sequencial e idempotente:

```powershell
python examples/music_studio_demo.py --batch-book1 --port 8900
```

Ele inventaria somente arquivos suportados diretamente em `workspace/inputs/music/book1`, cria um projeto por faixa em `workspace/exports/music-studio/book1-v11/<slug>/`, escolhe um Short de 24 segundos centrado na janela RMS de maior energia e grava `INDEX.json` e `BATCH-REPORT.md` após cada faixa.

Projetos com saídas já validadas são reutilizados na retomada. Uma faixa só recebe `DONE` quando possui os dois MP4s, as duas pranchas e validações de FFprobe, decode e blackdetect. Falhas são isoladas por faixa e registradas como `FAILED`.

## Primeiro lote produzido

Foram encontradas 7 faixas e produzidos 14 MP4s: um completo horizontal e um Short vertical por faixa. O índice e os relatórios completos estão fora do Git em:

`E:\Fabuloom\workspace\exports\music-studio\book1-v11\`

As fontes MP3 são preservadas por SHA-256 no índice e continuam com direitos comerciais `pending_owner_confirmation`. Nenhum vídeo V1 anterior é substituído.

## Links de exportação

O servidor agora procura projetos recursivamente, permite reabrir projetos em subpastas de lote e monta links somente com os formatos efetivamente retornados pelo relatório de exportação. Isso evita apresentar um link Short inexistente quando apenas o vídeo completo foi solicitado.

## Limitações

As janelas de energia são heurísticas RMS; BPM, batidas, drops e transições continuam `unavailable`. Os cenários são stills ambientais locais já aprovados do CB-001, com movimento Canvas determinístico. A aprovação artística final e a confirmação de direitos da origem Suno continuam necessárias antes de publicação.
