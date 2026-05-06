#!/usr/bin/env python3
"""
Build a 3,000-example financial regulation answer-verification benchmark.

The output is a draft benchmark intended for systematic review. Each example
contains a question, a candidate answer, a 3-way label, and source evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader


STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by",
    "is", "are", "was", "were", "be", "been", "being", "it", "its", "that",
    "this", "these", "those", "as", "at", "from", "into", "than", "then", "if",
    "when", "where", "which", "who", "whom", "what", "why", "how", "under",
    "over", "only", "other", "must", "may", "can", "could", "should", "would",
    "does", "do", "did", "not", "no", "any", "all", "each", "such", "their",
    "there", "where", "within", "between", "into", "onto", "than", "also",
    "shall", "will", "bank", "banks", "framework", "section", "chapter",
    "furthermore", "therefore", "however", "including", "include", "includes",
    "sets", "set", "out", "various", "approach", "approaches", "following",
    "described", "paragraph", "table", "annex", "footnote",
}

QUALITY_KEYWORDS = {
    "must", "shall", "required", "requirement", "should", "may", "not", "only",
    "minimum", "maximum", "capital", "risk", "exposure", "disclosure", "ratio",
    "supervisory", "credit", "liquidity", "leverage", "eligible", "criteria",
    "assets", "liabilities", "authority", "consumer", "creditor", "transaction",
}

QUESTION_TEMPLATES = [
    "According to {doc_title}, what does the text say about {topic}?",
    "Under {doc_title}, what requirement applies to {topic}?",
    "What does {doc_title} state regarding {topic}?",
    "For {topic}, what position does {doc_title} set out?",
    "How does {doc_title} describe the rule for {topic}?",
    "What should a reader conclude from {doc_title} about {topic}?",
    "What is the relevant regulatory treatment of {topic} in {doc_title}?",
    "How is {topic} addressed in {doc_title}?",
]

ANSWER_FRAMES = [
    "The relevant provision states that {claim}.",
    "The text indicates that {claim}.",
    "The rule provides that {claim}.",
    "The cited material says that {claim}.",
    "The passage supports the statement that {claim}.",
]

UNSUPPORTED_ACTORS = [
    "institutions",
    "covered entities",
    "regulated firms",
    "reporting banks",
    "compliance officers",
    "senior management",
    "supervised firms",
]

UNSUPPORTED_ACTIONS = [
    "submit a certified implementation memo",
    "file a board-approved attestation",
    "use a regulator-hosted intake form",
    "retain a named external auditor",
    "publish a customer-facing notice",
    "send a machine-readable compliance report",
    "obtain written supervisory pre-clearance",
    "maintain a transaction-level exception log",
    "complete an annual technology certification",
    "provide a reconciliation workbook",
]

UNSUPPORTED_CHANNELS = [
    "through the supervisory reporting portal",
    "by encrypted email to the competent authority",
    "using a prescribed XML schema",
    "through a board governance pack",
    "via a secure case-management system",
    "in a regulator-approved spreadsheet template",
    "through a public disclosure archive",
    "using a named third-party compliance platform",
]

UNSUPPORTED_TIMINGS = [
    "within one business day",
    "within five calendar days",
    "before the end of each quarter",
    "no later than the next supervisory review",
    "within 30 days of a material change",
    "before the relevant exposure is booked",
    "at least annually",
    "within ten working days",
]

UNSUPPORTED_AUTHORITIES = [
    "the chief compliance officer",
    "the board risk committee",
    "an external legal reviewer",
    "the internal audit function",
    "the chief technology officer",
    "a designated senior manager",
    "the model risk committee",
    "the disclosure control officer",
]

UNSUPPORTED_RECORDS = [
    "a signed certificate",
    "an audit trail reference",
    "a digital seal",
    "a version-controlled policy appendix",
    "a unique submission identifier",
    "a customer notification record",
    "a supervisory acknowledgement receipt",
    "a management escalation note",
]
DOCS = [
    {
        "doc_id": "basel_framework",
        "doc_title": "the Basel Framework",
        "jurisdiction": "international",
        "source_path": "source_documents/raw/BaselFramework.pdf",
        "target_per_label": 900,
    },
    {
        "doc_id": "ccpa",
        "doc_title": "the Consumer Credit Protection Act",
        "jurisdiction": "US",
        "source_path": "source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf",
        "target_per_label": 100,
    },
]

HELDOUT_DOCS = [
    {
        "doc_id": "fed_cbe_manual",
        "doc_title": "the Federal Reserve Commercial Bank Examination Manual",
        "jurisdiction": "US",
        "source_path": "source_documents/raw/Commercial Bank Examination.pdf",
        "target_per_label": 300,
    },
]


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    doc_title: str
    jurisdiction: str
    source_path: str
    page: int
    text: str
    topic: str
    quality_score: float


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"Downloaded on \d{2}\.\d{2}\.\d{4} at \d{2}:\d{2} CET", "", text)
    text = re.sub(r"^\d+\s*/\s*\d+\s*", "", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z(0-9])", text)
    return [clean_text(piece) for piece in pieces if piece.strip()]


def content_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
        if token not in STOPWORDS
    ]


def topic_from_text(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"^[A-Z]{2,}\d+(?:\.\d+)?\s*", "", text)
    text = re.sub(r"^\(?\d+[a-z]?\)?\s*", "", text)
    text = re.sub(r"^(Furthermore|Therefore|However|In addition|For example),?\s+", "", text, flags=re.I)

    patterns = [
        r"\bfor\s+([^,.]{18,110}?)(?:\s+where|\s+when|,|\.|$)",
        r"\bif\s+([^,.]{18,110}?)(?:,|\s+then|\.|$)",
        r"\bthe\s+([^,.]{18,110}?)(?:\s+is\b|\s+are\b|\s+must\b|\s+shall\b|\s+should\b|\s+may\b|\s+will\b)",
        r"\bbanks?\s+(?:must|should|may|shall|are required to)\s+([^,.]{18,110}?)(?:,|\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue
        phrase = clean_topic_phrase(match.group(1))
        if phrase:
            return phrase

    counts: Counter[str] = Counter(content_tokens(text))
    tokens = [token for token, _ in counts.most_common(5)]
    if not tokens:
        return "the relevant requirement"
    return " ".join(tokens[:4])


def clean_topic_phrase(phrase: str) -> str:
    phrase = clean_text(phrase)
    phrase = re.sub(r"^[\"'`(]+|[\"'`).,:;]+$", "", phrase)
    phrase = re.sub(r"\b(SCO|CAP|CRE|MAR|LCR|NSF|DIS|SRP|RBC)\d+(?:\.\d+)?\b", "", phrase)
    words = [word for word in phrase.split() if content_tokens(word)]
    phrase = " ".join(words[:10]).strip()
    if len(phrase) < 12:
        return ""
    return phrase


def quality_score(sentence: str) -> float:
    tokens = content_tokens(sentence)
    score = 0.0
    score += min(len(tokens) / 24.0, 1.0)
    score += 0.15 * sum(1 for token in tokens if token in QUALITY_KEYWORDS)
    score += 0.20 if re.search(r"\b\d+(\.\d+)?\s*(%|percent|days?|months?|years?|basis points?)\b", sentence, re.I) else 0.0
    score += 0.20 if re.search(r"\b(must|shall|required|should|may not|must not|shall not)\b", sentence, re.I) else 0.0
    score -= 0.35 if "................................................................" in sentence else 0.0
    score -= 0.25 if sentence.count(".") > 4 else 0.0
    return score


def is_candidate_sentence(sentence: str) -> bool:
    if not 80 <= len(sentence) <= 420:
        return False
    if len(content_tokens(sentence)) < 9:
        return False
    if re.search(r"\.{5,}", sentence):
        return False
    if not re.search(r"[A-Za-z]", sentence):
        return False
    if quality_score(sentence) < 0.55:
        return False
    return True


def extract_evidence(doc: dict[str, Any]) -> list[Evidence]:
    reader = PdfReader(doc["source_path"])
    evidence: list[Evidence] = []

    for page_no, page in enumerate(reader.pages, start=1):
        page_text = clean_text(page.extract_text() or "")
        if len(page_text) < 200:
            continue
        for sentence in split_sentences(page_text):
            if not is_candidate_sentence(sentence):
                continue
            evidence.append(
                Evidence(
                    doc_id=doc["doc_id"],
                    doc_title=doc["doc_title"],
                    jurisdiction=doc["jurisdiction"],
                    source_path=doc["source_path"],
                    page=page_no,
                    text=sentence,
                    topic=topic_from_text(sentence),
                    quality_score=quality_score(sentence),
                )
            )

    evidence.sort(key=lambda row: row.quality_score, reverse=True)
    return evidence


def mutate_number(text: str) -> str | None:
    priority_patterns = [
        r"\b(\d+(?:\.\d+)?)\s*(%|percent|days?|business days?|months?|years?|basis points?|per centum|hours?)\b",
        r"\b(\d+)\s*/\s*(\d+)\b",
    ]
    for pattern in priority_patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return replace_numeric_match(text, match)

    matches = list(re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", text))
    match = next((item for item in matches if item.start() > 30), None)
    if match is None:
        return None

    return replace_numeric_match(text, match)


def replace_numeric_match(text: str, match: re.Match[str]) -> str:
    original = match.group(1)
    value = float(original)
    if value == 0:
        replacement = "1"
    elif value < 10:
        replacement = str(int(value + 2)) if value.is_integer() else f"{value + 1.0:.1f}"
    else:
        replacement = str(int(round(value * 1.5)))

    return text[:match.start()] + replacement + text[match.end():]


def mutate_obligation(text: str) -> str | None:
    replacements = [
        (r"\bmust not\b", "must"),
        (r"\bshall not\b", "shall"),
        (r"\bmay not\b", "may"),
        (r"\bmust\b", "must not"),
        (r"\bshall\b", "shall not"),
        (r"\brequired to\b", "not required to"),
        (r"\bis required\b", "is not required"),
        (r"\bare required\b", "are not required"),
        (r"\bshould\b", "should not"),
        (r"\bmay\b", "may not"),
        (r"\bdoes not\b", "does"),
        (r"\bdo not\b", "do"),
        (r"\bis not\b", "is"),
        (r"\bare not\b", "are"),
    ]
    for pattern, replacement in replacements:
        if re.search(pattern, text, flags=re.I):
            return re.sub(pattern, replacement, text, count=1, flags=re.I)
    return None


def mutate_contradiction(text: str) -> str:
    mutation = mutate_number(text)
    if mutation and mutation != text:
        return mutation

    mutation = mutate_obligation(text)
    if mutation and mutation != text:
        return mutation

    if "," in text:
        return text.replace(",", " only,", 1)
    return "It is not the case that " + text[0].lower() + text[1:]


def sentence_to_claim(sentence: str) -> str:
    claim = clean_text(sentence).rstrip(" .")
    claim = re.sub(r"^(FAQ|Footnotes?|Introduction)\s+", "", claim, flags=re.I)
    if claim and claim[0].isupper() and (len(claim) == 1 or claim[1].islower()):
        claim = claim[0].lower() + claim[1:]
    return claim


def frame_answer(claim: str, rng: random.Random) -> str:
    claim = sentence_to_claim(claim)
    template = rng.choice(ANSWER_FRAMES)
    answer = template.format(claim=claim)
    return clean_text(answer)


def make_unsupported_claim(evidence: Evidence, rng: random.Random) -> str:
    actor = rng.choice(UNSUPPORTED_ACTORS)
    action = rng.choice(UNSUPPORTED_ACTIONS)
    channel = rng.choice(UNSUPPORTED_CHANNELS)
    timing = rng.choice(UNSUPPORTED_TIMINGS)
    authority = rng.choice(UNSUPPORTED_AUTHORITIES)
    record = rng.choice(UNSUPPORTED_RECORDS)
    topic = evidence.topic

    templates = [
        "{actor} must {action} for {topic} {channel} {timing}",
        "{topic} requires {actor} to {action} {channel} and keep {record}",
        "for {topic}, {authority} must approve {record} {timing}",
        "{actor} handling {topic} must keep {record} and {action} {timing}",
        "{topic} is subject to a process where {authority} must {action} {channel}",
        "the required control for {topic} is {record} reviewed by {authority} {timing}",
        "{actor} must document {topic} using {record} {channel}",
        "{topic} requires {action} by {authority} {timing}",
    ]
    return rng.choice(templates).format(
        actor=actor,
        action=action,
        channel=channel,
        timing=timing,
        authority=authority,
        record=record,
        topic=topic,
    )


def make_supported_plus_unsupported_claim(evidence: Evidence, rng: random.Random) -> str:
    supported = sentence_to_claim(evidence.text)
    unsupported = make_unsupported_claim(evidence, rng)
    connectors = [
        "{supported}, and {unsupported}",
        "{supported}; additionally, {unsupported}",
        "{supported}. The same provision also says that {unsupported}",
        "{supported}, provided that {unsupported}",
    ]
    return rng.choice(connectors).format(supported=supported.rstrip(" ."), unsupported=unsupported)


def stable_id(*parts: str) -> str:
    joined = "\n".join(parts).encode("utf-8")
    return hashlib.sha1(joined).hexdigest()[:12]


def make_question(evidence: Evidence, rng: random.Random) -> str:
    template = rng.choice(QUESTION_TEMPLATES)
    return template.format(doc_title=evidence.doc_title, topic=evidence.topic)


def make_example(
    evidence: Evidence,
    label: str,
    index: int,
    rng: random.Random,
    split: str,
    id_prefix: str = "finreg3000",
    neutral_distractor: Evidence | None = None,
    neutral_claim: str | None = None,
    neutral_generation_method: str | None = None,
) -> dict[str, Any]:
    question = make_question(evidence, rng)
    ambiguity_type = "none"
    difficulty = "easy"

    if label == "entailment":
        candidate_answer = frame_answer(evidence.text, rng)
        generation_method = "grounded_evidence_reframed"
    elif label == "contradiction":
        candidate_answer = frame_answer(mutate_contradiction(evidence.text), rng)
        generation_method = "rule_mutated_evidence_reframed"
    else:
        if neutral_claim is not None:
            candidate_answer = frame_answer(neutral_claim, rng)
            generation_method = neutral_generation_method or "supported_plus_unstated_detail"
            ambiguity_type = "partially_supported_extra_detail"
            difficulty = "hard"
        elif neutral_distractor is not None:
            candidate_answer = frame_answer(neutral_distractor.text, rng)
            generation_method = "same_document_distractor_reframed"
            ambiguity_type = "distractor_evidence_not_supported_by_cited_span"
            difficulty = "hard"
        else:
            candidate_answer = frame_answer(make_unsupported_claim(evidence, rng), rng)
            generation_method = "topic_conditioned_unstated_detail"
            ambiguity_type = "unstated_specific_detail"
            difficulty = "medium"

    row_id = f"{id_prefix}_{label}_{index:04d}_{stable_id(evidence.doc_id, evidence.text, candidate_answer)}"
    return {
        "id": row_id,
        "split": split,
        "task": "financial_regulation_answer_verification",
        "label": label,
        "expected_label": label,
        "query": question,
        "candidate_answer": candidate_answer,
        "doc_id": evidence.doc_id,
        "doc_title": evidence.doc_title,
        "jurisdiction": evidence.jurisdiction,
        "source_path": evidence.source_path,
        "source_pages": [evidence.page],
        "evidence_span": evidence.text,
        "topic": evidence.topic,
        "ambiguity_type": ambiguity_type,
        "difficulty": difficulty,
        "generation_method": generation_method,
        "quality_score": round(evidence.quality_score, 4),
        "review_status": "auto_generated_needs_human_review",
    }


def select_neutral_distractor(
    target: Evidence,
    candidates: list[Evidence],
    rng: random.Random,
) -> Evidence | None:
    target_tokens = set(content_tokens(target.topic)) | set(content_tokens(target.text))
    scored: list[tuple[int, float, Evidence]] = []

    for candidate in candidates:
        if candidate.text == target.text:
            continue
        if candidate.doc_id == target.doc_id and candidate.page == target.page:
            continue

        candidate_tokens = set(content_tokens(candidate.topic)) | set(content_tokens(candidate.text))
        overlap = len(target_tokens & candidate_tokens)
        if overlap == 0:
            continue

        length_penalty = abs(len(candidate.text) - len(target.text)) / 500.0
        score = overlap + candidate.quality_score - length_penalty
        scored.append((overlap, score, candidate))

    if scored:
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        top_candidates = [item[2] for item in scored[:30]]
        return rng.choice(top_candidates)

    fallback = [
        candidate
        for candidate in candidates
        if candidate.text != target.text
        and not (candidate.doc_id == target.doc_id and candidate.page == target.page)
    ]
    return rng.choice(fallback) if fallback else None


def build_dataset(
    seed: int,
    docs: list[dict[str, Any]] | None = None,
    split_mode: str = "dev_test",
    id_prefix: str = "finreg3000",
    neutral_strategy: str = "synthetic",
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    all_rows: list[dict[str, Any]] = []
    global_index = 0
    source_docs = docs if docs is not None else DOCS

    for doc in source_docs:
        evidence = extract_evidence(doc)
        evidence = dedupe_evidence(evidence)
        if not evidence:
            raise RuntimeError(f"No evidence extracted for {doc['doc_id']}")

        target = int(doc["target_per_label"])
        needed = target * 3
        if len(evidence) < needed:
            # Reuse high-quality evidence only after the extracted pool is exhausted.
            repeated = []
            while len(repeated) < needed:
                repeated.extend(evidence)
            evidence_pool = repeated[:needed]
        else:
            evidence_pool = evidence[:needed]

        rng.shuffle(evidence_pool)
        by_label = {
            "entailment": evidence_pool[:target],
            "contradiction": evidence_pool[target:target * 2],
            "neutral": evidence_pool[target * 2:target * 3],
        }

        for label in ("entailment", "contradiction", "neutral"):
            label_rows = list(by_label[label])
            dev_count = max(1, target // 10)
            for label_index, evidence_item in enumerate(label_rows, start=1):
                global_index += 1
                if split_mode == "test_only":
                    split = "test"
                elif split_mode == "dev_test":
                    split = "dev" if label_index <= dev_count else "test"
                else:
                    raise ValueError(f"unknown split mode: {split_mode}")

                neutral_distractor = None
                if label == "neutral":
                    if neutral_strategy == "same_doc_distractor":
                        neutral_distractor = select_neutral_distractor(evidence_item, evidence, rng)
                        neutral_claim = None
                        neutral_generation_method = None
                    elif neutral_strategy == "supported_plus_unstated_detail":
                        neutral_distractor = None
                        neutral_claim = make_supported_plus_unsupported_claim(evidence_item, rng)
                        neutral_generation_method = "supported_plus_unstated_detail"
                    elif neutral_strategy == "mixed_hard":
                        if label_index % 2:
                            neutral_distractor = select_neutral_distractor(evidence_item, evidence, rng)
                            neutral_claim = None
                            neutral_generation_method = None
                        else:
                            neutral_distractor = None
                            neutral_claim = make_supported_plus_unsupported_claim(evidence_item, rng)
                            neutral_generation_method = "supported_plus_unstated_detail"
                    elif neutral_strategy != "synthetic":
                        raise ValueError(f"unknown neutral strategy: {neutral_strategy}")
                    else:
                        neutral_claim = None
                        neutral_generation_method = None
                else:
                    neutral_claim = None
                    neutral_generation_method = None

                all_rows.append(
                    make_example(
                        evidence_item,
                        label,
                        global_index,
                        rng,
                        split,
                        id_prefix=id_prefix,
                        neutral_distractor=neutral_distractor,
                        neutral_claim=neutral_claim,
                        neutral_generation_method=neutral_generation_method,
                    )
                )

    rng.shuffle(all_rows)
    return all_rows


def dedupe_evidence(evidence: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    deduped: list[Evidence] = []
    for item in evidence:
        key = re.sub(r"\s+", " ", item.text.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_review_sample(path: Path, rows: list[dict[str, Any]], seed: int, per_label: int = 20) -> None:
    rng = random.Random(seed)
    sampled: list[dict[str, Any]] = []
    for label in ("entailment", "contradiction", "neutral"):
        label_rows = [row for row in rows if row["label"] == label]
        sampled.extend(rng.sample(label_rows, min(per_label, len(label_rows))))
    rng.shuffle(sampled)
    write_jsonl(path, sampled)


def compute_quality_checks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_label = {
        label: [row for row in rows if row["label"] == label]
        for label in ("entailment", "contradiction", "neutral")
    }
    query_markers = [
        "specific implementation channel",
        "exact vendor or platform",
        "named submission portal",
        "mandatory font size",
        "specific email address",
    ]
    neutral_answers = {row["candidate_answer"] for row in by_label["neutral"]}
    exact_entailment = sum(
        1 for row in by_label["entailment"]
        if row["candidate_answer"] == row["evidence_span"]
    )
    neutral_query_marker_hits = sum(
        1 for row in rows
        if any(marker in row["query"].lower() for marker in query_markers)
    )
    shortcut_correct = 0
    for row in rows:
        if row["candidate_answer"] == row["evidence_span"]:
            predicted = "entailment"
        elif row["candidate_answer"] in neutral_answers:
            predicted = "neutral"
        else:
            predicted = "contradiction"
        shortcut_correct += int(predicted == row["label"])

    return {
        "candidate_equals_evidence_count": exact_entailment,
        "neutral_unique_candidate_answers": len(neutral_answers),
        "neutral_query_marker_hits": neutral_query_marker_hits,
        "old_shortcut_baseline_accuracy": round(shortcut_correct / len(rows), 4) if rows else 0.0,
        "unique_candidate_answers_by_label": {
            label: len({row["candidate_answer"] for row in label_rows})
            for label, label_rows in by_label.items()
        },
        "unique_queries": len({row["query"] for row in rows}),
    }


def build_summary(rows: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
    by_label = Counter(row["label"] for row in rows)
    by_doc = Counter(row["doc_id"] for row in rows)
    by_doc_label: dict[str, dict[str, int]] = defaultdict(dict)
    for (doc_id, label), count in Counter((row["doc_id"], row["label"]) for row in rows).items():
        by_doc_label[doc_id][label] = count

    by_split = Counter(row["split"] for row in rows)
    return {
        "output_path": str(output_path),
        "total_rows": len(rows),
        "label_counts": dict(by_label),
        "doc_counts": dict(by_doc),
        "doc_label_counts": dict(by_doc_label),
        "split_counts": dict(by_split),
        "quality_checks": compute_quality_checks(rows),
        "review_status": "auto_generated_needs_human_review",
        "recommended_next_step": "Manually review a stratified sample before using this as an academic benchmark.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 3,000-row FinReg benchmark draft")
    parser.add_argument(
        "--output",
        default="data/finreg_3000_draft.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument(
        "--summary-output",
        default="data/finreg_3000_draft_summary.json",
        help="Summary JSON path",
    )
    parser.add_argument(
        "--review-sample-output",
        default="data/sample_60_for_review.jsonl",
        help="Stratified review sample JSONL path",
    )
    parser.add_argument(
        "--heldout-output",
        default="data/finreg_heldout_cbe_test.jsonl",
        help="Heldout Commercial Bank Examination Manual test JSONL path",
    )
    parser.add_argument(
        "--heldout-summary-output",
        default="data/finreg_heldout_cbe_test_summary.json",
        help="Heldout test summary JSON path",
    )
    parser.add_argument(
        "--heldout-review-sample-output",
        default="data/sample_60_heldout_cbe_for_review.jsonl",
        help="Heldout stratified review sample JSONL path",
    )
    parser.add_argument(
        "--skip-heldout",
        action="store_true",
        help="Only build the original 3,000-row draft dataset",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_path = Path(args.output)
    summary_path = Path(args.summary_output)
    review_sample_path = Path(args.review_sample_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    review_sample_path.parent.mkdir(parents=True, exist_ok=True)

    rows = build_dataset(seed=args.seed)
    write_jsonl(output_path, rows)
    write_review_sample(review_sample_path, rows, seed=args.seed + 1)

    summary = build_summary(rows, output_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {"main": summary}

    if not args.skip_heldout:
        heldout_path = Path(args.heldout_output)
        heldout_summary_path = Path(args.heldout_summary_output)
        heldout_review_sample_path = Path(args.heldout_review_sample_output)
        heldout_path.parent.mkdir(parents=True, exist_ok=True)
        heldout_summary_path.parent.mkdir(parents=True, exist_ok=True)
        heldout_review_sample_path.parent.mkdir(parents=True, exist_ok=True)

        heldout_rows = build_dataset(
            seed=args.seed + 1000,
            docs=HELDOUT_DOCS,
            split_mode="test_only",
            id_prefix="finreg_heldout_cbe",
            neutral_strategy="mixed_hard",
        )
        write_jsonl(heldout_path, heldout_rows)
        write_review_sample(heldout_review_sample_path, heldout_rows, seed=args.seed + 1001)

        heldout_summary = build_summary(heldout_rows, heldout_path)
        heldout_summary["intended_use"] = "heldout_document_test"
        heldout_summary["heldout_warning"] = (
            "Do not use this file for model selection or training; reserve it for final "
            "generalization checks on an unseen source document."
        )
        heldout_summary_path.write_text(
            json.dumps(heldout_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["heldout"] = heldout_summary

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
