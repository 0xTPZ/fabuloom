# Missão 029 — Fabuloom UX & Visual Audit

Data: 2026-11-01  
Branch: `release/fabuloom-alpha-preparation`  
Commit auditado: `02a63e1`  
Ambiente: Windows, Python 3.12.10, FFmpeg disponível, Kokoro detectado, Studio local em `http://127.0.0.1:8893/`.

## Escopo e evidência

A auditoria foi feita no navegador real, sem mockups, em checkout público separado. Foram observadas as rotas Dashboard, Projetos, Roteiro, Cenas, Narradores, Áudio, Prévia, Exportação e Configurações. As capturas reais incluem o dashboard inicial e Configurações; a captura de Cenas da validação anterior mostrou o editor com três cenas, duração, movimento e reordenação. A inspeção cobriu desktop amplo, notebook e viewport estreito de aproximadamente 599 px; a composição mobile de 390 px permanece recomendada para a próxima rodada, pois não há emulação física confiável neste ambiente sem alterar o navegador do usuário.

## Resultado do primeiro uso

| Etapa | Resultado | Evidência / fricção |
|---|---|---|
| Abrir Studio | PASS | Dashboard local, projeto ativo vazio e CTA de primeiro vídeo visíveis. |
| Criar projeto | PASS | Dialogo de projeto e persistência local funcionais. |
| Projetos | PASS | Lista reaberta após reload; projetos locais visíveis. |
| Roteiro | PASS | Exemplo cria texto original e permite edição. |
| Cenas | PASS | Três cenas, editor de texto/duração/movimento e seleção persistem. |
| Imagens | PARTIAL | Fluxo depende de arquivos locais válidos; falta feedback mais guiado para o primeiro asset. |
| Movimento | PASS técnico / PARTIAL visual | `static`, `zoom`, `pan-horizontal` e `pan-vertical` são validados e exportados; a prévia principal não os representa. |
| Narração | PASS condicionado | Kokoro/`pm_santa` funciona quando pacote, modelo e cache público estão configurados; primeiro setup continua técnico. |
| Prévia | PARTIAL | Prévia persistente é o palco do Narrator Mode Santa V5, não a composição de imagens e câmera da cena. |
| Exportação | PASS técnico | MP4 real H.264/AAC validado por FFprobe: 1920x1080, 13.566667 s, 693290 bytes. |
| Reabrir projeto | PASS | Ordem, texto e configuração de cena sobrevivem ao reload. |

## Matriz de capacidades

| Capacidade | Estado |
|---|---|
| Persistência local | PASS |
| Santa V5 visual aprovado | PASS |
| Kokoro real com `pm_santa` | PARTIAL: requer instalação/modelo/cache documentados |
| Validação de cenas e caminhos | PASS |
| Exportação FFmpeg | PASS |
| Prévia de composição final | FAIL como paridade; PARTIAL como Narrator Mode |
| Mensagens para dependências ausentes | PARTIAL |
| Instalação limpa | PARTIAL: checkout reproduzível, mas download inicial do modelo ainda é responsabilidade do usuário |

## Canvas versus FFmpeg

O exportador foi validado com um MP4 real existente no workspace público. FFprobe confirmou vídeo H.264 1920x1080, áudio AAC e duração de 13.566667 s. As opções de câmera são aceitas no manifesto e chegam ao job FFmpeg.

Achado reproduzível UX-029-01 (P1): a prévia exibida pela interface é o `Narrator Mode` com Santa V5, enquanto os controles de cena e câmera alteram a composição de imagens usada pelo exportador. Assim, mover uma cena ou escolher zoom/pan pode alterar o MP4 sem alterar visualmente o palco persistente da prévia. Isso é uma divergência de produto, não uma falha de FFmpeg. Não foi feita reescrita de renderer nesta missão.

## Achados priorizados

- **P1 — UX-029-01:** prévia e composição exportada não compartilham a mesma representação visual; o usuário pode aprovar uma coisa e exportar outra.
- **P2 — UX-029-02:** setup de Kokoro ainda expõe detalhes técnicos de pacote, modelo, licença e cache; o estado “instalado” não significa necessariamente “modelo pronto para gerar”.
- **P2 — UX-029-03:** editor de cenas fica comprimido em viewport estreito; textarea e controles competem por largura e exigem rolagem.
- **P2 — UX-029-04:** importação de imagem e recuperação de arquivo ausente poderiam explicar o próximo passo com mais clareza para primeiro uso.
- **P3 — UX-029-05:** rótulos como “Roteiro beta”, “Cenas beta” e `pm_santa` são úteis para diagnóstico, mas aumentam a carga cognitiva de um usuário comunitário.

Não foi identificado P0. Não foram observados vazamentos remotos: a interface informa modo local e os caminhos de exportação permanecem no workspace autorizado.

## Testes de falha e recuperação

Validações automatizadas cobrem câmera suportada, duração inválida, IDs duplicados, caminhos inseguros e rejeição de assets inválidos. O botão de exportação possui bloqueio contra duplicação durante job. A arquitetura também distingue ausência de Kokoro/FFmpeg e erro de geração; falta uma jornada visual mais completa para simular cada dependência ausente sem alterar o ambiente global.

## Testes executados

- Python: **39 passed, 1 skipped**.
- Testes Node/frontend: **todos passaram**.
- FFprobe: MP4 real validado em 1920x1080, H.264/AAC, 13.566667 s.
- Navegador: dashboard inicial, configurações, projeto de exemplo, cenas, edição, reordenação e reload observados em execução real.

## Recomendações para a Missão 030

1. Definir uma composição de cena compartilhada entre Canvas e FFmpeg, com amostras de frame no mesmo timestamp.
2. Exibir no preview a composição real de imagens/câmera quando o projeto estiver nessa etapa; manter Narrator Mode como modo separado.
3. Transformar Kokoro em onboarding guiado com estados “pacote”, “modelo”, “voz” e “pronto”.
4. Adicionar harness de auditoria visual para static/zoom/pan e regressão de layout em 390/768/1080 px.

Conclusão: o alpha é utilizável para criar, persistir e exportar um projeto local narrado, mas a aceitação visual completa fica **PARTIAL** até resolver a paridade entre prévia e MP4.
