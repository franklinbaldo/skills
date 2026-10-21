#!/usr/bin/env python3
"""Inventario verificavel dos aliases PUBLICOS DataJud/CNJ.

Nunca confundir API Publica com os endpoints de envio/manutencao reservados
a tribunais. O catalogo e offline; --probe faz consultas autenticadas reais,
com taxa limitada e persistencia a cargo do chamador.
"""
import argparse
import json
import os
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


def probe(alias: str, api_key: str, timeout: float = 20) -> dict:
    """Teste minimo, sem download de autos e sem assumir que erro seja ausencia."""
    body = json.dumps({"size": 0, "track_total_hits": False, "query": {"match_all": {}}}).encode()
    req = urllib.request.Request(
        endpoint(alias), data=body, method="POST",
        headers={"Authorization": f"APIKey {api_key}",
                 "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read())
            status = response.status
        if not isinstance(payload, dict) or "error" in payload or "hits" not in payload:
            return {"alias": alias, "status": status, "ok": False,
                    "erro": str(payload.get("error", "sem hits") if isinstance(payload, dict) else "formato invalido")[:200]}
        return {"alias": alias, "status": status, "ok": True}
    except urllib.error.HTTPError as exc:
        return {"alias": alias, "status": exc.code, "ok": False, "erro": str(exc.reason)}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"alias": alias, "status": None, "ok": False, "erro": str(exc)[:200]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="testa efetivamente a API (faz rede)")
    parser.add_argument("--alias", choices=sorted(ALIASES), help="testa somente um tribunal")
    parser.add_argument("--delay", type=float, default=1.0, help="intervalo minimo entre testes (segundos)")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    if args.delay < 0 or args.timeout <= 0:
        parser.error("delay deve ser >= 0 e timeout > 0")
    aliases = [args.alias] if args.alias else sorted(ALIASES)
    if not args.probe:
        print(json.dumps({"total": len(ALIASES), "grupos": {k: list(v) for k, v in GRUPOS.items()},
                          "endpoints": [endpoint(a) for a in aliases]}, ensure_ascii=False, indent=2))
        return 0
    key = os.environ.get("DATAJUD_API_KEY")
    if not key:
        parser.error("--probe exige DATAJUD_API_KEY no ambiente; consulte a chave publica atual no CNJ")
    falhas = 0
    for i, alias in enumerate(aliases):
        if i:
            time.sleep(args.delay)
        result = probe(alias, key, args.timeout)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        falhas += not result["ok"]
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
