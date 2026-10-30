# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Acesso HTTP à API Pública do DataJud: endpoint, chave pública, retry e `search`."""

from __future__ import annotations

import datetime
import email.utils
import json
import sqlite3
import time
import urllib.error
import urllib.request

import datajud_store as store

BASE = "https://api-publica.datajud.cnj.jus.br"
# Chave PUBLICA do CNJ — a mesma para todo mundo, documentada na wiki do DataJud.
# Se der 401, pegue a atualizada em https://datajud-wiki.cnj.jus.br/api-publica/acesso/
APIKEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
UA = "Mozilla/5.0 (datajud skill)"

DEFAULT_TRIBUNAL = "tjro"

# Campos de capa que queremos ver (evita puxar o array gigante de movimentos
# quando nao precisamos dele).


def _endpoint(tribunal):
    return f"{BASE}/api_publica_{tribunal.lower()}/_search"


def _is_es_rejection(d):
    if not isinstance(d, dict) or "error" not in d:
        return False
    erro = d.get("error")
    rc = erro.get("root_cause", []) if isinstance(erro, dict) else []
    return any("rejected_execution" in (c.get("type", "")) for c in rc)


def _guardar(tribunal, body, resposta=None, *, erro=None):
    """Toda resposta e toda falha de rede viram eventos duraveis no SQLite."""
    try:
        if resposta is None:
            store.registrar_erro(tribunal, body, erro or "erro sem descricao")
        else:
            store.registrar_resposta(
                tribunal, body, resposta, resultado="erro" if erro else "ok",
                erro=erro,
            )
    except (OSError, sqlite3.Error, ValueError, TypeError) as e:
        raise RuntimeError(f"falha ao persistir a observacao no SQLite: {e}") from e


class FalhaHTTPTransitoria(RuntimeError):
    """Falha HTTP temporaria apos esgotar as tentativas."""

    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo


def _espera_retry_after(cabecalhos, espera):
    """Respeita a janela informada pelo CNJ, limitada a 120 segundos."""
    valor = cabecalhos.get("Retry-After") if cabecalhos else None
    if valor:
        try:
            segundos = float(valor)
        except (ValueError, TypeError):
            try:
                data = email.utils.parsedate_to_datetime(valor)
                if data.tzinfo is None:
                    data = data.replace(tzinfo=datetime.timezone.utc)
                segundos = (data - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                segundos = espera
        return min(120, max(espera, segundos))
    return espera


def search(body, tribunal=DEFAULT_TRIBUNAL, timeout=90, tentativas=5):
    url = _endpoint(tribunal)
    data = json.dumps(body).encode("utf-8")
    espera = 2.0
    ultimo_erro = None
    for n in range(1, tentativas + 1):
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json",
                     "Authorization": f"APIKey {APIKEY}",
                     "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resposta_bytes = r.read()
            try:
                d = json.loads(resposta_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                ultimo_erro = f"resposta HTTP sem JSON valido: {e}"
                _guardar(tribunal, body, erro=ultimo_erro)
                if n < tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
                raise RuntimeError(ultimo_erro) from e

            if not isinstance(d, dict):
                _guardar(tribunal, body, erro="resposta nao e objeto JSON")
                raise RuntimeError("resposta DataJud sem formato JSON esperado")
            if "error" in d:
                ultimo_erro = f"DataJud: {str(d['error'])[:300]}"
                _guardar(tribunal, body, d, erro=ultimo_erro)
                if _is_es_rejection(d) and n < tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, 30)
                    continue
                raise RuntimeError(ultimo_erro)
            if not isinstance(d.get("hits"), dict):
                _guardar(tribunal, body, d, erro="resposta sem hits")
                raise RuntimeError("resposta DataJud sem hits: nao interpretar como ausencia")

            _guardar(tribunal, body, d)
            return d
        except urllib.error.HTTPError as e:
            corpo = ""
            try:
                corpo = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            ultimo_erro = f"HTTP {e.code}: {corpo}"
            _guardar(tribunal, body, erro=ultimo_erro)
            if e.code in (429, 500, 502, 503, 504) and n < tentativas:
                time.sleep(_espera_retry_after(e.headers, espera))
                espera = min(espera * 2, 30)
                continue
            if e.code == 401:
                raise RuntimeError(
                    "HTTP 401: a chave publica provavelmente foi trocada pelo CNJ. "
                    "Pegue a atual em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ "
                    "e atualize APIKEY no topo deste script.") from e
            if e.code in (429, 500, 502, 503, 504):
                raise FalhaHTTPTransitoria(e.code, ultimo_erro) from e
            raise RuntimeError(ultimo_erro) from e
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo_erro = f"rede: {e}"
            _guardar(tribunal, body, erro=ultimo_erro)
            if n < tentativas:
                time.sleep(espera)
                espera = min(espera * 2, 30)
                continue
            raise RuntimeError(ultimo_erro) from e
    raise RuntimeError(ultimo_erro or "falha desconhecida")


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
