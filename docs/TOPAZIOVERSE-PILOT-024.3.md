# Topazioverse Book 1 — piloto V3

O piloto V3 transforma o Santa V5 em anfitrião recorrente sem reescrever o
miolo literário. A narrativa existente da V2 continua sendo a fonte do bloco
`STORY_CHAPTER`; a V3 acrescenta apenas duas falas editoriais sintetizadas
com Kokoro `pm_santa` em `pt-BR`.

## Blocos

1. `HOST_INTRO`: Santa aparece maior, em um estúdio/biblioteca procedural,
   acolhe os viajantes e apresenta o projeto.
2. `STORY_CHAPTER`: os 46 segmentos medidos da V1/V2 são reutilizados sem
   nova síntese. Santa permanece no medalhão durante todas as cenas.
3. `HOST_OUTRO`: Santa retorna ao enquadramento maior, agradece e convida a
   audiência a continuar a jornada.

As pausas de transição são editoriais e explícitas no timeline; não são
apresentadas como duração de fala. As legendas usam somente os intervalos
medidos dos WAVs. O pipeline não inventa timestamps de palavras, fonemas ou
visemas; a boca continua sendo uma aproximação por RMS.

## Execução local

Com o ambiente Kokoro local disponível e FFmpeg instalado:

```powershell
python examples/topazioverse_book1_pilot_v3_demo.py
```

Para re-sintetizar apenas as falas do anfitrião:

```powershell
python examples/topazioverse_book1_pilot_v3_demo.py --resynthesize-host --overwrite
```

O script reutiliza as falas existentes quando os manifestos locais de intro e
outro já existem. Todos os artefatos ficam em
`E:/Fabuloom/workspace/exports/topazioverse-book1-episode1-pilot-v3/` e não
devem ser adicionados ao Git.

## Áudio e publicação

A trilha fornecida pelo proprietário é mantida localmente. O mix usa volume
discreto durante as falas do anfitrião, retorna ao nível usado pela V2 durante
a história, aplica ducking por sidechain e sobe suavemente no encerramento.
As condições de publicação da faixa original/Suno ainda precisam ser
confirmadas pelo proprietário.

## Estado

O resultado técnico deve ser revisado por uma pessoa quanto à naturalidade da
fala, equilíbrio entre voz e música, legibilidade das legendas e qualidade
artística. A aprovação automática dos testes não substitui essa revisão.
