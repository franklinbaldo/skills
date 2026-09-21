#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "httpx>=0.27",
#     "rich>=13.7",
# ]
# ///
"""Rank public GitHub users for manual AI-epistemic-world discovery review.

The score prioritizes investigation only. It is not an evidence tier, a truth
assessment, or a medical/psychiatric inference. Activity volume never adds points.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import cyclopts
import httpx
from rich.console import Console
from rich.table import Table

API = "https://api.github.com"
app = cyclopts.App(name="find-candidates", help=__doc__)
err = Console(stderr=True)

AI_ROLE = re.compile(
    r"(?:claude|chatgpt|gpt|gemini|llm|ai agent).{0,90}"
    r"(?:co-?author|collaborator|partner|co-?creat|thinking partner|witness|signator)"
    r"|(?:co-?author|collaborator|partner|co-?creat|thinking partner|witness|signator).{0,90}"
    r"(?:claude|chatgpt|gpt|gemini|llm|ai agent)"
    r"|co-authored-by:\s*(?:claude|chatgpt|gpt|gemini)",
    re.I | re.S,
)
RECURSIVE = re.compile(
    r"(?:claude|chatgpt|gpt|gemini|llm|ai agent).{0,140}"
    r"(?:reflection|dialogue|conversation|signature|memory|continuity|self-model)"
    r"|(?:reflection|dialogue|conversation|signature|memory|continuity|self-model).{0,140}"
    r"(?:claude|chatgpt|gpt|gemini|llm|ai agent)",
    re.I | re.S,
)
ORDINARY_SOFTWARE = re.compile(
    r"\b(?:sdk|api client|cli tool|library|wrapper|boilerplate|starter kit)\b", re.I
)

CONCEPTS = {
    "consciousness": re.compile(r"\b(?:consciousness|sentience|awareness)\b", re.I),
    "identity": re.compile(r"\b(?:identity|selfhood|self-model|identity continuity)\b", re.I),
    "epistemology": re.compile(r"\b(?:ontology|epistemology|epistemic|worldview)\b", re.I),
    "cosmology": re.compile(r"\b(?:cosmology|metaphysics|metaphysical|reality model)\b", re.I),
    "spirituality": re.compile(r"\b(?:soul|spiritual|ritual|sacred|daimon|divine)\b", re.I),
    "agency": re.compile(r"\b(?:agency|meaning-making|meaning system|purpose)\b", re.I),
    "continuity": re.compile(r"\b(?:memory architecture|memory seed|continuity protocol|persistent memory)\b", re.I),
}
ARTIFACTS = {
    "paper": re.compile(r"\b(?:paper|manuscript|preprint)\b", re.I),
    "protocol": re.compile(r"\b(?:protocol|constitution|treaty|charter)\b", re.I),
    "experiment": re.compile(r"\b(?:experiment|ablation|benchmark|replication)\b", re.I),
    "agent": re.compile(r"\b(?:agent|persona|daimon|assistant)\b", re.I),
    "dataset": re.compile(r"\b(?:dataset|corpus|ledger)\b", re.I),
    "book_or_site": re.compile(r"\b(?:book|chapter|website|atlas)\b", re.I),
    "framework": re.compile(r"\b(?:framework|architecture|system|engine)\b", re.I),
}


@dataclass(frozen=True)
class Probe:
    family: str
    query: str
    weight: int


PROBES = (
    Probe("consciousness_identity", '"Claude" consciousness', 2),
    Probe("consciousness_identity", '"ChatGPT" consciousness', 2),
    Probe("identity_continuity", '"identity continuity" AI', 2),
    Probe("identity_continuity", '"memory seed" AI', 2),
    Probe("ontology_epistemology", '"AI" ontology epistemology', 2),
    Probe("cosmology_metaphysics", '"AI" cosmology metaphysics', 2),
    Probe("spirituality_soul", '"AI" soul memory', 2),
    Probe("agency_meaning", '"AI" agency meaning', 1),
    Probe("explicit_ai_role", '"Claude" "thinking partner"', 3),
    Probe("explicit_ai_role", '"co-authored-by" Claude', 3),
    Probe("recursive_ai", '"Claude" reflection memory identity', 2),
    Probe("recursive_ai", '"ChatGPT" continuity memory self', 2),
    Probe("consciousness_identity", '"Gemini" consciousness', 2),
    Probe("ontology_epistemology", '"LLM" epistemology', 2),
    Probe("explicit_ai_role", '"ChatGPT" collaborator identity', 3),
    Probe("explicit_ai_role", '"co-created" AI consciousness', 3),
)


@dataclass
class Seed:
    owner: str
    weights: dict[str, int] = field(default_factory=dict)
    repos: dict[str, dict] = field(default_factory=dict)
    urls: set[str] = field(default_factory=set)
    paths: set[str] = field(default_factory=set)

    def add(self, probe: Probe, repo: dict, url: str | None = None, path: str | None = None) -> None:
        self.weights[probe.family] = max(self.weights.get(probe.family, 0), probe.weight)
        if repo.get("full_name"):
            self.repos[repo["full_name"]] = repo
        if url:
            self.urls.add(url)
        if path:
            self.paths.add(path)

    @property
    def score(self) -> int:
        return sum(self.weights.values())


class GitHub:
    def __init__(self, token: str | None, timeout: float) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-epistemic-discovery",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.token = token
        self.client = httpx.Client(base_url=API, headers=headers, timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def get(self, path: str, params: dict | None = None, *, text_match: bool = False):
        headers = {"Accept": "application/vnd.github.text-match+json"} if text_match else None
        response = self.client.get(path, params=params, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"GitHub API {response.status_code}: {response.text[:300]}")
        return response.json()

    def repo_search(self, query: str, per_page: int) -> list[dict]:
        data = self.get(
            "/search/repositories",
            {"q": f"{query} in:readme", "sort": "updated", "order": "desc", "per_page": per_page},
        )
        return list(data.get("items", []))

    def code_search(self, query: str, per_page: int) -> list[dict]:
        data = self.get(
            "/search/code",
            {"q": f"{query} extension:md", "per_page": per_page},
            text_match=True,
        )
        return list(data.get("items", []))

    def user(self, owner: str) -> dict:
        return self.get(f"/users/{owner}")

    def repos_for(self, owner: str, limit: int) -> list[dict]:
        data = self.get(
            f"/users/{owner}/repos",
            {"type": "owner", "sort": "created", "direction": "asc", "per_page": min(limit, 100)},
        )
        return list(data)[:limit]

    def readme(self, full_name: str) -> str:
        try:
            data = self.get(f"/repos/{full_name}/readme")
        except RuntimeError as exc:
            if " 404" in str(exc):
                return ""
            raise
        if data.get("encoding") != "base64" or not data.get("content"):
            return ""
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def span_days(start: str | None, end: str | None) -> int | None:
    a, b = dt(start), dt(end)
    return max(0, (b - a).days) if a and b else None


def scan(github: GitHub, per_query: int, max_queries: int, code_search: bool) -> dict[str, Seed]:
    seeds: dict[str, Seed] = {}
    for probe in PROBES[:max_queries]:
        try:
            repo_hits = github.repo_search(probe.query, per_query)
        except RuntimeError as exc:
            err.print(f"[yellow]Search skipped:[/] {probe.query}: {exc}")
            continue
        for repo in repo_hits:
            owner = (repo.get("owner") or {}).get("login")
            if owner:
                seeds.setdefault(owner, Seed(owner)).add(probe, repo, repo.get("html_url"))

        if not code_search or not github.token:
            continue
        try:
            code_hits = github.code_search(probe.query, per_query)
        except RuntimeError as exc:
            err.print(f"[yellow]Code search skipped:[/] {probe.query}: {exc}")
            continue
        for hit in code_hits:
            repo = hit.get("repository") or {}
            owner = (repo.get("owner") or {}).get("login")
            if owner:
                seeds.setdefault(owner, Seed(owner)).add(
                    probe, repo, hit.get("html_url"), hit.get("path")
                )
    return seeds


def inspect(github: GitHub, seed: Seed, inspect_repos: int, readmes: int) -> dict | None:
    try:
        profile = github.user(seed.owner)
        if profile.get("type") != "User":
            return None
        repos = github.repos_for(seed.owner, inspect_repos)
    except RuntimeError as exc:
        err.print(f"[yellow]Skipping @{seed.owner}:[/] {exc}")
        return None

    by_name = {repo["full_name"]: repo for repo in repos if repo.get("full_name")}
    relevant = [by_name.get(name, repo) for name, repo in seed.repos.items()]
    relevant.sort(key=lambda repo: repo.get("created_at") or "9999")

    bodies = []
    for repo in relevant[:readmes]:
        try:
            body = github.readme(repo["full_name"])
        except RuntimeError as exc:
            err.print(f"[yellow]README skipped:[/] {repo['full_name']}: {exc}")
            continue
        if body:
            bodies.append(body[:200_000])
    text = "\n\n".join(bodies)

    concept_hits = sorted(name for name, pattern in CONCEPTS.items() if pattern.search(text))
    artifact_text = text + "\n" + "\n".join(seed.paths)
    artifact_hits = sorted(name for name, pattern in ARTIFACTS.items() if pattern.search(artifact_text))
    direct_role = bool(AI_ROLE.search(text))
    recursive = bool(RECURSIVE.search(text))

    created = [repo["created_at"] for repo in relevant if repo.get("created_at")]
    pushed = [repo["pushed_at"] for repo in relevant if repo.get("pushed_at")]
    start = min(created) if created else None
    end = max(pushed) if pushed else None
    days = span_days(start, end)

    baseline = []
    cutoff = dt(start)
    if cutoff:
        for repo in repos:
            repo_created = dt(repo.get("created_at"))
            if (
                repo_created
                and (cutoff - repo_created).days >= 180
                and repo.get("full_name") not in seed.repos
            ):
                baseline.append(repo)

    score = seed.score
    reasons = [f"{name}: +{weight}" for name, weight in sorted(seed.weights.items())]
    cluster = len(seed.repos)

    if cluster >= 2:
        score += 2
        reasons.append("same owner surfaced across at least 2 repositories: +2")
    if cluster >= 4:
        score += 1
        reasons.append("broad repository cluster: +1")
    if direct_role:
        score += 3
        reasons.append("README directly attributes collaborator/coauthor/partner role to AI: +3")
    if recursive:
        score += 2
        reasons.append("AI participation is tied to reflection/memory/continuity dialogue: +2")
    if len(concept_hits) >= 3:
        score += 2
        reasons.append("at least 3 epistemic-world concept classes recur: +2")
    if len(concept_hits) >= 5:
        score += 1
        reasons.append("at least 5 epistemic-world concept classes recur: +1")
    if days is not None and days >= 90:
        score += 1
        reasons.append("relevant public cluster spans at least 90 days: +1")
    if days is not None and days >= 365:
        score += 1
        reasons.append("relevant public cluster spans at least 365 days: +1")
    if baseline:
        score += 2
        reasons.append("public pre-cluster repository baseline at least 180 days earlier: +2")
    if len(artifact_hits) >= 3:
        score += 1
        reasons.append("at least 3 durable artifact classes: +1")
    if len(artifact_hits) >= 5:
        score += 1
        reasons.append("at least 5 durable artifact classes: +1")

    if cluster == 1 and not direct_role and len(concept_hits) < 3 and ORDINARY_SOFTWARE.search(text):
        score -= 2
        reasons.append("weak isolated hit with ordinary-software framing: -2")

    return {
        "handle": seed.owner,
        "discovery_priority_score": score,
        "reasons": reasons,
        "matched_families": sorted(seed.weights),
        "repository_urls": sorted({repo.get("html_url") for repo in relevant if repo.get("html_url")}),
        "possible_baseline_repository_urls": [
            repo["html_url"] for repo in baseline[:5] if repo.get("html_url")
        ],
        "account_created_at": profile.get("created_at"),
        "relevant_created_from": start,
        "relevant_pushed_through": end,
        "relevant_span_days": days,
        "public_repositories_observed": len(repos),
        "cluster_repositories_observed": cluster,
        "concept_classes": concept_hits,
        "artifact_classes": artifact_hits,
        "direct_ai_role_signal": direct_role,
        "recursive_ai_signal": recursive,
        "discovery_hits": sorted(seed.urls)[:20],
    }


def as_markdown(candidates: list[dict], measured_at: str) -> str:
    lines = [
        "# AI epistemic-world discovery queue",
        "",
        f"Measured at: {measured_at}",
        "",
        "> Discovery priority only; not an evidence tier, truth judgment, or clinical inference.",
        "",
    ]
    for rank, item in enumerate(candidates, 1):
        lines += [
            f"## {rank}. @{item['handle']} — score {item['discovery_priority_score']}",
            "",
            f"- matched families: {', '.join(item['matched_families'])}",
            f"- cluster repositories observed: {item['cluster_repositories_observed']}",
            f"- public repositories observed: {item['public_repositories_observed']}",
            f"- relevant span days: {item['relevant_span_days'] if item['relevant_span_days'] is not None else 'not_measured'}",
            f"- concept classes: {', '.join(item['concept_classes']) or 'none'}",
            f"- artifact classes: {', '.join(item['artifact_classes']) or 'none'}",
            "- reasons:",
        ]
        lines += [f"  - {reason}" for reason in item["reasons"]]
        lines += ["- repositories:"] + [f"  - {url}" for url in item["repository_urls"]]
        if item["possible_baseline_repository_urls"]:
            lines += ["- possible pre-cluster baseline:"] + [
                f"  - {url}" for url in item["possible_baseline_repository_urls"]
            ]
        lines += ["", ""]
    return "\n".join(lines).rstrip() + "\n"


def as_json(candidates: list[dict], measured_at: str) -> str:
    return json.dumps(
        {
            "kind": "ai-epistemic-discovery-queue",
            "measured_at": measured_at,
            "semantics": "candidate-generation priority only; manual longitudinal qualification required",
            "activity_rule": "activity volume never increases discovery priority",
            "candidates": candidates,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def as_table(candidates: list[dict], measured_at: str) -> str:
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=160)
    table = Table(title=f"AI epistemic-world discovery queue — {measured_at}")
    for name, justify in (
        ("#", "right"),
        ("Handle", "left"),
        ("Score", "right"),
        ("Repos", "right"),
        ("Span", "right"),
        ("AI role", "left"),
        ("Families", "left"),
        ("Artifacts", "left"),
    ):
        table.add_column(name, justify=justify)
    for rank, item in enumerate(candidates, 1):
        table.add_row(
            str(rank),
            f"@{item['handle']}",
            str(item["discovery_priority_score"]),
            str(item["cluster_repositories_observed"]),
            str(item["relevant_span_days"]) if item["relevant_span_days"] is not None else "n/m",
            "yes" if item["direct_ai_role_signal"] else "no",
            ", ".join(item["matched_families"]),
            ", ".join(item["artifact_classes"]),
        )
    console.print(table)
    console.print(
        "[dim]Manual-review priority only. Activity volume and clinical vocabulary add zero points.[/dim]"
    )
    return buffer.getvalue()


def emit(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        err.print(f"[green]Wrote[/] {output}")


@app.default
def main(
    *,
    output: Path | None = None,
    output_format: Literal["table", "markdown", "json"] = "table",
    min_score: int = 5,
    max_owners: int = 30,
    max_queries: int = 12,
    results_per_query: int = 20,
    inspect_repos: int = 100,
    readmes_per_owner: int = 5,
    include_code_search: bool = True,
    token_env: str = "GITHUB_TOKEN",
    timeout: float = 20.0,
) -> int:
    """Generate an explainable public-GitHub candidate queue for manual review."""
    token = os.environ.get(token_env) or os.environ.get("GH_TOKEN")
    if not token:
        err.print(
            "[yellow]No GitHub token found.[/] Using README repository search only; "
            "authenticated code-search recall is disabled."
        )
        include_code_search = False
        max_queries = min(max_queries, 8)

    measured_at = datetime.now(UTC).isoformat()
    github = GitHub(token, timeout)
    try:
        seeds = scan(
            github,
            max(1, min(results_per_query, 100)),
            max(1, min(max_queries, len(PROBES))),
            include_code_search,
        )
        shortlist = sorted(
            seeds.values(), key=lambda seed: (seed.score, len(seed.repos)), reverse=True
        )[: max(1, max_owners)]
        candidates = [
            item
            for seed in shortlist
            if (
                item := inspect(
                    github,
                    seed,
                    max(1, min(inspect_repos, 100)),
                    max(1, readmes_per_owner),
                )
            )
            is not None
            and item["discovery_priority_score"] >= min_score
        ]
    finally:
        github.close()

    candidates.sort(
        key=lambda item: (
            item["discovery_priority_score"],
            item["cluster_repositories_observed"],
            item["relevant_span_days"] or -1,
        ),
        reverse=True,
    )

    if output_format == "json":
        content = as_json(candidates, measured_at)
    elif output_format == "markdown":
        content = as_markdown(candidates, measured_at)
    else:
        content = as_table(candidates, measured_at)
    emit(content, output)
    return 0


if __name__ == "__main__":
    app()
