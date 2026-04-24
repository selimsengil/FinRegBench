# FinRegBench

FinRegBench is a draft benchmark for testing retrieval, abstention, and answer
verification in financial regulation RAG systems.

The current release contains 3,000 synthetic-but-evidence-grounded examples
derived from two public regulatory documents:

- Basel Framework: 2,700 examples
- Consumer Credit Protection Act: 300 examples

Each example contains a user-style regulatory question, a candidate answer, a
3-way verification label, and source evidence metadata.

## Status

This repository is currently a draft benchmark workspace, not a final academic
dataset release.

The generated examples are useful for development and stress-testing, but a
stratified human review pass is required before presenting this as a polished
benchmark.

## Labels

- `entailment`: the candidate answer is supported by the source evidence.
- `contradiction`: the candidate answer conflicts with the source evidence.
- `neutral`: the source evidence does not provide enough information.

## Repository Layout

```text
FinRegBench/
  data/
    finreg_3000_draft.jsonl
    finreg_3000_draft_summary.json
    sample_60_for_review.jsonl
  docs/
    annotation_guidelines.md
    benchmark_methodology.md
    academic_release_plan.md
  scripts/
    build_benchmark.py
    validate_schema.py
    evaluate_predictions.py
  source_documents/
    README.md
```

## Quick Start

Validate the dataset schema:

```bash
python3 scripts/validate_schema.py data/finreg_3000_draft.jsonl
```

Evaluate model predictions:

```bash
python3 scripts/evaluate_predictions.py \
  --gold data/finreg_3000_draft.jsonl \
  --predictions path/to/predictions.jsonl
```

The predictions file should contain one JSON object per line with:

```json
{"id": "example_id", "predicted_label": "entailment"}
```

## Source Documents

The source PDFs are not committed by default. See
`source_documents/README.md` for official URLs and expected checksums.

## Academic Use

For academic use, do not report the current file as a fully validated human QA
dataset. Report it as a reproducible benchmark construction pipeline plus a
draft synthetic benchmark unless human validation has been completed.

Recommended before release:

- Review at least 300 examples, balanced by label and source document.
- Freeze a test split that is not used for tuning.
- Report inter-annotator agreement if more than one reviewer is involved.
- Publish exact source-document versions and hashes.
- Report retrieval and verification metrics separately.
