---
name: mbql
description: >-
  Converte consultas SELECT escritas em SQL do DuckDB para MBQL 5 portátil do
  Metabase, com conformance auditável e oracle diferencial opcional.
compatibility: >-
  Requires Python 3.11+ and uv. The bundled converter uses sqlglot with the
  DuckDB dialect. Output targets portable MBQL 5 and needs the exact Metabase
  database name; table and field IDs are not required.
---

# MBQL — DuckDB SQL → Metabase MBQL 5

Esta skill compila SQL declarativo do DuckDB para **MBQL 5 portátil**.

A regra é: converter apenas quando existe contrato semântico explícito. Caso
ambíguo fica visível como xfail/erro; caso não representável não é aproximado.

## Uso

```bash
uv run scripts/sql_to_mbql.py \
  --database "Analytics" \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Também aceita `--file consulta.sql` ou stdin. O schema padrão de tabelas não
qualificadas é `main`; altere com `--schema`.

## Subconjunto atualmente suportado

O conversor cobre, entre outros:

- `SELECT` sobre tabela direta;
- projeções, aliases e expressões aritméticas;
- `WHERE` com `AND`, `OR`, comparações, `BETWEEN`, `IN`,
  `IS NULL`, `IS NOT NULL`, `LIKE` e `ILIKE` simples;
- `GROUP BY` por coluna, alias de projeção ou ordinal;
- `ORDER BY` por coluna, expressão/alias, agregação ou ordinal;
- `COUNT`, `COUNT(DISTINCT campo)`, `SUM`, `AVG`, `MIN`, `MAX`,
  `MEDIAN`, `STDDEV_POP` e `VAR_POP`;
- `HAVING` simples sobre agregações projetadas, via stage posterior;
- `LIMIT`;
- `LIMIT N OFFSET k*N` exatamente como
  `page: {page: k+1, items: N}`;
- `SELECT DISTINCT` de uma ou várias colunas diretas como breakouts/distinct-values;
- `INNER`, `LEFT`, `RIGHT` e `FULL JOIN` com comparações ligadas por
  `AND`, desde que campos em contexto de JOIN estejam qualificados;
- `LOWER`, `UPPER`, `COALESCE`, `ABS`;
- `CONCAT`, `SUBSTRING`, `REPLACE`, `TRIM` simples e `LENGTH`;
- `CASE` pesquisado e simples, além de `IF`;
- `EXTRACT` para year/month/day/hour/minute/second/quarter;
- casts seguros para texto, inteiros e float/double;
- subquery linear em `FROM`, inclusive agregações com alias SQL explícito,
  compilada como stage anterior;
- JOIN contra subquery derivada linear, usando `stages` próprios do join;
- cadeia de CTEs não recursivos estritamente linear (`x -> y -> SELECT final`),
  compilada como pipeline de stages;
- aliases cross-stage de agregações e colunas diretas, resolvidos para os
  machine names efetivos do MBQL.

Em stages posteriores, refs usam nomes de coluna, por exemplo
`["field", {}, "id"]`, em vez de FK portátil da tabela original.

## Fronteiras deliberadas

Continuam ambíguos ou não suportados, conforme o caso:

- `OFFSET` não alinhado ao `LIMIT`;
- `OFFSET` sem `LIMIT`;
- `SELECT DISTINCT` sobre expressão/alias/composição;
- window functions e `QUALIFY`;
- `HAVING` com aritmética entre agregações ainda não materializada;
- agregação em fonte derivada **sem alias SQL explícito**; com alias, o
  conversor resolve o nome SQL para o machine name MBQL (`sum`, `sum_2`, etc.);
- breakout agrupado **por expressão** quando o machine name cross-stage não é
  estável;
- CTE recursivo, cadeia ramificada/não linear ou query final que não consome
  exclusivamente o último CTE;
- JOIN sobre cadeia de CTEs; joins contra subquery derivada linear são suportados;
- coluna sem qualificação em query com JOIN;
- `UNION`, `INTERSECT`, `EXCEPT`;
- `UNNEST`, `PIVOT`, `ASOF JOIN`;
- `TRY_CAST`, casts DECIMAL/temporais ainda sem equivalência explícita;
- `EXTRACT` de unidades com convenções calendáricas não fixadas, como week;
- `STDDEV`/`STDDEV_SAMP` e `VARIANCE`/`VAR_SAMP`: DuckDB usa semântica
  amostral, enquanto MBQL `stddev`/`var` são populacionais;
- agregações sem contrato explícito (por exemplo, `CORR`) até mapeamento
  semântico comprovado;
- referência `catalog.schema.table`.

Falhar explicitamente é parte do contrato.

## Conformance harness

Rode:

```bash
uv run tests/test_conformance.py
uv run tests/test_live_conformance.py
uv run tests/test_corpus_runner.py
uv run scripts/conformance.py
```

A suíte combina:

- Hypothesis com centenas de queries geradas por run;
- testes metamórficos;
- fixture DuckDB adversarial;
- matriz de features `SUPPORTED / AMBIGUOUS / UNSUPPORTED`;
- xfails estritos para contratos ainda não decididos;
- corpus runner para `.sql`, DuckDB SQLLogicTest `.test` e `.test_slow`.

O orçamento de mismatch semântico silencioso é **zero**.

### Drift bidirecional

`scripts/corpus_runner.py` sempre tenta converter cada query e compara isso com
a matriz:

- matriz diz `SUPPORTED`, conversor falha → `contract_gap`;
- matriz diz `AMBIGUOUS/UNSUPPORTED`, conversor já converte →
  `classification_gap`.

Ambos fazem o runner sair com erro. Assim implementação e classificação não
podem divergir silenciosamente.

O runner entende diretamente a suíte SQLLogicTest do DuckDB, ignorando blocos
`statement` de setup e extraindo os blocos `query`. O relatório também
contabiliza `driver_feature_counts`, separando equivalência MBQL da capacidade
real de execução de cada driver.

## Auditoria upstream do DuckDB

O workflow `.github/workflows/mbql-duckdb-corpus.yml` faz checkout
esparso de `duckdb/test/sql`, roda o corpus runner e publica o relatório como
artifact. A auditoria é exploratória: serve para transformar a linguagem real
testada pelo DuckDB em backlog mensurável de gaps.

## Oracle real: SQL ↔ MBQL no Metabase

`scripts/live_conformance.py` usa o Agent API:

```text
DuckDB SQL
  -> sql_to_mbql.py
  -> MBQL 5 portátil
  -> POST /api/agent/v2/construct-query
  -> POST /api/agent/v1/execute
```

Com `--database-id`, o oracle consulta as capabilities reais do driver e
falha cedo quando a query exige algo que o backend não oferece (por exemplo,
`nested-queries`, `expressions`, `right-join`,
`percentile-aggregations` ou `standard-deviation-aggregations`).

Com `--compare-native`, também executa o SQL em
`/api/agent/v1/execute-sql` e compara os resultados.

```bash
export METABASE_URL="https://metabase.example.com"
export METABASE_API_KEY="..."

uv run scripts/live_conformance.py \
  --database "Analytics" \
  --database-id 7 \
  --compare-native \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Com `ORDER BY`, a sequência de linhas deve coincidir. Sem `ORDER BY`, o
oracle compara **multiconjuntos**: ignora ordem, mas preserva duplicidade.

Nunca grave API key no repositório.

## Regra de fidelidade

O conversor é AST → AST. `sqlglot` interpreta a entrada com
`read="duckdb"`; só depois são emitidas cláusulas MBQL.

Toda cláusula MBQL 5 usa `["operador", {}, ...args]`. Campos da primeira stage
usam FK portátil `[database, schema, table, field]`; stages posteriores usam
machine names.

## TDD

Nova semântica nasce primeiro como teste.

Ambiguidades ficam como `pytest.mark.xfail(strict=True)` ou
`unittest.expectedFailure`. Se uma evolução fizer o caso passar, o teste deve
ser promovido e a matriz atualizada.

## Definition of Done

Uma tradução é considerada coberta quando:

- o SQL é aceito pelo parser DuckDB;
- todas as construções usadas têm classificação explícita;
- `SUPPORTED` converte sem `contract_gap`;
- a saída usa MBQL 5 portátil sem IDs inventados;
- JOINs não dependem de resolução de coluna que exigiria metadata ausente;
- features fora do contrato falham de forma útil;
- o corpus runner não reporta `contract_gap` nem `classification_gap`;
- quando houver Metabase configurado, o oracle live constrói/executa e pode
  provar equivalência SQL ↔ MBQL.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction
effect, and any friction/workaround. Routine success stays ephemeral. If there
is actionable learning, search `franklinbaldo/skills` issues and update a
matching issue or open a sanitized **Skill use feedback** issue. Never publish
secrets or private/confidential data merely to report feedback.
