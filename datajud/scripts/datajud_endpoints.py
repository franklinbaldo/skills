#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3.0"]
# ///
"""Inventario verificavel dos aliases PUBLICOS DataJud/CNJ.

Nunca confundir API Publica com os endpoints de envio/manutencao reservados
a tribunais. O catalogo e offline; --probe faz consultas autenticadas reais,
com taxa limitada e persistencia a cargo do chamador.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = "https://api-publica.datajud.cnj.jus.br"
UFS = ("ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma",
       "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
       "rs", "ro", "rr", "sc", "se", "sp", "to")
ESTADUAL = tuple("tjdft" if uf == "df" else "tj" + uf for uf in UFS)
ELEITORAL = tuple("tre-dft" if uf == "df" else "tre-" + uf for uf in UFS)
TRABALHO = tuple("trt" + str(i) for i in range(1, 25))
FEDERAL = tuple("trf" + str(i) for i in range(1, 7))
SUPERIORES = ("stj", "tst", "tse", "stm")
MILITAR_ESTADUAL = ("tjmmg", "tjmrs", "tjmsp")
GRUPOS = {
    "estadual": ESTADUAL,
    "eleitoral": ELEITORAL,
    "trabalho": TRABALHO,
    "federal": FEDERAL,
    "superiores": SUPERIORES,
    "militar_estadual": MILITAR_ESTADUAL,
}
ALIASES = frozenset(x for grupo in GRUPOS.values() for x in grupo)


def endpoint(alias: str) -> str:
    """Rejeita alias inexistente antes de produzir URL de rede."""
    if alias not in ALIASES:
        raise ValueError(f"Alias publico nao catalogado: {alias!r}")
    return f"{BASE}/api_publica_{alias}/_search"


FEATURE_QUERIES = {
    "match_all": {"size": 0, "query": {"match_all": {}}},
    "term": {"size": 0, "query": {"term": {"grau.keyword": "G1"}}},
    "bool": {"size": 0, "query": {"bool": {"filter": [{"exists": {"field": "numeroProcesso"}}]}}},
    "range": {"size": 0, "query": {"range": {"dataAjuizamento": {"gte": "20200101000000"}}}},
    "aggs": {"size": 0, "aggs": {"graus": {"terms": {"field": "grau.keyword", "size": 2}}}},
    "source": {"size": 1, "_source": ["numeroProcesso"]},
    "sort": {"size": 1, "sort": [{"@timestamp": {"order": "asc"}}]},
}
# Resultados dos probes nao demonstram suporte universal a qualquer DSL.
# Um HTTP 200 pode ocultar erros internos: checar hits e shard failures.


def _request(alias: str, api_key: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        endpoint(alias), data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"APIKey {api_key}",
                 "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            status = response.status
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            return {"status": status, "ok": False, "erro": "resposta nao JSON", "categoria": "formato"}
        if not isinstance(payload, dict) or "error" in payload or "hits" not in payload:
            err = payload.get("error", "sem hits") if isinstance(payload, dict) else "formato invalido"
            return {"status": status, "ok": False, "erro": str(err)[:200], "categoria": "api"}
        failed = (payload.get("_shards") or {}).get("failed", 0)
        if failed:
            return {"status": status, "ok": False, "erro": f"{failed} shards falharam", "categoria": "parcial"}
        return {"status": status, "ok": True}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "ok": False, "erro": str(exc.reason), "categoria": "http"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": None, "ok": False, "erro": str(exc)[:200], "categoria": "rede"}


def probe(alias: str, api_key: str, timeout: float = 20, *, feature: str = "match_all") -> dict:
    """Consulta isolada por recurso; resultado indica observacao, nao garantia."""
    if feature not in FEATURE_QUERIES:
        raise ValueError(f"recurso desconhecido: {feature}")
    result = _request(alias, api_key, FEATURE_QUERIES[feature], timeout)
    return {"alias": alias, "feature": feature, **result}


def _observation_key(alias: str, feature: str) -> str:
    # Nao incluir segredo; hash do corpo permite invalidar probes alterados.
    body = json.dumps(FEATURE_QUERIES[feature], sort_keys=True)
    return hashlib.sha256(f"{alias}:{feature}:{body}".encode()).hexdigest()


def _append_event(path: Path, event: dict) -> None:
    """Journal append-only, um resultado por linha, fsync para retomada segura."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        out.flush()
        os.fsync(out.fileno())


def _sucessos(path: Path) -> set[str]:
    """Retomada somente de testes comprovadamente bem sucedidos."""
    if not path.exists():
        return set()
    ok = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
            if event.get("ok") is True and isinstance(event.get("key"), str):
                ok.add(event["key"])
        except (ValueError, TypeError):
            continue  # linha interrompida, nunca considerar como sucesso
    return ok


app = cyclopts.App(name="datajud-endpoints", help="Inventario e probes publicos do DataJud.")


def executar(
    *,
    probe: bool = False,
    alias: str | None = None,
    features: bool = False,
    journal: Path | None = None,
    resume: bool = False,
    delay: float = 1.0,
    timeout: float = 20.0,
) -> int:
    if delay < 0 or timeout <= 0:
        raise ValueError("delay deve ser >= 0 e timeout > 0")
    if alias is not None:
        endpoint(alias)
    if resume and journal is None:
        raise ValueError("--resume exige --journal")
    if features and not probe:
        raise ValueError("--features exige --probe")
    aliases = [alias] if alias else sorted(ALIASES)
    if not probe:
        print(json.dumps({"total": len(ALIASES), "grupos": {k: list(v) for k, v in GRUPOS.items()},
                          "endpoints": [endpoint(a) for a in aliases]}, ensure_ascii=False, indent=2))
        return 0
    key = os.environ.get("DATAJUD_API_KEY")
    if not key:
        raise ValueError("--probe exige DATAJUD_API_KEY no ambiente")
    resources = list(FEATURE_QUERIES) if features else ["match_all"]
    completed = _sucessos(journal) if resume and journal else set()
    failures = 0
    attempted = 0
    for target in aliases:
        for feature in resources:
            check = _observation_key(target, feature)
            if check in completed:
                continue
            if attempted:
                time.sleep(delay)
            result = globals()["probe"](target, key, timeout, feature=feature)
            event = {
                "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "key": check, **result,
            }
            if journal:
                _append_event(journal, event)
            print(json.dumps(event, ensure_ascii=False), flush=True)
            attempted += 1
            failures += not result["ok"]
    return 1 if failures else 0


@app.default
def cli(
    *,
    probe: bool = False,
    alias: str | None = None,
    features: bool = False,
    journal: Path | None = None,
    resume: bool = False,
    delay: float = 1.0,
    timeout: float = 20.0,
) -> int:
    """Lista aliases offline ou verifica disponibilidade e recursos com --probe."""
    return executar(probe=probe, alias=alias, features=features, journal=journal,
                    resume=resume, delay=delay, timeout=timeout)


if __name__ == "__main__":
    app()
