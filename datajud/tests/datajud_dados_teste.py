# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Dados e ajudantes comuns aos testes do acervo SQLite (respostas simuladas da API)."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_store as store  # noqa: E402

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
