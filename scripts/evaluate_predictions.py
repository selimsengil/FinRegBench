#!/usr/bin/env python3
"""Evaluate 3-way FinRegBench predictions."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LABELS = ["entailment", "contradiction", "neutral"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()

    gold_rows = read_jsonl(args.gold)
    prediction_rows = read_jsonl(args.predictions)

    gold_by_id = {row["id"]: row["label"] for row in gold_rows}
    predictions_by_id = {}
    for row in prediction_rows:
        if "id" not in row or "predicted_label" not in row:
            raise SystemExit("Each prediction row must contain 'id' and 'predicted_label'.")
        predictions_by_id[row["id"]] = row["predicted_label"]

    missing = sorted(set(gold_by_id) - set(predictions_by_id))
    extra = sorted(set(predictions_by_id) - set(gold_by_id))
    if missing:
        print(f"warning: {len(missing)} missing predictions")
    if extra:
        print(f"warning: {len(extra)} extra predictions ignored")

    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    total = 0
    correct = 0

    for row_id, gold_label in gold_by_id.items():
        predicted_label = predictions_by_id.get(row_id)
        if predicted_label not in LABELS:
            predicted_label = "missing_or_invalid"
        confusion[gold_label][predicted_label] += 1
        total += 1
        correct += int(predicted_label == gold_label)

    per_class = {}
    f1_values = []
    for label in LABELS:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[other][label] for other in LABELS if other != label)
        false_negative = sum(count for predicted, count in confusion[label].items() if predicted != label)
        precision = safe_divide(true_positive, true_positive + false_positive)
        recall = safe_divide(true_positive, true_positive + false_negative)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        f1_values.append(f1)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(confusion[label].values()),
        }

    result = {
        "accuracy": safe_divide(correct, total),
        "macro_f1": sum(f1_values) / len(f1_values),
        "total": total,
        "correct": correct,
        "per_class": per_class,
        "confusion_matrix": {label: dict(confusion[label]) for label in LABELS},
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
