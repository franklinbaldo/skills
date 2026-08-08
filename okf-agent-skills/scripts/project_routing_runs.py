#!/usr/bin/env python3
"""Project planned/reported routing benchmark runs into the derived OKF IR."""

from __future__ import annotations

import hashlib
from pathlib import Path

import routing_benchmark

OBSERVATIONS_PATH = Path('.okf/agent-skills-routing-observations.jsonl')
DEFAULT_REPETITIONS = 5


def _yaml_string(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'"{escaped}"'


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _load_observations(root: Path) -> dict[tuple[str, int, int], dict[str, object]]:
    path = root / OBSERVATIONS_PATH
    if not path.is_file():
        return {}
    rows = routing_benchmark.load_observations(path)
    result: dict[tuple[str, int, int], dict[str, object]] = {}
    for line_no, row in enumerate(rows, start=1):
        skill = row.get('skill')
        case_index = row.get('case_index')
        repetition = row.get('repetition')
        if not isinstance(skill, str) or not isinstance(case_index, int) or not isinstance(repetition, int):
            raise ValueError(f'{path}:{line_no}: skill, case_index and repetition are required')
        if repetition < 1:
            raise ValueError(f'{path}:{line_no}: repetition must be >= 1')
        key = (skill, case_index, repetition)
        if key in result:
            raise ValueError(f'{path}:{line_no}: duplicate observation for {key}')
        result[key] = row
    return result


def project(root: Path, output: Path, repetitions: int = DEFAULT_REPETITIONS) -> list[dict[str, object]]:
    root = root.resolve()
    output = output.resolve()
    planned = routing_benchmark.make_manifest(root, repetitions)
    observed = _load_observations(root)
    planned_keys = {(str(row['skill']), int(row['case_index']), int(row['repetition'])) for row in planned}
    stale = sorted(set(observed) - planned_keys)
    if stale:
        raise ValueError(f'observations do not match current routing manifest: {stale[:5]}')

    run_dir = output / 'routing-runs'
    run_dir.mkdir(parents=True, exist_ok=True)
    for stale_file in run_dir.glob('*.md'):
        stale_file.unlink()

    rows: list[dict[str, object]] = []
    for row in planned:
        skill = str(row['skill'])
        case_index = int(row['case_index'])
        repetition = int(row['repetition'])
        key = (skill, case_index, repetition)
        observation = observed.get(key)
        should_trigger = bool(row['should_trigger'])
        query = str(row['query'])
        source_path = str(row['source_path'])
        observed_trigger: bool | None = None
        execution_status: str | None = None
        runner: str | None = None
        model: str | None = None
        error_type: str | None = None
        error_message: str | None = None

        if observation is not None:
            if bool(observation['should_trigger']) != should_trigger:
                raise ValueError(f'observation expectation disagrees with current eval for {key}')
            if 'query' in observation and observation['query'] != query:
                raise ValueError(f'observation query disagrees with current eval for {key}')
            if 'source_path' in observation and observation['source_path'] != source_path:
                raise ValueError(f'observation source_path disagrees with current eval for {key}')
            execution_status = str(observation.get('execution_status', routing_benchmark.EXECUTION_OBSERVED))
            if execution_status == routing_benchmark.EXECUTION_OBSERVED:
                observed_trigger = bool(observation['observed_trigger'])
            runner = str(observation['runner']) if observation.get('runner') is not None else None
            model = str(observation['model']) if observation.get('model') is not None else None
            error_type = str(observation['error_type']) if observation.get('error_type') is not None else None
            error_message = str(observation['error_message']) if observation.get('error_message') is not None else None

        projected = {
            'skill': skill,
            'case_index': case_index,
            'repetition': repetition,
            'should_trigger': should_trigger,
            'observed_trigger': observed_trigger,
            'execution_status': execution_status,
            'source_path': source_path,
            'query_sha256': _sha256(query),
            'runner': runner,
            'model': model,
            'error_type': error_type,
            'error_message': error_message,
        }
        rows.append(projected)

        fields = [
            '---',
            'type: SkillRoutingRun',
            f'skill: {_yaml_string(skill)}',
            f'case_index: {case_index}',
            f'repetition: {repetition}',
            f'should_trigger: {"true" if should_trigger else "false"}',
            f'source_path: {_yaml_string(source_path)}',
            f'query_sha256: {_yaml_string(projected["query_sha256"])}',
        ]
        if observed_trigger is not None:
            fields.append(f'observed_trigger: {"true" if observed_trigger else "false"}')
        if execution_status is not None:
            fields.append(f'execution_status: {_yaml_string(execution_status)}')
        if runner is not None:
            fields.append(f'runner: {_yaml_string(runner)}')
        if model is not None:
            fields.append(f'model: {_yaml_string(model)}')
        if error_type is not None:
            fields.append(f'error_type: {_yaml_string(error_type)}')
        if error_message is not None:
            fields.append(f'error_message: {_yaml_string(error_message)}')
        fields.extend(['---', ''])
        filename = f'{skill}--case-{case_index:03d}--run-{repetition:02d}.md'
        (run_dir / filename).write_text('\n'.join(fields), encoding='utf-8')

    return rows
