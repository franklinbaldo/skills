# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0"]
# ///
"""Testes offline: a descoberta nunca inventa rotas ou atravessa outra origem."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "openapi_discovery.py"
spec = importlib.util.spec_from_file_location("openapi_discovery", MODULE)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def test_references_from_html_are_explicit_and_same_origin():
    base = "https://example.org/swagger-ui.html"
    html = """<script>const ui = SwaggerUIBundle({url: '/v3/api-docs'});</script>
    <script src="/swagger-ui/swagger-ui-bundle.js"></script>
    <script>const x = { configUrl: 'https://evil.org/api-docs' };</script>"""
    assert discovery.candidates(html, base) == [
        "https://example.org/v3/api-docs",
        "https://example.org/swagger-ui/swagger-ui-bundle.js",
    ]


def test_no_guessed_paths():
    assert discovery.candidates("<html>Sem configuração</html>", "https://example.org/swagger-ui.html") == []


def test_insecure_or_cross_origin_rejected():
    base = "https://example.org/swagger-ui.html"
    assert not discovery.same_origin(base, "http://example.org/v3/api-docs")
    assert not discovery.same_origin(base, "https://elsewhere.org/v3/api-docs")


def test_403_recorded_without_followup():
    with patch.object(discovery, "fetch", return_value=(403, b"", "")) as get:
        result = discovery.inspect("teste", "https://example.org/swagger-ui.html")
    get.assert_called_once()
    assert result["outcome"] == "blocked"
    assert result["http_status"] == 403
    assert "explicit_references" not in result


def test_openapi_document_summary():
    data = b'{"openapi":"3.0.3","paths":{"/items":{},"/users":{}}}'
    with patch.object(discovery, "fetch", return_value=(200, data, "application/json")):
        result = discovery.inspect("teste", "https://example.org/openapi.json")
    assert result["outcome"] == "openapi"
    assert result["paths_count"] == 2
    assert result["version"] == "3.0.3"
