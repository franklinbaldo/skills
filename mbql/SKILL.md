---
name: mbql
description: >-
  Converte consultas SELECT escritas em SQL do DuckDB para MBQL 5 portátil do
  Metabase. Use quando uma consulta existe em SQL/DuckDB e precisa virar uma
  query MBQL editável/normalizável pelo Metabase sem reescrever a lógica à mão.
compatibility: >-
  Requires Python 3.11+ and uv. The bundled converter uses sqlglot with the
  DuckDB dialect. Output targets the portable MBQL 5 representation used by
  Metabase's construct-query pipeline and therefore needs the exact Metabase
  database name; table and field IDs are not required.
---

# MBQL — DuckDB SQL → Metabase MBQL 5

Esta skill transforma SQL declarativo do DuckDB em **MBQL 5 portátil**.

A regra central é simples: converter somente quando há contrato semântico claro.
Quando a tradução é ambígua, o caso fica executável como xfail. Quando não há
mapeamento implementado, a conversão falha explicitamente.

## Contrato

Entrada:

```sql
SELECT status, count(*)
FROM orders
WHERE total > 100
GROUP BY status
HAVING count(*) > 3
ORDER BY count(*) DESC
LIMIT 20
```

Saída: objeto MBQL 5 com `lib/type: "mbql/query"`, uma ou mais stages MBQL e
referências portáteis de tabela/campo:

```json
["Database", "main", "orders", "status"]
```

O nome do database é o **nome exato exibido pelo Metabase**, não um ID. O schema
padrão para SQL DuckDB não qualificado é `main`, mas pode ser trocado com
`--schema`.

## Como executar

```bash
uv run scripts/sql_to_mbql.py \
  --database "Analytics" \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Arquivo:

```bash
uv run scripts/sql_to_mbql.py --database "Analytics" --file consulta.sql
```

Stdin:

```bash
cat consulta.sql | uv run scripts/sql_to_mbql.py --database "Analytics"
```

## O que a v2 converte

- `SELECT` simples;
- projeção de colunas e expressões aritméticas simples;
- aliases de projeções não agregadas;
- `FROM schema.table` e tabelas sem schema;
- `WHERE` com `AND`, `OR`, comparações, `BETWEEN`, `IN`, `IS NULL`,
  `IS NOT NULL`, `LIKE` e `ILIKE` simples;
- `GROUP BY`;
- `COUNT`, `COUNT(DISTINCT campo)`, `SUM`, `AVG`, `MIN`, `MAX`, `MEDIAN`;
- `HAVING` sobre agregações projetadas, convertido para segunda stage;
- `ORDER BY`, inclusive alias de agregação;
- `LIMIT`;
- `INNER`, `LEFT`, `RIGHT` e `FULL JOIN` com `ON` formado por comparações
  ligadas por `AND`.

## Conformance harness

A skill inclui uma suíte própria para responder uma pergunta mais forte que
"o exemplo converte?": **qual parte do dialeto DuckDB SQL tem contrato MBQL
conhecido, ambíguo ou ausente?**

Rode:

```bash
uv run tests/test_conformance.py
uv run scripts/conformance.py
```

O harness combina quatro técnicas:

1. **Geração property-based com Hypothesis.** Um gerador de gramática finita cria
   famílias de ASTs SQL válidas. O CI executa centenas de combinações por run e
   o Hypothesis minimiza automaticamente qualquer contraexemplo.
2. **Metamorphic testing.** Variações que não mudam a semântica do SQL, como
   whitespace e terminador, devem gerar MBQL idêntico.
3. **Fixture DuckDB adversarial.** `tests/fixtures/adversarial.sql` contém NULLs,
   duplicatas, números negativos, zero, Unicode, diferenças de caixa, joins sem
   correspondência e timestamps de borda para evitar equivalências acidentais.
4. **Matriz executável de features.** `scripts/conformance.py` classifica cada
   feature como `supported`, `ambiguous` ou `unsupported` e declara orçamento
   de `semantic_mismatch_allowed = 0`.

Isto é **exaustividade limitada por gramática/profundidade**, não a afirmação
impossível de enumerar todas as strings SQL. O espaço pode ser expandido de
forma monotônica adicionando operadores, tipos e profundidade ao gerador.

## TDD e xfails

Nova semântica nasce primeiro como teste.

Quando ainda não existe um contrato único e seguro, o caso permanece como
`pytest.mark.xfail(strict=True)`. `strict=True` é importante: se uma mudança fizer
o caso passar, o CI acusa XPASS e obriga a revisar a classificação em vez de
silenciosamente manter uma ambiguidade já resolvida.

Xfails atuais incluem:

- `SELECT DISTINCT` em nível de linha;
- `OFFSET`/paginação;
- window functions;
- o oracle diferencial DuckDB ↔ Metabase, até existir um executor MBQL real no
  CI.

O último xfail é deliberado. O lado DuckDB já roda sobre a fixture adversarial;
o lado Metabase **não é fingido**. Quando houver um executor MBQL conectado,
essa fronteira deve virar teste diferencial real:

```text
DuckDB SQL -> resultado A
DuckDB SQL -> converter -> MBQL -> Metabase -> resultado B
normalize(A) == normalize(B)
```

## O que deve falhar em vez de improvisar

A v2 continua rejeitando deliberadamente:

- CTEs (`WITH`);
- subqueries como fonte ou em `IN`;
- window functions / `QUALIFY`;
- `SELECT DISTINCT` enquanto o xfail não for resolvido;
- `OFFSET` enquanto o contrato de paginação não for resolvido;
- `HAVING` com expressão entre agregações ainda não materializada;
- joins com predicados sem representação segura;
- `UNION` / `INTERSECT` / `EXCEPT`;
- `UNNEST`, `PIVOT`, `ASOF JOIN`;
- referências `catalog.schema.table` do DuckDB.

## Regra de fidelidade

O conversor é **AST → AST**, não regex. `sqlglot` interpreta a entrada com
`read="duckdb"`; só depois o script produz cláusulas MBQL.

Uma conversão que muda o sentido silenciosamente é pior que um erro explícito.
O orçamento da suíte para mismatch semântico conhecido é zero.

## MBQL de destino

A saída segue o formato portátil MBQL 5:

```json
{
  "lib/type": "mbql/query",
  "stages": [
    {
      "lib/type": "mbql.stage/mbql",
      "source-table": ["Analytics", "main", "orders"]
    }
  ]
}
```

Cada cláusula usa:

```json
["operador", {}, "argumentos..."]
```

Cada campo da primeira stage usa FK portátil:

```json
["field", {}, ["Analytics", "main", "orders", "total"]]
```

Em JOIN explícito, campos da tabela juntada recebem `join-alias`.

## HAVING e nomes entre stages

MBQL usa o nome físico produzido pela stage anterior. Para agregações simples,
esses nomes são `count`, `sum`, `avg`, `min`, `max`, `median` e `distinct`, com
sufixos `_2`, `_3` quando uma mesma função aparece várias vezes.

O alias SQL ajuda a resolver a referência, mas não muda o machine name
materializado pelo MBQL.

## Próxima expansão da suíte

A direção natural é minerar consultas da própria suíte upstream do DuckDB e
adicioná-las ao corpus reproduzível. Cada consulta descoberta deve terminar em
uma das três classes, nunca em silêncio:

```text
SUPPORTED   -> converte e satisfaz as propriedades/oracle disponível
AMBIGUOUS   -> xfail estrito com razão explícita
UNSUPPORTED -> ConversionError explícito
```

## Definition of Done

A conversão está pronta quando:

- o SQL é aceito pelo parser DuckDB;
- toda construção usada tem tradução explícita;
- a saída é MBQL 5 portátil, sem IDs inventados;
- joins carregam alias corretamente;
- construções fora do suporte falham com mensagem útil;
- nova semântica nasce primeiro como teste;
- ambiguidades permanecem como xfails explicativos;
- o conformance report não admite mismatch semântico silencioso.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction
effect, and any friction/workaround. Routine success stays ephemeral. If there
is actionable learning, search `franklinbaldo/skills` issues and update a
matching issue or open a sanitized **Skill use feedback** issue. Never publish
secrets or private/confidential data merely to report feedback.
