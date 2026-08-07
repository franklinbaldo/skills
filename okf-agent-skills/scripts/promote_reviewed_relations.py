#!/usr/bin/env python3
"""Promote explicitly reviewed semantic mentions into derived OKF graph edges.

The source Agent Skills remain unchanged. A repository-local optional policy file
(`.okf/agent-skills-reviewed-relations.json`) records pairs that a human/agent review
has accepted as real routing/delegation relations. Each promoted pair must still have
source mention evidence in the current corpus; stale policy fails closed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

POLICY_PATH = Path('.okf/agent-skills-reviewed-relations.json')


def _yaml_string(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'"{escaped}"'


def _relative_target(source: PurePosixPath, target: PurePosixPath) -> str:
    return PurePosixPath(os.path.relpath(target.as_posix(), start=source.parent.as_posix())).as_posix()


def load_policy(root: Path) -> list[dict[str, str]]:
    path = root / POLICY_PATH
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError(f'{path}: expected a JSON array')
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f'{path}: item {index} must be an object')
        source = item.get('source_skill')
        target = item.get('target_skill')
        reason = item.get('reason')
        if not all(isinstance(value, str) and value.strip() for value in (source, target, reason)):
            raise ValueError(f'{path}: item {index} requires non-empty source_skill, target_skill, reason')
        pair = (source.strip(), target.strip())
        if pair in seen:
            raise ValueError(f'{path}: duplicate reviewed relation {pair[0]} -> {pair[1]}')
        seen.add(pair)
        result.append({'source_skill': pair[0], 'target_skill': pair[1], 'reason': reason.strip()})
    return result


def promote(root: Path, output: Path, mentions: list[dict[str, object]]) -> list[dict[str, object]]:
    policy = load_policy(root)
    if not policy:
        return []

    skill_paths = {path.stem: PurePosixPath('skills') / path.name for path in (output / 'skills').glob('*.md')}
    mention_by_pair: dict[tuple[str, str], list[dict[str, object]]] = {}
    for mention in mentions:
        pair = (str(mention['source_skill']), str(mention['target_skill']))
        mention_by_pair.setdefault(pair, []).append(mention)

    promoted: list[dict[str, object]] = []
    relation_dir = output / 'relations'
    relation_dir.mkdir(parents=True, exist_ok=True)

    per_source: dict[str, list[tuple[str, str]]] = {}
    for index, item in enumerate(policy, start=1):
        source = item['source_skill']
        target = item['target_skill']
        pair = (source, target)
        evidence = sorted(mention_by_pair.get(pair, []), key=lambda row: int(row['source_line']))
        if not evidence:
            raise ValueError(f'reviewed relation has no current mention evidence: {source} -> {target}')
        if source not in skill_paths or target not in skill_paths:
            raise ValueError(f'reviewed relation references unknown skill: {source} -> {target}')

        first = evidence[0]
        source_rel = skill_paths[source]
        target_rel = skill_paths[target]
        relation = {
            'source_skill': source,
            'target_skill': target,
            'target_kind': 'skill',
            'source_path': str(first['source_path']),
            'source_line': int(first['source_line']),
            'derived_source': source_rel.as_posix(),
            'derived_target': target_rel.as_posix(),
            'resolved': True,
            'evidence_kind': 'reviewed_mention',
            'review_reason': item['reason'],
            'context_sha256': str(first['context_sha256']),
        }
        promoted.append(relation)
        per_source.setdefault(source, []).append((target, _relative_target(source_rel, target_rel)))

        fields = [
            '---',
            'type: SkillRelation',
            f'source_skill: {_yaml_string(source)}',
            f'target_skill: {_yaml_string(target)}',
            'target_kind: "skill"',
            f'source_path: {_yaml_string(str(first["source_path"]))}',
            f'source_line: {int(first["source_line"])}',
            f'derived_source: {_yaml_string(source_rel.as_posix())}',
            f'derived_target: {_yaml_string(target_rel.as_posix())}',
            'resolved: true',
            'evidence_kind: "reviewed_mention"',
            f'review_reason: {_yaml_string(item["reason"])}',
            f'context_sha256: {_yaml_string(str(first["context_sha256"]))}',
            '---',
            '',
        ]
        (relation_dir / f'reviewed--{index:04d}.md').write_text('\n'.join(fields), encoding='utf-8')

    for source, targets in sorted(per_source.items()):
        path = output / Path(skill_paths[source].as_posix())
        text = path.read_text(encoding='utf-8').rstrip()
        lines = ['', '', '## Reviewed relations', '']
        for target, relative in sorted(targets):
            lines.append(f'- [{target}]({relative})')
        path.write_text(text + '\n'.join(lines) + '\n', encoding='utf-8')

    return promoted
