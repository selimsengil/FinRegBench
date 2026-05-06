# How To Apply FinRegBench

FinRegBench is used to evaluate whether a RAG system can verify regulatory
answers against source documents.

The core unit is one JSONL row:

```json
{
  "id": "...",
  "query": "What does the Basel Framework state regarding ...?",
  "candidate_answer": "...",
  "label": "entailment",
  "source_pages": [123],
  "evidence_span": "..."
}
```

Your system receives the `query` and `candidate_answer`. It should retrieve
evidence from the regulation PDFs and output a predicted label.

## Label Meaning

- `entailment`: the candidate answer is supported by the retrieved evidence.
- `contradiction`: the candidate answer conflicts with the retrieved evidence.
- `neutral`: the retrieved evidence is insufficient, so the system should abstain.

For an unsupported-answer risk detector, treat only `entailment` as safe. Treat
both `neutral` and `contradiction` as risk signals, with a useful scalar score:

```text
unsupported_risk = P(neutral) + P(contradiction)
```

## Recommended Evaluation Modes

### 1. Oracle Verification

Use the gold `evidence_span` directly as the context.

This mode tests the verifier only. Retrieval is bypassed.

If accuracy is low here, the verifier model or label mapping is the bottleneck.

### 2. Retrieval Evaluation

Use only the `query` to retrieve chunks from `source_documents/raw/`.

Check whether the retrieved chunks include the correct page or evidence.

Useful metrics:

- `Hit@1`
- `Hit@5`
- `Recall@k`
- `MRR`
- source page accuracy

### 3. Full RAG Verification

Use the normal system:

1. Chunk and index the PDFs.
2. Retrieve chunks using `query`.
3. Pass retrieved chunks, `query`, and `candidate_answer` to the verifier.
4. Predict `entailment`, `contradiction`, or `neutral`.
5. Compare with the gold `label`.

Before reporting results, also run:

```bash
python3 scripts/check_dataset_quality.py data/finreg_3000_draft.jsonl
```

This is the realistic benchmark setting.

## Expected Prediction File

`scripts/evaluate_predictions.py` expects one JSON object per line:

```json
{"id": "finreg3000_entailment_0001_...", "predicted_label": "entailment"}
```

Valid labels:

- `entailment`
- `contradiction`
- `neutral`

Run:

```bash
python3 scripts/evaluate_predictions.py \
  --gold data/finreg_3000_draft.jsonl \
  --predictions predictions/my_system.jsonl
```

## What A Good System Should Show

Report at least:

- overall accuracy,
- macro F1,
- per-label precision and recall,
- confusion matrix.

For RAG, do not stop there. Also report retrieval quality separately. Otherwise
it is impossible to know whether errors come from bad retrieval or bad
verification.

## Practical Interpretation

Example:

- Gold label: `contradiction`
- System predicts: `entailment`

Meaning: the system accepted a wrong regulatory answer as true. In financial
regulation, this is usually the most dangerous failure mode.

Example:

- Gold label: `entailment`
- System predicts: `neutral`

Meaning: the system failed to use available evidence. This is conservative but
less useful.

Example:

- Gold label: `neutral`
- System predicts: `entailment`

Meaning: the system hallucinated support for an answer that the regulation text
does not actually establish.
