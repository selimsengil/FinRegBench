# Academic Release Plan

## Contribution Framing

A strong framing is:

> We introduce FinRegBench, a synthetic-but-evidence-grounded benchmark for
> evaluating retrieval, abstention, and answer verification in financial
> regulation RAG systems.

Avoid claiming that the current draft is a fully human-authored legal QA
dataset unless the review process has actually been completed.

## Suggested Paper Structure

1. Motivation: financial regulation RAG needs grounded answers and abstention.
2. Dataset: source documents, label taxonomy, generation process, review process.
3. Methods: retrievers, chunking, verifier models, gating.
4. Metrics: retrieval, verification, and end-to-end metrics.
5. Experiments: baselines, ablations, oracle-evidence analysis.
6. Error analysis: retrieval misses, verifier label confusions, poor evidence spans.
7. Limitations: synthetic generation, legal risk, source-document coverage.
8. Release: schema, scripts, source hashes, license notes.

## GPT / LLM Disclosure Template

Use wording like:

> Candidate question-answer pairs were generated with LLM assistance using
> source regulatory passages as grounding material. Each generated item preserves
> source document metadata, page references, and an evidence span. We then
> applied automatic filtering and a stratified human validation pass before
> finalizing the benchmark.

If the benchmark has not yet been reviewed, write:

> The current dataset is a draft synthetic benchmark and is not intended for
> legal interpretation or compliance advice.

## Release Checklist

- Dataset schema documented.
- Source-document versions and hashes documented.
- Development and test splits frozen.
- Human review protocol documented.
- At least one baseline result reported.
- Retrieval and verification metrics reported separately.
- Failure cases discussed honestly.

## Recommended Publication Path

- GitHub: code, documentation, schema, sample review files.
- Hugging Face Datasets: dataset release.
- Zenodo: archived version with DOI.
