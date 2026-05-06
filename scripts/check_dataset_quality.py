#!/usr/bin/env python3
"""Run shortcut-oriented quality checks for the FinRegBench draft dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


LABELS = ("entailment", "contradiction", "neutral")
NEUTRAL_QUERY_MARKERS = (
    "specific implementation channel",
    "exact vendor or platform",
    "named submission portal",
    "mandatory font size",
    "specific email address",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--min-neutral-unique",
        type=int,
        default=None,
        help=(
            "Minimum number of unique neutral candidate answers. Defaults to "
            "90 percent of the neutral row count, capped at the old 900-row "
            "threshold for the 3,000-row draft."
        ),
    )
    parser.add_argument("--max-old-shortcut-accuracy", type=float, default=0.75)
    args = parser.parse_args()

    rows = read_jsonl(args.path)
    by_label = {label: [row for row in rows if row.get("label") == label] for label in LABELS}
    errors = []

    label_counts = Counter(row.get("label") for row in rows)
    missing_labels = [label for label in LABELS if label_counts[label] == 0]
    if missing_labels:
        errors.append(f"missing labels: {missing_labels}")

    exact_entailment = sum(
        1 for row in by_label["entailment"]
        if row.get("candidate_answer") == row.get("evidence_span")
    )
    if exact_entailment:
        errors.append(f"{exact_entailment} entailment rows copy evidence_span exactly")

    neutral_answers = {row.get("candidate_answer") for row in by_label["neutral"]}
    min_neutral_unique = (
        args.min_neutral_unique
        if args.min_neutral_unique is not None
        else min(900, int(0.9 * len(by_label["neutral"])))
    )
    if len(neutral_answers) < min_neutral_unique:
        errors.append(
            f"neutral candidate answers are under-diverse: "
            f"{len(neutral_answers)} < {min_neutral_unique}"
        )

    neutral_marker_hits = sum(
        1 for row in rows
        if any(marker in str(row.get("query", "")).lower() for marker in NEUTRAL_QUERY_MARKERS)
    )
    if neutral_marker_hits:
        errors.append(f"{neutral_marker_hits} rows contain old neutral-only query markers")

    shortcut_correct = 0
    for row in rows:
        if row.get("candidate_answer") == row.get("evidence_span"):
            predicted = "entailment"
        elif row.get("candidate_answer") in neutral_answers:
            predicted = "neutral"
        else:
            predicted = "contradiction"
        shortcut_correct += int(predicted == row.get("label"))

    old_shortcut_accuracy = shortcut_correct / len(rows) if rows else 0.0
    if old_shortcut_accuracy > args.max_old_shortcut_accuracy:
        errors.append(
            f"old shortcut baseline is too strong: "
            f"{old_shortcut_accuracy:.4f} > {args.max_old_shortcut_accuracy:.4f}"
        )

    summary = {
        "rows": len(rows),
        "labels": dict(label_counts),
        "exact_entailment_copies": exact_entailment,
        "neutral_unique_candidate_answers": len(neutral_answers),
        "neutral_query_marker_hits": neutral_marker_hits,
        "old_shortcut_baseline_accuracy": round(old_shortcut_accuracy, 4),
        "unique_candidate_answers_by_label": {
            label: len({row.get("candidate_answer") for row in label_rows})
            for label, label_rows in by_label.items()
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if errors:
        for error in errors:
            print(f"error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
