#!/usr/bin/env python3
"""Validate the FinRegBench JSONL schema."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "split",
    "task",
    "label",
    "expected_label",
    "query",
    "candidate_answer",
    "doc_id",
    "doc_title",
    "jurisdiction",
    "source_path",
    "source_pages",
    "evidence_span",
    "topic",
    "ambiguity_type",
    "difficulty",
    "generation_method",
    "quality_score",
    "review_status",
}

VALID_LABELS = {"entailment", "contradiction", "neutral"}
VALID_SPLITS = {"dev", "test"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            rows.append(row)
    return rows


def validate_row(row: dict[str, Any], line_number: int) -> list[str]:
    errors = []
    missing = REQUIRED_FIELDS - set(row)
    if missing:
        errors.append(f"line {line_number}: missing fields: {sorted(missing)}")

    label = row.get("label")
    expected_label = row.get("expected_label")
    if label not in VALID_LABELS:
        errors.append(f"line {line_number}: invalid label: {label!r}")
    if expected_label != label:
        errors.append(f"line {line_number}: expected_label does not match label")
    if row.get("split") not in VALID_SPLITS:
        errors.append(f"line {line_number}: invalid split: {row.get('split')!r}")
    if not isinstance(row.get("query"), str) or not row.get("query", "").strip():
        errors.append(f"line {line_number}: query must be a non-empty string")
    if not isinstance(row.get("candidate_answer"), str) or not row.get("candidate_answer", "").strip():
        errors.append(f"line {line_number}: candidate_answer must be a non-empty string")
    if not isinstance(row.get("source_pages"), list) or not row.get("source_pages"):
        errors.append(f"line {line_number}: source_pages must be a non-empty list")
    if not isinstance(row.get("quality_score"), (int, float)):
        errors.append(f"line {line_number}: quality_score must be numeric")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    rows = read_jsonl(args.path)
    errors = []
    seen_ids = set()

    for index, row in enumerate(rows, start=1):
        row_id = row.get("id")
        if row_id in seen_ids:
            errors.append(f"line {index}: duplicate id: {row_id}")
        seen_ids.add(row_id)
        errors.extend(validate_row(row, index))

    if errors:
        for error in errors[:50]:
            print(error)
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
        raise SystemExit(1)

    summary = {
        "rows": len(rows),
        "labels": dict(Counter(row["label"] for row in rows)),
        "splits": dict(Counter(row["split"] for row in rows)),
        "documents": dict(Counter(row["doc_id"] for row in rows)),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
