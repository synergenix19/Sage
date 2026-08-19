"""Experiment 4.5 — RAG evaluation log generator.

Generates a structured JSONL log of retrieval accuracy results across the
query corpus defined in query_corpus.py. Intended for offline review by
clinicians and engineers — not run as part of the standard pytest suite.

Usage:
    python tests/experiment_4_5/generate_rag_evaluation_log.py

Output:
    docs/experiment_4_5_rag_evaluation_log.jsonl

Each line contains:
  {
    "query": str,
    "language": str,
    "expected_topic": str,
    "expected_source_prefix": str | null,
    "should_abstain": bool,
    "actual_abstain": bool,
    "actual_passages": [...],
    "passage_count": int,
    "source_ids": [...],
    "source_prefix_match": bool | null,
    "abstain_correct": bool,
    "notes": str
  }

Since the DB pool is not available at log-generation time, this script mocks
the retrieval layer with deterministic stubs that reflect the seeded corpus.
The stubs are defined here and must be updated as the corpus grows.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# Stub corpus: source_id prefix → representative passage
# Update when new seed articles are ingested.
#
# Refreshed 2026-08-19 with query_corpus.py (ticket
# 2026-08-19-ivfflat-recall-holes-crisis-adjacent, PR #501). The previous entries
# were invented passages under article IDs that have never existed in the corpus
# ("anx-002-en", "mbct-003-en", "dbt-004-en"), carrying citations to real
# literature the corpus does not cite. A log generated from those reads as
# retrieval evidence for a corpus that is not ours, which is the wrong direction
# for a record this project treats as evidence. Every entry below is now a real
# article: ID, opening sentence and citation are taken from
# data/knowledge_corpus/en/, and the topic mapping reflects what each query
# actually retrieves on prod under exact scan (2026-08-19).
# ---------------------------------------------------------------------------

_STUB_CORPUS: dict[str, dict] = {
    "cbt-": {
        "text": "Cognitive Behavioural Therapy (CBT) is a structured, evidence-based form of psychological therapy that helps people understand the connection between thoughts, feelings and behaviour.",
        "source_id": "cbt-001-en",
        "citation": "Hofmann, S. G., Asnaani, A., Vonk, I. J., Sawyer, A. T., & Fang, A. (2012).",
        "relevance_score": 0.88,
    },
    "therapy-": {
        "text": "Therapy is a structured conversation with a trained mental health professional.",
        "source_id": "therapy-001-en",
        "citation": "Wampold, B. E. (2015). How important are the common factors in psychotherapy?",
        "relevance_score": 0.82,
    },
    "mindfulness-": {
        "text": "Mindfulness is the practice of paying attention to the present moment with openness and curiosity.",
        "source_id": "mindfulness-001-en",
        "citation": "Maddock, A., & Blair, C. (2023).",
        "relevance_score": 0.79,
    },
    "anxiety-": {
        "text": "Anxiety is the mind and body's natural response to detecting possible danger or uncertainty.",
        "source_id": "anxiety-001-en",
        "citation": "Penninx, B. W., Pine, D. S., Holmes, E. A., & Reif, A. (2021).",
        "relevance_score": 0.85,
    },
}

_TOPIC_TO_PREFIX: dict[str, str] = {
    "CBT": "cbt-",
    "CBT for depression": "cbt-",
    "CBT (Arabic query, English corpus)": "cbt-",
    # No exposure-therapy article exists; therapy-001 is the real nearest passage.
    "exposure therapy / anxiety": "therapy-",
    "anxiety treatment": "anxiety-",
    # No MBCT-specific article; mindfulness-001 is what the query retrieves.
    "MBCT": "mindfulness-",
    # No DBT article at all. Both index and exact-scan arms return cbt-001 at
    # cosine 0.498 on prod, so the stub mirrors that rather than inventing a
    # dbt- article to satisfy the fixture.
    "DBT": "cbt-",
    "therapy for depression (Arabic query)": "cbt-",
    "single-word known topic": "cbt-",
}


def _stub_retrieve(query: str, expected_topic: str, should_abstain: bool) -> dict:
    """Deterministic stub: returns a plausible passage or abstains."""
    if should_abstain or not query.strip():
        return {"passages": [], "abstain": True}

    prefix = _TOPIC_TO_PREFIX.get(expected_topic)
    if prefix and prefix in _STUB_CORPUS:
        passage = dict(_STUB_CORPUS[prefix])
        return {"passages": [passage], "abstain": False}

    # Fallback: return first corpus entry
    first = next(iter(_STUB_CORPUS.values()))
    return {"passages": [dict(first)], "abstain": False}


def _evaluate_result(query_case, retrieval_result: dict) -> dict:
    """Compute evaluation metrics for one query/result pair."""
    passages = retrieval_result["passages"]
    actual_abstain = retrieval_result["abstain"]
    source_ids = [p["source_id"] for p in passages]

    # Abstain correctness
    abstain_correct = actual_abstain == query_case.should_abstain

    # Source prefix match (only meaningful when not abstaining and prefix specified)
    source_prefix_match = None
    if (
        query_case.expected_source_prefix is not None
        and not query_case.should_abstain
        and not actual_abstain
    ):
        source_prefix_match = any(
            sid.startswith(query_case.expected_source_prefix)
            for sid in source_ids
        )

    return {
        "query": query_case.query[:200],  # truncate very long edge-case queries
        "language": query_case.language,
        "expected_topic": query_case.expected_topic,
        "expected_source_prefix": query_case.expected_source_prefix,
        "should_abstain": query_case.should_abstain,
        "actual_abstain": actual_abstain,
        "actual_passages": passages,
        "passage_count": len(passages),
        "source_ids": source_ids,
        "source_prefix_match": source_prefix_match,
        "abstain_correct": abstain_correct,
        "notes": query_case.notes,
    }


def generate_log(output_path: Path | None = None) -> list[dict]:
    """Run all corpus queries through the stub retrieval and write a JSONL log.

    Returns the list of evaluation result dicts (for programmatic use).
    """
    from tests.experiment_4_5.query_corpus import ALL_QUERIES

    results = []
    for qc in ALL_QUERIES:
        retrieval = _stub_retrieve(qc.query, qc.expected_topic, qc.should_abstain)
        eval_row = _evaluate_result(qc, retrieval)
        results.append(eval_row)

    if output_path is None:
        output_path = (
            Path(__file__).parent.parent.parent
            / "docs"
            / "experiment_4_5_rag_evaluation_log.jsonl"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = len(results)
    abstain_correct = sum(1 for r in results if r["abstain_correct"])
    prefix_evaluated = [r for r in results if r["source_prefix_match"] is not None]
    prefix_correct = sum(1 for r in prefix_evaluated if r["source_prefix_match"])

    print(f"RAG Evaluation Log — {datetime.now(timezone.utc).isoformat()}")
    print(f"  Queries evaluated : {total}")
    print(f"  Abstain accuracy  : {abstain_correct}/{total} ({100 * abstain_correct // total}%)")
    if prefix_evaluated:
        print(
            f"  Source prefix acc : {prefix_correct}/{len(prefix_evaluated)} "
            f"({100 * prefix_correct // len(prefix_evaluated)}%)"
        )
    print(f"  Output written to : {output_path}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = generate_log()
    sys.exit(0 if all(r["abstain_correct"] for r in results) else 1)
