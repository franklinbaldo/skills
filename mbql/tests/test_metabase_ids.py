#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "pytest>=8.4", "sqlglot>=27,<29"]
# ///
"""Portable MBQL to the id-based form `/api/dataset` runs, and the CLI around it (offline)."""
# ruff: noqa: E402, I001

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mbql_core.metabase_ids import catalogo_de_metadados, resolver_ids
from sql_to_mbql import ConversionError, convert_sql

METADADOS = {
    "tables": [
        {
            "id": 224,
            "name": "setores",
            "schema": "",
            "fields": [
                {"id": 2001, "name": "id", "base_type": "type/Integer", "semantic_type": "type/PK"},
                {"id": 2002, "name": "sigla", "base_type": "type/Text"},
            ],
        },
        {
            "id": 300,
            "name": "resumos",
            "schema": "",
            "fields": [
                {"id": 3001, "name": "id", "base_type": "type/Integer", "semantic_type": "type/PK"},
                {"id": 3002, "name": "pasta_id", "base_type": "type/Integer"},
                {"id": 3003, "name": "criado_em", "base_type": "type/DateTime"},
            ],
        },
    ]
}
CATALOGO = catalogo_de_metadados(METADADOS)


def _resolver(sql: str) -> dict:
    portavel = convert_sql(sql, database="ratio", source_dialect="mysql", tables=CATALOGO.esquema())
    return resolver_ids(portavel, CATALOGO, database="ratio")


def test_portable_refs_become_ids_and_expressions_a_named_list() -> None:
    estagio = _resolver("SELECT t0.id AS setor_id FROM setores AS t0 WHERE t0.sigla = '#PPI'")["stages"][0]
    assert estagio["source-table"] == 224
    assert estagio["expressions"] == [["field", {"lib/expression-name": "setor_id"}, 2001]]
    assert estagio["filters"] == [["=", {}, ["field", {}, 2002], "#PPI"]]


def test_later_stage_ref_by_name_carries_the_column_base_type() -> None:
    final = _resolver(
        "SELECT t2.id AS resumo_id, t2.criado_em FROM (SELECT t0.id, t0.criado_em FROM resumos AS t0 "
        "WHERE t0.pasta_id = 7 ORDER BY t0.criado_em DESC LIMIT 1) AS t2"
    )["stages"][-1]
    refs = [r for r in final.get("fields", []) + final.get("expressions", []) if r[0] == "field"]
    assert {r[2]: r[1]["base-type"] for r in refs if isinstance(r[2], str)} == {
        "id": "type/Integer",
        "criado_em": "type/DateTime",
    }


def test_unknown_column_is_refused() -> None:
    with pytest.raises(ConversionError):
        _resolver("SELECT t0.nao_existe FROM setores AS t0")


def test_primary_keys_come_from_the_metadata() -> None:
    assert CATALOGO.chaves_primarias() == {"setores": "id", "resumos": "id"}


def _cli(tmp_path: Path, *args: str) -> dict:
    metadados = tmp_path / "metadata.json"
    metadados.write_text(json.dumps(METADADOS), encoding="utf-8")
    saida = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "sql_to_mbql.py"),
            "--database",
            "ratio",
            "--source-dialect",
            "mysql",
            "--metadata",
            str(metadados),
            "--compact",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return json.loads(saida.stdout)


def test_cli_emits_id_based_mbql_for_api_dataset(tmp_path: Path) -> None:
    query = _cli(tmp_path, "--ids", "--database-id", "3", "SELECT t0.id FROM setores AS t0")
    assert query["database"] == 3
    assert query["stages"][0]["source-table"] == 224


def test_cli_reports_the_preconditions_of_a_guarded_rewrite(tmp_path: Path) -> None:
    saida = _cli(
        tmp_path,
        "--preconditions",
        "SELECT t0.id FROM setores AS t0 WHERE CAST(t0.sigla AS BINARY) = '#PPI'",
    )
    assert saida["preconditions"] == [
        {"kind": "CaseSensitiveEquality", "table": "setores", "column": "sigla", "value": "#PPI"}
    ]
    assert "binary" not in json.dumps(saida["query"]).lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
