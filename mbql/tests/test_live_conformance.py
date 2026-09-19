#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cyclopts>=3.0",
#   "httpx>=0.28",
#   "pytest>=8.4",
#   "sqlglot>=27,<29",
# ]
# ///
"""Contract tests for the live Metabase conformance oracle."""
# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from live_conformance import (
    LiveConformanceError,
    compare_results,
    construct,
    ensure_driver_features,
    execute_mbql,
    execute_sql,
    fetch_database_features,
    required_driver_features,
)


def test_required_driver_features_are_derived_from_sql_shape() -> None:
    assert required_driver_features(
        "SELECT lower(o.status) FROM orders o "
        "LEFT JOIN customers c ON o.customer_id = c.id"
    ) == {"expressions", "left-join"}

    assert required_driver_features(
        "SELECT status, sum(total) FROM orders GROUP BY status HAVING sum(total) > 10"
    ) == {"basic-aggregations", "nested-queries"}

    assert required_driver_features(
        "WITH x AS (SELECT id FROM orders) SELECT id FROM x"
    ) == {"nested-queries"}

    assert required_driver_features(
        "SELECT median(total) FROM orders"
    ) == {"percentile-aggregations"}
    assert required_driver_features(
        "SELECT stddev(total) FROM orders"
    ) == {"standard-deviation-aggregations"}


def test_database_features_are_read_and_missing_capabilities_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/database/7"
        return httpx.Response(
            200,
            json={"id": 7, "engine": "mongo", "features": ["inner-join", "left-join", "expressions"]},
        )

    client = httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(handler))
    try:
        features = fetch_database_features(client, 7)
    finally:
        client.close()

    assert features == {"inner-join", "left-join", "expressions"}
    ensure_driver_features({"left-join", "expressions"}, features)
    with pytest.raises(LiveConformanceError, match="right-join"):
        ensure_driver_features({"right-join"}, features)


def test_construct_posts_portable_query_to_agent_api() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"query": "opaque-query"})

    client = httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(handler))
    try:
        opaque = construct(client, {"lib/type": "mbql/query", "stages": []})
    finally:
        client.close()

    assert opaque == "opaque-query"
    assert seen["path"] == "/api/agent/v2/construct-query"
    assert '"lib/type":"mbql/query"' in seen["body"].replace(" ", "")


def test_execute_endpoints_use_documented_agent_api_paths() -> None:
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(202, json={"status": "completed", "data": {"rows": [[1]]}, "row_count": 1})

    client = httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(handler))
    try:
        execute_mbql(client, "opaque-query")
        execute_sql(client, database_id=7, sql="SELECT 1")
    finally:
        client.close()

    assert paths == ["/api/agent/v1/execute", "/api/agent/v1/execute-sql"]


def test_semantic_comparison_accepts_identical_ordered_rows() -> None:
    compare_results(
        {"data": {"rows": [["paid", 2], ["open", 1]]}},
        {"data": {"rows": [["paid", 2], ["open", 1]]}},
        ordered=True,
    )


def test_unordered_comparison_accepts_reordering_but_preserves_multiplicity() -> None:
    compare_results(
        {"data": {"rows": [["paid", 2], ["open", 1], ["paid", 2]]}},
        {"data": {"rows": [["paid", 2], ["paid", 2], ["open", 1]]}},
        ordered=False,
    )

    with pytest.raises(LiveConformanceError, match="semantic mismatch"):
        compare_results(
            {"data": {"rows": [["paid", 2], ["paid", 2], ["open", 1]]}},
            {"data": {"rows": [["paid", 2], ["open", 1]]}},
            ordered=False,
        )


def test_ordered_comparison_rejects_reordering() -> None:
    with pytest.raises(LiveConformanceError, match="semantic mismatch"):
        compare_results(
            {"data": {"rows": [["paid", 2], ["open", 1]]}},
            {"data": {"rows": [["open", 1], ["paid", 2]]}},
            ordered=True,
        )


def test_semantic_comparison_rejects_value_mismatch() -> None:
    with pytest.raises(LiveConformanceError, match="semantic mismatch"):
        compare_results(
            {"data": {"rows": [["paid", 2]]}},
            {"data": {"rows": [["paid", 3]]}},
            ordered=True,
        )


def test_streaming_failure_body_is_not_mistaken_for_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"status": "failed", "error": "boom"})

    client = httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(LiveConformanceError, match="boom"):
            execute_mbql(client, "opaque-query")
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
