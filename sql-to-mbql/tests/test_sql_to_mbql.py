"""Tests for conservative first slice; run with pytest and sqlglot installed."""
import importlib.util
from pathlib import Path

import pytest

module_path = Path(__file__).resolve().parents[1] / "scripts" / "sql_to_mbql.py"
spec = importlib.util.spec_from_file_location("sql_to_mbql", module_path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SCHEMA = {"tables": {"documents": {"id": 17, "fields": {"id": 11, "status": 12}}}}


def test_projection_filter_sort_limit():
    query = module.convert(
        "SELECT id FROM documents WHERE status = 'SENT' ORDER BY id DESC LIMIT 101",
        SCHEMA,
    )["query"]
    assert query == {
        "source-table": 17,
        "fields": [["field", 11, None]],
        "filter": ["=", ["field", 12, None], "SENT"],
        "order-by": [["desc", ["field", 11, None]]],
        "limit": 101,
    }


@pytest.mark.parametrize("sql", [
    "SELECT id FROM documents JOIN other ON documents.id = other.id",
    "SELECT id, COUNT(*) FROM documents GROUP BY id",
    "SELECT id FROM documents LIMIT 10 OFFSET 2",
    "SELECT id + 1 FROM documents",
    "SELECT id AS other FROM documents",
    "SELECT id FROM documents WHERE status IN ('SENT', NULL)",
    "DELETE FROM documents",
])
def test_refuse_unsupported(sql):
    with pytest.raises(module.UnsupportedSQL):
        module.convert(sql, SCHEMA)
