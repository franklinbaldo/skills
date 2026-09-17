---
name: mbql
description: >-
  Converte consultas SELECT escritas em SQL do DuckDB para MBQL 5 portátil do
  Metabase. Use quando uma consulta existe em SQL/ DuckDB e precisa virar uma
  query MBQL editável/normalizável pelo Metabase sem reescrever a lógica à mão.
compatibility: >-
  Requires Python 3.11+ and uv. The bundled converter uses sqlglot with the
  DuckDB dialect. Output targets the portable MBQL 5 representations format
  used by Metabase's construct-query pipeline and therefore needs the exact
  Metabase database name; table and field IDs are not required.
---

# MBQL — DuckDB SQL → Metabase MBQL 5

Esta skill transforma SQL declarativo do DuckDB em **MBQL 5 portátil**.

O objetivo não é converter qualquer SQL possível. O objetivo é converter com
segurança o subconjunto que aparece em consultas analíticas comuns e **falhar
explicitamente** quando a tradução exigiria adivinhar semântica.

## Contrato

Entrada:

```sql
SELECT status, count(*)
FROM orders
WHERE total > 100
GROUP BY status
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

Da raiz desta skill:

```bash
uv run scripts/sql_to_mbql.py \
  --database "Analytics" \
  'SELECT status, count(*) FROM orders GROUP BY status'
```

Arquivo:

```bash
uv run scripts/sql_to_mbql.py \
  --database "Analytics" \
  --file consulta.sql
```

Stdin:

```bash
cat consulta.sql | uv run scripts/sql_to_mbql.py --database "Analytics"
```

Tabela em outro schema:

```bash
uv run scripts/sql_to_mbql.py \
  --database "Warehouse" \
  --schema analytics \
  'SELECT customer_id, sum(total) FROM orders GROUP BY customer_id'
```

A saída padrão é JSON indentado. Use `--compact` para uma linha.

## O que a v1 converte

- `SELECT` simples;
- projeção de colunas e expressões aritméticas simples;
- aliases de projeções não agregadas;
- `FROM schema.table` e tabelas sem schema;
- `WHERE` com `AND`, `OR`, comparações, `BETWEEN`, `IN`, `IS NULL`,
  `IS NOT NULL` e formas simples de `LIKE`;
- `GROUP BY`;
- `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `MEDIAN`;
- `ORDER BY`, inclusive alias de agregação;
- `LIMIT`;
- `INNER`, `LEFT`, `RIGHT` e `FULL JOIN` com `ON` formado por comparações
  ligadas por `AND`.

## O que deve falhar em vez de improvisar

A v1 rejeita deliberadamente:

- CTEs (`WITH`);
- subqueries como fonte ou em `IN`;
- `HAVING`;
- window functions / `QUALIFY`;
- `SELECT DISTINCT` e `COUNT(DISTINCT ...)`;
- `OFFSET`;
- joins com predicados que não possam ser representados com segurança;
- referências `catalog.schema.table` do DuckDB.

Quando uma dessas formas for necessária, simplifique/materialize a consulta ou
estenda o conversor com teste de regressão antes de usá-la.

## Regra de fidelidade

O conversor é **AST → AST**, não regex. `sqlglot` interpreta a entrada com
`read="duckdb"`; só depois o script produz as cláusulas MBQL.

Não “corrija” SQL desconhecido por aproximação textual. Uma conversão que muda
o sentido silenciosamente é pior que um erro explícito.

## MBQL de destino

A saída segue o formato portátil MBQL 5 aceito pelo pipeline de construção do
Metabase:

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

Cada cláusula usa o formato universal:

```json
["operador", {}, "argumentos..."]
```

Cada campo da primeira stage usa FK portátil:

```json
["field", {}, ["Analytics", "main", "orders", "total"]]
```

Em JOIN explícito, campos da tabela juntada recebem `join-alias`, conforme o
contrato do MBQL 5.

## Limite importante: aliases de agregação

SQL aceita `SUM(total) AS revenue`. MBQL preserva a agregação, mas o nome físico
da coluna agregada é governado pela própria representação MBQL. O script usa o
alias para resolver `ORDER BY revenue`, mas não promete que o nome final da
coluna materializada será `revenue`.

Portanto, trate a skill como conversor de **semântica de consulta**, não como um
renomeador perfeito da camada de apresentação.

## Validação recomendada

Depois de converter:

1. inspecione o JSON quando a consulta for nova ou complexa;
2. valide/normalize no Metabase antes de persistir;
3. compare o resultado da query MBQL com a consulta DuckDB original em um
   conjunto pequeno quando a equivalência importar materialmente.

## Definition of Done

A conversão está pronta quando:

- o SQL é aceito pelo parser DuckDB;
- toda construção usada tem tradução explícita;
- a saída é MBQL 5 portátil, sem IDs inventados;
- joins carregam alias corretamente;
- construções fora do suporte falham com mensagem útil;
- uma regressão nova recebe teste antes de ampliar o subconjunto suportado.
