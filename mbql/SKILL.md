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

## O que a v2 converte

- `SELECT` simples;
- projeção de colunas e expressões aritméticas simples;
- aliases de projeções não agregadas;
- `FROM schema.table` e tabelas sem schema;
- `WHERE` com `AND`, `OR`, comparações, `BETWEEN`, `IN`, `IS NULL`,
  `IS NOT NULL`, `LIKE` e `ILIKE` simples;
- `GROUP BY`;
- `COUNT`, `COUNT(DISTINCT campo)`, `SUM`, `AVG`, `MIN`, `MAX`, `MEDIAN`;
- `HAVING` sobre agregações projetadas, convertido para uma segunda stage;
- `ORDER BY`, inclusive alias de agregação;
- `LIMIT`;
- `INNER`, `LEFT`, `RIGHT` e `FULL JOIN` com `ON` formado por comparações
  ligadas por `AND`.

## Ambiguidades ficam executáveis

O arquivo `scripts/test_sql_to_mbql.py` é também parte da especificação. O fluxo
de evolução é **TDD**: primeiro entra o caso em teste; depois entra a tradução.

Quando ainda não existe um contrato único e seguro, o caso permanece como
`unittest.expectedFailure`, com a ambiguidade descrita no próprio teste. Isso
mantém visível a fronteira entre "não implementado" e "semântica ainda não
decidida".

Xfails atuais:

- `SELECT DISTINCT`: row-level distinct não é sempre equivalente a mero
  `breakout` quando há expressão, ordenação ou limite;
- `OFFSET`: falta decidir o contrato exato `OFFSET/LIMIT` → `page/items`;
- `HAVING` com aritmética entre agregações: exige decidir como nomear/materializar
  a expressão entre stages;
- window functions: exigem semântica multi-stage específica, não uma aproximação.

## O que deve falhar em vez de improvisar

A v2 continua rejeitando deliberadamente:

- CTEs (`WITH`);
- subqueries como fonte ou em `IN`;
- window functions / `QUALIFY`;
- `SELECT DISTINCT` enquanto o xfail acima não for resolvido;
- `OFFSET` enquanto o contrato de paginação não for resolvido;
- `HAVING` cuja agregação não esteja projetada ou que faça aritmética ainda não
  materializada;
- joins com predicados que não possam ser representados com segurança;
- referências `catalog.schema.table` do DuckDB.

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

## HAVING e nomes entre stages

MBQL usa o nome físico produzido pela stage anterior. Para agregações simples,
esses nomes são `count`, `sum`, `avg`, `min`, `max`, `median` e `distinct`, com
sufixos `_2`, `_3` quando uma mesma função aparece várias vezes.

Assim, SQL como:

```sql
SELECT status, SUM(total) AS revenue
FROM orders
GROUP BY status
HAVING revenue >= 1000
```

vira uma primeira stage com `sum(total)` e uma segunda stage filtrando
`["field", {}, "sum"]`. O alias SQL ajuda a resolver a referência, mas não muda
o machine name materializado pelo MBQL.

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
- nova semântica nasce primeiro como teste;
- ambiguidades ainda não resolvidas permanecem como xfails explicativos, não
  como conversões aproximadas.
