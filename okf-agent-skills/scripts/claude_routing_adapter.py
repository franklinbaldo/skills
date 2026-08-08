#!/usr/bin/env python3
"""Observe implicit Agent Skill activation from Claude Code's stream-json output.

The skills themselves must already be exposed to Claude Code, normally with:

    npx skills add . --agent claude-code -y

This adapter does not install, select, or force a skill. It runs the eval query in a
fresh non-persistent Claude Code session and reports whether the target skill was
invoked through Claude's Skill tool. stdout is the tiny JSON protocol consumed by
routing_runner.py; Claude's stream stays internal to this process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterable


def _walk(value: object) -> Iterable[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _skill_name_from_tool_use(item: dict[str, object]) -> str | None:
    if item.get("type") != "tool_use" or item.get("name") != "Skill":
        return None
    payload = item.get("input")
    if not isinstance(payload, dict):
        return None
    for key in ("skill", "name", "command"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.removeprefix("$")
    return None


def inspect_stream(lines: Iterable[str], target_skill: str) -> tuple[bool, str | None, bool]:
    """Return (target_invoked, model, target_was_offered)."""
    invoked = False
    model: str | None = None
    offered = False

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        event = json.loads(raw)
        if not isinstance(event, dict):
            continue

        if event.get("type") == "system" and event.get("subtype") == "init":
            event_model = event.get("model")
            if isinstance(event_model, str) and event_model:
                model = event_model
            skills = event.get("skills")
            if isinstance(skills, list):
                offered = target_skill in {str(skill) for skill in skills}

        for item in _walk(event):
            if _skill_name_from_tool_use(item) == target_skill:
                invoked = True

    return invoked, model, offered


def main() -> int:
    target = os.environ.get("SKILL_ROUTING_SKILL")
    if not target:
        print("SKILL_ROUTING_SKILL is required", file=sys.stderr)
        return 2

    query = sys.stdin.read()
    if not query:
        print("routing query is empty", file=sys.stderr)
        return 2

    command = [
        "claude",
        "-p",
        query,
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--allowedTools",
        "Skill",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        print(f"claude exited {completed.returncode}: {detail[:2000]}", file=sys.stderr)
        return completed.returncode or 2

    try:
        invoked, model, offered = inspect_stream(completed.stdout.splitlines(), target)
    except json.JSONDecodeError as exc:
        print(f"invalid Claude stream-json: {exc}", file=sys.stderr)
        return 2

    if not offered:
        print(
            f"target skill {target!r} was not present in Claude Code's offered skill catalog; "
            "run `npx skills add . --agent claude-code -y` first",
            file=sys.stderr,
        )
        return 2

    payload: dict[str, object] = {"observed_trigger": invoked}
    if model:
        payload["model"] = model
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
