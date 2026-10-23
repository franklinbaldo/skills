---
name: sql-to-mbql
description: Convert a tightly supported subset of SQL to structured Metabase MBQL with verified table/field IDs
---

# SQL → structured MBQL

Run `python scripts/sql_to_mbql.py 'SELECT id FROM documents LIMIT 10' --schema schema.json`.

Install runtime dependency `sqlglot`. The caller provides trustworthy Metabase table IDs and field IDs; this tool never accesses credentials or production. Output uses **legacy structured MBQL** and must be wrapped by the caller with its verified database identifier and Metabase-version-compatible request envelope.

This first slice supports a physical single-table SELECT with simple columns or star, WHERE comparisons/boolean conditions/IS NULL/IN (without NULL), ORDER BY columns and positive LIMIT. It does **not** claim joins, grouping, subqueries, aliases, offsets, window functions, computed projections, or dialect-specific functions. Any unsupported syntax fails explicitly. SQL NULL, sort ordering, field-type coercion, and Metabase compatibility still require semantic/integration verification before production execution.

Do not interpret successful JSON generation as proof of equivalent results. Use the test suite and integration differential checks; never fall back to unsafe approximate conversion.
