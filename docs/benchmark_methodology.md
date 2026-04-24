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
   - supported answers copied or lightly normalized from evidence,
   - contradicted answers produced with controlled mutations,
   - neutral answers containing details not stated in the evidence.
5. Attach source document, page, evidence span, and generation metadata.
6. Split examples into development and test partitions.

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

## Why Oracle Evidence Matters

If the verifier fails even when given the gold evidence span, the verifier is the
main bottleneck. If oracle verification works but retrieved-evidence verification
fails, the retriever or chunking strategy is the bottleneck.
