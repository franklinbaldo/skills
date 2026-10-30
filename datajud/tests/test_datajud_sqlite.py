# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Regressao do acervo relacional append-only: modelo, historico e migracao; so SQLite local."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_store as store  # noqa: E402
from datajud_dados_teste import (  # noqa: E402
    _V2,
    ANTIGOS,
    NUMERO,
    REQUISICAO,
    TRANSITO,
    _legado,
    hit,
    mov,
    registrar,
    tabelas,
)

import datajud as dj  # noqa: E402


def test_ddl_sai_do_modelo_e_as_colunas_batem(tmp_path):
    banco = tmp_path / "a.sqlite"
    store.estatisticas(banco=banco)
    with sqlite3.connect(banco) as con:
        for modelo in store.TABELAS:
            colunas = [x[1] for x in con.execute(f"PRAGMA table_info({modelo.TABELA})")]
            assert colunas == list(modelo.model_fields), modelo.TABELA


def test_reindexacao_e_score_nao_mudam_nada(tmp_path):
    banco = tmp_path / "a.sqlite"
    primeira = registrar(banco, hit())
    segunda = registrar(banco, hit(score=8.5, timestamp="2026-10-19T03:00:00Z"))

    assert primeira.observacoes[0].primeira and primeira.observacoes[0].mudou
    assert not segunda.observacoes[0].mudou, "so campos volateis mudaram"
    t = tabelas(banco)
    assert (t["observacoes"], t["vistas"], t["capas"], t["movimentos"]) == (1, 1, 1, 2)
    assert t["presencas_movimento"] == 0, "a entrada esta no proprio movimento"
    historico = store.historico(NUMERO, banco=banco).registros[0]
    assert historico.observacoes == 2 and len(historico.mudancas) == 1


def test_data_da_api_vira_inteiro_e_volta_exata(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit([mov(26, "2024-01-10T10:00:00.000Z"), mov(51, "2024-01-11 10:00")]))
    with sqlite3.connect(banco) as con:
        linhas = con.execute("SELECT instante, data_hora_texto FROM movimentos ORDER BY id").fetchall()
    assert linhas[0] == (1704880800, None), "a forma da API guarda so os segundos"
    assert linhas[1][1] == "2024-01-11 10:00", "outra forma guarda o texto como veio"
    estado = store.estado(NUMERO, banco=banco)
    assert [m.movimento.data_hora for m in estado.registros[0].movimentos] == [
        "2024-01-10T10:00:00.000Z", "2024-01-11 10:00"]
    saida = json.loads(estado.model_dump_json())
    assert saida["registros"][0]["movimentos"][0]["movimento"]["data_hora"] == "2024-01-10T10:00:00.000Z"


def test_data_anterior_a_1970_volta_exata(tmp_path):
    """No Windows, `datetime.fromtimestamp` recusa instante negativo; o acervo real tem."""
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit([mov(26, "1969-05-01T03:04:05.000Z")]))
    estado = store.estado(NUMERO, banco=banco).registros[0]
    assert estado.movimentos[0].movimento.instante < 0
    assert estado.movimentos[0].movimento.data_hora == "1969-05-01T03:04:05.000Z"
    assert store.historico(NUMERO, detalhar=True, banco=banco).registros[0].mudancas[0].itens


def test_andamento_novo_e_uma_linha_e_nao_uma_copia(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    saida = registrar(banco, hit([*ANTIGOS, TRANSITO]))

    obs = saida.observacoes[0]
    assert (obs.movimentos_entraram, obs.movimentos_sairam, obs.capa_nova) == (1, 0, False)
    t = tabelas(banco)
    assert t["movimentos"] == 3, "so o andamento novo ganhou linha"
    assert t["presencas_movimento"] == 0 and t["observacoes"] == 2
    assert t["movimento_complementos"] == 1 and t["complementos"] == 1
    assert t["tipos_movimento"] == 3
    assert t["orgaos"] == 2, "a capa traz o municipio do orgao, o movimento nao"

    estado = store.estado(NUMERO, banco=banco).registros[0]
    assert [m.tipo.codigo for m in estado.movimentos] == [26, 51, 848]
    assert estado.movimentos[-1].complementos[0].descricao == "tipo"
    assert estado.capa.orgao.nome == "1a Vara"


def test_retificacao_sai_e_entra_e_o_passado_se_reconstroi(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    with sqlite3.connect(banco) as con:
        antes = con.execute("SELECT MAX(observado_em) FROM observacoes").fetchone()[0]
    corrigido = mov(51, "2024-01-11T10:00:00Z", "Conclusao para decisao")
    saida = registrar(banco, hit([ANTIGOS[0], corrigido]))
    obs = saida.observacoes[0]
    assert (obs.movimentos_entraram, obs.movimentos_sairam) == (1, 1)

    hoje = store.estado(NUMERO, banco=banco).registros[0]
    assert [m.tipo.nome for m in hoje.movimentos] == ["Distribuicao", "Conclusao para decisao"]
    ontem = store.estado(NUMERO, em=antes, banco=banco).registros[0]
    assert [m.tipo.nome for m in ontem.movimentos] == ["Distribuicao", "Conclusao"]

    historico = store.historico(NUMERO, detalhar=True, banco=banco).registros[0]
    assert historico.observacoes == 2 and len(historico.mudancas) == 2
    assert {(i.evento, i.nome) for i in historico.mudancas[0].itens} == {
        ("entrou", "Conclusao para decisao"), ("saiu", "Conclusao")}


def test_movimento_repetido_identico_nao_colapsa(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit([ANTIGOS[0], ANTIGOS[0], ANTIGOS[1]]))
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 3

    saida = registrar(banco, hit(ANTIGOS))
    assert saida.observacoes[0].movimentos_sairam == 1, "uma das repeticoes sumiu"
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 2


def test_capa_nova_so_quando_a_capa_muda(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    saida = registrar(banco, hit(classe=156))
    assert saida.observacoes[0].capa_nova
    assert tabelas(banco)["capas"] == 2
    assert store.estado(NUMERO, banco=banco).registros[0].capa.capa.classe_codigo == 156


def test_recorte_de_campos_nao_e_ausencia(tmp_path):
    """`buscar` pede so a capa: movimentos nao vieram, e nada sai do registro."""
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    with sqlite3.connect(banco) as con:
        completa = con.execute("SELECT MAX(observado_em) FROM consultas").fetchone()[0]
    so_capa = hit()
    del so_capa["_source"]["movimentos"]
    saida = registrar(banco, so_capa, requisicao={
        "query": {"match": {"numeroProcesso": NUMERO}}, "_source": dj.CAPA_FIELDS})

    obs = saida.observacoes[0]
    assert (obs.movimentos_sairam, obs.capa_nova, obs.mudou) == (0, False, False)
    estado = store.estado(NUMERO, banco=banco).registros[0]
    assert len(estado.movimentos) == 2
    assert estado.movimentos_observados_em == completa, "os movimentos valem ate a consulta completa"
    assert estado.observado_em > completa
    with sqlite3.connect(banco) as con:
        projecao = con.execute("SELECT projecao_json FROM consultas ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert json.loads(projecao) == dj.CAPA_FIELDS

    minimo = hit()
    minimo["_source"] = {"numeroProcesso": NUMERO, "grau": "G1"}
    sem_capa = registrar(banco, minimo, requisicao={"_source": ["numeroProcesso", "grau"]})
    assert not sem_capa.observacoes[0].mudou, "capa fora do recorte nao vira capa nova"
    assert store.estado(NUMERO, banco=banco).registros[0].capa.capa.classe_codigo == 7


def test_colecao_nunca_consultada_e_nula_e_nao_vazia(tmp_path):
    """So `buscar` (capa) ate agora: o estado nao pode afirmar zero movimentos."""
    banco = tmp_path / "a.sqlite"
    so_capa = hit()
    del so_capa["_source"]["movimentos"]
    registrar(banco, so_capa, requisicao={"_source": dj.CAPA_FIELDS})
    estado = store.estado(NUMERO, banco=banco).registros[0]
    assert estado.movimentos is None and estado.movimentos_observados_em is None
    assert estado.assuntos is not None, "assuntos estao no recorte da capa"

    registrar(banco, hit())
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 2


def test_capa_vista_pela_primeira_vez_depois_e_capa_nova(tmp_path):
    banco = tmp_path / "a.sqlite"
    minimo = hit()
    minimo["_source"] = {"numeroProcesso": NUMERO, "grau": "G1", "movimentos": ANTIGOS}
    registrar(banco, minimo, requisicao={"_source": ["numeroProcesso", "grau", "movimentos"]})
    with sqlite3.connect(banco) as con:
        depois = con.execute("SELECT MAX(observado_em) FROM consultas").fetchone()[0]
    saida = registrar(banco, hit())
    assert saida.observacoes[0].mudou, "a capa vista pela primeira vez e mudanca"
    novidade = store.novidades(datetime.fromisoformat(depois) + timedelta(microseconds=1),
                               banco=banco).processos[0].registros[0]
    assert novidade.capa_nova, "a primeira capa vista entra no relatorio"
    historico = store.historico(NUMERO, banco=banco).registros[0]
    assert historico.mudancas[0].capa_nova


def test_todas_as_tabelas_sao_append_only(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit([*ANTIGOS, TRANSITO]))
    registrar(banco, hit([*ANTIGOS, TRANSITO]))
    registrar(banco, hit([ANTIGOS[0]]))
    with closing(sqlite3.connect(banco)) as con:
        gatilhos = {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        for modelo in store.TABELAS:
            assert {f"{modelo.TABELA}_sem_update", f"{modelo.TABELA}_sem_delete"} <= gatilhos
            if not con.execute(f"SELECT COUNT(*) FROM {modelo.TABELA}").fetchone()[0]:
                continue
            coluna = next(iter(modelo.model_fields))
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                con.execute(f"UPDATE {modelo.TABELA} SET {coluna} = {coluna}")
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                con.execute(f"DELETE FROM {modelo.TABELA}")


def test_consulta_sem_hit_e_agregacoes_tambem_ficam_no_banco(tmp_path):
    banco = tmp_path / "eventos.sqlite"
    store.registrar_resposta(
        "tjro",
        {"size": 0, "aggs": {"c": {"terms": {"field": "classe.codigo"}}}},
        {"took": 12, "hits": {"total": {"value": 0}, "hits": []},
         "aggregations": {"c": {"buckets": [{"key": 1116, "doc_count": 2}]}}},
        banco=banco,
    )
    store.registrar_erro("stj", {"query": {"match_all": {}}}, "HTTP 504", banco=banco)
    dados = store.estatisticas(banco=banco)
    assert dados["consultas"] == 2 and dados["registros"] == 0 and dados.consultas_com_erro == 1
    with sqlite3.connect(banco) as con:
        ok, falha = con.execute(
            "SELECT resultado, resposta_meta_json, erro FROM consultas ORDER BY id"
        ).fetchall()
    payload = json.loads(ok[1])
    assert payload["aggregations"]["c"]["buckets"][0]["doc_count"] == 2
    assert "hits" not in payload["hits"], "hits.hits vao decompostos para as tabelas"
    assert falha[0] == "erro" and "504" in falha[2]


def test_migracao_do_legado_reconstroi_cada_data(tmp_path):
    banco = tmp_path / "v1.sqlite"
    _legado(banco, [
        ("2026-10-01T00:00:00.000000+00:00", hit()),
        ("2026-10-10T00:00:00.000000+00:00", hit(timestamp="2026-10-09T00:00:00Z")),
        ("2026-10-19T00:00:00.000000+00:00", hit([*ANTIGOS, TRANSITO])),
    ])
    resultado = store.migrar(banco=banco)
    assert (resultado.origem, resultado.observacoes) == ("legado", 3)
    assert Path(resultado.backup).exists(), "o arquivo antigo fica ao lado"
    assert store.migrar(banco=banco).origem == "nada", "idempotente"

    t = tabelas(banco)
    assert (t["observacoes"], t["vistas"], t["movimentos"]) == (2, 1, 3), "a reindexacao virou vista"
    assert len(store.estado(NUMERO, em="2026-10-15", banco=banco).registros[0].movimentos) == 2
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 3
    assert store.estado(NUMERO, em="2026-09-30", banco=banco).registros == []

    registrar(banco, hit([*ANTIGOS, TRANSITO]))
    assert tabelas(banco)["movimentos"] == 3, "escrita nova continua a linhagem"


def test_migracao_da_v2_preserva_estado_e_historico(tmp_path):
    """Banco da #128: consulta completa, depois reindexacao, depois retificacao."""
    banco = tmp_path / "v2.sqlite"
    dias = ["2026-10-01T00:00:00.000000+00:00", "2026-10-02T00:00:00.000000+00:00",
            "2026-10-03T00:00:00.000000+00:00"]
    with closing(sqlite3.connect(banco)) as con, con:
        for sql in _V2:
            con.execute(sql)
        for i, quando in enumerate(dias, 1):
            con.execute("INSERT INTO consultas VALUES (?, ?, 'tjro', ?, 'ok', '{}', NULL)",
                        (i, quando, json.dumps(REQUISICAO)))
        con.execute("INSERT INTO registros VALUES (1, 'api_publica_tjro:id:X', 'api_publica_tjro', 'X', 'tjro',"
                    " ?, 'G1', NULL, ?)", (NUMERO, dias[0]))
        con.execute("INSERT INTO tipos_movimento VALUES (1, 11, 26, 'Distribuicao'), (2, 12, 51, 'Conclusao')")
        con.execute("INSERT INTO capas (id, registro_id, hash64, classe_codigo) VALUES (1, 1, 5, 7)")
        con.execute("INSERT INTO assuntos VALUES (1, 1, 21, 0, 10288, 'Pensao', NULL)")
        con.execute("INSERT INTO movimentos VALUES (1, 1, 31, 0, 1, '2024-01-10T10:00:00.000Z', NULL, NULL),"
                    " (2, 1, 32, 0, 2, '2024-01-11T10:00:00.000Z', NULL, NULL)")
        con.execute("INSERT INTO observacoes VALUES (1, 1, 1, ?, 1, NULL, '{}', 1, NULL),"
                    " (2, 2, 1, ?, 1, NULL, '{}', 0, NULL), (3, 3, 1, ?, 1, NULL, '{}', 1, NULL)",
                    tuple(dias))
        con.execute("INSERT INTO presencas_movimento VALUES (1, 1, 'entrou'), (2, 1, 'entrou'), (2, 3, 'saiu')")
        con.execute("INSERT INTO presencas_assunto VALUES (1, 1, 'entrou')")
        con.execute("INSERT INTO fontes_brutas VALUES (1, 1, 'x', x'00')")

    resultado = store.migrar(banco=banco)
    assert (resultado.origem, resultado.observacoes) == ("v2", 3)
    t = tabelas(banco)
    assert (t["observacoes"], t["vistas"], t["presencas_movimento"], t["presencas_assunto"]) == (2, 1, 1, 0)
    assert store.estatisticas(banco=banco).versao == store.VERSAO
    antes = store.estado(NUMERO, em="2026-10-02", banco=banco).registros[0]
    assert [m.tipo.nome for m in antes.movimentos] == ["Distribuicao", "Conclusao"]
    assert antes.observado_em == dias[1], "a vista conta como observacao"
    depois = store.estado(NUMERO, banco=banco).registros[0]
    assert [m.tipo.nome for m in depois.movimentos] == ["Distribuicao"]
    assert [a.nome for a in depois.assuntos] == ["Pensao"]
    historico = store.historico(NUMERO, detalhar=True, banco=banco).registros[0]
    assert historico.observacoes == 3
    assert [(i.evento, i.nome) for i in historico.mudancas[0].itens] == [("saiu", "Conclusao")]
