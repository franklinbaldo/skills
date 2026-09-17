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

Rode:

```bash
uv run tests/test_conformance.py
uv run tests/test_live_conformance.py
uv run scripts/conformance.py
```

O harness combina geração property-based com Hypothesis, metamorphic testing,
fixture DuckDB adversarial e matriz executável de features. Cada feature termina
em uma das três classes:

```text
SUPPORTED   -> tradução definida e testada
AMBIGUOUS   -> xfail estrito com razão explícita
UNSUPPORTED -> ConversionError explícito
```

O orçamento declarado para mismatch semântico silencioso é zero.

## Oracle real: DuckDB SQL ↔ Metabase MBQL

`scripts/live_conformance.py` fecha o ciclo contra uma instância real do
Metabase usando o Agent API. O fluxo é:

```text
DuckDB SQL
  -> sql_to_mbql.py
  -> MBQL 5 portátil
  -> POST /api/agent/v2/construct-query
  -> query resolvida pelo próprio Metabase
  -> POST /api/agent/v1/execute
```

Para validar construção e executar MBQL:

```bash
export METABASE_URL="https://metabase.example.com"
export METABASE_API_KEY="..."

uv run scripts/live_conformance.py \
  --database "Analytics" \
  --execute \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Para teste diferencial completo, quando o database conectado ao Metabase aceita
o mesmo SQL DuckDB, informe também o ID numérico do database:

```bash
uv run scripts/live_conformance.py \
  --database "Analytics" \
  --database-id 7 \
  --compare-native \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Nesse modo a skill executa o SQL via `/api/agent/v1/execute-sql`, executa o MBQL
via `/api/agent/v1/execute` e exige igualdade das linhas. HTTP 202 não é tratado
como sucesso por si só: `status: failed` no corpo continua sendo falha.

Nunca grave API key no repositório. Use variável de ambiente ou secret do CI.

## Exaustividade limitada e expansão

A suíte é exaustiva **dentro de uma gramática e profundidade parametrizadas**,
não sobre todas as strings SQL possíveis. O espaço cresce monotonicamente:
adicione operadores, tipos, combinações e profundidade; o Hypothesis minimiza
qualquer contraexemplo encontrado.

A próxima camada de escala é minerar consultas da suíte upstream do DuckDB e
alimentá-las ao mesmo classificador. Cada query importada deve terminar em
`SUPPORTED`, `AMBIGUOUS` ou `UNSUPPORTED`, nunca em conversão silenciosamente
aproximada.

## TDD e xfails

Nova semântica nasce primeiro como teste. Ambiguidades permanecem como
`pytest.mark.xfail(strict=True)`: se uma evolução fizer o caso passar, XPASS
quebra o CI e obriga a promover/reclassificar aquela feature.

Xfails atuais incluem:

- `SELECT DISTINCT` em nível de linha;
- `OFFSET`/paginação enquanto o formato portátil não estiver fixado no contrato;
- window functions;
- execução diferencial sem uma instância Metabase configurada no ambiente de CI.

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

Cada cláusula usa `["operador", {}, ...args]`; campos da primeira stage usam FK
portátil. Em JOIN explícito, campos da tabela juntada recebem `join-alias`.

## HAVING e nomes entre stages

MBQL usa o nome físico produzido pela stage anterior. Para agregações simples,
esses nomes são `count`, `sum`, `avg`, `min`, `max`, `median` e `distinct`, com
sufixos `_2`, `_3` quando uma mesma função aparece várias vezes. O alias SQL
ajuda a resolver a referência, mas não muda o machine name materializado.

## Definition of Done

A conversão está pronta quando:

- o SQL é aceito pelo parser DuckDB;
- toda construção usada tem tradução explícita;
- a saída é MBQL 5 portátil, sem IDs inventados;
- joins carregam alias corretamente;
- construções fora do suporte falham com mensagem útil;
- nova semântica nasce primeiro como teste;
- ambiguidades permanecem como xfails explicativos;
- o conformance report não admite mismatch semântico silencioso;
- quando houver Metabase configurado, o oracle live consegue construir/executar
  e, no modo diferencial, comparar SQL e MBQL no servidor real.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction
effect, and any friction/workaround. Routine success stays ephemeral. If there
is actionable learning, search `franklinbaldo/skills` issues and update a
matching issue or open a sanitized **Skill use feedback** issue. Never publish
secrets or private/confidential data merely to report feedback.
