---
name: legislacao-ro
description: >-
  Consulta a legislação estadual de Rondônia nos datasets abertos do Leizilla:
  leis, leis complementares, decretos e decretos-leis listados pela Casa Civil
  (1981 em diante) — ementa, data, situação no índice oficial, normas que as
  alteram, revogam ou regulamentam, links para o PDF e o texto (OCR) ou um
  artigo. Use ao redigir peças e pareceres, ou para "tem lei estadual sobre X?",
  "qual decreto regulamenta Y?", "o que diz a LC 68?", "a Lei 1.234 foi alterada
  por quais normas?", "o Decreto 12.345 está revogado?", "me dê o art. 5º da Lei
  tal". Dispare mesmo sem a palavra "legislação": basta o objeto ser norma
  estadual de Rondônia. Não use para jurisprudência (juris-tjro), metadados
  processuais (datajud), Constituição Estadual, resoluções e decretos
  legislativos da ALE-RO, lei municipal ou lei federal.
compatibility: >-
  Requires Python 3 and, on first use, outbound HTTPS to the Leizilla portal
  mirror or the Internet Archive (public, read-only, no credential). Datasets
  are cached locally; with a cache or local files it works offline. Dependencies
  are declared inline (PEP 723) and resolved by `uv run`.
---

# Legislação de Rondônia — norma, situação no índice, relações e texto

A função desta skill é responder **qual norma estadual existe, o que o índice oficial mostra sobre
ela, o que a liga a outras normas e o que o seu texto diz** — com a proveniência de cada dado à vista.

Contrato da fonte:

```text
Leizilla sabe:    norma listada pela Casa Civil/RO, título, data, ementa, marca do índice,
                  links, relações lidas das ementas, texto OCR e (poucas) normas estruturadas
Leizilla não é:   parecer de vigência, histórico completo de alterações, texto consolidado
```

Complementa [`juris-tjro`](../juris-tjro/SKILL.md) (o que o tribunal decidiu) e
[`datajud`](../datajud/SKILL.md) (metadados do processo): esta skill traz o **texto e os metadados da
norma**, não a sua aplicação.

## Regra de roteamento

- "tem lei estadual sobre X?", "qual decreto regulamenta Y?", "qual a ementa da LC 68?" → esta skill;
- "a Lei X foi alterada por quais normas?", "o Decreto Y está revogado?" → esta skill, **com as
  ressalvas abaixo**;
- "me dê o art. 5º da Lei 1.234" → esta skill (`texto`), conferindo no PDF;
- "o TJRO aplica essa lei assim?" → [`juris-tjro`](../juris-tjro/SKILL.md);
- "em que fase está o processo?" → [`datajud`](../datajud/SKILL.md);
- Constituição Estadual, resoluções e decretos legislativos da ALE-RO, lei municipal, lei federal →
  **fora do escopo**; use a fonte oficial adequada.

## O que esta skill nunca deve afirmar

1. **"Está em vigor."** A situação é **o que o índice oficial mostra**, não parecer de vigência.
   `sem-indicacao-de-revogacao` quer dizer só que o índice da Casa Civil não traz marca de revogação.
   A norma pode estar revogada tacitamente, suspensa por decisão judicial ou superada sem marca. As
   outras situações também não são vigência: `revogada` (arquivo "revogado" ou anotação "REVOGADO
   PELO…" na ementa), `retificada` e `tem-compilada` (existe versão compilada; a norma pode ter sido
   alterada).
2. **"Essas são todas as alterações."** As relações são **extraídas automaticamente das ementas por
   regras**. Faltam as alterações que só aparecem no corpo da norma. A precisão medida em amostras
   lidas à mão é de cerca de 94% ou mais, não 100%; uma ementa "altera a composição de órgão nomeado
   pelo Decreto X" fica registrada como alteração de X. Trate a lista como **pistas a conferir**, nunca
   como o histórico de alterações.
3. **"O texto é este."** O texto de `textos` é **OCR bruto da publicação capturada**: pode ter erros de
   reconhecimento, **não é consolidado** (não inclui alterações posteriores) e o PDF original prevalece.
   O texto de `versoes` é a versão estruturada, ainda derivada de OCR por um modelo; também pode errar.
4. **"A norma não existe."** A ausência no catálogo só prova que a Casa Civil não a lista (ou que o
   catálogo carregado é parcial; veja `avisos`).

## Cobertura

O catálogo cobre as **leis, leis complementares, decretos e decretos-leis listados pela Casa Civil
(1981 em diante)**. **Não inclui** a Constituição Estadual, resoluções e decretos legislativos da
ALE-RO, normas municipais nem federais.

Só uma fração das normas tem texto. O `estagio` diz até onde o Leizilla chegou:

```text
só-catalogada  <  preservada (PDF no Internet Archive)  <  legível (OCR em textos)  <  estruturada (versoes)
```

Flag nula é "não medido", nunca "falso". O `norma` confere `textos` e `versoes` diretamente. Sem texto,
use o link do PDF oficial. Medido em 2026-11-16: cerca de 39,5 mil normas no índice, cerca de 2 mil
com OCR publicado, cerca de cem estruturadas.

**Estado dos dados (2026-11-16, confira nos `avisos`):** o catálogo no formato 0.2 (com
`situacao_norma`, `busca` e links) e as `relacoes` estavam sendo publicados pela primeira vez. O
catálogo publicado ainda podia ser o formato 0.1 (parcial; o aviso informa os anos cobertos) e
`relacoes` podia dar 404. A CLI lida com isso: catálogo 0.1 funciona, com aviso e sem situação; sem
`relacoes`, `norma` diz que as relações **não foram consultadas** (não que não existem) e `relacoes`
falha nomeando o dataset.

## Como executar

Toda consulta passa por `scripts/legislacao_ro.py` (dependências inline, resolvidas por `uv run`;
saída em JSON por padrão, `--formato texto` para leitura).

```bash
uv run scripts/legislacao_ro.py buscar "plano de carreira" --tipo lc
uv run scripts/legislacao_ro.py buscar "LC 68/1992"            # citação direta
uv run scripts/legislacao_ro.py norma "LC 68/1992"
uv run scripts/legislacao_ro.py relacoes "LC 68/1992" --direcao entrada --verbo altera
uv run scripts/legislacao_ro.py texto "Lei 1234" --artigo 5
```

### `buscar`

Assunto ou citação. Filtros: `--tipo lei|lc|decreto|decreto-lei`, `--ano`, `--de`/`--ate` (anos),
`--situacao`, `--limite` (padrão 20). Todos os termos precisam casar, sem acento, como **início de
palavra** na ementa/título (não é busca por frase: "plano de carreira" casa "Plano de Cargo,
Carreira…"). Ordem: número exato primeiro, depois as mais recentes. Citações aceitas: "LC 68/1992",
"lc 68/92", "Lei 1.234", "Decreto 12345", "Lei Complementar nº 68, de 09-12-1992", "Decreto-Lei 9-A"
(ano de 2 dígitos: 81–99 é 19xx, 00–80 é 20xx). Citação sem correspondência **não** vira busca textual.

### `norma`

Identificação oficial, data, ementa, `situacao_no_indice` com as evidências, links (oficial e Internet
Archive), cobertura e relações nos dois sentidos, agrupadas por verbo (altera / alterada por, revoga /
revogada por, regulamenta / regulamentada por…). Relação não resolvida aparece marcada
(`resolvida: false`, sem `outra_norma`): é texto da ementa, não norma localizada. Se o índice lista só
a rendição compilada, o `aviso` do link diz que **não é a publicação original**.

### `relacoes`

As relações com o **trecho da ementa** que produziu cada uma (`--direcao ambas|saida|entrada`,
`--verbo`). Quando `fonte_relacao` é `anotacao-do-indice`, o trecho é a anotação "REVOGADO PELO…" da
ementa da norma revogada, não da que revoga. `parcial: true` significa que a ação recai sobre parte
da norma (artigo, inciso, anexo).

### `texto`

`--artigo N` (ou `5-A`), `--dispositivo art-5-par-2`, `--fonte auto|versoes|textos`, `--max N`.
**Sempre informa a fonte** (`fonte`: `versoes` ou `textos`). Com `auto`, usa a estruturada se houver,
senão o OCR. Com `--artigo` no OCR, devolve o trecho entre âncoras de artigo **só se a sequência de
artigos fecha**; senão recusa (saída 1) e diz que a navegação por artigo não é confiável para aquela
norma. O último artigo vai até o fim do texto e pode incluir fecho e assinaturas. O campo `proveniencia`
traz o PDF, a captura e o motor de OCR. Norma com letra no número (Decreto-Lei 9 e 9A) divide a camada
de texto com a irmã: o aviso diz para conferir no PDF.

### Fontes, cache e erros

Padrão: espelho do portal (`franklinbaldo.github.io/leizilla/data/ro/`) e, se falhar, Internet
Archive; cópia em cache (`~/.cache/legislacao-ro`, 24 h, revalidada por ETag). Para apontar outra
fonte: `--base-url` (URL ou diretório) ou `--catalogo`/`--relacoes`/`--textos`/`--versoes`
(caminho ou URL), `--cache-dir`, `--ttl-horas`, `--atualizar`, `--offline`; variáveis
`LEGISLACAO_RO_BASE_URL`, `LEGISLACAO_RO_CATALOGO` (e `_RELACOES`, `_TEXTOS`, `_VERSOES`),
`LEGISLACAO_RO_CACHE`, `LEGISLACAO_RO_TTL_HORAS`. Dataset indisponível: mensagem que o nomeia, sem
stack trace.

Saídas: 0 ok; 1 não encontrado (ou trecho recusado); 2 uso inválido; 3 dataset indisponível.

## Fluxo para peça ou parecer

1. Identifique a norma pela **citação** (`norma "LC 68/1992"`); se for assunto, `buscar` e confira a
   ementa antes de escolher.
2. Cite pela **identificação oficial** (campo `identificacao`, ex.: "Lei Complementar n. 68, de
   09-12-1992") e inclua **sempre o link do PDF oficial ou preservado**.
3. Só **transcreva** texto depois de conferi-lo no PDF. Reproduza o texto do PDF, não o OCR.
4. Sobre alterações, use `relacoes` como roteiro e leia as normas apontadas; diga que a lista é
   extraída das ementas e pode estar incompleta.
5. Sobre vigência, escreva o que o índice mostra e que **precisa ser confirmado** (Diário Oficial,
   texto consolidado oficial, normas posteriores, decisões que suspendam a eficácia).

Formulação correta:

> Segundo o índice da Casa Civil/RO, a Lei Complementar n. 68/1992 consta com versão compilada e sem
> marca de revogação; isso não equivale a confirmar sua vigência, que deve ser verificada.

Evite:

> A LC 68/1992 está em vigor.
> A LC 68/1992 foi alterada apenas pelas LCs 81, 91 e 100.

## Como apresentar

Para cada norma: identificação oficial, data, ementa, situação **no índice** (com a evidência), link e
o estágio de cobertura. Para relações, separe as resolvidas das não resolvidas e diga que são
automáticas. Para texto, diga a fonte (`versoes` ou `textos`), a rendição e que o PDF prevalece. Não
despeje JSON cru.

## Definition of Done

A consulta termina quando:

- a norma está identificada por citação oficial ou `norma_id`, sem adivinhar quando a citação é ambígua;
- a situação foi apresentada como **marca do índice**, nunca como vigência;
- as relações foram tratadas como pistas, e as não resolvidas separadas;
- todo texto traz a fonte, o aviso de OCR/consolidação e o link do PDF; trechos citados foram
  conferidos no PDF;
- os `avisos` (dataset ausente ou parcial) foram lidos e repassados;
- jurisprudência, processo, Constituição, resoluções e normas municipais ou federais ficaram com as
  fontes adequadas.

A skill é bem-sucedida quando diz **qual norma é, o que o índice marca e onde está o texto
oficial**, e sabe não dizer "está em vigor".

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
