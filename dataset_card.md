# Dataset Card: FinRegBench Draft

## Dataset Summary

FinRegBench is a draft financial regulation benchmark for evaluating RAG systems
on answer verification and abstention. Each item pairs a regulatory question
with a candidate answer and an expected 3-way label.

## Intended Tasks

- Financial regulation RAG evaluation
- Evidence retrieval evaluation
- Answer verification / hallucination detection
- Abstention testing for underspecified or unsupported answers

## Labels

- `entailment`: answer is supported by the cited regulatory evidence.
- `contradiction`: answer is contradicted by the cited regulatory evidence.
- `neutral`: the evidence does not contain enough information to verify the answer.
  For RAG gating, neutral is an unsupported-answer risk rather than a safe answer.

## Current Composition

- Main draft examples: 3,000
- `entailment`: 1,000
- `contradiction`: 1,000
- `neutral`: 1,000
- Basel Framework examples: 2,700
- Consumer Credit Protection Act examples: 300
- Supported answers are reframed rather than copied exactly from the evidence.
- Neutral answers are generated from topic-conditioned unsupported details rather
  than a small fixed answer list.

## Heldout Test Set

The repository also includes `data/finreg_heldout_cbe_test.jsonl`, a separate
900-example test set generated only from the Federal Reserve Commercial Bank
Examination Manual:

- `entailment`: 300
- `contradiction`: 300
- `neutral`: 300
- split: `test` only
- document: `fed_cbe_manual`

This heldout file is intended for unseen-document generalization checks. Do not
train on it and do not use it for checkpoint selection. Its neutral examples mix
same-document distractor passages with partially supported answers that append
unstated requirements, so the candidate answer may be plausible or partly
grounded while remaining unsupported by the cited evidence span.

## Source Documents

The current repository includes the source PDFs used to construct the draft and
heldout test:

- `source_documents/raw/BaselFramework.pdf`
- `source_documents/raw/Commercial Bank Examination.pdf`
- `source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf`

Official source URLs and checksums are documented in
`source_documents/README.md`.

## Data Fields

- `id`: stable example identifier
- `split`: `dev` or `test`
- `task`: task name
- `query`: user-style question
- `candidate_answer`: answer to be verified
- `label`: expected 3-way label
- `expected_label`: duplicate label field for compatibility with older scripts
- `doc_id`: source document identifier
- `doc_title`: source document title
- `jurisdiction`: jurisdiction or regulatory scope
- `source_path`: expected local source PDF path
- `source_pages`: source page list
- `evidence_span`: source sentence or passage used during generation
- `topic`: extracted topic phrase
- `ambiguity_type`: ambiguity category when relevant
- `difficulty`: coarse difficulty estimate
- `generation_method`: how the item was generated
- `quality_score`: automatic heuristic score
- `review_status`: review state

## Known Limitations

- The current benchmark is automatically generated.
- Some questions may be awkward, overly broad, or too close to the source text.
- Some contradiction examples are rule-mutated and may require human cleanup.
- Neutral examples test unsupported-detail abstention, not every type of ambiguity.
- Heldout neutral examples are still automatically generated and require human
  review before academic reporting.
- The generator reduces obvious shortcut patterns but does not replace human
  validation or adversarial evaluation.
- The benchmark is not legal advice and should not be used for compliance decisions.

## Recommended Validation

Before publication, perform a stratified human review of at least 300 examples.
For a stronger academic release, use two reviewers and report agreement.

## Disclosure

Candidate examples were generated from source regulatory passages using an
automated construction pipeline. If LLM assistance is used during further
cleanup or expansion, disclose the model, prompting strategy, and review process.
