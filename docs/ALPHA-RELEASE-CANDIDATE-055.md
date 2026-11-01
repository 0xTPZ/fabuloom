# Alpha Release Candidate 055

Data: 2026-11-01  
HEAD: `52c2d1f` at start; documentation candidate prepared from the current branch.  
Status: **BLOCKED_FOR_PUBLICATION / READY_FOR_OWNER_REVIEW**

## Conteúdo exato

O candidato source-only isolado foi criado em:

`C:\Users\User\AppData\Local\Temp\fabuloom-alpha-055-source-candidate-ee0a2ac5623d4a9b97d7ad1559e94eb3`

Manifesto: `MANIFEST.json`; SHA-256 do manifesto: `C752F9DFDBED4440682E93D290E5E26927702844EC768D0EC971BACA3DBC7DAE`.

O checkout contém código Fabuloom, documentação, testes, scripts, exemplos e os assets atualmente rastreados. Não contém modelos Kokoro, caches Hugging Face, ambientes virtuais, FFmpeg, credenciais, WAVs ou MP4s. O inventário tem 492 arquivos no checkout candidato.

## Bloqueio de distribuição

O inventário FAB-IP-043 registra 178 arquivos em `frontend/assets/characters/` e classifica Santa V5, Dora, Alex, logos, office art e material de identidade Topazioverse como Class C: autorização do proprietário ou licença separada não comprovada. A licença MIT do código não cobre automaticamente esses assets.

Por isso, o candidato foi preparado apenas para revisão do proprietário e **não está liberado para publicação ou distribuição**. Os assets não foram removidos, movidos ou relicenciados.

## Dependências e instalação

- Python 3.11+; ambiente virtual local.
- Node/npm para a suíte `.mjs`.
- FFmpeg/FFprobe para exportação.
- Kokoro 0.9.4, PyTorch e modelo Kokoro-82M apenas como instalação opcional, a partir das fontes oficiais e sob os termos aceitos pelo usuário.
- Nenhum runtime ou modelo é empacotado.

`INSTALL.md` documenta preparação, diagnóstico, inicialização, Kokoro opcional e exportação. A instalação totalmente gráfica não é prometida.

## Testes

- Python: 48 passed, 1 skipped.
- Node: 160 passed.
- Playwright rápido: fluxos de projeto, imagem, movimento, Ponto e persistência passaram.
- Exportação E2E 051.1: PASS, MP4 H.264/AAC validado por FFprobe/FFmpeg.
- Gate visual: PARTIAL, conforme `docs/ALPHA-VISUAL-FINAL-054.md`.
- Validação humana do diálogo nativo Windows: pendente.

## Documentação preparada

`README.md`, `INSTALL.md`, `CHANGELOG.md`, `KNOWN_LIMITATIONS.md`, `SECURITY.md`, `ALPHA-TESTING-GUIDE.md` e `RELEASE-NOTES-0.1.0-ALPHA.md` delimitam a modalidade source-only e seus limites.

## Decisão

Classificação formal do candidato: **BLOCKED** para publicação enquanto a autorização dos 178 assets não estiver registrada. Recomendação: **não publicar**; submeter o inventário e o candidato ao proprietário para decisão sobre remoção, pack local separado ou autorização artística explícita.

PR #33 deve permanecer Draft. Nenhum merge, tag, release ou alteração de visibilidade foi feito.
