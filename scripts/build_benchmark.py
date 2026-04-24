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
]

NEUTRAL_QUESTION_TEMPLATES = [
    "According to {doc_title}, what specific implementation channel is required for {topic}?",
    "Under {doc_title}, what exact vendor or platform must be used for {topic}?",
    "What named submission portal does {doc_title} require for {topic}?",
    "What mandatory font size does {doc_title} prescribe for notices about {topic}?",
    "What specific email address does {doc_title} require for reporting {topic}?",
]

NEUTRAL_ANSWERS = [
    "The text requires submission through a dedicated mobile application named FinReg Portal.",
    "The text requires institutions to use a vendor-approved XML template supplied by a named private provider.",
    "The text requires all notices to be printed in 14-point type with a regulator-approved watermark.",
    "The text requires reporting through compliance-submissions@example.org within one business day.",
    "The text requires a quarterly attestation signed by the chief technology officer using a prescribed digital seal.",
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


def stable_id(*parts: str) -> str:
    joined = "\n".join(parts).encode("utf-8")
    return hashlib.sha1(joined).hexdigest()[:12]


def make_question(evidence: Evidence, rng: random.Random, neutral: bool = False) -> str:
    templates = NEUTRAL_QUESTION_TEMPLATES if neutral else QUESTION_TEMPLATES
    template = rng.choice(templates)
    return template.format(doc_title=evidence.doc_title, topic=evidence.topic)


def make_example(
    evidence: Evidence,
    label: str,
    index: int,
    rng: random.Random,
) -> dict[str, Any]:
    neutral = label == "neutral"
    question = make_question(evidence, rng, neutral=neutral)

    if label == "entailment":
        candidate_answer = evidence.text
        generation_method = "evidence_sentence"
    elif label == "contradiction":
        candidate_answer = mutate_contradiction(evidence.text)
        generation_method = "rule_mutated_evidence_sentence"
    else:
        candidate_answer = rng.choice(NEUTRAL_ANSWERS)
        generation_method = "invented_unstated_detail"

    row_id = f"finreg3000_{label}_{index:04d}_{stable_id(evidence.doc_id, evidence.text, candidate_answer)}"
    return {
        "id": row_id,
        "split": "dev" if index % 10 == 0 else "test",
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
        "ambiguity_type": "unstated_specific_detail" if neutral else "none",
        "difficulty": "medium" if label == "neutral" else "easy",
        "generation_method": generation_method,
        "quality_score": round(evidence.quality_score, 4),
        "review_status": "auto_generated_needs_human_review",
    }


def build_dataset(seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    all_rows: list[dict[str, Any]] = []
    global_index = 0

    for doc in DOCS:
        evidence = extract_evidence(doc)
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
            for evidence_item in by_label[label]:
                global_index += 1
                all_rows.append(make_example(evidence_item, label, global_index, rng))

    rng.shuffle(all_rows)
    return all_rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_path = Path(args.output)
    summary_path = Path(args.summary_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = build_dataset(seed=args.seed)
    write_jsonl(output_path, rows)

    summary = build_summary(rows, output_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
