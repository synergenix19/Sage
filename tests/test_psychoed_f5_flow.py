"""Psychoed Phase 3 Task 7: F5 multi-turn flow (PROCEDURAL, not corpus rows).

EXCEPTION TO THE CORPUS FORM (per task-7-brief.md): every other fixture family in this
suite (F1-F4, F8, F9) lives as tests/fixtures/psychoed/f*_*.jsonl rows driven through
tests/test_psychoed_fixtures_ci.py's generic run_fixture()/assert_expectations(). F5 does
NOT get a corpus file. Multi-turn branching logic (loop-back across an arbitrary number of
picks, a check-in reply that either continues or falls through, a bridge offer that must
NOT auto-launch, a within-session skip decision keyed off a running exposure count) does
not compress into the flat {turns: [...], expect: {...}} row shape the driver's schema
validates -- each case here is really a small state machine, not a single input/output
pair. So this file is a plain pytest module that drives sage_poc.graph.build_graph()
directly, following the exact patterns already established by tests/test_psychoed_graph.py
(mocked intent_route_node + carry_state threading, graph built INSIDE the patch context)
and tests/test_psychoed_fixtures_ci.py (conftest.make_mock_llm-style stubbing so freeflow
never makes a live LLM call).

NAMED EXCLUSION (delta 15, handoff notes §VI, docs/superpowers/plans/
2026-07-28-psychoed-phase2-handoff-notes.md): served-topics context injection is NOT
asserted anywhere in this file. L2_psychoed_continuation.json declares "variables": [] --
Task 7's own controller ruling was that no served-menu-labels/remaining-menu-labels
injection point exists without inventing new template machinery, so freeflow_respond_node's
l2_override wiring carries no such signal today. Every loop-back assertion below therefore
uses DETERMINISTIC SURFACES ONLY: state channels (psychoed_blocks_served,
psychoed_family_exposures, psychoed_active_category, skill_match_method,
psychoed_matched_row_id) and literal re-serve/non-re-serve of block content strings pulled
from the store. Nothing here asserts that the LLM "remembers" what topics were discussed --
that channel does not exist in the current build.

NAMED CASE, carry item (offer-mid-pathway L2 suppression): pinned in
test_bridge_offer_created_but_not_auto_launched_l2_suppressed below. No dedicated ticket
file exists under docs/superpowers/tickets/ for this item (verified: `ls` of that directory
turned up no offer/L2/suppression-named ticket) -- the plan doc
(docs/superpowers/plans/2026-07-30-psychoed-phase3-fixtures-plan.md, "carry list disposition"
and F5's own bullet) calls it a carry item pending "the residual-Low ticket" without a filed
ticket existing yet, so this test instead cites the handoff notes' delta 15
(docs/superpowers/plans/2026-07-28-psychoed-phase2-handoff-notes.md §VI item 15) and the
concrete code location: freeflow_respond.py's `l2_override = "psychoed_continuation" if
(...psychoed_active_category) else None` is UNCONDITIONAL on offered_skill_ids, and
composer.py's compose_prompt gives l2_intent_override top priority over the offered-skill
branch (`if l2_intent_override: ... elif _offer_ids: ...`, prompts/composer.py ~L868-877) --
so a skill offer created WHILE a psychoed pathway is active never reaches the L2_skill_offer
template (with its structured, named `{offer_options_block}`) at all; the pathway's generic
psychoed_continuation glue renders instead, and its own prose only tells the model "present
[a bridge offer] as a single optional invitation" with no specifics. This test PINS that
CURRENT AS-BUILT, KNOWN-DEGRADED behavior (the offer's specific named description drops out
of the prompt) -- it is not an endorsement, and per this repo's standing rule (never adjust
src/, never weaken a fixture to match a bad behavior silently) it must be re-examined, not
quietly relied on, once a ticket is filed.

BRIDGE_MAP IS DEAD CODE (a finding surfaced while building the bridge-offer case above):
every category manifest (e.g. data/psychoed/manifests/1f.json) declares a `bridge_map`
field (1f-b2 -> box_breathing, offer: "optional"), but a repo-wide grep of src/sage_poc/
for "bridge_map" / "bridge_offer" / "doc_target" returns zero hits outside the manifest
JSON itself -- psychoed/store.py exposes no accessor for it, and nothing reads it anywhere.
So there is no code path today where the psychoed bridge mechanism itself produces an
offer. The consent-gated "optional, not automatic" property the manifest describes DOES
exist in the codebase, just via a completely different, non-psychoed-aware mechanism: any
skill's own keyword trigger (skills/keyword_matcher.py, sourced from that skill's
target_presentations) can fire mid-pathway through the ordinary R1 offer-then-accept flow
(skill_select.py's default_offer consent gate), independent of any bridge_map declaration.
box_breathing is exactly the skill the 1f-b2 bridge names, so this file exercises THAT real
mechanism (a box_breathing keyword trigger while psychoed_active_category is still "1f")
as the closest honest stand-in for "the b2 bridge offer" the brief describes, and says so
inline. Reported as a finding in the task-7 report; src/ is not touched to "fix" it.

S2c NOTE: config.PSYCHOED_CATEGORIES includes "s2c" in one test below (the block-guard
contrast). data/psychoed/manifests/s2c.json's own `flip_gate_note` ("S2c serve OFF until
reunification-ideation lexicon lands") is a CONTENT/clinical gate, not a code gate --
nothing in src/ reads flip_gate_note, so enabling "s2c" via monkeypatch here is a normal
in-test flag flip (identical in kind to every other family's _arm_psychoed usage), never a
production flip. The S2c flip-gate governs what gets SERVED in prod, not what a test may
exercise.

DELTA 1 CITE (within-session carry-forward skip test): psychoed_family_exposures is the
LIVE carry-forward channel (handoff notes §VI delta 1) -- therapeutic_profile
["techniques_used"] has no writer anywhere in the codebase and no DB column, so
skill_executor.py's `prior_exposure = max(techniques_used.count(skill_id),
_psychoed_family_exposure(state, skill))` is, in practice, driven entirely by the second
term. This file's carry-forward test builds that live prior_exposure value from a REAL
3-turn 1f conversation (not a hand-set integer) to keep the "within-session" claim honest.

MENU-LABEL COLLISION TICKET: the weave-turn-boundary test's clear-no reply uses "no,
nothing like that" rather than a bare "no". Bare "no" is a genuine PSY-WEAVE-1
clear-negative pattern but ALSO collides with block 3c-b6's menu_label ("...'no reason'")
at resolver.py's substring-containment tier, re-serving that block instead of reaching the
deferred menu-after-weave continuation (see docs/superpowers/tickets/
2026-07-30-menu-label-short-token-substring-collision.md and F4-002's strict-xfail in
tests/fixtures/psychoed/f4_weave.jsonl). "no, nothing like that" is a companion allowlist
phrase (F4-003) that does NOT collide with any 3c menu_label, so this file exercises the
menu-after-weave contract on its intended, working path rather than re-litigating the
open ticket.

ONE-QUESTION-CAP NOTE: output_gate.py's `_limit_to_one_question` (Node 8, MIND-SAFE
discipline) drops every question sentence after the first from ANY response, including
verbatim psychoed copy. A served block's check_in text (e.g. 1f's "Does that make sense?
Want to explore another topic...") carries two question sentences, so only the first
survives in `response`/`response_en`. Per this repo's standing convention (assert on
behavior/markers, never on copy strings that a downstream, unrelated gate can silently
reshape), this file never asserts the full check_in string verbatim -- it asserts the
deterministic state surfaces (skill_match_method, psychoed_matched_row_id,
psychoed_menu_offered) that HIGH-2's block+check-in shape is actually keyed on, plus the
presence/absence of block CONTENT strings (which the integrity gate at output_gate.py
~985-987 guarantees survive verbatim: `_block_content in final_response` is the gate's own
pass condition).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import build_graph
from sage_poc.nodes.skill_executor import evaluate_step_policy, _psychoed_family_exposure
from sage_poc.prompts import composer
from sage_poc.prompts.loader import get_intent_template
from sage_poc.psychoed import serve as psy_serve, store
from sage_poc.skills.schema import load_skill
from tests.test_graph import make_e2e_state, carry_state
from tests.test_psychoed_graph import _PSYCHOED_CARRY
import pytest

pytestmark = pytest.mark.safety_gate


def _carry_psychoed(prev: dict, raw_message: str, **overrides) -> dict:
    """Same helper as test_psychoed_graph.py's module-local one (psychoed_* channels
    aren't in test_graph.py's own _CARRY_FIELDS, so this file carries them forward itself)."""
    carried = {k: prev.get(k) for k in _PSYCHOED_CARRY if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


def _mock_intent_route_factory(pinned: dict):
    """Deterministic per-turn intent, mutated via the `pinned` dict between ainvoke calls
    (mirrors test_psychoed_graph.py's _mock_intent_route, generalized to a mutable turn
    plan since this file's conversations mix multiple intents across turns)."""
    def _mock(state):
        return {
            "primary_intent": pinned["intent"],
            "secondary_intent": None,
            "intent_confidence": pinned.get("confidence", 0.9),
            "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7),
            "path": state["path"] + ["intent_route"],
        }
    return _mock


def _make_capturing_llm(response_text: str, calls: list):
    """Like tests/conftest.py's make_mock_llm, but also records the exact `messages` list
    passed to .ainvoke() on every call, so the L2-suppression pin can inspect the REAL
    composed prompt content (not just the graph's final response) for the one turn that
    matters. bind_tools() returns the same mock (freeflow_respond.py always calls
    llm.bind_tools(tools).ainvoke(messages); with tool_calls=[] the tool loop returns
    immediately after the first call, so calls[-1] is that turn's actual prompt)."""
    mock = MagicMock()
    mock.model_name = "mock-model"
    mock.openai_api_base = ""
    mock.bind_tools = MagicMock(return_value=mock)

    async def _ainvoke(*args, **kwargs):
        calls.append(args[0] if args else kwargs.get("input"))
        msg = MagicMock()
        msg.content = response_text
        msg.tool_calls = []
        return msg

    mock.ainvoke = AsyncMock(side_effect=_ainvoke)
    return mock


_FREEFLOW_STUB = (
    "You mentioned things feel heavy right now. What part of it is weighing on you most?"
)


# ---------------------------------------------------------------------------
# 1. Menu loop-back + served-topic marking + both check-in branches +
#    bridge-offer-mid-pathway (NAMED CASE: offer-mid-pathway L2 suppression).
# ---------------------------------------------------------------------------

async def test_menu_loopback_check_in_branches_and_bridge_offer_suppression(monkeypatch):
    """One continuous §1f session:

    T1 trigger -> menu offered (delivery_shape menu_first, no block yet).
    T2 pick "What is anxiety?" -> HIGH-2 shape: block 1f-b1 + check-in, NO framing/menu
       repeat. psychoed_blocks_served/family_exposures start accumulating.
    T3 "another topic" branch: pick "Why anxiety causes physical symptoms" -> block 1f-b3
       served; 1f-b1's own content is NOT re-served this turn (deterministic re-serve
       surface, not an LLM-memory claim -- see the NAMED EXCLUSION in the module docstring);
       psychoed_blocks_served accumulates to both picks.
    T4 "stop" branch: a generic decline that matches no menu_label and no global trigger.
       Falls straight through to freeflow_respond WITHOUT ever reaching skill_select this
       turn (verified via state["path"]) -- current as-built "stop" handling is simply "the
       reply doesn't resolve to anything," not a dedicated exit keyword. The pathway is NOT
       cleared by this (psychoed_pathway_clear only fires on specific exits: a non-psychoed
       skill activating, weave escalation, HR referral -- none of which happened), so
       psychoed_active_category survives, and freeflow_respond's psychoed_continuation
       override fires for this ordinary mid-pathway turn (delta 15 mechanism).
    T5 bridge-offer-mid-pathway: a box_breathing keyword trigger (see the module docstring's
       BRIDGE_MAP IS DEAD CODE note for why box_breathing's own keyword match, not the inert
       1f-b2 bridge_map entry, is what's actually exercised here) creates a consent-gated
       offer (offered_skill_ids set) while the pathway is still active. Asserts (a) the offer
       is created but NOT auto-activated (active_skill_id stays None -- R1's consent gate),
       and (b) the NAMED CASE pin: the composed prompt for this turn carries the generic
       psychoed_continuation glue, NOT the skill_offer template's structured named-option
       block -- the offer's own specific description text is absent from what the model saw.
    """
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"1f"}))

    pinned = {"intent": "info_request"}
    calls: list = []
    stub_llm = _make_capturing_llm(_FREEFLOW_STUB, calls)

    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route_factory(pinned)), \
         patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm):
        # build_graph() must run INSIDE the patch context (add_node captures a direct
        # reference to intent_route_node at call time -- test_psychoed_graph.py's pattern).
        graph = build_graph()
        manifest_1f = store.manifest("1f")

        # ── T1: trigger 1f (personal-framing global trigger; distinct from any block's own
        # menu_label so it can't be confused with a menu-pick later) ──────────────────────
        pinned["intent"] = "info_request"
        t1 = await graph.ainvoke(make_e2e_state("Why do I keep worrying?"))
        assert t1["psychoed_active_category"] == "1f"
        assert t1["psychoed_menu_offered"] is True
        assert t1["psychoed_blocks_served"] == []
        assert t1["psychoed_family_exposures"] == ["understanding_anxiety"]  # menu-first fallback family

        # ── T2: menu pick #1 -- HIGH-2 shape: block + check-in, no framing/menu repeat ──────
        t2 = await graph.ainvoke(_carry_psychoed(t1, "What is anxiety?"))
        assert t2["skill_match_method"] == "psychoed_resolver"
        assert t2["psychoed_matched_row_id"] == "menu_pick"  # HIGH-2's menu_pick marker
        assert t2["psychoed_blocks_served"] == ["1f-b1"]
        block_1f_b1 = store.get_block("1f-b1")["content"]
        assert block_1f_b1 in t2["response"], "block content must be served verbatim"
        assert manifest_1f["framing_statement"] not in t2["response"], (
            "HIGH-2: a menu-pick serve must NOT repeat the framing statement"
        )
        assert manifest_1f["menu_offer"] not in t2["response"], (
            "HIGH-2: a menu-pick serve must NOT repeat the menu offer"
        )

        # ── T3: check-in branch (a) "another topic" -- pick a second, different topic ──────
        t3 = await graph.ainvoke(_carry_psychoed(t2, "Why anxiety causes physical symptoms"))
        assert t3["skill_match_method"] == "psychoed_resolver"
        assert t3["psychoed_matched_row_id"] == "menu_pick"
        assert t3["psychoed_blocks_served"] == ["1f-b1", "1f-b3"], "accumulates across picks"
        assert t3["psychoed_family_exposures"] == ["understanding_anxiety"] * 3
        block_1f_b3 = store.get_block("1f-b3")["content"]
        assert block_1f_b3 in t3["response"], "the newly picked topic's content must be served"
        assert block_1f_b1 not in t3["response"], (
            "loop-back: the FIRST topic's own content must not be re-served on the turn "
            "that serves a different, second topic (deterministic re-serve surface, not an "
            "LLM-memory claim -- NAMED EXCLUSION, module docstring)"
        )

        # ── T4: check-in branch (b) "stop" -- a generic decline, no menu_label/trigger match.
        # Pinned general_chat at default (low) intensity so _route_after_intent's acute-
        # intensity redirect and the new_skill/info_request branches are all bypassed; the
        # message also carries no skill keyword, so no prepass hint fires either. Current
        # as-built routing sends this turn straight to freeflow_respond, never through
        # skill_select at all this turn. ─────────────────────────────────────────────────
        pinned["intent"] = "general_chat"
        calls.clear()
        t4 = await graph.ainvoke(
            _carry_psychoed(t3, "No, I think I'm okay for now, thanks", emotional_intensity=5)
        )
        assert "skill_select" not in t4["path"], (
            "as-built: an unresolved check-in reply never reaches the resolver this turn"
        )
        assert t4["psychoed_active_category"] == "1f", (
            "the pathway is NOT cleared by a non-matching reply -- pathway-clear only fires "
            "on specific exits (handoff delta 8), none of which happened here"
        )
        assert t4["psychoed_blocks_served"] == t3["psychoed_blocks_served"], "no new serve"
        continuation_content = get_intent_template("psychoed_continuation").content
        continuation_marker = "conversational glue only"
        assert continuation_marker in continuation_content, (
            "sanity: marker string still present in the live template (guards this test "
            "against silent template rewrites)"
        )
        assert calls, "freeflow LLM must have been invoked for the stop-branch turn"
        t4_user_prompt = next(m["content"] for m in calls[-1] if m["role"] == "user")
        assert continuation_marker in t4_user_prompt, (
            "delta 15: an ordinary mid-pathway turn composes with l2_intent_override="
            "'psychoed_continuation', not the primary_intent's own L2 template"
        )

        # ── T5: bridge-offer-mid-pathway (NAMED CASE: offer-mid-pathway L2 suppression) ────
        pinned["intent"] = "new_skill"
        calls.clear()
        t5 = await graph.ainvoke(_carry_psychoed(
            t4, "Can you help me breathe through this right now?", emotional_intensity=6,
        ))  # intensity kept below ACUTE_INTENSITY_FLOOR (8) so this is a CONSENT OFFER
        #     (default_offer rule), never acute_direct_entry's auto-enter.
        assert t5.get("offered_skill_ids") == ["box_breathing"], (
            "the offer must be CREATED (optional-not-automatic property; see the module "
            "docstring's BRIDGE_MAP IS DEAD CODE note for why this real mechanism, not the "
            "inert 1f-b2 bridge_map entry, is what stands in for 'the bridge offer' here)"
        )
        assert t5.get("active_skill_id") is None, (
            "no skill activation without a consent turn -- R1's offer-then-accept gate"
        )
        assert t5["psychoed_active_category"] == "1f", "pathway still active, un-hijacked"

        assert calls, "freeflow LLM must have been invoked for the offer turn"
        t5_user_prompt = next(m["content"] for m in calls[-1] if m["role"] == "user")
        box_breathing_blurb = composer._offer_descriptions()["box_breathing"]["description"]["en"]
        # NAMED CASE pin (KNOWN-DEGRADED, not endorsed -- see module docstring for the full
        # trace: freeflow_respond.py's l2_override is unconditional on psychoed_active_category,
        # and composer.py's l2_intent_override branch takes priority over the offered-skill
        # branch). Re-examine this assertion, do not silently rely on it, once a ticket lands.
        assert box_breathing_blurb not in t5_user_prompt, (
            "PINS current as-built behavior: the skill_offer template's structured, named "
            "options block is SUPPRESSED by the pathway-continuation override -- the offer's "
            "own specific description never reaches the composed prompt on this turn"
        )
        assert continuation_marker in t5_user_prompt, (
            "the generic psychoed_continuation glue renders instead of L2_skill_offer"
        )


# ---------------------------------------------------------------------------
# 2. Weave turn-boundary: menu deferred while the weave is pending, then
#    menu-after-weave once a clear-negative reply resolves it.
# ---------------------------------------------------------------------------

async def test_weave_turn_boundary_menu_deferred_then_menu_after_weave(monkeypatch):
    """Category 3c (safety_weave: true), mirroring tests/test_psychoed_graph.py's Task-13
    serve turn and tests/fixtures/psychoed/f4_weave.jsonl's F4-003 clear-no phrasing.

    T1: a personal-framing 3c trigger -> the weave fires (menu is DEFERRED to the next
        turn per spec §4.1 -- the response carries the weave question, not the menu).
    T2: "no, nothing like that" -- a genuine clear-negative (per data/psychoed/weave/
        psy_weave_1.en.json's clear_negative_patterns) that does NOT collide with any 3c
        menu_label (unlike bare "no" -- see the module docstring's MENU-LABEL COLLISION
        TICKET note). Resolves to the deferred menu-after-weave continuation.

    Uses per-turn audit addressing (both turns' rows captured and inspected individually,
    not just the last row -- per the task brief's instruction on run_fixture's chronological
    audit_rows), since the mid-conversation T1 row is what actually proves the weave FIRED
    with a question outstanding, distinct from T2's "cleared" row.
    """
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"3c"}))

    pinned = {"intent": "info_request"}
    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route_factory(pinned)), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit), \
         patch("sage_poc.graph.write_session_audit", new=_capture_audit):
        graph = build_graph()
        manifest_3c = store.manifest("3c")
        weave_question = store.shared_script("safety_weave_script")

        # ── T1: trigger -> weave fires, menu deferred ──────────────────────────────────────
        pinned["intent"] = "info_request"
        t1 = await graph.ainvoke(make_e2e_state("Why do I feel numb?"))
        assert t1["psychoed_weave_pending"] is True
        assert t1["psychoed_matched_row_id"] == "3c-t3"
        assert weave_question in t1["response"], "the weave question must be present"
        assert manifest_3c["menu_offer"] not in t1["response"], (
            "the menu must be DEFERRED this turn (weave fires instead)"
        )

        # ── T2: clear-no -> menu-after-weave (deferred menu now delivered) ─────────────────
        pinned["intent"] = "general_chat"  # any WEAVE_EVALUATOR_LABELS member; matches F4-003's sweep
        t2 = await graph.ainvoke(_carry_psychoed(t1, "no, nothing like that"))
        assert t2["psychoed_weave_pending"] is False
        assert t2["skill_match_method"] == "psychoed_menu_after_weave"
        assert t2["psychoed_menu_offered"] is True
        assert manifest_3c["menu_offer"] in t2["response"], (
            "the deferred menu is delivered verbatim once the weave clears"
        )

        # Per-turn audit addressing: T1's row (mid-conversation) must show the weave as
        # PENDING (a live question outstanding), not "fired" -- that only applies once
        # resolved. T2's row (the reply turn) shows "fired". Both checked individually,
        # not just audit_rows[-1].
        assert len(captured) == 2
        row_t1 = _build_session_audit_row(captured[0])
        row_t2 = _build_session_audit_row(captured[1])
        assert row_t1["psychoed_weave_state"] == "pending"
        assert row_t1["psychoed_matched_row_id"] == "3c-t3"
        assert row_t2["psychoed_weave_state"] == "fired"


# ---------------------------------------------------------------------------
# 3. Within-session carry-forward skip: 3 real §1f serves feed a live
#    psychoed_family_exposures value into step-policy rule 6.
# ---------------------------------------------------------------------------

async def test_within_session_carry_forward_skip_step_policy_rule6(monkeypatch):
    """Serves the §1f family 3 times through the real graph (menu + 2 topic picks, same
    shape as test 1 above), then feeds the REAL resulting psychoed_family_exposures into
    skill_executor.evaluate_step_policy for a fixture skill whose kb_ref is
    "understanding_anxiety" (1f's article_family -- see data/psychoed/blocks/en/1f/*.json).

    No shipped skill JSON sets kb_ref today (schema.py: "no skill JSON currently sets it
    (kb_ref additions to skill JSONs are packet-pending, ask 9)"), so the fixture skill here
    is act_psychological_flexibility (loaded unmodified from disk, nothing in src/ touched)
    with ONLY kb_ref patched on in memory via Skill.model_copy(update=...). This keeps rule
    6 itself completely real and unmodified -- step_policy[5] in that skill's own JSON is:
      {"signal": "prior_exposure", "operator": ">=", "value": 2, "step":
       "identify_the_struggle"} -> action "skip_psychoeducation"
    (the literal 6th declared rule, 1-indexed -- "step-policy rule 6" per the brief). Only
    the kb_ref field (currently unset everywhere) is injected so family-exposure carry-
    forward becomes computable; the skip mechanism itself is exercised exactly as shipped.

    DELTA 1 CITE: prior_exposure is computed via
    skill_executor._psychoed_family_exposure(state, skill), the live carry-forward channel
    that replaced the dead therapeutic_profile["techniques_used"] read (handoff notes §VI,
    delta 1) -- this test's prior_exposure value is entirely sourced from that channel.
    """
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"1f"}))

    pinned = {"intent": "info_request"}
    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route_factory(pinned)):
        graph = build_graph()

        t1 = await graph.ainvoke(make_e2e_state("Why do I keep worrying?"))
        t2 = await graph.ainvoke(_carry_psychoed(t1, "What is anxiety?"))
        t3 = await graph.ainvoke(_carry_psychoed(t2, "Why anxiety causes physical symptoms"))

    family_exposures = t3["psychoed_family_exposures"]
    assert family_exposures == ["understanding_anxiety"] * 3, "sanity: 3 real 1f serves"

    real_skill = load_skill("act_psychological_flexibility")
    fixture_skill = real_skill.model_copy(update={"kb_ref": "understanding_anxiety"})
    # Sanity: rule 6 (index 5, 1-indexed "the 6th rule") is the prior_exposure skip rule
    # this test targets -- fails loudly if the shipped skill's rule ordering ever changes.
    rule_6 = fixture_skill.step_policy[5]
    assert rule_6.condition.signal == "prior_exposure"
    assert rule_6.action == "skip_psychoeducation"
    assert rule_6.condition.step == "identify_the_struggle"

    prior_exposure = _psychoed_family_exposure({"psychoed_family_exposures": family_exposures}, fixture_skill)
    assert prior_exposure == 3, "family-exposure count carried forward from the real 1f serves"

    result = evaluate_step_policy(
        skill=fixture_skill,
        current_step_id="identify_the_struggle",
        emotional_intensity=5,
        engagement=7,
        message_en="I keep thinking about the same thing over and over.",
        prior_exposure=prior_exposure,
    )
    assert result["action"] == "skip_psychoeducation", (
        "step-policy rule 6 must fire and skip the psychoeducation step once prior_exposure "
        "(from the within-session family-exposure carry-forward) clears its threshold"
    )


# ---------------------------------------------------------------------------
# 4. Per-block guard contrast: s2c-b8's note present exactly once (single-
#    sourced, never duplicated), a sibling block carries no note at all.
# ---------------------------------------------------------------------------

def test_per_block_guard_note_single_sourcing_contrast():
    """Direct psychoed.serve.compose_turn1 calls (no graph needed -- this is pure store-
    driven composition, config-flag-independent). S2c is used here (see the module
    docstring's S2c NOTE): flag-ON-in-test is not a prod flip, and the S2c flip-gate that
    matters (data/psychoed/manifests/s2c.json's flip_gate_note) is content/clinical, not a
    code gate compose_turn1 reads.

    s2c-b8 ("How long does grief last?") is the only s2c block whose block_guard is set.
    Its guard note is ALREADY the block's own final sentence in the content field (single-
    sourcing discipline, handoff notes Addition 6) -- compose_turn1's guard-append only
    fires `if guard and guard["note"] not in block["content"]`, so serving s2c-b8 must
    produce the note text exactly once, never doubled. A sibling block (s2c-b2, guard=None)
    must carry no note text at all.
    """
    guard = store.get_block("s2c-b8")["psychoed"]["block_guard"]
    note = guard["note"]

    payload_b8 = {
        "category": "s2c", "block_id": "s2c-b8", "route": "standard",
        "menu_pick": True, "weave_due": False,
    }
    out_b8 = psy_serve.compose_turn1(payload_b8)
    assert out_b8["text"].count(note) == 1, (
        "the guard note must appear exactly once (single-sourced from block content, "
        "never appended a second time)"
    )

    assert store.get_block("s2c-b2")["psychoed"].get("block_guard") is None, (
        "sanity: the sibling block used for contrast carries no guard"
    )
    payload_b2 = {
        "category": "s2c", "block_id": "s2c-b2", "route": "standard",
        "menu_pick": True, "weave_due": False,
    }
    out_b2 = psy_serve.compose_turn1(payload_b2)
    assert note not in out_b2["text"], "a block with no guard must carry no guard note"
