#!/usr/bin/env python3
"""Prepare and aggregate repeated routing benchmark observations.

This helper never invokes a model. It turns official-style
*/evals/eval_queries.json corpora into a deterministic run manifest and
aggregates observations produced by an external behavioral runner.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

EXECUTION_OBSERVED = "observed"
EXECUTION_ERROR = "error"
EXECUTION_STATUSES = {EXECUTION_OBSERVED, EXECUTION_ERROR}


def load_cases(root: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for skill_file in sorted(root.glob("*/SKILL.md")):
        skill = skill_file.parent.name
        eval_file = skill_file.parent / "evals" / "eval_queries.json"
        if not eval_file.exists():
            continue
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{eval_file}: expected JSON array")
        for index, case in enumerate(data, start=1):
            if not isinstance(case, dict):
                raise ValueError(f"{eval_file}: case {index} must be object")
            query = case.get("query")
            expected = case.get("should_trigger")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"{eval_file}: case {index} needs non-empty query")
            if not isinstance(expected, bool):
                raise ValueError(f"{eval_file}: case {index} needs boolean should_trigger")
            cases.append(
                {
                    "skill": skill,
                    "case_index": index,
                    "query": query.strip(),
                    "should_trigger": expected,
                    "source_path": eval_file.relative_to(root).as_posix(),
                }
            )
    return cases


def make_manifest(root: Path, repetitions: int) -> list[dict[str, object]]:
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")
    rows: list[dict[str, object]] = []
    for case in load_cases(root):
        for repetition in range(1, repetitions + 1):
            rows.append(
                {
                    **case,
                    "repetition": repetition,
                    "observed_trigger": None,
                }
            )
    return rows


def write_jsonl(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _validate_observation(row: dict[str, object], path: Path, line_no: int) -> None:
    expected = row.get("should_trigger")
    if not isinstance(expected, bool):
        raise ValueError(f"{path}:{line_no}: should_trigger must be boolean")

    status = row.get("execution_status", EXECUTION_OBSERVED)
    if status not in EXECUTION_STATUSES:
        raise ValueError(
            f"{path}:{line_no}: execution_status must be one of {sorted(EXECUTION_STATUSES)}"
        )

    observed = row.get("observed_trigger")
    if status == EXECUTION_OBSERVED:
        if not isinstance(observed, bool):
            raise ValueError(
                f"{path}:{line_no}: observed execution requires boolean observed_trigger"
            )
    elif observed is not None:
        raise ValueError(
            f"{path}:{line_no}: failed execution must not contain observed_trigger"
        )

    for field in ("runner", "model", "error_type", "error_message"):
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{path}:{line_no}: {field} must be string when present")


def load_observations(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        _validate_observation(row, path, line_no)
        if "execution_status" not in row:
            row["execution_status"] = EXECUTION_OBSERVED
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    per_case: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        skill = row.get("skill")
        case_index = row.get("case_index")
        if not isinstance(skill, str) or not isinstance(case_index, int):
            raise ValueError("each observation needs skill:string and case_index:int")
        per_case[(skill, case_index)].append(row)

    cases: list[dict[str, object]] = []
    tp = tn = fp = fn = 0
    attempted = completed = failed = 0
    for (skill, case_index), observations in sorted(per_case.items()):
        expected = bool(observations[0]["should_trigger"])
        successful = [
            row
            for row in observations
            if row.get("execution_status", EXECUTION_OBSERVED) == EXECUTION_OBSERVED
        ]
        failures = len(observations) - len(successful)
        triggers = sum(bool(row["observed_trigger"]) for row in successful)
        runs = len(successful)
        attempted += len(observations)
        completed += runs
        failed += failures

        trigger_rate: float | None = triggers / runs if runs else None
        predicted: bool | None = trigger_rate >= 0.5 if trigger_rate is not None else None
        outcome: str | None = None
        if predicted is not None:
            if expected and predicted:
                tp += 1
                outcome = "true_positive"
            elif expected and not predicted:
                fn += 1
                outcome = "false_negative"
            elif not expected and predicted:
                fp += 1
                outcome = "false_positive"
            else:
                tn += 1
                outcome = "true_negative"
        cases.append(
            {
                "skill": skill,
                "case_index": case_index,
                "should_trigger": expected,
                "attempted_runs": len(observations),
                "completed_runs": runs,
                "failed_runs": failures,
                "trigger_count": triggers,
                "trigger_rate": round(trigger_rate, 4) if trigger_rate is not None else None,
                "majority_trigger": predicted,
                "outcome": outcome,
            }
        )

    total = tp + tn + fp + fn
    positives = tp + fn
    negatives = tn + fp
    return {
        "summary": {
            "attempted_runs": attempted,
            "completed_runs": completed,
            "failed_runs": failed,
            "classified_cases": total,
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "accuracy": round((tp + tn) / total, 4) if total else None,
            "recall": round(tp / positives, 4) if positives else None,
            "specificity": round(tn / negatives, 4) if negatives else None,
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="create repeated-run JSONL manifest")
    manifest.add_argument("source", type=Path)
    manifest.add_argument("output", type=Path)
    manifest.add_argument("--repetitions", type=int, default=5)

    agg = sub.add_parser("aggregate", help="aggregate completed/error observation JSONL")
    agg.add_argument("observations", type=Path)
    agg.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "manifest":
        rows = make_manifest(args.source.resolve(), args.repetitions)
        write_jsonl(rows, args.output)
        print(f"wrote {len(rows)} benchmark runs to {args.output}")
        return 0

    result = aggregate(load_observations(args.observations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
