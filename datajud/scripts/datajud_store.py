# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Armazenamento imutavel das observacoes da API publica DataJud (SQLite).

Cada resposta HTTP produz um evento de consulta; cada hit aponta para uma versao
identificada por SHA-256 e uma observacao propria. Nova consulta ao mesmo
conteudo cria apenas observacao, sem sobrescrever nem duplicar a versao.

Nao armazena cabecalhos HTTP ou credenciais. Guarda os metadados completos da
resposta e todos os campos de cada hit (separando _score, que pertence a
observacao e nao ao conteudo do documento).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()

_TABELAS = ("consultas", "versoes_documento", "observacoes_documento")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observado_em TEXT NOT NULL,
    tribunal TEXT NOT NULL,
    requisicao_json TEXT NOT NULL,
    resultado TEXT NOT NULL CHECK(resultado IN ('ok', 'erro')),
    resposta_meta_json TEXT,
    erro TEXT
);

CREATE TABLE IF NOT EXISTS versoes_documento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identidade TEXT NOT NULL,
    tribunal TEXT NOT NULL,
    numero_processo TEXT NOT NULL,
    grau TEXT,
    sha256 TEXT NOT NULL,
    conteudo_json TEXT NOT NULL,
    primeira_observacao TEXT NOT NULL,
    UNIQUE(identidade, sha256)
);

CREATE TABLE IF NOT EXISTS observacoes_documento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observado_em TEXT NOT NULL,
    consulta_id INTEGER NOT NULL REFERENCES consultas(id),
    versao_id INTEGER NOT NULL REFERENCES versoes_documento(id),
    atributos_hit_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_consultas_tribunal_data
    ON consultas(tribunal, observado_em);
CREATE INDEX IF NOT EXISTS idx_versoes_numero
    ON versoes_documento(numero_processo, identidade);
CREATE INDEX IF NOT EXISTS idx_observacoes_versao_data
    ON observacoes_documento(versao_id, observado_em);
CREATE INDEX IF NOT EXISTS idx_observacoes_consulta
    ON observacoes_documento(consulta_id);
"""


def caminho_banco() -> Path:
    """O banco padrao fica na area persistente do usuario, fora do Git."""
    configurado = os.environ.get("DATAJUD_SQLITE")
    if configurado:
        return Path(configurado).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "datajud" / "acervo.sqlite"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _conexao(banco: Path | None = None) -> sqlite3.Connection:
    caminho = banco or caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, timeout=30)
    try:
        con.execute("PRAGMA busy_timeout = 30000")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(_SCHEMA)
        for tabela in _TABELAS:
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS {tabela}_sem_update "
                f"BEFORE UPDATE ON {tabela} BEGIN "
                "SELECT RAISE(ABORT, 'DataJud append-only: UPDATE proibido'); END"
            )
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS {tabela}_sem_delete "
                f"BEFORE DELETE ON {tabela} BEGIN "
                "SELECT RAISE(ABORT, 'DataJud append-only: DELETE proibido'); END"
            )
        con.commit()
        con.row_factory = sqlite3.Row
        return con
    except BaseException:
        con.close()
        raise


def _identidade(hit: dict[str, Any], tribunal: str) -> str:
    """Identidade logica estavel do documento, independente do seu conteudo."""
    indice = str(hit.get("_index") or f"api_publica_{tribunal}")
    doc_id = hit.get("_id")
    if doc_id is not None:
        return f"{indice}:id:{doc_id}"
    fonte = hit.get("_source") or {}
    orgao = fonte.get("orgaoJulgador") or {}
    return _json(
        [
            indice,
            fonte.get("numeroProcesso") or "",
            fonte.get("grau") or "",
            orgao.get("codigo") or orgao.get("nome") or "",
        ]
    )


def _projecao(requisicao: dict[str, Any]) -> str | None:
    """Assinatura do recorte de campos pedido (`_source`), ou None se veio o documento inteiro.

    `buscar` pede so a capa; gravar esse recorte como versao do documento faria
    a mesma fonte parecer ter mudado ao ser consultada depois por `processo`.
    """
    recorte = requisicao.get("_source") if isinstance(requisicao, dict) else None
    if recorte is None or recorte is True:
        return None
    return _sha(_json(recorte))[:16]


def _envelope(resposta: dict[str, Any]) -> dict[str, Any]:
    """Tudo da resposta exceto hits.hits, guardados com deduplicacao por documento."""
    envelope = dict(resposta)
    hits = envelope.get("hits")
    if isinstance(hits, dict):
        envelope["hits"] = {k: v for k, v in hits.items() if k != "hits"}
    return envelope


def registrar_resposta(
    tribunal: str,
    requisicao: dict[str, Any],
    resposta: dict[str, Any],
    *,
    resultado: str = "ok",
    erro: str | None = None,
    banco: Path | None = None,
) -> int:
    """Acrescenta uma consulta e uma observacao por hit, de forma atomica.

    Se o conteudo for identico ao de uma versao anterior, apenas a observacao
    e inserida; se mudou, a nova versao convive com as anteriores. Nao faz
    atualizacoes nem delecoes. Devolve o ID do evento de consulta.
    """
    if resultado not in ("ok", "erro"):
        raise ValueError("resultado deve ser ok ou erro")
    if not isinstance(resposta, dict):
        raise TypeError("resposta DataJud deve ser um objeto JSON")
    hits_container = resposta.get("hits") or {}
    if not isinstance(hits_container, dict):
        raise ValueError("hits deve ser um objeto JSON")
    hits = hits_container.get("hits") or []
    if not isinstance(hits, list):
        raise ValueError("hits.hits deve ser uma lista")
    observado_em = _agora()
    projecao = _projecao(requisicao)
    with _LOCK:
        con = _conexao(banco)
        try:
            with con:
                cursor = con.execute(
                    "INSERT INTO consultas "
                    "(observado_em, tribunal, requisicao_json, resultado, resposta_meta_json, erro) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (observado_em, tribunal, _json(requisicao), resultado, _json(_envelope(resposta)), erro),
                )
                consulta_id = cursor.lastrowid
                for hit in hits:
                    if not isinstance(hit, dict):
                        raise ValueError("hit nao e um objeto")
                    fonte = hit.get("_source")
                    if not isinstance(fonte, dict):
                        raise ValueError("hit nao contem _source valido")
                    indice = str(hit.get("_index") or f"api_publica_{tribunal}")
                    conteudo = _json(
                        {"_index": indice, "_id": hit.get("_id"), "_source": fonte}
                    )
                    identidade = _identidade(hit, tribunal)
                    if projecao:
                        # Recorte tem linhagem propria: nunca vira versao do documento completo.
                        identidade = f"{identidade}|projecao:{projecao}"
                    digest = _sha(conteudo)
                    con.execute(
                        "INSERT OR IGNORE INTO versoes_documento "
                        "(identidade, tribunal, numero_processo, grau, sha256, "
                        "conteudo_json, primeira_observacao) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            identidade, indice.removeprefix("api_publica_"),
                            str(fonte.get("numeroProcesso") or ""),
                            fonte.get("grau"), digest, conteudo, observado_em,
                        ),
                    )
                    linha = con.execute(
                        "SELECT id FROM versoes_documento WHERE identidade = ? AND sha256 = ?",
                        (identidade, digest),
                    ).fetchone()
                    atributos = {
                        k: v for k, v in hit.items()
                        if k not in ("_source", "_id", "_index")
                    }
                    con.execute(
                        "INSERT INTO observacoes_documento "
                        "(observado_em, consulta_id, versao_id, atributos_hit_json) "
                        "VALUES (?, ?, ?, ?)",
                        (observado_em, consulta_id, linha["id"], _json(atributos)),
                    )
            return consulta_id
        finally:
            con.close()


def registrar_erro(
    tribunal: str,
    requisicao: dict[str, Any],
    erro: str,
    *,
    banco: Path | None = None,
) -> int:
    """Registra tentativas falhas; nao cria observacoes falsas de documentos."""
    return registrar_resposta(
        tribunal, requisicao, {}, resultado="erro", erro=str(erro), banco=banco
    )


def historico(numero: str, *, limite: int = 100, banco: Path | None = None) -> list[dict]:
    """Versoes e frequencia de observacoes de um processo; apenas leitura."""
    digitos = "".join(c for c in numero if c.isdigit())
    with _LOCK:
        con = _conexao(banco)
        try:
            linhas = con.execute(
                """
                SELECT v.identidade, v.tribunal, v.grau, v.sha256,
                       v.primeira_observacao,
                       MIN(o.observado_em) AS primeira_vista,
                       MAX(o.observado_em) AS ultima_vista,
                       COUNT(o.id) AS observacoes,
                       v.conteudo_json
                FROM versoes_documento AS v
                JOIN observacoes_documento AS o ON o.versao_id = v.id
                WHERE v.numero_processo = ?
                GROUP BY v.id
                ORDER BY ultima_vista DESC, v.id DESC
                LIMIT ?
                """,
                (digitos, max(1, min(limite, 10000))),
            ).fetchall()
            return [dict(x) for x in linhas]
        finally:
            con.close()


def estatisticas(*, banco: Path | None = None) -> dict[str, int | str]:
    """Resumo para inspecao do acervo local; nao consulta o DataJud."""
    with _LOCK:
        con = _conexao(banco)
        try:
            tabelas = {
                "consultas": "consultas",
                "versoes": "versoes_documento",
                "observacoes": "observacoes_documento",
            }
            valores = {
                nome: con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                for nome, tabela in tabelas.items()
            }
            return {"banco": str(banco or caminho_banco()), **valores}
        finally:
            con.close()
