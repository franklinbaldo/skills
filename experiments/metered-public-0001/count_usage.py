#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
"""Derive and verify Experiment 0001 principal-skill metering invariants."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

EXP = Path(__file__).parent
USAGE = EXP / "usage"
POLICY = EXP / "policy.yaml"
SUMMARY = USAGE / "usage-summary.md"
INVOICE = EXP / "invoice-request.md"
GOVERNED_SKILL = "okf-agent-skills"


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise SystemExit(f"missing frontmatter: {path}")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return result
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    raise SystemExit(f"unterminated frontmatter: {path}")


def policy_values(path: Path) -> dict[str, str]:
    """Read the experiment's intentionally shallow policy without a YAML dependency."""
    result: dict[str, str] = {}
    section: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        key, sep, value = raw.strip().partition(":")
        if not sep:
            continue
        value = value.strip().strip('"')
        if indent == 0:
            section = key if not value else None
            if value:
                result[key] = value
        elif indent == 2 and section:
            result[f"{section}.{key}"] = value
    return result


def require(data: dict[str, str], key: str, expected: str, where: Path) -> None:
    actual = data.get(key)
    if actual != expected:
        raise SystemExit(f"{where}: {key}={actual!r}, expected {expected!r}")


def as_int(data: dict[str, str], key: str, where: Path) -> int:
    try:
        return int(data[key])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"{where}: invalid integer {key}={data.get(key)!r}") from exc


def main() -> None:
    policy = policy_values(POLICY)
    require(policy, "commercial_terms.pricing_model", "metered_public", POLICY)
    require(policy, "metering.metric", "invocation", POLICY)
    require(policy, "metering.scope", "principal_skill", POLICY)
    require(policy, "metering.counter", "cumulative", POLICY)
    require(policy, "metering.rounding", "ceiling", POLICY)
    require(policy, "metering.coverage", "paid_block_watermark", POLICY)

    license_id = policy["license_id"]
    free_allowance = as_int(policy, "metering.free_allowance", POLICY)
    billing_unit = as_int(policy, "metering.billing_unit", POLICY)
    digest = "sha256:" + hashlib.sha256(POLICY.read_bytes()).hexdigest()

    records: list[tuple[str, str, int]] = []
    invocation_ids: list[str] = []
    for path in sorted(USAGE.glob("usage-*.md")):
        if path == SUMMARY:
            continue
        data = frontmatter(path)
        require(data, "type", "UsageStatement", path)
        require(data, "status", "experiment_evidence", path)
        require(data, "skill", GOVERNED_SKILL, path)
        require(data, "metric", "invocation", path)
        require(data, "license_id", license_id, path)
        require(data, "policy_sha256", digest, path)

        # The economic event is derived from the factual productive-start field.
        # `counted` and per-record `usage_total` are assertions, never inputs.
        productive = data.get("productive_execution_started") == "true"
        derived = 1 if productive else 0
        require(data, "counted", "true" if derived else "false", path)
        require(data, "usage_total", str(derived), path)

        invocation_id = data.get("invocation_id", "")
        if derived and not invocation_id:
            raise SystemExit(f"{path}: counted productive attempt lacks invocation_id")
        if derived:
            invocation_ids.append(invocation_id)
        records.append((path.name, invocation_id, derived))

    if len(invocation_ids) != len(set(invocation_ids)):
        raise SystemExit(f"duplicate invocation_id: {invocation_ids}")

    usage_total = sum(derived for _, _, derived in records)

    summary = frontmatter(SUMMARY)
    require(summary, "type", "UsageStatement", SUMMARY)
    require(summary, "status", "experiment_summary", SUMMARY)
    require(summary, "skill", GOVERNED_SKILL, SUMMARY)
    require(summary, "metric", "invocation", SUMMARY)
    require(summary, "license_id", license_id, SUMMARY)
    require(summary, "policy_sha256", digest, SUMMARY)
    require(summary, "usage_total", str(usage_total), SUMMARY)
    require(summary, "free_allowance", str(free_allowance), SUMMARY)

    receipted_coverage = as_int(summary, "receipted_coverage_through", SUMMARY)
    covered = max(free_allowance, receipted_coverage)
    uncovered = max(0, usage_total - covered)
    blocks = math.ceil(uncovered / billing_unit)
    requested_coverage = covered + blocks * billing_unit
    require(summary, "covered_through", str(covered), SUMMARY)

    invoice = frontmatter(INVOICE)
    if uncovered:
        require(invoice, "type", "InvoiceRequest", INVOICE)
        require(invoice, "status", "simulated_experiment", INVOICE)
        require(invoice, "license_id", license_id, INVOICE)
        require(invoice, "policy_sha256", digest, INVOICE)
        require(invoice, "covered", str(covered), INVOICE)
        require(invoice, "uncovered", str(uncovered), INVOICE)
        require(invoice, "blocks", str(blocks), INVOICE)
        require(
            invoice,
            "requested_coverage_through",
            str(requested_coverage),
            INVOICE,
        )
    elif INVOICE.exists():
        raise SystemExit(f"{INVOICE}: InvoiceRequest exists with no uncovered usage")

    for name, invocation_id, derived in records:
        print(f"{name}\t{invocation_id or '-'}\t+{derived}")
    print(f"usage_total={usage_total}")
    print(f"policy_sha256={digest}")
    print(f"covered={covered}")
    print(f"uncovered={uncovered}")
    print(f"blocks={blocks}")
    print(f"requested_coverage_through={requested_coverage}")
    print("summary_verified=true")
    print("invoice_request_verified=true")


if __name__ == "__main__":
    main()
