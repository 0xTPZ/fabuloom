# Kokoro E2E Environment Recovery — Mission 051

## Estado

**PARTIAL / READY para narração; exportação final pendente de uma nova execução do harness.**

HEAD confirmado no início: `a2cd306`. A árvore estava limpa. Nenhum arquivo de `E:\Fabuloom\studio` foi alterado.

## Diagnóstico reproduzível

- Python efetivo: `.venv\Scripts\python.exe`, Python 3.12.10.
- Kokoro: 0.9.4.
- PyTorch: 2.15.0.
- huggingface-hub: 2.4.0.
- FFmpeg/FFprobe: 9.0.1.
- Cache local detectado: snapshot `hexgrad/Kokoro-82M`, contendo `kokoro-v1_0.pth`, `pf_dora.pt`, `pm_alex.pt` e `pm_santa.pt`.
- `pm_santa` foi sintetizado com sucesso pelo provider real; WAV de diagnóstico de 3025 ms foi produzido.

O bloqueio observado na Missão 050 não era ausência de modelo. O E2E observava o estado inicial do player (`pm_santa · indisponível`) antes de a operação iniciada pelo botão terminar. Depois, uma segunda asserção procurava “concluída” no campo do player, que corretamente muda para `pm_santa · pronta` após o manifesto ser carregado.

## Correções

`tools/e2e/run.mjs` agora:

- explicita `HF_HOME` somente quando a variável já existe ou o cache público padrão do usuário foi detectado;
- mantém workspace, projetos, packs e exports em diretório temporário isolado;
- aguarda o status da operação de geração, incluindo carregamento frio do modelo;
- valida sucesso pelo status da operação, não pelo estado visual do player.

`frontend/src/studio-shell.mjs` mantém a mensagem de erro da narração no estado do player para diagnóstico compreensível.

## Evidências

Execução real do botão de narração em `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-phDyKc` chegou a `pm_santa · pronta`; os fluxos de projeto, imagem, movimento, pack Ponto, persistência e restauração passaram. A rodada foi classificada incorretamente pelo teste antigo e não deve ser usada como aprovação de exportação.

O teste direto do provider foi apenas diagnóstico; não substitui a evidência exigida do botão da interface.

## Gates

| Gate | Resultado |
|---|---|
| Python/Kokoro/modelo/voz | PASS |
| Workspace isolado e pack Ponto persistente | PASS |
| Narração real via botão | PASS observado; reteste do harness corrigido pendente |
| MP4 via botão + FFprobe/FFmpeg | BLOCKED nesta execução, sem MP4 fabricado |
| Negative tests de ambiente | PENDENTE |
| PR/release | Draft; sem merge ou release |

## Limitações

O primeiro carregamento do pipeline levou aproximadamente 70 segundos e a síntese HTTP completa levou cerca de 110 segundos. O harness deve ser executado novamente após a última correção para produzir o MP4 e os resultados FFprobe/FFmpeg. Nenhum modelo, voz ou binário foi copiado para o repositório.
