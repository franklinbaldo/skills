#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0", "pytest>=8.4", "sqlglot>=27,<29"]
# ///
"""Exact SQL rewrites and the ones that hold under a checked precondition (offline)."""
# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sql_to_mbql import CaseSensitiveEquality, UniqueRowPerGroup
from mbql_core.rewrite import rewrite_for_mbql
from sql_to_mbql import ConversionError, convert_sql

TABELAS = {
    "caixas": {"id": "INT", "nome": "TEXT", "setores_id": "INT", "apagado_em": "DATETIME"},
    "setores": {"id": "INT", "sigla": "TEXT", "ativo": "INT"},
    "pastas": {"id": "INT", "setores_id": "INT", "responsavel_id": "INT"},
}


def _converter(sql: str) -> dict:
    return convert_sql(sql, database="ratio", source_dialect="mysql", tables=TABELAS)


def test_rewrite_merges_filtered_subquery_into_the_join() -> None:
    sql = (
        "SELECT `t4`.`nome`, `t2`.`sigla` FROM (SELECT * FROM `caixas` AS `t0` "
        "WHERE `t0`.`apagado_em` IS NULL) AS `t4` "
        "INNER JOIN `setores` AS `t2` ON `t4`.`setores_id` = `t2`.`id`"
    )
    plano = rewrite_for_mbql(sql, dialect="mysql", tables=TABELAS)
    assert "(select" not in plano.lower()
    assert "from caixas" in plano.lower().replace("`", "")


def test_without_tables_the_subquery_join_is_still_refused() -> None:
    sql = (
        "SELECT `t4`.`nome` FROM (SELECT * FROM `caixas` AS `t0` WHERE `t0`.`apagado_em` IS NULL) "
        "AS `t4` INNER JOIN `setores` AS `t2` ON `t4`.`setores_id` = `t2`.`id`"
    )
    with pytest.raises(ConversionError):
        convert_sql(sql, database="ratio", source_dialect="mysql")
    assert _converter(sql)["stages"]


@pytest.mark.parametrize(("lado", "estrategia"), [("INNER", "inner-join"), ("LEFT", "left-join")])
def test_join_only_predicate_goes_to_the_join_stage(lado: str, estrategia: str) -> None:
    sql = (
        "SELECT `t0`.`nome` FROM `caixas` AS `t0` "
        f"{lado} JOIN `setores` AS `t2` ON `t0`.`setores_id` = `t2`.`id` AND `t2`.`ativo` = 1"
    )
    juncao = _converter(sql)["stages"][0]["joins"][0]
    assert juncao["strategy"] == estrategia
    assert len(juncao["conditions"]) == 1
    filtros = juncao["stages"][0]["filters"]
    assert filtros == [["=", {}, ["field", {}, ["ratio", "main", "setores", "ativo"]], 1]]


def test_join_without_a_linking_condition_is_refused() -> None:
    sql = "SELECT `t0`.`nome` FROM `caixas` AS `t0` INNER JOIN `setores` AS `t2` ON `t2`.`ativo` = 1"
    with pytest.raises(ConversionError, match="liguem|ligue"):
        _converter(sql)


def test_same_table_under_two_aliases_is_fine_until_the_name_is_cited() -> None:
    duas = (
        "SELECT `a`.`sigla`, `b`.`sigla` FROM `pastas` AS `p` "
        "INNER JOIN `setores` AS `a` ON `p`.`setores_id` = `a`.`id` "
        "LEFT JOIN `setores` AS `b` ON `p`.`responsavel_id` = `b`.`id`"
    )
    assert len(convert_sql(duas, database="ratio", source_dialect="mysql")["stages"][0]["joins"]) == 2
    citado = duas.replace("SELECT `a`.`sigla`", "SELECT `setores`.`sigla`")
    with pytest.raises(ConversionError, match="ambíguo"):
        convert_sql(citado, database="ratio", source_dialect="mysql")


CHAVES = {"caixas": "id", "setores": "id", "pastas": "id"}


def _tem_in(plano: str) -> bool:
    return " in (select" in plano


def _reescrever(sql: str) -> str:
    return rewrite_for_mbql(sql, dialect="mysql", tables=TABELAS, primary_keys=CHAVES).lower()


def test_cte_used_twice_is_inlined() -> None:
    sql = (
        "WITH a AS (SELECT * FROM caixas WHERE apagado_em IS NULL) "
        "SELECT x.id, y.nome FROM a AS x INNER JOIN a AS y ON x.id = y.id"
    )
    assert "with" not in _reescrever(sql)


def test_cte_with_volatile_function_is_not_copied() -> None:
    sql = "WITH a AS (SELECT id, RAND() AS r FROM caixas) SELECT x.r, y.r FROM a AS x INNER JOIN a AS y ON x.id = y.id"
    assert _reescrever(sql).startswith("with")


def test_primary_key_in_becomes_inner_join() -> None:
    sql = "SELECT p.id FROM pastas AS p WHERE p.setores_id IN (SELECT s.id FROM setores AS s WHERE s.ativo = 1)"
    plano = _reescrever(sql)
    assert not _tem_in(plano) and "inner join setores" in plano


def test_other_in_becomes_grouped_join() -> None:
    sql = (
        "SELECT p.id FROM pastas AS p WHERE p.setores_id IN "
        "(SELECT c.setores_id FROM caixas AS c WHERE c.apagado_em IS NULL)"
    )
    plano = _reescrever(sql)
    assert not _tem_in(plano) and "group by" in plano


def test_in_under_or_becomes_left_join_and_is_not_null() -> None:
    sql = (
        "SELECT p.id FROM pastas AS p WHERE p.responsavel_id = 1 OR p.setores_id IN "
        "(SELECT c.setores_id FROM caixas AS c)"
    )
    plano = _reescrever(sql)
    assert not _tem_in(plano) and "left join" in plano and "not semi_1.setores_id is null" in plano


def test_in_under_not_is_left_alone() -> None:
    sql = "SELECT p.id FROM pastas AS p WHERE NOT p.setores_id IN (SELECT c.setores_id FROM caixas AS c)"
    assert _tem_in(_reescrever(sql))


def test_correlated_in_is_left_alone() -> None:
    sql = (
        "SELECT p.id FROM pastas AS p WHERE p.setores_id IN "
        "(SELECT c.setores_id FROM caixas AS c WHERE c.id = p.responsavel_id)"
    )
    assert _tem_in(_reescrever(sql))


def test_date_of_min_becomes_min_of_date() -> None:
    sql = "SELECT CAST(MIN(apagado_em) AS DATE) AS d FROM caixas"
    assert "min(cast(" in _reescrever(sql)


def test_cast_to_date_is_the_mbql_date_expression() -> None:
    query = _converter("SELECT CAST(`t0`.`apagado_em` AS DATE) AS `dia` FROM `caixas` AS `t0`")
    assert query["stages"][0]["expressions"]["dia"][0] == "date"


def test_final_aggregations_carry_their_sql_alias() -> None:
    query = _converter(
        "SELECT `t0`.`setores_id`, COUNT(`t0`.`id`) AS `n`, COUNT(DISTINCT `t0`.`nome`) AS `nomes` "
        "FROM `caixas` AS `t0` GROUP BY `t0`.`setores_id`"
    )
    nomes = [clausula[1].get("name") for clausula in query["stages"][-1]["aggregation"]]
    assert nomes == ["n", "nomes"]


def test_renamed_grouped_column_in_the_outer_query_is_refused() -> None:
    with pytest.raises(ConversionError, match="breakout"):
        _converter(
            "SELECT `t0`.`setores_id` AS `setor`, COUNT(`t0`.`id`) AS `n` "
            "FROM `caixas` AS `t0` GROUP BY `t0`.`setores_id`"
        )


TABELAS_GUARDAS = {
    "setores": {"id": "INT", "sigla": "TEXT"},
    "comentarios": {"id": "INT", "expediente_id": "INT", "criado_em": "DATETIME"},
}

BINARIO = "SELECT `t0`.`id` FROM `setores` AS `t0` WHERE CAST(`t0`.`sigla` AS BINARY) = '#PPI'"


def _janela(direcao: str = "DESC", filtro: str = "`t1`.`posicao` = 0") -> str:
    return (
        "SELECT `t1`.`expediente_id`, `t1`.`id` FROM (SELECT `t0`.`expediente_id`, `t0`.`id`, "
        "`t0`.`criado_em`, ROW_NUMBER() OVER (PARTITION BY `t0`.`expediente_id` "
        f"ORDER BY `t0`.`criado_em` {direcao}, `t0`.`id` {direcao}) - 1 AS `posicao` "
        f"FROM `comentarios` AS `t0`) AS `t1` WHERE {filtro}"
    )


def _reescrever_com_guardas(sql: str, guards: list | None) -> str:
    return rewrite_for_mbql(sql, dialect="mysql", tables=TABELAS_GUARDAS, guards=guards).lower()


def test_binary_equality_becomes_plain_and_records_its_precondition() -> None:
    guards: list = []
    plano = _reescrever_com_guardas(BINARIO, guards)
    assert "binary" not in plano
    assert guards == [CaseSensitiveEquality("setores", "sigla", "#PPI")]


def test_without_a_guard_list_the_binary_cast_stays() -> None:
    assert "binary" in _reescrever_com_guardas(BINARIO, None)


def test_latest_per_group_window_becomes_aggregations_with_its_precondition() -> None:
    guards: list = []
    plano = _reescrever_com_guardas(_janela(), guards)
    assert "over (" not in plano and "row_number" not in plano
    assert "max(" in plano and "a_max is null" in plano
    assert len(guards) == 1
    assert isinstance(guards[0], UniqueRowPerGroup)
    assert (guards[0].group, guards[0].key) == ("expediente_id", "id")


def test_ascending_window_is_not_rewritten() -> None:
    guards: list = []
    assert "row_number" in _reescrever_com_guardas(_janela("ASC"), guards)
    assert guards == []


def test_window_kept_beyond_the_first_row_is_not_rewritten() -> None:
    guards: list = []
    assert "row_number" in _reescrever_com_guardas(_janela(filtro="`t1`.`posicao` <= 2"), guards)
    assert guards == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
