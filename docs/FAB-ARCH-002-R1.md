# FAB-ARCH-002 R1 — auditoria audiovisual e operabilidade

Esta revisão mantém o `EngineService` compartilhado e acrescenta controles
explícitos para captura, exportação de áudio, armazenamento e sessão fria.

## Captura Canvas

O perfil continua econômico por padrão (`capture_fps=5`). Nesse modo o Canvas
captura quadros reais a 5 fps e o serviço materializa a sequência de saída,
registrando duplicações; o contêiner a 30 fps não é tratado como prova de
fluidez.

`capture_fps=24` ou `30` habilita captura real configurável. O serviço mede
hashes dos JPEGs de origem e da sequência de saída, verifica a contagem
esperada, mudanças adjacentes, quadros únicos e continuidade. O QA só marca
`real_canvas_capture_validated` quando a captura foi feita a 24/30 fps e houve
movimento observável entre quadros.

Validação realizada:

- Saída: `E:\Fabuloom\workspace\exports\fab-arch-002-r1-real-30fps\video.mp4`.
- 461/461 quadros de origem únicos; 460 mudanças adjacentes.
- 461/461 quadros de saída únicos; zero duplicações.
- 30 fps, 1080×1920, 15.340 s; duração do contêiner exata.
- FFprobe, decodificação FFmpeg e blackdetect aprovados.

O custo medido para essa captura foi aproximadamente 295 s para 15,34 s de
vídeo, devido ao upload local de JPEGs 1080×1920 pelo navegador. O timeout foi
feito proporcional ao número de quadros. Essa é uma limitação de desempenho
conhecida, não uma alegação de tempo real.

## Áudio

O WAV nativo do provedor permanece sem reamostragem durante a composição. A
exportação FFmpeg aceita AAC estéreo a 48 kHz por padrão. O QA compara a taxa e
o número de canais efetivamente reportados pelo FFprobe. Mixagens mantêm a
cadeia existente de ducking sidechain e limiter.

Validação Kokoro:

- Saída: `E:\Fabuloom\workspace\exports\fab-arch-002-kokoro-pm-santa-r1\video.mp4`.
- Ambiente reutilizado: `E:\Fabuloom\workspace\.venv`.
- Snapshot local: `hexgrad/Kokoro-82M`; revisão registrada no manifesto.
- Voz: `pm_santa`, `pt-BR`, WAV nativo mono a 24 kHz; exportação AAC a 48 kHz,
  estéreo.
- Duração medida no manifesto: 15.190 s; contêiner: 15.200 s (delta de 10 ms).
- FFprobe, decodificação e blackdetect aprovados.
- Não foram instaladas dependências nem alterados modelos/cache.

O pipeline continua sem alinhamento de palavras, fonemas ou visemas quando o
Kokoro não os fornece; os tempos usados são os limites medidos dos WAVs.

## Armazenamento

`FabuloomPaths` agora informa existência do root, contenção de todos os paths
gerenciados e violações explícitas. `validate_runtime_root()` falha se
`FABULOOM_ROOT` divergir do root ativo; a produção não cai silenciosamente no
perfil do usuário ou no C:. Temporários de produção seguem em
`E:\Fabuloom\workspace\staging`; exports, cache e renders permanecem dentro
do root configurado.

Preflight R1: root `E:\Fabuloom`, aproximadamente 658 GB livres, nenhuma
violação de path.

## Sessão fria

`tools/cold_agent_session.py` inicia um subprocesso sem histórico de conversa,
lê `AGENTS.md` e `docs/AGENT-OPERATIONS.md`, descobre capacidades/perfis e
seleciona dinamicamente `render.demo`. A validação produziu:

- Saída: `E:\Fabuloom\workspace\exports\fab-arch-002-cold-agent-r1`.
- Estado: `PASS`; artefatos e QA presentes.
- Captura econômica registrada corretamente como 5 fps, com 384 duplicações
  explícitas na saída de 30 fps.
- `private_assets_used=false` e aprovação artística pendente.

Não há runtime local de agente LLM independente nesta sessão. O relatório
marca `independent_model_agent=false`; portanto o teste comprova o protocolo
de operabilidade baseado somente nas instruções versionadas, não raciocínio
autônomo de um modelo.

## Limitações e próximos passos

- Otimizar o transporte de frames para reduzir o custo da captura real sem
  criar um segundo renderizador.
- Medir loudness integrado e true peak em produções musicais longas, além do
  limiter atual.
- Repetir a validação com o runtime de agente aprovado quando ele estiver
  disponível.
- A aprovação artística continua humana e separada do QA técnico.
