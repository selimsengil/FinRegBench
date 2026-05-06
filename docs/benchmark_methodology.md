# Benchmark Methodology

## Goal

FinRegBench is designed to test whether a financial regulation RAG system can:

- retrieve relevant regulatory evidence,
- avoid answering when evidence is insufficient,
- detect when a candidate answer contradicts the retrieved evidence,
- separate retrieval quality from verifier quality.

## Construction Pipeline

1. Extract text from official regulatory PDFs.
2. Split extracted text into candidate evidence sentences.
3. Score candidate evidence using regulatory keywords and length heuristics.
4. Generate three example types:
   - supported answers reframed from evidence without exact evidence copying,
   - contradicted answers produced with controlled mutations and the same answer
     framing style used for supported answers,
   - neutral answers containing topic-conditioned details not stated in the
     evidence.
5. Attach source document, page, evidence span, and generation metadata.
6. Split examples into development and test partitions.
7. Run shortcut-oriented quality checks for exact evidence copying, old
   neutral-only query markers, neutral answer diversity, and exact evidence
   leakage across splits.

## Heldout Document Construction

`data/finreg_heldout_cbe_test.jsonl` is built from the Federal Reserve
Commercial Bank Examination Manual only. It is generated as a `test`-only file
and is intended for final unseen-document evaluation.

The heldout set keeps the same `entailment` and `contradiction` construction
style as the main draft. Its `neutral` rows mix two harder patterns:
same-document distractor passages and partially supported answers that append an
unstated requirement to an otherwise grounded claim. This makes the neutral
class closer to realistic RAG failures where retrieval or verification sees
plausible regulatory text but not enough evidence for the full answer.

## Evaluation Layers

Evaluate the system in separate layers rather than with one blended score.

### Retrieval

Use the query to retrieve passages from the regulation corpus.

Suggested metrics:

- `Hit@1`
- `Hit@5`
- `Recall@k`
- `MRR`
- source page accuracy

### Verification

Given query, candidate answer, and retrieved evidence, predict one of:

- `entailment`
- `contradiction`
- `neutral`

For abstention-oriented RAG gates, `neutral` and `contradiction` are both risk
classes: `contradiction` means the answer conflicts with evidence, while
`neutral` means the evidence is insufficient to support the answer.

Suggested metrics:

- accuracy
- macro F1
- per-class precision
- per-class recall
- confusion matrix
- neutral recall

### End-To-End RAG

For a complete RAG system, also report:

- final answer correctness
- groundedness
- citation correctness
- abstention rate
- false-answer rate

## Baselines

Recommended baselines:

- BM25 or lexical retrieval plus NLI verifier
- dense retrieval plus NLI verifier
- hybrid retrieval plus NLI verifier
- generation-only model without verification
- oracle-evidence verifier upper bound
- unsupported-answer risk detector using `P(neutral) + P(contradiction)`
- unseen-document heldout evaluation using `data/finreg_heldout_cbe_test.jsonl`

## Why Oracle Evidence Matters

If the verifier fails even when given the gold evidence span, the verifier is the
main bottleneck. If oracle verification works but retrieved-evidence verification
fails, the retriever or chunking strategy is the bottleneck.
