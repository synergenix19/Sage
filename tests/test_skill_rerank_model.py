"""Cross-encoder reranker model — head-loaded positive control.

Pins the silent-headless-load bug that nearly killed this effort: sentence_transformers.CrossEncoder
loaded bge-reranker-v2-m3 WITHOUT its trained reranker head → ~0 logits → a confident-wrong number
that passed a too-weak control. The canonical AutoModelForSequenceClassification path produces real
logit separation (relevant >> off-topic). This test asserts that separation for WHICHEVER PRECISION
is active (int8 default / fp32 fallback), so a refactor or a precision change can't silently revert
to the headless load.

Marked `slow`: loads bge-reranker-v2-m3 (~2.2GB) — excluded from CI (no model), runs locally/pre-merge.
"""
import pytest

from sage_poc.nodes.skill_rerank_model import score_pairs, head_loaded_ok, active_precision


_REL_DESC = "Guided practice for writing down an automatic negative thought and examining the evidence for and against it."


@pytest.mark.slow
def test_reranker_head_is_loaded_and_separates():
    # The load-bearing control: head loaded AND logits separate by a real margin (>3), not ~0.
    assert head_loaded_ok(), (
        f"reranker head not loaded / not separating for precision={active_precision()} "
        "— the CrossEncoder-headless-load class of bug"
    )


@pytest.mark.slow
def test_score_pairs_ranks_relevant_above_offtopic():
    scores = score_pairs([
        ("I want to write down and challenge my negative thoughts", _REL_DESC),
        ("what time does the grocery store close today", _REL_DESC),
    ])
    assert scores[0] - scores[1] > 3.0, f"relevant must outscore off-topic by >3 logits, got {scores}"
