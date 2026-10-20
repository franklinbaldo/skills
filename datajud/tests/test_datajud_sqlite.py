# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Regressao do acervo relacional append-only; so SQLite local e HTTP simulado."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_store as store  # noqa: E402

import datajud as dj  # noqa: E402

NUMERO = "70095117120248220001"
REQUISICAO = {"query": {"terms": {"numeroProcesso": [NUMERO]}}}


def mov(codigo, data, nome="ato", **extra):
    return {"codigo": codigo, "nome": nome, "dataHora": data,
            "orgaoJulgador": {"codigo": "101", "nome": "1a Vara"}, **extra}


ANTIGOS = [mov(26, "2024-01-10T10:00:00Z", "Distribuicao"),
           mov(51, "2024-01-11T10:00:00Z", "Conclusao")]
TRANSITO = mov(848, "2026-10-18T09:00:00Z", "Transito em julgado",
               complementosTabelados=[{"codigo": 5, "valor": 1, "nome": "x", "descricao": "tipo"}])


def hit(movimentos=None, *, score=1.0, timestamp="2026-10-01T00:00:00Z", classe=7):
    return {
        "_index": "api_publica_tjro",
        "_id": "TJRO_G1_" + NUMERO,
        "_score": score,
        "_source": {
            "numeroProcesso": NUMERO,
            "grau": "G1",
            "tribunal": "TJRO",
            "id": "TJRO_G1_" + NUMERO,
            "@timestamp": timestamp,
            "dataHoraUltimaAtualizacao": timestamp,
            "classe": {"codigo": classe, "nome": "Procedimento Comum"},
            "sistema": {"codigo": 1, "nome": "PJe"},
            "formato": {"codigo": 1, "nome": "Eletronico"},
            "orgaoJulgador": {"codigo": 101, "nome": "1a Vara", "codigoMunicipioIBGE": 1100205},
            "nivelSigilo": 0,
            "dataAjuizamento": "20240110100000",
            "assuntos": [{"codigo": 10288, "nome": "Pensao"}],
            "movimentos": list(ANTIGOS if movimentos is None else movimentos),
        },
    }


def resposta(*hits):
    return {
        "took": 17,
        "_shards": {"total": 1, "successful": 1, "failed": 0},
        "hits": {"total": {"value": len(hits), "relation": "eq"}, "hits": list(hits)},
    }


def registrar(banco, *hits, requisicao=REQUISICAO):
    return store.registrar_resposta("tjro", requisicao, resposta(*hits), banco=banco)


def tabelas(banco):
    return store.estatisticas(banco=banco).tabelas


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


_V1 = (
    """CREATE TABLE consultas (id INTEGER PRIMARY KEY AUTOINCREMENT, observado_em TEXT NOT NULL,
        tribunal TEXT NOT NULL, requisicao_json TEXT NOT NULL, resultado TEXT NOT NULL,
        resposta_meta_json TEXT, erro TEXT)""",
    """CREATE TABLE versoes_documento (id INTEGER PRIMARY KEY AUTOINCREMENT, identidade TEXT NOT NULL,
        tribunal TEXT NOT NULL, numero_processo TEXT NOT NULL, grau TEXT, sha256 TEXT NOT NULL,
        conteudo_json TEXT NOT NULL, primeira_observacao TEXT NOT NULL, UNIQUE(identidade, sha256))""",
    """CREATE TABLE observacoes_documento (id INTEGER PRIMARY KEY AUTOINCREMENT,
        observado_em TEXT NOT NULL, consulta_id INTEGER NOT NULL, versao_id INTEGER NOT NULL,
        atributos_hit_json TEXT NOT NULL)""",
)


def _legado(banco, observacoes):
    """Monta o banco no formato da #125: documento inteiro por versao."""
    with closing(sqlite3.connect(banco)) as con, con:
        for sql in _V1:
            con.execute(sql)
        for i, (quando, documento) in enumerate(observacoes, 1):
            conteudo = store._json({k: documento[k] for k in ("_index", "_id", "_source")})
            con.execute(
                "INSERT INTO consultas (observado_em, tribunal, requisicao_json, resultado, "
                "resposta_meta_json) VALUES (?, 'tjro', ?, 'ok', '{}')",
                (quando, json.dumps(REQUISICAO)))
            con.execute(
                "INSERT OR IGNORE INTO versoes_documento (identidade, tribunal, numero_processo, "
                "grau, sha256, conteudo_json, primeira_observacao) "
                "VALUES (?, 'tjro', ?, 'G1', ?, ?, ?)",
                (store._identidade(documento, "tjro"), NUMERO, store._sha(conteudo), conteudo, quando))
            versao = con.execute("SELECT id FROM versoes_documento WHERE sha256 = ?",
                                 (store._sha(conteudo),)).fetchone()[0]
            con.execute(
                "INSERT INTO observacoes_documento (observado_em, consulta_id, versao_id, "
                "atributos_hit_json) VALUES (?, ?, ?, ?)",
                (quando, i, versao, json.dumps({"_score": documento["_score"]})))


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


_V2 = (
    "CREATE TABLE consultas (id INTEGER PRIMARY KEY, observado_em TEXT, tribunal TEXT, requisicao_json TEXT,"
    " resultado TEXT, resposta_meta_json TEXT, erro TEXT)",
    "CREATE TABLE registros (id INTEGER PRIMARY KEY, identidade TEXT, indice TEXT, doc_id TEXT, tribunal TEXT,"
    " numero_processo TEXT, grau TEXT, fonte_id TEXT, primeira_observacao TEXT)",
    "CREATE TABLE orgaos (id INTEGER PRIMARY KEY, hash64 INTEGER, codigo TEXT, nome TEXT, municipio_ibge INTEGER,"
    " extras_json TEXT)",
    "CREATE TABLE tipos_movimento (id INTEGER PRIMARY KEY, hash64 INTEGER, codigo INTEGER, nome TEXT)",
    "CREATE TABLE complementos (id INTEGER PRIMARY KEY, hash64 INTEGER, codigo INTEGER, valor INTEGER,"
    " nome TEXT, descricao TEXT, extras_json TEXT)",
    "CREATE TABLE capas (id INTEGER PRIMARY KEY, registro_id INTEGER, hash64 INTEGER, classe_codigo INTEGER,"
    " classe_nome TEXT, sistema_codigo INTEGER, sistema_nome TEXT, formato_codigo INTEGER, formato_nome TEXT,"
    " orgao_id INTEGER, nivel_sigilo INTEGER, data_ajuizamento TEXT, extras_json TEXT)",
    "CREATE TABLE assuntos (id INTEGER PRIMARY KEY, registro_id INTEGER, hash64 INTEGER, ocorrencia INTEGER,"
    " codigo INTEGER, nome TEXT, extras_json TEXT)",
    "CREATE TABLE movimentos (id INTEGER PRIMARY KEY, registro_id INTEGER, hash64 INTEGER, ocorrencia INTEGER,"
    " tipo_id INTEGER, data_hora TEXT, orgao_id INTEGER, extras_json TEXT)",
    "CREATE TABLE movimento_complementos (movimento_id INTEGER, ordem INTEGER, complemento_id INTEGER)",
    "CREATE TABLE observacoes (id INTEGER PRIMARY KEY, consulta_id INTEGER, registro_id INTEGER,"
    " observado_em TEXT, capa_id INTEGER, projecao_json TEXT, volateis_json TEXT, mudou INTEGER,"
    " observacao_v1_id INTEGER)",
    "CREATE TABLE presencas_movimento (movimento_id INTEGER, observacao_id INTEGER, evento TEXT)",
    "CREATE TABLE presencas_assunto (assunto_id INTEGER, observacao_id INTEGER, evento TEXT)",
    "CREATE TABLE fontes_brutas (id INTEGER PRIMARY KEY, observacao_id INTEGER, sha256 TEXT, conteudo_zlib BLOB)",
)


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


def test_search_realmente_registra_toda_resposta_sem_configuracao_extra(monkeypatch, tmp_path):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    recebidas = [resposta(hit(score=1.0)), resposta(hit(score=2.0))]

    class HTTPResposta:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(self.body).encode("utf-8")

    monkeypatch.setattr(dj.urllib.request, "urlopen",
                        lambda *_a, **_kw: HTTPResposta(recebidas.pop(0)))
    assert dj.search(REQUISICAO, tribunal="tjro")["hits"]
    assert dj.search(REQUISICAO, tribunal="tjro")["hits"]
    t = tabelas(banco)
    assert (t["consultas"], t["registros"], t["observacoes"], t["vistas"]) == (2, 1, 1, 1)


def test_search_registra_falha_sem_criar_falso_nao_encontrado(monkeypatch, tmp_path):
    banco = tmp_path / "erros.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))

    def erro(*_a, **_kw):
        raise HTTPError(
            "https://example.test", 503, "service unavailable", {}, io.BytesIO(b"gateway")
        )

    monkeypatch.setattr(dj.urllib.request, "urlopen", erro)
    with pytest.raises(RuntimeError, match="HTTP 503"):
        dj.search({"query": {"match_all": {}}}, tribunal="tjro", tentativas=1)

    t = tabelas(banco)
    assert t["consultas"] == 1 and t["observacoes"] == 0
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT resultado FROM consultas").fetchone()[0] == "erro"


def test_lote_padrao_nao_exporta_json_e_observa_outra_vez(monkeypatch, tmp_path):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    entrada = tmp_path / "processos.txt"
    entrada.write_text("7009511-71.2024.8.22.0001\n", encoding="utf-8")

    class HTTPResposta:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(resposta(hit())).encode()

    monkeypatch.setattr(dj.urllib.request, "urlopen",
                        lambda *_a, **_kw: HTTPResposta())
    assert dj.cmd_lote(entrada, None, 1, True, True) == 0
    assert dj.cmd_lote(entrada, None, 1, True, True) == 0
    t = tabelas(banco)
    assert (t["consultas"], t["registros"], t["observacoes"], t["vistas"], t["movimentos"]) == (
        2, 1, 1, 1, 2)
    assert not list(tmp_path.rglob("*.json"))


def test_cli_estado_historico_e_banco_emitem_os_modelos(monkeypatch, tmp_path, capsys):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    registrar(banco, hit())

    assert dj.app(result_action="return_value", tokens=["estado", NUMERO, "--json"]) == 0
    saida = store.EstadoProcesso.model_validate_json(capsys.readouterr().out)
    assert len(saida.registros[0].movimentos) == 2

    assert dj.app(result_action="return_value", tokens=["historico", NUMERO, "--json"]) == 0
    assert store.HistoricoProcesso.model_validate_json(capsys.readouterr().out).registros

    assert dj.app(result_action="return_value", tokens=["banco", "--json"]) == 0
    assert store.Estatisticas.model_validate_json(capsys.readouterr().out)["movimentos"] == 2

    assert dj.app(result_action="return_value", tokens=["estado", "0000000-00.2024.8.22.0001"]) == 1


def test_roteamento_df_e_justica_militar():
    assert dj.tribunal_do_cnj("0000001-00.2024.6.07.0001") == "tre-dft"
    assert "tre-dft" in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert "tre-df" not in dj.familia_do_cnj("0000001-00.2024.8.07.0001")
    assert dj.tribunal_do_cnj("0000001-00.2024.7.01.0001") == "stm"


def test_numero_sem_indice_nao_e_ausencia_confirmada(monkeypatch, tmp_path, capsys):
    """Número do STF: nenhum índice consultado, logo nada foi observado."""
    import datajud_mcp as mod

    monkeypatch.setenv("DATAJUD_SQLITE", str(tmp_path / "datajud.sqlite"))
    monkeypatch.setattr(dj, "search", lambda *a, **k: pytest.fail("não deveria consultar"))
    saida = mod.datajud_processo("0126778-57.2022.1.00.0000")
    assert saida.encontrado is False and saida.completo is False

    assert dj.cmd_processo("0126778-57.2022.1.00.0000", None, False, False) == 1
    assert "incompleta" in capsys.readouterr().err


def test_falha_de_indice_nao_vira_nenhum_encontrado(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATAJUD_SQLITE", str(tmp_path / "datajud.sqlite"))

    def search(body, tribunal="tjro", **_):
        if tribunal == "stj":
            raise RuntimeError("HTTP 504: NSX LB")
        return {"hits": {"total": {"value": 0}, "hits": []}}

    monkeypatch.setattr(dj, "search", search)
    assert dj.cmd_processo("7009511-71.2024.8.22.0001", None, False, False) == 1
    erro = capsys.readouterr().err
    assert "incompleta" in erro and "Nenhum processo" not in erro


def test_novidades_separa_linha_de_base_marco_e_rotina(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    base = store.novidades("2000-01-01", ruido=dj.RUIDO, banco=banco)
    (processo,) = base.processos
    assert processo.processo_novo and processo.registros[0].registro_novo
    assert processo.registros[0].movimentos_iniciais == 2 and processo.registros[0].movimentos == []

    with sqlite3.connect(banco) as con:
        depois_da_base = con.execute("SELECT MAX(observado_em) FROM observacoes").fetchone()[0]
    marco = mov(848, "2026-10-18T09:00:00Z", "Transito em julgado")
    rotina = mov(581, "2026-10-18T10:00:00Z", "Juntada")
    registrar(banco, hit([*ANTIGOS, marco, rotina]))
    stj = hit([mov(26, "2026-10-18T11:00:00Z", "Distribuicao")])
    stj["_index"], stj["_id"] = "api_publica_stj", "STJ_SUP_" + NUMERO
    stj["_source"]["grau"] = "SUP"
    store.registrar_resposta("stj", REQUISICAO, resposta(stj), banco=banco)

    agora = store.novidades(datetime.fromisoformat(depois_da_base) + timedelta(microseconds=1),
                            ruido=dj.RUIDO, banco=banco)
    (processo,) = agora.processos
    assert not processo.processo_novo
    tjro, stj_reg = sorted(processo.registros, key=lambda r: r.registro.tribunal, reverse=True)
    assert [(m.codigo, m.marco, m.evento) for m in tjro.movimentos] == [
        (848, True, "entrou"), (581, False, "entrou")]
    assert stj_reg.registro_novo and stj_reg.movimentos_iniciais == 1
    assert store.novidades("2000-01-01", numeros=["0000000-00.2024.8.22.0001"], banco=banco).processos == []


def test_cli_novidades_emite_o_modelo(monkeypatch, tmp_path, capsys):
    banco = tmp_path / "acervo.sqlite"
    monkeypatch.setenv("DATAJUD_SQLITE", str(banco))
    registrar(banco, hit())
    assert dj.app(result_action="return_value", tokens=["novidades", "2000-01-01", "--json"]) == 0
    saida = store.Novidades.model_validate_json(capsys.readouterr().out)
    assert saida.processos[0].processo_novo
    assert dj.app(result_action="return_value", tokens=["novidades", "2000-01-01"]) == 0
    assert "primeira observacao" in capsys.readouterr().out


def _v2_em_troca(banco):
    with closing(sqlite3.connect(banco)) as con, con:
        for sql in _V2:
            con.execute(sql)
        con.execute(f"PRAGMA user_version = {store.EM_TROCA}")


def test_escrita_durante_a_troca_espera_o_arquivo_novo(tmp_path, monkeypatch):
    """Antigo ja copiado e carimbado: quem chega nao grava nele, espera o novo."""
    import threading
    import time

    banco = tmp_path / "acervo.sqlite"
    _v2_em_troca(banco)
    novo = tmp_path / "novo.sqlite"
    store._abrir(novo, novo=True).close()

    def trocar():
        time.sleep(0.5)
        banco.replace(tmp_path / "backup.sqlite")
        novo.replace(banco)

    threading.Thread(target=trocar).start()
    registrar(banco, hit())
    assert tabelas(banco)["consultas"] == 1, "a escrita foi para o arquivo novo"
    with closing(sqlite3.connect(tmp_path / "backup.sqlite")) as con:
        assert con.execute("SELECT COUNT(*) FROM consultas").fetchone()[0] == 0, "nada no antigo"
    with pytest.raises(store._ArquivoTrocado):
        store._abrir(tmp_path / "backup.sqlite")


def test_troca_que_morreu_no_meio_e_refeita(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "ESPERA_TROCA", 0.3)
    banco = tmp_path / "acervo.sqlite"
    _v2_em_troca(banco)
    registrar(banco, hit())
    dados = store.estatisticas(banco=banco)
    assert dados.versao == store.VERSAO and dados["consultas"] == 1
    assert list(tmp_path.glob("acervo-antes-v3-*.sqlite")), "o antigo ficou como backup"


def test_dois_processos_convertendo_o_mesmo_banco(tmp_path):
    """So um converte; o outro espera e abre o novo. Nunca some o acervo."""
    import subprocess

    banco = tmp_path / "v1.sqlite"
    _legado(banco, [("2026-10-01T00:00:00.000000+00:00", hit())])
    scripts = Path(store.__file__).parent
    codigo = (f"import sys; sys.path.insert(0, {str(scripts)!r}); import datajud_store as s; "
              f"from pathlib import Path; print(s.migrar(banco=Path({str(banco)!r})).origem)")
    processos = [subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True)
                 for _ in range(2)]
    origens = sorted(p.communicate(timeout=120)[0].strip() for p in processos)
    assert all(p.returncode == 0 for p in processos)
    assert origens == ["legado", "nada"], "um converteu, o outro achou pronto"
    assert banco.exists() and store.estatisticas(banco=banco).versao == store.VERSAO
    assert len(list(tmp_path.glob("v1-antes-v3-*.sqlite"))) == 1
    assert not list(tmp_path.glob("*em-construcao*")), "nenhum temporario sobra"


def test_troca_que_falha_deixa_o_antigo_no_lugar(tmp_path, monkeypatch):
    """O caminho principal nunca fica vazio: falhou a troca, o antigo segue intacto."""
    banco = tmp_path / "v1.sqlite"
    _legado(banco, [("2026-10-01T00:00:00.000000+00:00", hit())])

    def recusa(*_a, **_k):
        raise PermissionError("aberto")

    monkeypatch.setattr(store.os, "replace", recusa)
    monkeypatch.setattr(store.relogio, "monotonic", iter(range(0, 10_000, 100)).__next__)
    with pytest.raises(RuntimeError, match="aberto noutro processo"):
        store.migrar(banco=banco)
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 0, "versao restaurada"
        assert con.execute("SELECT COUNT(*) FROM observacoes_documento").fetchone()[0] == 1
    assert sorted(x.name for x in tmp_path.iterdir() if x.suffix == ".sqlite") == ["v1.sqlite"]

    monkeypatch.undo()
    assert store.migrar(banco=banco).origem == "legado", "a proxima abertura converte"


def test_carimbo_acompanha_a_ordem_das_gravacoes(tmp_path):
    """Gravacoes concorrentes: id maior nunca tem horario anterior."""
    import threading

    banco = tmp_path / "a.sqlite"
    linhas = [threading.Thread(target=registrar, args=(banco, hit())) for _ in range(8)]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    with closing(sqlite3.connect(banco)) as con:
        horarios = [h for (h,) in con.execute("SELECT observado_em FROM consultas ORDER BY id")]
    assert len(horarios) == 8 and horarios == sorted(horarios)
