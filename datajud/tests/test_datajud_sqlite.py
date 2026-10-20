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
import zlib
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


def test_banco_da_versao_anterior_abre_e_continua(tmp_path):
    """`consultas` criada pela #125 tem as mesmas colunas do modelo."""
    banco = tmp_path / "v1.sqlite"
    with sqlite3.connect(banco) as con:
        con.execute("""CREATE TABLE consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, observado_em TEXT NOT NULL,
            tribunal TEXT NOT NULL, requisicao_json TEXT NOT NULL,
            resultado TEXT NOT NULL CHECK(resultado IN ('ok', 'erro')),
            resposta_meta_json TEXT, erro TEXT)""")
    registrar(banco, hit())
    assert tabelas(banco)["consultas"] == 1


def test_reindexacao_e_score_nao_mudam_nada(tmp_path):
    banco = tmp_path / "a.sqlite"
    primeira = registrar(banco, hit())
    segunda = registrar(banco, hit(score=8.5, timestamp="2026-10-19T03:00:00Z"))

    assert primeira.observacoes[0].primeira and primeira.observacoes[0].mudou
    assert not segunda.observacoes[0].mudou, "so campos volateis mudaram"
    t = tabelas(banco)
    assert t["observacoes"] == 2 and t["capas"] == 1 and t["movimentos"] == 2
    assert t["presencas_movimento"] == 2, "nenhuma presenca nova"
    assert t["fontes_brutas"] == 1, "o bruto so se guarda quando algo muda"
    with sqlite3.connect(banco) as con:
        volateis = [json.loads(v) for (v,) in con.execute(
            "SELECT volateis_json FROM observacoes ORDER BY id")]
    assert volateis[1]["_score"] == 8.5
    assert volateis[1]["@timestamp"] == "2026-10-19T03:00:00Z"


def test_andamento_novo_e_uma_linha_e_nao_uma_copia(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit())
    saida = registrar(banco, hit([*ANTIGOS, TRANSITO]))

    obs = saida.observacoes[0]
    assert (obs.movimentos_entraram, obs.movimentos_sairam, obs.capa_nova) == (1, 0, False)
    t = tabelas(banco)
    assert t["movimentos"] == 3, "so o andamento novo ganhou linha"
    assert t["presencas_movimento"] == 3
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
    so_capa = hit()
    del so_capa["_source"]["movimentos"]
    saida = registrar(banco, so_capa, requisicao={
        "query": {"match": {"numeroProcesso": NUMERO}}, "_source": dj.CAPA_FIELDS})

    obs = saida.observacoes[0]
    assert (obs.movimentos_sairam, obs.capa_nova, obs.mudou) == (0, False, False)
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 2
    with sqlite3.connect(banco) as con:
        projecao, capa = con.execute(
            "SELECT projecao_json, capa_id FROM observacoes ORDER BY id DESC LIMIT 1").fetchone()
    assert json.loads(projecao) == dj.CAPA_FIELDS and capa is not None

    minimo = hit()
    minimo["_source"] = {"numeroProcesso": NUMERO, "grau": "G1"}
    sem_capa = registrar(banco, minimo, requisicao={"_source": ["numeroProcesso", "grau"]})
    assert not sem_capa.observacoes[0].mudou, "capa fora do recorte nao vira capa nova"
    assert store.estado(NUMERO, banco=banco).registros[0].capa.capa.classe_codigo == 7


def test_fonte_bruta_reproduz_o_hit(tmp_path):
    banco = tmp_path / "a.sqlite"
    original = hit()
    registrar(banco, original)
    with sqlite3.connect(banco) as con:
        conteudo = con.execute("SELECT conteudo_zlib FROM fontes_brutas").fetchone()[0]
    assert json.loads(zlib.decompress(conteudo))["_source"] == original["_source"]


def test_todas_as_tabelas_sao_append_only(tmp_path):
    banco = tmp_path / "a.sqlite"
    registrar(banco, hit([*ANTIGOS, TRANSITO]))
    with sqlite3.connect(banco) as con:
        for modelo in store.TABELAS:
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


def _legado(banco, observacoes):
    """Monta o banco no formato da #125: documento inteiro por versao."""
    with sqlite3.connect(banco) as con:
        for modelo in (store.LinhaConsulta, *store.LEGADO):
            con.execute(store.ddl(modelo))
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
    assert (resultado.migradas, resultado.legado) == (3, 3)
    assert store.migrar(banco=banco).migradas == 0, "idempotente"

    t = tabelas(banco)
    assert t["observacoes"] == 3 and t["movimentos"] == 3
    assert t["versoes_documento"] == 3, "no legado, a reindexacao virava versao"
    assert store.estatisticas(banco=banco).observacoes_com_mudanca == 2, "aqui, nao"
    assert len(store.estado(NUMERO, em="2026-10-15", banco=banco).registros[0].movimentos) == 2
    assert len(store.estado(NUMERO, banco=banco).registros[0].movimentos) == 3
    assert store.estado(NUMERO, em="2026-09-30", banco=banco).registros == []

    # Escrita nova depois da migracao continua a linhagem, sem repetir o legado.
    registrar(banco, hit([*ANTIGOS, TRANSITO]))
    assert tabelas(banco)["movimentos"] == 3
    with sqlite3.connect(banco) as con, pytest.raises(sqlite3.IntegrityError, match="append-only"):
        con.execute("DELETE FROM versoes_documento")


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
    assert (t["consultas"], t["registros"], t["observacoes"]) == (2, 1, 2)


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
    assert (t["consultas"], t["registros"], t["observacoes"], t["movimentos"]) == (2, 1, 2, 2)
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
