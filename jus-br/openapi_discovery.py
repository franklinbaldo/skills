#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Descobre contratos OpenAPI públicos a partir de Swagger UI, sem autenticação.

Não tenta contornar 401/403; apenas URLs informadas explicitamente e referências
encontradas no HTML/configuração do Swagger. Não imprime respostas arbitrárias.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

SOURCES = {
    "portal-externo": "https://portalexterno-tribunais.stg.pdpj.jus.br/swagger-ui.html",
    "cabecalho-processual": "https://gateway.stg.cloud.pje.jus.br/cabecalho-processual/swagger-ui.html",
    "repositorio": "https://gateway.stg.cloud.pje.jus.br/repositorio/swagger-ui.html",
}
MAX_BYTES = 4_000_000


def same_origin(base: str, candidate: str) -> bool:
    a, b = urlparse(base), urlparse(candidate)
    return b.scheme == "https" and (a.hostname, a.port) == (b.hostname, b.port)


def candidates(html: str, base: str) -> list[str]:
    """Extrai somente referências explícitas no HTML, nunca adivinha api-docs."""
    found = []
    patterns = [
        r'(?:configUrl|url)\s*:\s*["\']([^"\']+)["\']',
        r'(?:src|href)=["\']([^"\']*swagger[^"\']*\.js[^"\']*)["\']',
    ]
    for pattern in patterns:
        for rel in re.findall(pattern, html):
            url = urljoin(base, rel)
            if same_origin(base, url) and url not in found:
                found.append(url)
    return found


def fetch(url: str) -> tuple[int, bytes, str]:
    try:
        with urlopen(Request(url, headers={"User-Agent": "jus-br-openapi-discovery/1.0"}), timeout=12) as resp:
            body = resp.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Resposta maior que o limite configurado")
            return resp.status, body, resp.headers.get("Content-Type", "")
    except HTTPError as exc:
        return exc.code, b"", ""


def inspect(name: str, url: str) -> dict:
    """Um resultado de inventário sem incluir conteúdo protegido ou dados pessoais."""
    record = {"service": name, "swagger_ui": url, "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        status, body, ctype = fetch(url)
        record["http_status"] = status
        if status != 200:
            record["outcome"] = "blocked" if status in (401, 403) else "unavailable"
            return record
        record["sha256"] = hashlib.sha256(body).hexdigest()
        if "json" in ctype.lower():
            data = json.loads(body)
            if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                record.update(outcome="openapi", version=data.get("openapi", data.get("swagger")),
                              paths_count=len(data.get("paths", {})))
                return record
        record.update(outcome="swagger_ui", explicit_references=candidates(body.decode("utf-8", "replace"), url))
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        record.update(outcome="error", error=type(exc).__name__)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", choices=sorted(SOURCES), action="append")
    args = parser.parse_args()
    selection = args.service or list(SOURCES)
    print(json.dumps([inspect(name, SOURCES[name]) for name in selection], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
