---
name: mbql
description: >-
  Converte consultas SELECT escritas em SQL do DuckDB para MBQL 5 portátil do
  Metabase, com conformance auditável e oracle diferencial opcional.
compatibility: >-
  Requires Python 3.11+ and uv. The bundled converter uses sqlglot with the
  DuckDB dialect. Output targets portable MBQL 5 and needs the exact Metabase
  database name; with the database metadata JSON it can also emit id-based
  MBQL 5 for /api/dataset.
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

Com os metadados do banco (`GET /api/database/<id>/metadata?include_hidden=true`,
salvos em arquivo), a conversão vai mais longe:

```bash
uv run scripts/sql_to_mbql.py --database "ratio" --source-dialect mysql \
  --metadata metadata.json --ids --database-id 3 --file consulta.sql
```

- `--metadata` liga as reescritas que dependem do esquema (ver abaixo);
- `--ids` emite MBQL 5 com ids numéricos de tabela e campo, pronto para
  `POST /api/dataset`;
- `--preconditions` liga também as reescritas que só valem sob uma condição
  sobre os dados e devolve `{"query": ..., "preconditions": [...]}`: quem
  executa **precisa** conferir cada condição antes (ver "Pré-condições").

## Dialetos de origem (SQLGlot)

A API Python `convert_sql(sql, database="Analytics", source_dialect="mysql")`
aceita SQL de outros dialetos e normaliza **estritamente** para a representação
DuckDB antes de compilar MBQL 5. O padrão continua `duckdb`, para preservar
o contrato original. Use `--source-dialect mysql` na CLI.

O conversor fica em `scripts/mbql_core/` (camadas `base` → `expressions` →
`aggregations` → `stages` → `converter`, mais `rewrite`, `rewrite_window` e
`metabase_ids`); `scripts/sql_to_mbql.py` é a CLI e mantém a superfície de
import (`convert_sql`, `ConversionError`, `Converter`). O Pink carrega a própria
cópia em `pink.sql_to_mbql`, sem depender desta skill; a evolução semântica de
um deve ser verificada com os testes de conformidade do outro.

A normalização SQLGlot não garante equivalência semântica entre dialetos,
especialmente em funções, collations, datas, NULL ou casts. Só habilite uma
consulta em produção depois da validação diferencial SQL ↔ MBQL na instalação
Metabase efetiva. Falhas de transpile ou de MBQL devem continuar explícitas.

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

- `CAST(x AS DATE)` como a expressão `date` do MBQL;

- condição do `ON` que só lê a tabela da junção, levada para a etapa da
  própria junção (`JOIN b ON k AND p(b)` ≡ `JOIN (SELECT * FROM b WHERE p(b)) ON k`,
  para INNER e LEFT);

- a mesma tabela sob dois aliases (só é ambígua se uma coluna citar o nome da
  tabela).

Em stages posteriores, refs usam nomes de coluna, por exemplo
`["field", {}, "id"]`, em vez de FK portátil da tabela original.

### Reescritas exatas com `--metadata`

Antes de compilar, `mbql_core.rewrite` reescreve o SQL, só onde a equivalência
vale por construção:

- CTE não recursiva sem `RAND()`, expandida em cada referência;
- `x IN (SELECT pk FROM t ...)` como junção com a tabela, e qualquer outro `IN`
  sem correlação como junção com a subconsulta agrupada pela chave: `INNER` no
  `AND` de nível de cima, `LEFT` com `IS NOT NULL` sob `AND`/`OR` sem `NOT`;
- subconsultas derivadas fundidas (`merge_subqueries` do SQLGlot);
- `CAST(MIN(x) AS DATE)` como `MIN(CAST(x AS DATE))`, e o mesmo para `MAX`.

### Pré-condições (`--preconditions`)

Duas reescritas valem só sob uma condição sobre os dados. A CLI devolve a
condição; quem executa a confere com uma consulta e **recusa** se ela falha:

- `CAST(t.c AS BINARY) = 'v'` → `t.c = 'v'` (`CaseSensitiveEquality`): vale
  quando todo valor de `t.c` igual a `'v'` pela collation é `'v'` byte a byte
  (consulte os valores distintos de `t.c` com `t.c = 'v'`);
- `ROW_NUMBER() OVER (PARTITION BY p ORDER BY a DESC, k DESC)` na primeira
  posição → `MAX(a)` por grupo e `MAX(k)` entre as linhas com esse `a` (ou entre
  todas, quando o grupo só tem `a` nulo, como no `DESC` do MySQL)
  (`UniqueRowPerGroup`): vale quando, na fonte, `COUNT(*) = COUNT(DISTINCT k) = COUNT(p)`.

## Fronteiras deliberadas

Continuam ambíguos ou não suportados, conforme o caso:

- `OFFSET` não alinhado ao `LIMIT`;
- `OFFSET` sem `LIMIT`;
- `SELECT DISTINCT` sobre expressão/alias/composição;
- window functions e `QUALIFY`, salvo o `ROW_NUMBER` da primeira posição com
  `--preconditions`;
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
- `TRY_CAST`, casts DECIMAL/TIME/TIMESTAMP ainda sem equivalência explícita;
- coluna agrupada renomeada na consulta final (`SELECT t.a AS b ... GROUP BY t.a`):
  o Metabase dá à coluna o nome dela e ignora `name` em breakout;
- `SELECT` sem `FROM`, funções de tabela e `VALUES`: não há tabela do Metabase;
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
testada pelo DuckDB em backlog mensurável de gaps, e por isso **não bloqueia a
PR**: o passo final só emite um aviso com o código de saída. Em 03/11/2026, sobre
44.368 statements: 8.336 `supported`, 26.552 `unsupported`, 5.833
`contract_gap`, 64 `classification_gap` e 2.656 `parse_error`. Os gates que
bloqueiam são as suítes da skill.

## Fatos do Metabase conferidos

Conferidos no código do Metabase (`metabase.lib.aggregation`,
`metabase.driver.sql.query-processor`, `metabase.driver.mysql`) e numa
instância real (v0.63, MySQL):

- a contagem distinta (`distinct`) se chama `count`, como `count`; repetidas
  na etapa, viram `count`, `count_2`...;
- a opção `name` numa agregação dá nome à coluna; num breakout é ignorada;
- `date` compila para `CAST(x AS date)`; `temporal-unit :day` no MySQL volta
  ao tipo da coluna (DATETIME à meia-noite), então não equivale a `CAST AS DATE`;
- o driver MySQL não oferece comparação de texto sensível a maiúsculas
  (`:case-sensitivity-string-filter-options false`);
- o `/api/dataset` aceita MBQL 5 com ids numéricos de uma conta só com query
  builder, inclusive sem `lib/uuid`; responde 202 mesmo quando a consulta
  falha, então confira `status == "completed"`.

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

Com `--transport dataset`, o oracle lê os metadados do banco, converte com as
reescritas de `--metadata`, resolve ids e executa pelo `/api/dataset`; com
`--compare-native`, o SQL nativo também vai pelo `/api/dataset`. Use quando o
Agent API estiver desligado (resposta 403 "Os recursos de IA não estão
ativados") ou quando a conta só tem query builder.

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
- a saída usa MBQL 5 portátil sem IDs inventados (ids só de `--metadata`);
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
