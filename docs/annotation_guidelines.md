# Annotation Guidelines

Use these guidelines when manually reviewing or correcting FinRegBench examples.

## Label Definitions

### Entailment

Choose `entailment` when the candidate answer is clearly supported by the
evidence span.

The wording does not need to be identical, but the meaning must match.

### Contradiction

Choose `contradiction` when the candidate answer makes a claim that conflicts
with the evidence span.

Typical contradiction types:

- numeric value changed,
- obligation changed into permission,
- permission changed into prohibition,
- required condition removed or reversed,
- exception stated as the general rule.

### Neutral

Choose `neutral` when the answer may be plausible but the evidence span does not
state enough information to verify it.

Neutral is not the same as false. It means "not enough information from this
evidence."

## Review Rules

- Mark awkward or ungrammatical questions for rewrite.
- Remove examples where the evidence span is too noisy to support a decision.
- Remove examples where the label depends on external legal knowledge.
- Prefer short, precise regulatory questions.
- Keep page and evidence metadata stable when editing text.

## Review Status Values

Suggested values:

- `auto_generated_needs_human_review`
- `human_reviewed_keep`
- `human_reviewed_rewrite`
- `human_reviewed_remove`

## Minimum Review Plan

For a draft academic release:

- Review 300 examples.
- Use 100 examples per label.
- Include both source documents.

For a stronger release:

- Review the full development split.
- Double-review at least 10 percent of the test split.
- Report agreement between reviewers.
