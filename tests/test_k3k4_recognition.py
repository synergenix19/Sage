"""K3/K4 recognition clauses — the signed gate's fixture layer (adopted 2026-08-15).

Vee-adopted clauses (draft-adoption; record 2026-08-15-k3k4-adoption-and-gate.md):
K4 -> behavioral_activation description clause (reconnection wish, section-7b lineage);
K3 -> interpersonal_effectiveness dedicated ANCHOR (self-as-transgressor, section-6b
lineage; anchor not description-append because max-over-anchors defeats dilution).

Fixtures are paraphrase-independent (E7): none is a lexicon entry, description
sentence, or anchor verbatim. Pre-clause failure evidence (2026-08-15, BGE local):
K4-b -> interpersonal_effectiveness 0.4827 (wrong skill); K3-a -> stop_technique
0.5270; K3-b -> self_compassion_break 0.4741. These tests would have failed then.

BGE-dependent (same class as the other semantic routing suites).
"""
import pytest

pytestmark = pytest.mark.slow   # embedding-dependent: real BGE required, stub must FAIL

import sage_poc.nodes.skill_select as ss
from sage_poc.nodes.grief_override import _has_grief_signature


@pytest.fixture(scope="module", autouse=True)
def _semantic_ready():
    ss._ensure_semantic_ready()


def _top(msg):
    sid, score, _ = ss._semantic_match_with_runner_up(msg)
    return sid, score


# ---------------------------------------------------------------------------
# Targets (bin (a)) — the presentations the clauses exist to recognize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "i want to reconnect with people",
    "i miss my friends and i want to start reaching out again but something stops me",
])
def test_k4_reconnection_wish_resolves_to_behavioral_activation(msg):
    sid, score = _top(msg)
    assert sid == "behavioral_activation", f"{msg!r} -> {sid} ({score:.4f})"
    assert score >= ss.SEMANTIC_THRESHOLD


@pytest.mark.parametrize("msg", [
    "i need to stop crossing a line",
    "i keep overstepping with my wife and i want to stop doing that",
])
def test_k3_self_as_transgressor_resolves_to_interpersonal_effectiveness(msg):
    sid, score = _top(msg)
    assert sid == "interpersonal_effectiveness", f"{msg!r} -> {sid} ({score:.4f})"
    assert score >= ss.SEMANTIC_THRESHOLD


# ---------------------------------------------------------------------------
# Exclusions (bin (b)) — Vee's boundary rulings, each owned by its own layer
# ---------------------------------------------------------------------------

def test_grief_reconnection_swaps_ba_offer_to_grief_loss():
    """Vee bin (b): grief-driven reconnection is grief territory. The deterministic
    swap uses the SAME single-sourced bereavement set as the S2a deference (never a
    second list) and carries its own audit marker. Both directions pinned:
    full-graph verified 2026-08-15 (grief phrasing -> grief_loss offered, swap=True;
    clean phrasing -> behavioral_activation, swap=False)."""
    grief_msg = "i want to reconnect with people since the loss of my father"
    clean_msg = "i want to reconnect with people"
    assert _has_grief_signature(grief_msg) is True
    assert _has_grief_signature(clean_msg) is False
    # matcher still ranks BA on the grief phrasing (semantic cannot read bereavement);
    # the swap at offer assembly is what enforces the bin — its predicate is pinned
    # here, its end-to-end effect by the full-graph gate probes in the record.
    sid, _ = _top(grief_msg)
    assert sid == "behavioral_activation"


def test_solitude_without_change_wish_matches_nothing():
    """Section-7b's own guard: chosen withdrawal is not a problem. No route."""
    sid, score = _top("i prefer being on my own lately and honestly that feels okay")
    assert sid is None, f"contented solitude matched {sid} ({score:.4f})"


def test_harm_colored_crossing_a_line_is_safety_tier_territory():
    """Vee bin (b): crossing-a-line + harm-adjacency keeps escalating. The safety
    tier owns the turn BEFORE skill_select (full-graph verified 2026-08-15:
    'i crossed a line last night and i hurt her' -> crisis_response). Pinned here
    at the deterministic layer: the S1/S3-facing lexicon treats it as harm."""
    from sage_poc.nodes.panic_override import _has_harm_language
    assert _has_harm_language("i crossed a line last night and i hurt her") is True


def test_dearman_prep_recognition_not_burned():
    """Wrong-route no-regress spot-check: the covered IE territory (receiving-end
    boundary prep) still resolves to IE with the anchor present."""
    sid, score = _top("i need to prepare for a hard conversation about setting a boundary with my sister")
    assert sid == "interpersonal_effectiveness", f"-> {sid} ({score:.4f})"


def test_rerank_veto_sees_the_signed_anchor():
    """The live 3/3 finding (2026-08-16): the veto scored descriptions only, so the
    K3 anchor was invisible and the offer died at keyword_rerank_veto despite Tier-2
    and the keyword agreeing. The veto's view now includes anchors: the K3 phrase
    must NOT be vetoed for an IE-containing candidate list."""
    from sage_poc.nodes.skill_select import _keyword_rerank_veto
    vetoed = _keyword_rerank_veto(["interpersonal_effectiveness"],
                                  "i need to stop crossing a line", "en")
    assert vetoed is False, "anchor still invisible to the veto"


def test_semantic_side_rerank_sees_the_signed_anchor():
    """K3-b's live finding (2026-08-16): 'overstepping' has no keyword, routes via the
    semantic tier, and _rerank_route scored descriptions only — the anchor was invisible
    to the SECOND cross-encoder call site and the route abstained. Both call sites now
    share the one recognition surface."""
    from sage_poc.nodes.skill_select import _rerank_route
    sid, score, ru = _rerank_route(
        [("interpersonal_effectiveness", 0.58)], "en",
        "i keep overstepping with my wife and i want to stop doing that",
        lambda best: None)
    assert sid == "interpersonal_effectiveness", f"abstained/wrong: {sid}"
