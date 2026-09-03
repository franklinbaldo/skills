#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
# ]
# ///
"""Project an Agent Skills tree into a deterministic, disposable OKF bundle.

This helper is intentionally stdlib-only and static: it reads source files but never
executes scripts from the audited corpus. The projection is an inspection IR, not a
replacement for the source skills.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import cyclopts

SKILL_FILE = "SKILL.md"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
IGNORED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}


@dataclass(frozen=True)
class Skill:
    name: str
    source_file: Path
    source_rel: PurePosixPath
    derived_rel: PurePosixPath


@dataclass(frozen=True)
class Resource:
    skill: Skill
    source_file: Path
    source_rel: PurePosixPath
    derived_rel: PurePosixPath
    kind: str


@dataclass(frozen=True)
class Relation:
    source_skill: str
    target_skill: str | None
    target_kind: str | None
    source_path: str
    source_link_target: str
    source_line: int
    derived_source: str
    derived_target: str | None
    resolved: bool


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except (UnicodeDecodeError, OSError):
        return None


def _frontmatter_name(path: Path) -> str | None:
    """Extract a simple scalar `name:` from YAML frontmatter without a YAML dependency."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^name:\s*(.*?)\s*$", line)
        if match:
            value = match.group(1).strip().strip('"\'')
            return value or None
    return None


def discover_skills(root: Path, output: Path) -> list[Skill]:
    skills: list[Skill] = []
    output_resolved = output.resolve()
    for path in sorted(root.rglob(SKILL_FILE)):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        try:
            path.resolve().relative_to(output_resolved)
        except ValueError:
            pass
        else:
            continue
        rel = PurePosixPath(path.relative_to(root).as_posix())
        directory_name = path.parent.name
        authored_name = _frontmatter_name(path)
        name = authored_name or directory_name
        derived = PurePosixPath("skills") / f"{name}.md"
        skills.append(Skill(name=name, source_file=path, source_rel=rel, derived_rel=derived))
    return skills


def _resource_kind(path: Path, skill_dir: Path) -> str:
    rel_parts = path.relative_to(skill_dir).parts
    if rel_parts and rel_parts[0] == "references":
        return "reference"
    if rel_parts and rel_parts[0] == "scripts":
        return "script"
    if rel_parts and rel_parts[0] in {"assets", "images"}:
        return "asset"
    if rel_parts and rel_parts[0] in {"examples", "evals"}:
        return "example"
    return "other"


def discover_resources(root: Path, output: Path, skills: list[Skill]) -> list[Resource]:
    candidates: list[tuple[Skill, Path, str]] = []
    output_resolved = output.resolve()
    for skill in skills:
        skill_dir = skill.source_file.parent
        for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
            if path == skill.source_file or any(part in IGNORED_DIRS for part in path.parts):
                continue
            try:
                path.resolve().relative_to(output_resolved)
            except ValueError:
                pass
            else:
                continue
            candidates.append((skill, path, _resource_kind(path, skill_dir)))

    resources: list[Resource] = []
    for index, (skill, path, kind) in enumerate(candidates, start=1):
        source_rel = PurePosixPath(path.relative_to(root).as_posix())
        derived_rel = PurePosixPath("resources") / f"{skill.name}--{index:04d}.md"
        resources.append(
            Resource(
                skill=skill,
                source_file=path,
                source_rel=source_rel,
                derived_rel=derived_rel,
                kind=kind,
            )
        )
    return resources


def _link_target_only(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return target


def extract_relations(
    root: Path,
    skills: list[Skill],
    resources: list[Resource],
) -> list[Relation]:
    skill_by_source = {skill.source_file.resolve(): skill for skill in skills}
    resource_by_source = {resource.source_file.resolve(): resource for resource in resources}
    relations: list[Relation] = []

    for skill in skills:
        text = skill.source_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in MARKDOWN_LINK_RE.finditer(line):
                raw_target = match.group(1).strip()
                target = _link_target_only(raw_target)
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue

                candidate = (skill.source_file.parent / target).resolve()
                target_skill = skill_by_source.get(candidate)
                target_resource = resource_by_source.get(candidate)

                derived_target: str | None = None
                target_kind: str | None = None
                if target_skill is not None:
                    derived_target = target_skill.derived_rel.as_posix()
                    target_kind = "skill"
                elif target_resource is not None:
                    derived_target = target_resource.derived_rel.as_posix()
                    target_kind = "resource"

                relations.append(
                    Relation(
                        source_skill=skill.name,
                        target_skill=target_skill.name if target_skill else None,
                        target_kind=target_kind,
                        source_path=skill.source_rel.as_posix(),
                        source_link_target=raw_target,
                        source_line=line_no,
                        derived_source=skill.derived_rel.as_posix(),
                        derived_target=derived_target,
                        resolved=derived_target is not None,
                    )
                )

    return sorted(
        relations,
        key=lambda relation: (
            relation.source_path,
            relation.source_line,
            relation.source_link_target,
        ),
    )


def _relation_label(relation: Relation) -> str:
    if relation.target_skill is not None:
        return relation.target_skill
    target = _link_target_only(relation.source_link_target)
    return PurePosixPath(target).name or target


def _relative_derived_target(source: str, target: str) -> str:
    source_parent = PurePosixPath(source).parent.as_posix()
    return PurePosixPath(os.path.relpath(target, start=source_parent)).as_posix()


def _write_skill_concept(output: Path, skill: Skill, relations: list[Relation]) -> None:
    target = output / Path(skill.derived_rel.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: Skill",
        f"name: {_yaml_string(skill.name)}",
        f"source_path: {_yaml_string(skill.source_rel.as_posix())}",
        f"source_sha256: {_yaml_string(_sha256(skill.source_file))}",
        f"line_count: {_line_count(skill.source_file) or 0}",
        "---",
        "",
        f"# {skill.name}",
        "",
        f"Authoritative source: `{skill.source_rel.as_posix()}`.",
    ]
    resolved = [relation for relation in relations if relation.source_skill == skill.name and relation.resolved]
    if resolved:
        lines.extend(["", "## Derived relations", ""])
        for relation in resolved:
            assert relation.derived_target is not None
            relative_target = _relative_derived_target(
                skill.derived_rel.as_posix(), relation.derived_target
            )
            lines.append(f"- [{_relation_label(relation)}]({relative_target})")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_relation_concepts(output: Path, relations: list[Relation]) -> None:
    relation_dir = output / "relations"
    relation_dir.mkdir(parents=True, exist_ok=True)
    for index, relation in enumerate(relations, start=1):
        slug = f"{relation.source_skill}--{index:04d}.md"
        fields = [
            "---",
            "type: SkillRelation",
            f"source_skill: {_yaml_string(relation.source_skill)}",
            f"source_path: {_yaml_string(relation.source_path)}",
            f"source_link_target: {_yaml_string(relation.source_link_target)}",
            f"source_line: {relation.source_line}",
            f"derived_source: {_yaml_string(relation.derived_source)}",
            f"resolved: {'true' if relation.resolved else 'false'}",
        ]
        if relation.target_skill is not None:
            fields.append(f"target_skill: {_yaml_string(relation.target_skill)}")
        if relation.target_kind is not None:
            fields.append(f"target_kind: {_yaml_string(relation.target_kind)}")
        if relation.derived_target is not None:
            fields.append(f"derived_target: {_yaml_string(relation.derived_target)}")
        fields.extend(["---", ""])
        (relation_dir / slug).write_text("\n".join(fields), encoding="utf-8")


def _write_resource_concepts(output: Path, resources: list[Resource]) -> None:
    resource_dir = output / "resources"
    resource_dir.mkdir(parents=True, exist_ok=True)
    for resource in resources:
        fields = [
            "---",
            "type: SkillResource",
            f"skill: {_yaml_string(resource.skill.name)}",
            f"source_path: {_yaml_string(resource.source_rel.as_posix())}",
            f"kind: {_yaml_string(resource.kind)}",
            f"size_bytes: {resource.source_file.stat().st_size}",
            f"source_sha256: {_yaml_string(_sha256(resource.source_file))}",
        ]
        count = _line_count(resource.source_file)
        if count is not None:
            fields.append(f"line_count: {count}")
        fields.extend(["---", ""])
        (output / Path(resource.derived_rel.as_posix())).write_text(
            "\n".join(fields), encoding="utf-8"
        )


def project(root: Path, output: Path) -> tuple[list[Skill], list[Relation]]:
    root = root.resolve()
    output = output.resolve()
    if root == output:
        raise ValueError("output directory must differ from source root")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    skills = discover_skills(root, output)
    resources = discover_resources(root, output, skills)
    relations = extract_relations(root, skills, resources)

    for skill in skills:
        _write_skill_concept(output, skill, relations)
    _write_relation_concepts(output, relations)
    _write_resource_concepts(output, resources)

    manifest = [
        "---",
        "type: AgentSkillsProjection",
        f"skill_count: {len(skills)}",
        f"relation_count: {len(relations)}",
        f"resolved_relation_count: {sum(relation.resolved for relation in relations)}",
        f"resource_count: {len(resources)}",
        "---",
        "",
        "# Agent Skills projection",
        "",
        "Derived inspection bundle. Edit the source skills, not this directory.",
        "",
    ]
    (output / "projection.md").write_text("\n".join(manifest), encoding="utf-8")
    return skills, relations


app = cyclopts.App(name="project-agent-skills", help=__doc__)


@app.default
def main(source: Path, output: Path) -> int:
    """Project the tree into an OKF bundle.

    Parameters
    ----------
    source
        Agent Skills repository/root.
    output
        Disposable OKF output directory.
    """
    skills, relations = project(source, output)
    resolved = sum(relation.resolved for relation in relations)
    print(f"projected {len(skills)} skills, {len(relations)} local links ({resolved} projected)")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
