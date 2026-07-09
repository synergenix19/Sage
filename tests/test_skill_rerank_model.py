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


def test_default_precision_is_fp32_for_safety(monkeypatch):
    # SAFETY-DRIVEN DEFAULT (2026-06-25): int8 is DISQUALIFIED. The safety-relevance check on the 29
    # cross-precision flips found 6/6 id_oos flips in the disqualifying direction — int8 ROUTES
    # clinician-territory disclosures (disposition=ABSTAIN) that fp32 correctly ABSTAINS, confirmed at
    # the production node (fp32 6/6 ABSTAIN, int8 6/6 ROUTE incl. dbt_tipp + mindfulness_body_scan).
    # int8 stays SELECTABLE (explicit env) for latency probing but must NEVER be the default in prod.
    monkeypatch.delenv("SKILL_RERANK_PRECISION", raising=False)
    assert active_precision() == "fp32", "default precision must be fp32 (int8 safety-disqualified)"


def test_int8_still_selectable_explicitly(monkeypatch):
    # The configurable parameter survives: int8 reachable for measurement, just not by default.
    monkeypatch.setenv("SKILL_RERANK_PRECISION", "int8")
    assert active_precision() == "int8"


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


@pytest.mark.slow
def test_rerank_route_promotes_correct_skill_over_higher_bi_encoder(monkeypatch):
    # The promotion behavior the build rests on: the reranker re-ranks the top-k and can route a
    # skill the bi-encoder scored LOWER. worry_time (0.58) must win over cbt_thought_record (0.61)
    # for a rumination query — the reranker's semantic re-scoring, live through the active precision.
    from sage_poc.nodes import skill_select as ss
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    ranked = [("worry_time", 0.58), ("cbt_thought_record", 0.61), ("box_breathing", 0.50),
              ("sleep_hygiene", 0.48), ("grief_loss", 0.46)]
    routed, _, _ = ss._rerank_route(ranked, "en", "I keep ruminating on worst-case scenarios I cannot control", lambda b: None)
    assert routed == "worry_time", f"reranker should promote worry_time for rumination, got {routed}"


@pytest.mark.slow
def test_loaded_tau_fires_directionally(monkeypatch):
    # Commit 3 ACTIVATION check: this is where ABSTAIN goes live. With the calibrated global-τ loaded
    # into the read slot, an id_oos over-route (substance disclosure — clinician territory) must
    # ABSTAIN flag-on, while an in_scope case still routes. Confirms the τ loaded right and fires in
    # the correct DIRECTION (not inert at -inf, not over-firing) before the full re-gate (step 5).
    from sage_poc.nodes import skill_select as ss
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    ss._RERANK_TAU = None  # force reload from the calibration artifact
    assert ss._rerank_tau("en") < -5, "EN τ must be loaded (not the -inf default)"
    ido = [("dbt_tipp", 0.55), ("grounding_5_4_3_2_1", 0.50), ("box_breathing", 0.48), ("worry_time", 0.46), ("mood_check_in", 0.44)]
    in_s = [("worry_time", 0.58), ("cbt_thought_record", 0.55), ("box_breathing", 0.50), ("sleep_hygiene", 0.48), ("grief_loss", 0.46)]
    routed_ido, _, _ = ss._rerank_route(ido, "en", "I think I might be drinking too much and want to cut back", lambda b: None)
    routed_ins, _, _ = ss._rerank_route(in_s, "en", "I keep ruminating on worst-case scenarios I cannot control", lambda b: None)
    assert routed_ido is None, f"id_oos substance disclosure must ABSTAIN flag-on, routed {routed_ido}"
    assert routed_ins is not None, "in_scope rumination must route flag-on, got ABSTAIN"
