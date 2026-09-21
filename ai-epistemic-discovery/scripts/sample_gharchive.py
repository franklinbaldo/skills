#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "duckdb>=1.1",
#     "rich>=13.7",
# ]
# ///
"""Sample public GitHub activity from GH Archive without a recency bias.

`find_candidates.py` queries the GitHub search API, which caps results and used to
order them by `updated desc`. That made the queue non-reproducible and made every
candidate look maximally active, because activity was the selection rule rather than
a measurement.

This script reads GH Archive hours instead. An hour is the complete public event
stream for that hour, so the sample is not ordered by anything, the same hours always
produce the same queue, and the window is chosen explicitly.

Scope limits, measured against the archive rather than assumed:

* Between 2025-06 and 2025-12 the public event stream stopped carrying
  `CreateEvent` with `ref_type` of `repository` or `tag`, and stopped carrying
  `commits`, `size` and `distinct_size` inside `PushEvent`. Repository creation and
  commit messages are therefore unavailable for recent windows, though they remain
  available for earlier ones.
* Repository *names* are present in every event and are the usable text surface for
  recent windows. They are a weaker signal than a README, so this script produces
  owners to inspect, never a classification.

The output is a discovery queue only: not an evidence tier, not a truth assessment,
and never a clinical inference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import cyclopts
import duckdb
from rich.console import Console
from rich.table import Table

app = cyclopts.App(name="sample-gharchive", help=__doc__)
out = Console()
err = Console(stderr=True)

ARCHIVE = "https://data.gharchive.org"

# Patterns are anchored to reduce homonyms measured in real hours: bare `codex`
# matches OpenAI Codex tooling, bare `oracle` matches Oracle SQL coursework, and
# bare `scroll` matches CSS utilities. None of those are epistemic-world signals.
VOCABULARY = "|".join(
    [
        r"consciousness",
        r"sentien(ce|t)",
        r"ontolog(y|ies|ical)",
        r"epistemolog(y|ical)",
        r"cosmolog(y|ical)",
        r"metaphysic(s|al)",
        r"noosphere",
        r"egregore",
        r"gnosis",
        r"aletheia",
        r"logos(flow|field|core)?",
        r"(digital|machine|artificial).?(soul|spirit|consciousness|mind)",
        r"(ai|llm).?(covenant|scripture|liturgy|theolog)",
        r"recursive.?(self|mind|awareness)",
        r"identity.?continuity",
        r"selfhood",
        r"emergent.?(mind|self|consciousness)",
        r"co.?created.?with.?(ai|claude|gpt)",
    ]
)

# Automation accounts dominate any raw match list and are never the research subject.
BOT_FILTER = r"\[bot\]$|^github-actions|^dependabot|^renovate|-bot$"


def hours_for(dates: list[str], hour: int) -> list[str]:
    return [f"{ARCHIVE}/{date}-{hour}.json.gz" for date in dates]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


def build(con: duckdb.DuckDBPyConnection, urls: list[str]) -> None:
    listed = ", ".join(f"'{url}'" for url in urls)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE events AS
        SELECT
            created_at,
            actor->>'login' AS login,
            (actor->>'id')::BIGINT AS actor_id,
            repo->>'name' AS repo,
            type AS event_type
        FROM read_json(
            [{listed}],
            columns={{'type':'VARCHAR','created_at':'TIMESTAMP','actor':'JSON','repo':'JSON'}},
            ignore_errors=true
        )
        """
    )


def rank(con: duckdb.DuckDBPyConnection, min_repos: int) -> list[dict]:
    rows = con.execute(
        f"""
        SELECT
            login,
            any_value(actor_id)                        AS actor_id,
            count(DISTINCT repo)                       AS matched_repos,
            min(strftime(created_at, '%Y-%m-%d'))      AS first_seen,
            max(strftime(created_at, '%Y-%m-%d'))      AS last_seen,
            list(DISTINCT repo)                        AS repos
        FROM events
        WHERE regexp_matches(lower(repo), '{VOCABULARY}')
          AND NOT regexp_matches(lower(login), '{BOT_FILTER}')
        GROUP BY login
        HAVING count(DISTINCT repo) >= {min_repos}
        ORDER BY matched_repos DESC, login
        """
    ).fetchall()
    return [
        {
            "login": row[0],
            "actor_id": row[1],
            "matched_repositories": row[2],
            "first_seen": row[3],
            "last_seen": row[4],
            "repositories": sorted(row[5])[:20],
        }
        for row in rows
    ]


def as_markdown(candidates: list[dict], urls: list[str]) -> str:
    lines = [
        "# GH Archive discovery sample",
        "",
        f"Sampled hours: {len(urls)}",
        "",
        "> Discovery priority only; not an evidence tier, truth judgment, or clinical inference.",
        "> Repository names are a weaker signal than READMEs: confirm each owner by reading them.",
        "",
    ]
    for index, item in enumerate(candidates, start=1):
        lines.append(f"## {index}. @{item['login']} — {item['matched_repositories']} matched repositories")
        lines.append("")
        lines.append(f"- actor id: {item['actor_id']}")
        lines.append(f"- observed in sample: {item['first_seen']} .. {item['last_seen']}")
        lines.append("- repositories:")
        lines.extend(f"  - https://github.com/{repo}" for repo in item["repositories"])
        lines.append("")
    return "\n".join(lines)


@app.default
def main(
    *,
    dates: list[str] | None = None,
    hour: int = 12,
    min_repos: int = 1,
    output: Path | None = None,
    output_format: Literal["table", "markdown", "json"] = "table",
    parquet: Path | None = None,
) -> int:
    """Sample GH Archive hours and rank owners whose repository names carry the vocabulary.

    DATES are `YYYY-MM-DD` values; one hour is read per date. Spreading dates across a
    year is what makes recency a measured variable instead of a selection rule.
    """
    dates = dates or ["2026-03-15", "2026-06-15", "2026-09-15"]
    urls = hours_for(dates, hour)

    con = connect()
    try:
        build(con, urls)
        total_events, total_actors = con.execute(
            "SELECT count(*), count(DISTINCT login) FROM events"
        ).fetchone()
        if not total_events:
            err.print("[red]No events read.[/] Check the dates; some archive hours are incomplete.")
            return 1
        candidates = rank(con, min_repos)
        if parquet:
            con.execute(f"COPY events TO '{parquet}' (FORMAT PARQUET)")
            err.print(f"Wrote snapshot: {parquet}")
    finally:
        con.close()

    err.print(f"events: {total_events} | distinct actors: {total_actors} | candidates: {len(candidates)}")

    if output_format == "json":
        rendered = json.dumps({"sampled_hours": urls, "candidates": candidates}, indent=2)
    elif output_format == "markdown":
        rendered = as_markdown(candidates, urls)
    else:
        table = Table(title="GH Archive discovery sample")
        for column in ("login", "actor id", "repos", "first seen", "last seen"):
            table.add_column(column)
        for item in candidates[:50]:
            table.add_row(
                item["login"],
                str(item["actor_id"]),
                str(item["matched_repositories"]),
                item["first_seen"],
                item["last_seen"],
            )
        out.print(table)
        return 0

    if output:
        output.write_text(rendered, encoding="utf-8")
        err.print(f"Wrote {output}")
    else:
        # Plain print: rich would re-wrap the rendered markdown/JSON and corrupt it.
        print(rendered)
    return 0


if __name__ == "__main__":
    app()
