# Missão 033 — Clean User Acceptance

Data: 2026-11-01  
Commit de referência: `319dc53`  
Resultado: **PARTIAL**

## Ambiente isolado

Checkout: `C:\Temp\fabuloom-alpha-033-clean`  
Venv: `C:\Temp\fabuloom-alpha-033-clean\.venv`  
HF_HOME vazio inicial: `C:\Temp\fabuloom-alpha-033-hf-empty`  
Workspace/export independente: `C:\Temp\fabuloom-alpha-033-clean\workspace`

Executáveis encontrados no host, fora da distribuição: Python 3.12.10, FFmpeg e FFprobe. Isso é uma dependência do computador de validação Windows, não uma prova de máquina sem pré-requisitos.

## Instalação e Kokoro

- Clone da branch Alpha: PASS.
- Venv novo e `pip install -e .`: PASS.
- Extra `.[kokoro]` instalado após ação explícita: PASS.
- Pacote Kokoro 0.9.4, PyTorch e dependências instalados no venv isolado: PASS.
- Modelo Kokoro-82M baixado pela integração Hugging Face oficial para o HF_HOME temporário: PASS.
- Nenhum cache real do desenvolvedor foi apagado ou copiado.
- Síntese real `pm_santa`: PASS. WAV mono PCM, 24.000 Hz, 70.200 frames, 2.925 ms.

Intervenção manual: os comandos foram executados pelo agente no terminal porque o pacote ainda não oferece um instalador gráfico; o app explica essa limitação e pede consentimento no `.bat` antes do extra Kokoro.

## Primeiro vídeo

Foi criado o projeto original **A Jornada de uma Estrela**, com três cenas, três imagens públicas de teste, narração real `pm_santa`, movimentos static/zoom/pan-horizontal e exportação pelo job FFmpeg do checkout limpo. A primeira tentativa falhou corretamente porque a narração regenerou IDs de cena e as imagens ainda não estavam vinculadas; após reimportar as imagens nas cenas persistidas, a exportação concluiu.

MP4 produzido do zero: `C:\Temp\fabuloom-alpha-033-clean\workspace\exports\projects\project-ee244a51feb9\project-ee244a51feb9-1080p.mp4`  
FFprobe: H.264, AAC, 1920×1080, 8.133333 s, 604924 bytes. Decodificação integral FFmpeg: PASS.

O navegador real abriu o Studio e exibiu o projeto na biblioteca, com três cenas e estado local salvo. A captura mostrou honestamente `pm_santa · verificar` antes de uma geração pelo botão da interface; a produção do MP4 foi feita via API/terminal e, portanto, a aceitação “sem terminal” não é PASS.

## Falhas e recuperação

| Caso | Resultado |
|---|---|
| Sem modelo/cache | PASS — health identifica configuração necessária; download só ocorre após instalação/síntese autorizada |
| Imagem ausente | PASS — exportação bloqueia com mensagem clara |
| Falha inicial de exportação após regenerar cenas | PASS — erro recuperável reimportando assets nas cenas atuais |
| Porta ocupada | PASS — inicializador detecta sem encerrar processo |
| Servidor loopback | PASS — somente 127.0.0.1 |
| FFmpeg ausente | PARTIAL — estado é detectado; não foi removido do PATH global para simular |
| Download interrompido | PARTIAL — não foi interrompido durante o download real para evitar corromper o HF_HOME; retry permanece manual |
| Reabertura | PARTIAL — projeto persistido e visível no navegador; o ciclo completo após reinício gráfico ainda precisa de teste humano dedicado |

## Regressão

Após as correções da Missão 032: Python **41 passed, 1 skipped** e Node **147 passed**. Santa V5, Narrator Mode, modo Cinematográfico, persistência e validações de caminho permanecem cobertos.

## Classificação final

| Área | Estado |
|---|---|
| Instalação básica independente | PASS |
| Configuração Kokoro sem cache preexistente | PASS técnico |
| Narração real `pm_santa` | PASS técnico |
| Edição via interface | PARTIAL |
| Exportação real do zero | PASS técnico / PARTIAL via UI |
| Recuperação de falhas | PARTIAL |
| Experiência sem terminal | FAIL para aceitação pública completa |

Conclusão: o produto é reproduzível tecnicamente em checkout limpo com dependências Windows presentes, mas a Alpha ainda não atende ao critério de um usuário comum concluir tudo sem terminal. Não declarar aprovação pública, não publicar release e manter pendentes os gates Canvas × FFmpeg e aprovação humana.
