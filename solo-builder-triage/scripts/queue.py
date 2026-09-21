#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "duckdb>=1.1",
#     "rich>=13.7",
# ]
# ///
"""Maintain the solo-builder triage queue across days.

One run samples a day of GH Archive, admits the accounts inside the current band, and
merges them into a persistent queue. The queue is the memory of the ritual: it records
who is still unanalysed, and which criteria version admitted each entry.

The band is a band on purpose. Below the floor there is no production to speak of;
above the ceiling the sample is automation rather than people. Volume is never a rank.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import cyclopts
import duckdb
from rich.console import Console
from rich.table import Table

app = cyclopts.App(name="queue", help=__doc__)
out = Console()
err = Console(stderr=True)

ARCHIVE = "https://data.gharchive.org"
CRITERIA_VERSION = "2026-09-21"
BOTS = r"\[bot\]$|^github-actions|^dependabot|^renovate|-bot$|^copilot|noreply$"
DISPOSABLE_LOGIN = r"^[a-z0-9]{8,12}$"


def sample(
    date: str,
    hours: list[int],
    min_events: int,
    max_events: int,
    max_repos: int,
    min_pct_own: float,
    min_kinds: int,
) -> list[dict]:
    urls = ", ".join(f"'{ARCHIVE}/{date}-{hour}.json.gz'" for hour in hours)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(
        f"""
        CREATE TABLE ev AS
        SELECT actor->>'login' AS login,
               (actor->>'id')::BIGINT AS actor_id,
               repo->>'name' AS repo,
               split_part(repo->>'name', '/', 1) AS repo_owner,
               type AS ev_type
        FROM read_json([{urls}],
             columns={{'type':'VARCHAR','actor':'JSON','repo':'JSON'}}, ignore_errors=true)
        WHERE NOT regexp_matches(lower(actor->>'login'), '{BOTS}')
        """
    )
    con.execute(
        """
        CREATE TABLE reception AS
        SELECT repo_owner AS owner,
               count(DISTINCT CASE WHEN login <> repo_owner THEN login END) AS other_actors
        FROM ev GROUP BY repo_owner
        """
    )
    rows = con.execute(
        f"""
        SELECT e.login,
               any_value(e.actor_id)                     AS actor_id,
               count(*)                                  AS events,
               count(DISTINCT e.repo)                    AS repos,
               count(DISTINCT e.ev_type)                 AS kinds,
               round(100.0 * count(*) FILTER (WHERE e.repo_owner = e.login) / count(*), 1) AS pct_own,
               max(CASE WHEN lower(e.repo) = lower(e.login) || '/' || lower(e.login) || '.github.io'
                        THEN 1 ELSE 0 END)               AS has_site,
               list(DISTINCT e.repo)[1:6]                AS repositories
        FROM ev e LEFT JOIN reception r ON r.owner = e.login
        GROUP BY e.login
        HAVING count(*) BETWEEN {min_events} AND {max_events}
           AND count(DISTINCT e.repo) <= {max_repos}
           AND count(DISTINCT e.ev_type) >= {min_kinds}
           AND 100.0 * count(*) FILTER (WHERE e.repo_owner = e.login) / count(*) >= {min_pct_own}
           AND coalesce(any_value(r.other_actors), 0) = 0
           AND NOT regexp_matches(e.login, '{DISPOSABLE_LOGIN}')
        ORDER BY count(DISTINCT e.ev_type) DESC, count(*) DESC
        """
    ).fetchall()
    con.close()
    columns = ["login", "actor_id", "events", "repos", "kinds", "pct_own", "has_site", "repositories"]
    return [dict(zip(columns, row)) for row in rows]


def merge(existing: list[dict], found: list[dict], date: str) -> tuple[list[dict], int]:
    by_login = {entry["login"]: entry for entry in existing}
    added = 0
    for item in found:
        entry = by_login.get(item["login"])
        if entry is None:
            by_login[item["login"]] = {
                **item,
                "criteria_version": CRITERIA_VERSION,
                "first_sampled": date,
                "last_sampled": date,
                "times_sampled": 1,
                "analysed": False,
                "record": None,
            }
            added += 1
            continue
        # Recurrence across sampled days is the persistence signal; keep it.
        entry["last_sampled"] = max(entry.get("last_sampled", date), date)
        entry["times_sampled"] = entry.get("times_sampled", 1) + 1
        entry["has_site"] = max(entry.get("has_site", 0), item["has_site"])
    return list(by_login.values()), added


@app.default
def main(
    queue_file: Path = Path("queue.json"),
    *,
    date: str | None = None,
    hours: list[int] | None = None,
    min_events: int = 20,
    max_events: int = 300,
    max_repos: int = 10,
    min_pct_own: float = 80.0,
    min_kinds: int = 3,
    show: int = 20,
) -> int:
    """Sample DATE and merge admitted accounts into QUEUE_FILE."""
    date = date or (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)).isoformat()
    hours = hours or [2, 6, 10, 14, 18, 22]

    try:
        found = sample(date, hours, min_events, max_events, max_repos, min_pct_own, min_kinds)
    except duckdb.Error as error:
        err.print(f"[red]Sampling failed:[/] {error}")
        return 1
    if not found:
        err.print(f"[yellow]No accounts admitted for {date}.[/] Some archive hours are incomplete.")

    existing = []
    if queue_file.exists():
        existing = json.loads(queue_file.read_text(encoding="utf-8")).get("queue", [])
    merged, added = merge(existing, found, date)

    # Unanalysed first, then recurrence, then event-kind breadth. Never raw volume.
    merged.sort(key=lambda e: (e["analysed"], -e.get("times_sampled", 1), -e["kinds"], e["login"]))
    queue_file.write_text(
        json.dumps(
            {
                "criteria_version": CRITERIA_VERSION,
                "updated": dt.datetime.now(dt.UTC).isoformat(),
                "queue": merged,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pending = [entry for entry in merged if not entry["analysed"]]
    err.print(f"{date}: admitted {len(found)} | new {added} | pending {len(pending)} | total {len(merged)}")

    table = Table(title=f"next up (criteria {CRITERIA_VERSION})")
    for column in ("login", "kinds", "events", "repos", "seen", "site", "repositories"):
        table.add_column(column)
    for entry in pending[:show]:
        table.add_row(
            entry["login"],
            str(entry["kinds"]),
            str(entry["events"]),
            str(entry["repos"]),
            str(entry.get("times_sampled", 1)),
            "yes" if entry.get("has_site") else "",
            ", ".join(entry["repositories"][:3])[:54],
        )
    out.print(table)
    return 0


if __name__ == "__main__":
    app()
