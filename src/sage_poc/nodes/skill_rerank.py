"""Skill rerank interface.

Production path: top-k bi-encoder candidates → Falcon-3B cross-encoder
→ single selection. The cross-encoder sees (message, candidate_description)
pairs jointly, enabling disambiguation that single-vector retrieval cannot do.

Current state: stub returns highest-scored retrieval candidate unmodified.
Plug Falcon-3B in by replacing _rerank_stub with _rerank_with_model below.
"""
from __future__ import annotations


def rerank_candidates(
    message: str,
    candidates: list[tuple[str, float]],
) -> tuple[str, float]:
    """Return winning (skill_id, score) from bi-encoder retrieval candidates.

    Args:
        message: The user message being routed.
        candidates: (skill_id, score) tuples, descending score order. Non-empty.

    Returns:
        (skill_id, score) of selected skill.

    Raises:
        ValueError: If candidates is empty.
    """
    if not candidates:
        raise ValueError("rerank_candidates requires at least one candidate")
    return _rerank_stub(message, candidates)


def _rerank_stub(
    message: str,
    candidates: list[tuple[str, float]],
) -> tuple[str, float]:
    """Stub: return top bi-encoder candidate. Replace with Falcon-3B when validated."""
    return candidates[0]


# Falcon-3B cross-encoder plug-in point:
#
# def _rerank_with_model(
#     message: str,
#     candidates: list[tuple[str, float]],
# ) -> tuple[str, float]:
#     from sage_poc.nodes.skill_rerank_model import score_pairs
#     from sage_poc.skills.schema import load_skill
#     pairs = [(message, load_skill(sid).semantic_description) for sid, _ in candidates]
#     scores = score_pairs(pairs)
#     best_idx = max(range(len(scores)), key=lambda i: scores[i])
#     return candidates[best_idx][0], float(scores[best_idx])
