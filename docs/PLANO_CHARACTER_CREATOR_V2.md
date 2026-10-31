# Plano Character Creator V2 — MISSÃO 024

## Base reutilizável

O código atual já oferece os elementos corretos para um criador futuro:

- `fabuloom.character/0.1` e perfil `animation-ready/0.1`;
- `validateCharacterPack` com IDs, hierarquia acíclica, pivôs, z-order e paths
  locais;
- `LayeredCharacterRig`/`LayeredCharacterRenderer`;
- expressões e bindings sem dependência direta de Kokoro;
- `NarratorAvatarRenderer` para o recorte facial;
- packs V2 de Dora, Santa e Alex como referência técnica;
- testes de determinismo, assets e transformações.

## Arquitetura proposta

1. **Modelo de edição:** estado imutável de personagem, versão, assets,
   camadas, bindings, expressões e metadados de voz.
2. **Biblioteca de partes:** somente assets locais autorizados, com dimensões,
   pivô, papel anatômico e integridade registrados.
3. **Editor:** seleção de corpo, cabelo, rosto, boca, olhos, acessórios,
   cores e expressões; cada operação atualiza o descriptor, não código.
4. **Preview:** renderer compartilhado com controles de repouso, piscada,
   fala RMS e rotação de cabeça.
5. **Persistência:** arquivo versionado no projeto, com migração explícita e
   autosave seguro; `localStorage` fica apenas para rascunho temporário.
6. **Exportação:** gerar asset pack somente depois da validação completa e
   dentro da raiz do projeto.

## Segurança obrigatória

Manter limites de tamanho/quantidade, MIME e magic bytes, rejeição de paths
externos, sanitização SVG ou desabilitação de SVG importado, CSP, isolamento
de decoding e confirmação antes de substituir assets. A validação atual não é
um importador seguro completo.

## Fases

- V2.0: modelo editável e preview de um pack local.
- V2.1: biblioteca de partes e expressões.
- V2.2: salvar/carregar, migração e associação de voz.
- V2.3: exportar pack e integrar ao Studio.

Não implementar nenhuma dessas fases como parte da MISSÃO 022.

