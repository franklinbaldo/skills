#!/usr/bin/env python3
"""Execute routing eval cases through an external isolated runner protocol.

Each attempt launches a fresh subprocess, sends the eval query on stdin, and
expects one JSON object on stdout. A successful adapter response must contain
`observed_trigger: bool`; it may also report `model`. Process/timeout/protocol
failures are preserved as execution errors and never converted into routing
false negatives.
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


def _base_observation(row: dict[str, object], runner: str) -> dict[str, object]:
    query = str(row['query'])
    return {
        'skill': str(row['skill']),
        'case_index': int(row['case_index']),
        'repetition': int(row['repetition']),
        'query': query,
        'query_sha256': _sha256(query),
        'should_trigger': bool(row['should_trigger']),
        'source_path': str(row['source_path']),
        'runner': runner,
    }


def _error(
    row: dict[str, object],
    runner: str,
    error_type: str,
    message: str,
    *,
    model: str | None = None,
) -> dict[str, object]:
    result = _base_observation(row, runner)
    result.update(
        {
            'execution_status': routing_benchmark.EXECUTION_ERROR,
            'error_type': error_type,
            'error_message': message,
        }
    )
    if model:
        result['model'] = model
    return result


def run_one(
    row: dict[str, object],
    command: list[str],
    runner: str,
    timeout: float,
) -> dict[str, object]:
    query = str(row['query'])
    env = os.environ.copy()
    env.update(
        {
            'SKILL_ROUTING_SKILL': str(row['skill']),
            'SKILL_ROUTING_CASE_INDEX': str(row['case_index']),
            'SKILL_ROUTING_REPETITION': str(row['repetition']),
            'SKILL_ROUTING_SHOULD_TRIGGER': 'true' if bool(row['should_trigger']) else 'false',
            'SKILL_ROUTING_SOURCE_PATH': str(row['source_path']),
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
    except subprocess.TimeoutExpired as exc:
        return _error(row, runner, 'timeout', f'runner exceeded {timeout:g}s timeout')
    except OSError as exc:
        return _error(row, runner, 'spawn_error', str(exc))

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or 'runner exited non-zero'
        return _error(
            row,
            runner,
            'process_exit',
            f'exit={completed.returncode}: {detail[:2000]}',
        )

    stdout = completed.stdout.strip()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return _error(row, runner, 'invalid_json', f'{exc}: {stdout[:1000]}')
    if not isinstance(payload, dict):
        return _error(row, runner, 'invalid_output', 'runner stdout must be a JSON object')

    observed = payload.get('observed_trigger')
    model = payload.get('model')
    if model is not None and not isinstance(model, str):
        return _error(row, runner, 'invalid_output', 'model must be a string when present')
    if not isinstance(observed, bool):
        return _error(
            row,
            runner,
            'invalid_output',
            'successful runner output requires boolean observed_trigger',
            model=model,
        )

    result = _base_observation(row, runner)
    result.update(
        {
            'execution_status': routing_benchmark.EXECUTION_OBSERVED,
            'observed_trigger': observed,
        }
    )
    if model:
        result['model'] = model
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
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help='external adapter command after --; query is sent on stdin',
    )
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

    completed = sum(row['execution_status'] == routing_benchmark.EXECUTION_OBSERVED for row in observations)
    failed = len(observations) - completed
    print(
        json.dumps(
            {
                'attempted': len(observations),
                'observed': completed,
                'failed': failed,
                'output': str(output),
            },
            sort_keys=True,
        )
    )
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
