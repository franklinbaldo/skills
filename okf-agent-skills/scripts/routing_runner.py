#!/usr/bin/env python3
"""Execute routing eval cases and emit import-ready observation facts.

Each attempt launches a fresh subprocess, sends the eval query on stdin, and
expects one JSON object on stdout. A success contains `observed_trigger: bool`;
a failed attempt contains `error` and no observed trigger. The output JSONL is
data for `okf-parser import`, not a second projection format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import routing_benchmark

DEFAULT_OUTPUT = Path('.okf/agent-skills-routing-observations.jsonl')


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _observation_id(row: dict[str, object]) -> str:
    return (
        f"{row['skill']}--case-{int(row['case_index']):03d}"
        f"--run-{int(row['repetition']):02d}"
    )


def _base_observation(row: dict[str, object], runner: str) -> dict[str, object]:
    query = str(row['query'])
    return {
        'observation_id': _observation_id(row),
        'skill': str(row['skill']),
        'case_index': int(row['case_index']),
        'repetition': int(row['repetition']),
        'should_trigger': bool(row['should_trigger']),
        'query_sha256': _sha256(query),
        'runner': runner,
    }


def _failure(row: dict[str, object], runner: str, error: str) -> dict[str, object]:
    result = _base_observation(row, runner)
    result['error'] = error
    return result


def run_one(
    row: dict[str, object], command: list[str], runner: str, timeout: float
) -> dict[str, object]:
    query = str(row['query'])
    env = os.environ.copy()
    env.update(
        {
            'SKILL_ROUTING_SKILL': str(row['skill']),
            'SKILL_ROUTING_CASE_INDEX': str(row['case_index']),
            'SKILL_ROUTING_REPETITION': str(row['repetition']),
            'SKILL_ROUTING_SHOULD_TRIGGER': 'true' if bool(row['should_trigger']) else 'false',
            'SKILL_ROUTING_QUERY_SHA256': _sha256(query),
        }
    )
    try:
        completed = subprocess.run(
            command,
            input=query,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _failure(row, runner, f'timeout after {timeout:g}s')
    except OSError as exc:
        return _failure(row, runner, f'spawn error: {exc}')

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or 'no output'
        return _failure(row, runner, f'exit {completed.returncode}: {detail[:2000]}')

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return _failure(row, runner, f'invalid JSON: {exc}')
    if not isinstance(payload, dict) or not isinstance(payload.get('observed_trigger'), bool):
        return _failure(row, runner, 'adapter must return JSON object with boolean observed_trigger')

    result = _base_observation(row, runner)
    result['observed_trigger'] = payload['observed_trigger']
    model = payload.get('model')
    if isinstance(model, str) and model:
        result['model'] = model
    elif model is not None:
        return _failure(row, runner, 'adapter model must be a string when present')
    return result


def select_runs(
    root: Path,
    repetitions: int,
    *,
    skill: str | None = None,
    case_index: int | None = None,
    repetition: int | None = None,
) -> list[dict[str, object]]:
    rows = routing_benchmark.make_manifest(root, repetitions)
    selected = [
        row
        for row in rows
        if (skill is None or row['skill'] == skill)
        and (case_index is None or row['case_index'] == case_index)
        and (repetition is None or row['repetition'] == repetition)
    ]
    if not selected:
        raise ValueError('selection matched no routing runs')
    return selected


def write_observations(rows: list[dict[str, object]], path: Path, append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 'a' if append else 'w'
    with path.open(mode, encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Agent Skills repository/root')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--skill')
    parser.add_argument('--case-index', type=int)
    parser.add_argument('--repetition', type=int)
    parser.add_argument('--runner', required=True, help='stable adapter/runner identifier')
    parser.add_argument('--timeout', type=float, default=120.0)
    parser.add_argument('--append', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('external adapter command is required after --')
    if args.timeout <= 0:
        parser.error('--timeout must be > 0')

    root = args.source.resolve()
    rows = select_runs(
        root,
        args.repetitions,
        skill=args.skill,
        case_index=args.case_index,
        repetition=args.repetition,
    )
    observations = [run_one(row, command, args.runner, args.timeout) for row in rows]
    output = args.output if args.output.is_absolute() else root / args.output
    write_observations(observations, output, args.append)

    failed = sum('error' in row for row in observations)
    print(
        json.dumps(
            {
                'attempted': len(observations),
                'observed': len(observations) - failed,
                'failed': failed,
                'output': str(output),
            },
            sort_keys=True,
        )
    )
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
