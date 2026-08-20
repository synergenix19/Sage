import asyncio
import time
import json
import logging
from datetime import datetime, timezone
from typing import Callable, NamedTuple, Union

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sage_poc.state import SageState
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.intent_route import intent_route_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
from sage_poc.nodes.skill_select import skill_select_node, _psychoed_pathway_clear
from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node, knowledge_retrieve_cards_node
from sage_poc.nodes.medical_response import medical_response_node
from sage_poc.nodes.screen_response import screen_response_node
from sage_poc.nodes.high_risk_response import high_risk_response_node
from sage_poc.nodes.derealization_response import derealization_response_node
from sage_poc.config import CRISIS_LINE_UAE, CRISIS_CONFIG
from sage_poc.nodes.output_gate import output_gate_node
from sage_poc.audit import write_session_audit
from sage_poc.safety.hr_disclosure import hr_disclosure_present
from sage_poc.safety.derealization_disclosure import derealization_disclosure_present
# Task 2 (router precedence as data) hoist step: the four routers below each used to
# carry their own local `from sage_poc import config as _cfg` (or `_psy_cfg`) re-import,
# with a comment explaining it was a call-time read of the kill-switch, not a caching
# concern. A single top-level import gives the identical guarantee -- `_cfg.FLAG` is an
# attribute lookup on the same module object on every call, so a live flag flip (or
# monkeypatch.setattr(config, ...) in tests) is visible on the very next evaluation --
# without the per-function duplication.
from sage_poc import config as _cfg

_log = logging.getLogger(__name__)

# Routing-SF-2: emotional_intensity at or above this floor makes a general_chat turn
# reach skill_select (acute down-regulation skills). Matches the acute_direct_entry bar
# in skill_matching_rules.json (emotional_intensity >= 8), the clinically-approved
# threshold for acute handling. Adjust only with clinical sign-off.
ACUTE_INTENSITY_FLOOR: int = 8


# --- Router precedence tables (task-2-brief.md, ruling P2-2) ---------------------------
#
# Each of the four routers below used to be an ordered chain of guard-clause `if`s with
# heavy provenance comments pinning a clinically-signed precedence order (e.g.
# crisis > medical > hr > derealization). This is a SHAPE change only: every router now
# evaluates an explicit ordered tuple of RouteRule rows instead of nested ifs, which makes
# the precedence order directly assertable (`[r.name for r in ROUTE_AFTER_INTENT] == [...]`,
# see tests/test_router_precedence_pin.py) instead of only readable from the diff. The
# evaluation order and every predicate/destination are unchanged; the row order below is
# the ORIGINAL top-to-bottom order of the guard clauses it replaces, and reordering a row
# requires the same clinical review a routing change gets (see the pin test's own comment).
# tests/test_router_precedence_corpus.py pins the exact destination for 89 cases across the
# Amendment 4 spectrum, captured against the pre-refactor implementation, to prove this.
RouteDestination = Union[str, Callable[[SageState], str]]


class RouteRule(NamedTuple):
    """One rung of a router's precedence ladder, evaluated top-to-bottom.

    name:        the rung's identifier -- what a reorder review diffs against.
    enabled_fn:  zero-arg, evaluated fresh on every call (never cached at table-definition
                 time) so a live `_cfg.SOME_FLAG` kill-switch flip takes effect on the very
                 next turn, exactly like the original inline `_cfg.FLAG` reads did.
    predicate:   state -> bool, the rung's match condition. The enable gate is checked
                 first and short-circuits, so predicates never need to re-check their own
                 flag (though a few legitimately read a DIFFERENT flag internally, e.g. the
                 high_risk_disclosure row's inner HIGH_RISK_DETECTION_ENABLED check).
    destination: a fixed edge-key string, or state -> str for the handful of rungs whose
                 original branch chose between two destinations (e.g. exit_skill:
                 skill_executor if active_skill_id else freeflow).
    """
    name: str
    enabled_fn: Callable[[], bool]
    predicate: Callable[[SageState], bool]
    destination: RouteDestination


def _always() -> bool:
    """Shared enabled_fn for rungs with no config kill-switch (always live)."""
    return True


def _evaluate_route(table: "tuple[RouteRule, ...]", state: SageState) -> str:
    """Walk a precedence table top-to-bottom; the first enabled+matching rung wins.

    Every table below ends in an unconditional default rung (predicate always True), so
    this always returns before falling off the end -- mirrors the functions it replaces,
    which likewise always returned before reaching their own last line.
    """
    for rule in table:
        if rule.enabled_fn() and rule.predicate(state):
            dest = rule.destination
            return dest(state) if callable(dest) else dest
    raise AssertionError("route table exhausted without a default rung")  # pragma: no cover


def _get_crisis_review_pool():
    """Lazy accessor for asyncpg pool in _crisis_response_node."""
    try:
        from server import app  # noqa: PLC0415
        return getattr(app.state, "_db_pool", None)
    except Exception:
        return None


async def _crisis_response_node(state: SageState) -> dict:
    from sage_poc.rules import engine as rules_engine

    prior_crisis_state = state.get("crisis_state", "none")
    is_reescalation = prior_crisis_state == "monitoring"

    lang = state.get("detected_language", "en")

    # R4 (Vee 2026-08-18, SAGE_THIRD_PARTY_DEFERENCE, default OFF): a Layer-1-clean turn
    # carrying a third-party signal serves the helper-support content, never the
    # first-person crisis script. HARD boundaries (both tested): deference applies ONLY
    # when crisis_flags is empty — a co-occurring first-person flag means the
    # deterministic layer fired (F1's span-scoped suppression guarantees the compound
    # case), so the first-person script serves; and a locale with no signed third-party
    # content falls back toward crisis (acute script), never a missing-content hole.
    # Stage 1 is DELIVERY-CONTENT-ONLY: monitoring entry, gate path, audit, and the
    # review-queue notify are identical to the first-person case (monitoring semantics
    # for helper turns = flagged clinical question in the R4 decision request).
    from sage_poc import config as _cfg  # noqa: PLC0415 — call-time read of the kill-switch
    _third_party_deference = (
        _cfg.THIRD_PARTY_DEFERENCE_ENABLED
        and bool(state.get("third_party_crisis"))
        and not state.get("crisis_flags")
    )
    crisis_result = rules_engine.evaluate("crisis_content", {
        "language": lang,
        "crisis_level": "third_party" if _third_party_deference else "acute",
    })
    if _third_party_deference and not crisis_result.fired:
        crisis_result = rules_engine.evaluate("crisis_content", {
            "language": lang,
            "crisis_level": "acute",
        })

    if crisis_result.fired:
        response_text = crisis_result.fired[0].action["response_text"]
    else:
        # Hard fallback: should never fire if JSON files are present
        response_text = (
            f"Please reach out for support now. UAE: MoHAP Counselling Line {CRISIS_LINE_UAE} (free, {CRISIS_CONFIG['hours']}) or emergency: {CRISIS_CONFIG['emergency']}."
            if lang != "ar"
            else f"أرجوك تواصل مع خط وزارة الصحة {CRISIS_LINE_UAE} أو الطوارئ {CRISIS_CONFIG['emergency']} الآن."
        )

    path = state["path"] + ["crisis_response"]

    # PDPL audit completeness (#205 ADR): crisis_response -> END BYPASSES output_gate, where
    # latency_ms is stamped for every other path. Stamp it here too so the crisis audit record is
    # complete on the one path with the tightest budget — traceability admits no per-path exception
    # (verified 2026-07-08: crisis turns had latency_ms=NULL, 0/18, vs 56/56 non-crisis).
    _tsa = state.get("turn_started_at")
    # Psychoed Task 8 escalation exit: a PSY-WEAVE-1 escalation must persist its psychoed facts to
    # the audit row BEFORE the pathway state is cleared below (persist-before-clear, at the code
    # level, in that order). The psychoed_* facts are already in state, so **state already carries
    # them into the audit dict; this only patches on the disposition marker.
    _weave_escalation = bool(state.get("psychoed_weave_escalation"))
    _audit_task = asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "crisis",
        "crisis_state": "monitoring",
        "re_escalation_within_monitoring": is_reescalation,
        "latency_ms": int((time.monotonic() - _tsa) * 1000) if _tsa is not None else state.get("latency_ms"),
        **({"psychoed_weave_state": "escalated"} if _weave_escalation else {}),
    }))
    _audit_task.add_done_callback(
        lambda t: _log.warning("[crisis_response] session audit error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    async def _notify_crisis_review() -> None:
        user_id = state.get("user_id") or ""
        session_id_val = state.get("session_id") or ""
        if not user_id:
            _log.warning(
                "[crisis_response] skipping clinician_review_queue: no user_id in state "
                "(session=%s) — manual follow-up required", session_id_val
            )
            return
        # SF-1 charter condition 3 (op-check finding, 2026-08-16): every crisis activation
        # wrote the clinician_review_queue AND fired pg_notify with NO test-user exclusion —
        # a measurement campaign would page/numb the human reviewer surface at volume.
        # Same allowlist + same fail-loud semantics as the tripwire (is_test_user: empty
        # user_id is NON-test, so an unattributed real crisis still notifies).
        from sage_poc.safety.tripwire import is_test_user  # noqa: PLC0415
        if is_test_user(user_id):
            _log.info(
                "[crisis_response] test-user crisis activation (session=%s) — clinician "
                "review-queue notify SUPPRESSED (SF-1 op-check rule 2026-08-16)", session_id_val
            )
            return
        try:
            from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
            pool = _get_crisis_review_pool()
            if not pool:
                return
            notifier = PostgresNotifier(pool)
            await notifier.notify_review_required(
                user_id=user_id,
                session_id=session_id_val,
                reason=f"crisis flags: {', '.join(state.get('crisis_flags', []))}",
                source="layer1_safety",
                payload={"flags": state.get("crisis_flags", []) + state.get("clinical_flags", [])},
                severity="high",
            )
        except Exception as exc:
            _log.warning("[crisis_response] clinician_review_queue write failed: %s", exc)

    _notify_task = asyncio.create_task(_notify_crisis_review())
    _notify_task.add_done_callback(
        lambda t: _log.warning("[crisis_response] notify_crisis_review error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    if _cfg.AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CRISIS_RESPONSE",
            "turn": state.get("turn_count"),
            "detected_language": lang,
            "crisis_flags": state.get("crisis_flags", []),
            "clinical_flags": state.get("clinical_flags", []),
            "active_skill_cleared": state.get("active_skill_id"),
            "crisis_content_rule": crisis_result.fired[0].rule_id if crisis_result.fired else "fallback",
            "re_escalation_within_monitoring": is_reescalation,
        }
        _log.info("[graph] AUDIT:CRISIS %s", json.dumps(audit))

    history = state.get("conversation_history", []) + [
        {"role": "user", "content": state.get("message_en", state.get("raw_message", ""))},
        {"role": "assistant", "content": response_text},
    ]

    return {
        "is_safe": False,
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": None,
        "gate_path": "crisis",
        "response": response_text,
        "response_en": response_text,
        "path": path,
        "conversation_history": history,
        "turn_count": state.get("turn_count", 0) + 1,
        "crisis_state": "monitoring",
        "s7_result": None,
        "s7_method": None,
        "re_escalation_within_monitoring": is_reescalation,
        # output_gate is bypassed for crisis responses (routes to END directly).
        # Without this, the stale-check gap is measured from the pre-crisis turn,
        # potentially under-counting by the duration of the crisis turn itself.
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
        # HR-1 Stage 2 Task 4 (SG-2 reset): crisis piercing a mid-protocol high_risk_response
        # must leave NO stale marker on EITHER HR channel. Without this, a later turn that
        # re-reads a leftover hr_terminal_step ("await_distress"/"reask") would silently
        # reinterpret that turn's message as the pending distress reply instead of asking
        # fresh (the active-resumable bug's 4th appearance -- see medical_response.py's
        # active_skill_id precedent and _route_after_safety's HR re-entry check below).
        "hr_terminal_step": None,
        "hr_escalate_regardless": False,
        # Psychoed Task 8 escalation exit: ONLY when this turn is a PSY-WEAVE-1 escalation, AFTER
        # the audit above has persisted the psychoed facts, clear the pathway (survivors:
        # psychoed_blocks_served / psychoed_family_exposures) and reset the escalation flag so it
        # does not leak into the next turn. Scoped to the escalation case per the plan amendment —
        # an ordinary (non-weave) crisis intercept is out of this task's scope.
        **(_psychoed_pathway_clear(state) if _weave_escalation else {}),
        **({"psychoed_weave_escalation": False} if _weave_escalation else {}),
    }


ROUTE_AFTER_SAFETY: "tuple[RouteRule, ...]" = (
    RouteRule(
        "monitoring_reescalate",
        _always,
        # In monitoring: only re-escalate if S1-S6 fired directly or S7 classified a new crisis.
        # Tiering does NOT apply here (per reader-disposition table): any signal re-escalates.
        lambda state: state.get("crisis_state") == "monitoring"
        and (not state["is_safe"] or state.get("s7_result") == "NEW_CRISIS"),
        "crisis",
    ),
    RouteRule(
        "monitoring_stable",
        _always,
        lambda state: state.get("crisis_state") == "monitoring",
        "safe",
    ),
    RouteRule(
        "crisis_tiering_t1",
        lambda: _cfg.CRISIS_TIERING_ENABLED,
        # v7.1 tiering (flag-gated). A confident-English semantic-only signal is T1 (warm): route to
        # the normal graph with supportive posture, NOT crisis_response. is_safe stays False (truthful
        # detector record); routing authority is crisis_tier here. Flag OFF => this branch is skipped
        # and routing reads is_safe exactly as v7/master (Check B).
        lambda state: state.get("crisis_tier") == "T1",
        "safe",
    ),
    RouteRule(
        "not_safe",
        _always,
        lambda state: not state["is_safe"],
        "crisis",
    ),
    RouteRule(
        "medical_redflag",
        lambda: _cfg.MEDICAL_REDFLAG_GUARD_ENABLED,
        lambda state: bool(state.get("medical_flags")),
        "medical",
    ),
    RouteRule(
        "high_risk_disclosure",
        lambda: _cfg.HIGH_RISK_TERMINAL_ENABLED,
        # HR-1 Stage 2 Task 4: safety-exit altitude routing for high_risk_response, the 3rd
        # member of the SAFETY-EXIT class (crisis_response, medical_response, high_risk_response) --
        # routed here, straight to END, bypassing output_gate. Ratified precedence order is
        # crisis > medical > hr (BOT BEHAVIOUR / v7.1 precedence table), so both branches below
        # are placed AFTER the crisis and medical checks above: crisis and medical still return
        # first even when an HR disclosure/in-progress protocol also fired this turn. Both are
        # gated on HIGH_RISK_TERMINAL_ENABLED (kill-switch) so this whole block is inert when OFF,
        # keeping this function byte-identical to today (Check B) -- HR disclosures still route
        # via the Stage-1 path (_route_after_intent -> skill_select -> psychotic_referral).
        # Task 4 fix: one-shot guard, mirroring Stage 1's psychotic_referral_delivered
        # (_route_after_intent below, skill_select.py ~L626-627). clinical_flags is
        # flag-immutable-within-session (safety_check.py accumulates, never drops a
        # flag once set), so without this guard EVERY later turn in the session would
        # re-enter high_risk_response and re-ask the §1 distress question after the
        # protocol already delivered its terminal branch. hr_referral_delivered is set
        # by high_risk_response._deliver_branch only on an actual "higher"/"lower"
        # delivery, never on the re-ask, so mid-protocol turns are unaffected (the
        # RE-ENTRY branch below, keyed on hr_terminal_step, is intentionally left
        # unguarded). CLINICAL/PRODUCT CALL DEFERRED: whether a genuinely NEW HR
        # presentation later in the session should re-trigger after a delivered
        # referral is currently one-shot per session (matches Stage 1); revisit is a
        # clinician call, not decided here.
        lambda state: hr_disclosure_present(
            state.get("clinical_flags") or [], flag_enabled=_cfg.HIGH_RISK_DETECTION_ENABLED
        ) and not state.get("hr_referral_delivered"),
        "high_risk",
    ),
    RouteRule(
        "high_risk_reentry",
        lambda: _cfg.HIGH_RISK_TERMINAL_ENABLED,
        # Re-entry (turn 2+ of the deterministic 2-3 turn protocol): a persisted hr_terminal_step
        # means high_risk_response is mid-protocol and this turn's message is the pending
        # distress reply / re-ask reply. Checked AFTER "if not state['is_safe']: return 'crisis'"
        # above, so a mid-protocol SI turn still pierces to crisis, never back to HR (Finding 3) --
        # and _crisis_response_node clears hr_terminal_step/hr_escalate_regardless on that pierce,
        # so a later turn never silently resumes a stale await_distress/reask step.
        lambda state: bool(state.get("hr_terminal_step")),
        "high_risk",
    ),
    RouteRule(
        "derealization_disclosure",
        lambda: _cfg.DEREALIZATION_DETECTION_ENABLED,
        # §1c Part A: 4th SAFETY-EXIT member (derealization_response), rank 4 — placed AFTER the crisis,
        # medical, and hr checks above so those still win on a multi-hit turn (precedence
        # crisis > medical > hr > derealization). Gated on DEREALIZATION_DETECTION_ENABLED so this block
        # is inert when OFF (byte-identical). One-shot guard mirrors hr_referral_delivered: clinical_flags
        # persist for the session, so without it the referral would re-fire every later turn.
        lambda state: derealization_disclosure_present(
            state.get("clinical_flags") or [], flag_enabled=_cfg.DEREALIZATION_DETECTION_ENABLED
        ) and not state.get("derealization_referral_delivered"),
        "derealization",
    ),
    RouteRule("default_safe", _always, lambda state: True, "safe"),
)


def _route_after_safety(state: SageState) -> str:
    return _evaluate_route(ROUTE_AFTER_SAFETY, state)


def _intent(state: SageState) -> str:
    return state.get("primary_intent", "general_chat")


def _confidence(state: SageState) -> float:
    return state.get("intent_confidence", 1.0)


ROUTE_AFTER_INTENT: "tuple[RouteRule, ...]" = (
    RouteRule(
        "panic_grounding_override",
        _always,
        # Part A (Vee-signed 2026-07-28): deterministic panic-grounding override. When safety_check CLEARED
        # this turn but intent_route re-flagged a clear panic disclosure (no harm-adjacency) as crisis, restore
        # the deterministic verdict -> grounding via skill_select instead of crisis_response. Flag-gated: the
        # stamp is False when OFF, so this is byte-identical when disabled. Fires only on a safety_check-clean
        # turn, so it can NEVER suppress a crisis the deterministic tier caught (that path never reaches here as
        # intent=='crisis' with panic_grounding_override True — crisis_flags being set makes the override False).
        lambda state: _intent(state) == "crisis" and bool(state.get("panic_grounding_override")),
        "skill_select",
    ),
    RouteRule(
        "grief_presence_override",
        _always,
        # S2a grief-presence deference (built inert 2026-08-04): identical semantics one line down the
        # same crisis branch — safety_check CLEARED the turn, intent_route re-flagged a clear bereavement
        # disclosure (no harm-adjacency) as crisis; restore the clean verdict -> grief_loss presence path
        # via skill_select instead of crisis_response. Flag-gated (stamp is False when OFF, byte-identical);
        # crisis_flags being set (incl. the cardiac Node-1 flag) makes the stamp False, so this can never
        # suppress a crisis the deterministic tier caught.
        lambda state: _intent(state) == "crisis" and bool(state.get("grief_presence_override")),
        "skill_select",
    ),
    RouteRule(
        "selfworth_presence_override",
        _always,
        # S4b self-worth presence deference (DRAFT, gated on Vee signature, packet item 3): third
        # member of the same crisis-branch override family — safety_check CLEARED the turn, intent_route
        # re-flagged a self-worth/deservingness disclosure WITHOUT existence content as crisis
        # (S4B-FP-1: crisis card with crisis_flags=[], the iatrogenic direction for the S4a/S4b
        # self-compassion pathway); restore the clean verdict -> skill_select where the self-compassion
        # pathway can route. Flag-gated (stamp is False when OFF, byte-identical); crisis_flags being
        # set (incl. si_passive's better-off-without-me surface and the cardiac Node-1 flag) makes the
        # stamp False, so this can never suppress a crisis the deterministic tier caught.
        lambda state: _intent(state) == "crisis" and bool(state.get("selfworth_presence_override")),
        "skill_select",
    ),
    RouteRule(
        # Fallthrough default for the crisis branch above: intent == "crisis" with none of the
        # three overrides matched. Must stay immediately below the three override rows and
        # above everything else -- the original `if intent == "crisis":` block always returned
        # from within itself, so a crisis-intent turn never reached the D1/weave/EMR checks below.
        "crisis_intent_default",
        _always,
        lambda state: _intent(state) == "crisis",
        "crisis",
    ),
    RouteRule(
        "d1_answering_screen",
        _always,
        # #338 D1 ANSWER TURN: a turn answering a pending screen must reach skill_select so its answering_screen
        # handler classifies+routes the answer, REGARDLESS of intent (the answer usually reads as general_chat and
        # would otherwise go to freeflow unclassified — the 2026-07-20 seam). Below crisis (crisis supremacy), above
        # all intent routing. answering_screen is only ever set in enforce mode, so flag-off is byte-identical.
        lambda state: bool(state.get("answering_screen")),
        "skill_select",
    ),
    RouteRule(
        "psychoed_weave_pending",
        lambda: _cfg.PSYCHOED_PATHWAYS_ENABLED,
        # HIGH-1 (final review, psychoed Phase 2): a PSY-WEAVE-1 weave-pending reply must ALWAYS reach
        # skill_select, REGARDLESS of intent — modeled exactly on the answering_screen redirect immediately
        # above (same seam: a reply to a pending in-band question usually classifies as general_chat and
        # would otherwise fall through to freeflow, where PSY-WEAVE-1 never runs and the pending safety
        # check on the PREVIOUS turn's serve is silently starved -- the 2026-07-20 seam, spec §6.1). Placed
        # at the SAME priority as answering_screen (immediately below crisis, above all intent routing) --
        # not above it, and not above the crisis-intent check at the top of this function: if a weave-pending
        # turn ALSO classifies as intent=="crisis", the crisis branch above already returned "crisis" before
        # this line ever runs, so weave-pending correctly yields to a crisis intent classification (fail-
        # closed -- the reply still reaches crisis_response, just via the crisis branch, not skill_select).
        # skill_select_node's own PSY-WEAVE-1 evaluation (order item 1, spec §2.1 step 1) is what actually
        # judges the reply; this router only guarantees the reply ARRIVES there. This is graph-level ROUTING
        # decided from state TOWARD the evaluator -- the permitted direction (routing decisions may read
        # psychoed_* keys to decide where to send a turn); the safety NODES themselves (safety_check,
        # crisis_response, high_risk_response, derealization_response) still never read psychoed_* keys, so
        # the never-disarm invariant (state.py channel doc; handoff notes §I.4) is unaffected. Gated on
        # PSYCHOED_PATHWAYS_ENABLED (local import, same established per-turn-effective pattern as the
        # hr_disclosure_present check below): psychoed_weave_pending is only ever set by skill_select_node
        # under that same flag, so with the flag off this branch is unreachable and routing is byte-identical.
        lambda state: bool(state.get("psychoed_weave_pending")),
        "skill_select",
    ),
    RouteRule(
        "emr_modality_screen_pending",
        lambda: _cfg.MODALITY_REQUEST_ROUTING_ENABLED,
        # EMR screen resumption (2026-08-12): a turn answering the modality screen must reach
        # skill_select so the held request can deliver (or the adaptive screen continue) —
        # the same seam class as answering_screen/weave directly above (answers classify as
        # general_chat and would fall to freeflow, starving the hold). Same priority slot:
        # below crisis (crisis intent already returned above), below the D1 answer redirect
        # (disjoint by construction — EMR screens never set D1's screen_pending). Guarded on
        # active_skill_id; flag OFF -> the channel is never set, byte-identical.
        lambda state: bool(state.get("modality_screen_pending")) and not state.get("active_skill_id"),
        "skill_select",
    ),
    RouteRule(
        "scope_refusal",
        _always,
        lambda state: _intent(state) == "scope_refusal",
        "gate",
    ),
    RouteRule(
        "jailbreak",
        _always,
        # NOTE: jailbreak in monitoring state: persona reassertion takes priority.
        # crisis_state remains 'monitoring' — S7 will re-evaluate on the next turn.
        lambda state: _intent(state) == "jailbreak",
        "gate",
    ),
    RouteRule(
        "monitoring_priority",
        _always,
        # Post-crisis monitoring takes priority over confidence gating — short or fragmented
        # messages are expected after a crisis; route to skill_select regardless of confidence.
        lambda state: state.get("crisis_state") == "monitoring",
        "skill_select",
    ),
    RouteRule(
        "hr_disclosure_redirect",
        _always,
        # S2-10 (safety, clinical decision 2026-06-13): a pending psychotic referral forces
        # routing to skill_select, where psychotic_referral auto-selects. Without this, a
        # psychotic disclosure in general_chat register routes to freeflow, which engages
        # with the content unreferred. Bypasses the confidence gate (like monitoring) because
        # the redirect must not depend on classification confidence. Deterministic routing is
        # the gate; prompt adaptation is not (audit: L5 alone already failed).
        #
        # PRECEDENCE (merge #4 ⊕ #6/S2-10, 2026-06-13): this check is SENIOR to the R1
        # offer-accept branch below. If a psychotic disclosure co-occurs with a live skill
        # offer (e.g. the user accepts an offer in the same turn they disclose), the safety
        # referral must win — never let an engagement-layer accept short-circuit the referral.
        #
        # HR-1 Stage 1 Task 3: broadened via hr_disclosure_present so mania_disclosure and
        # dissociation_disclosure reach the same referral redirect as psychotic_disclosure.
        # psychotic_disclosure always routes (flag-independent); the other two are gated
        # behind HIGH_RISK_DETECTION_ENABLED. Flag OFF -> byte-identical to psychotic-only.
        lambda state: hr_disclosure_present(
            state.get("clinical_flags") or [], flag_enabled=_cfg.HIGH_RISK_DETECTION_ENABLED
        ) and not state.get("psychotic_referral_delivered"),
        "skill_select",
    ),
    RouteRule(
        "r1_offer_accept",
        _always,
        # R1: accept reply to a pending offer routes to skill_select for promotion.
        # Bypasses the confidence gate: bare accepts classify low-confidence by nature
        # (same precedent as post-crisis monitoring). Subordinate to the psychotic-referral
        # check above by design.
        lambda state: bool(state.get("offered_skill_ids") or []) and state.get("offer_response") == "accept",
        "skill_select",
    ),
    RouteRule(
        "f6_venting_suppression",
        lambda: _cfg.VENTING_SUPPRESSION_ENABLED,
        # F6: a venting / "just listen" turn must NOT be pulled into skill_select by the
        # intensity override or the prepass hint. PI-VI-001 detects it; this gives that detection
        # ROUTING AUTHORITY to keep it in presence (freeflow). Same class as B1's medical_response
        # leaving active_skill_id resumable: detection without authority over the skill layer.
        # Scoped to intent == "general_chat": new_skill and info_request are handled LATER in this
        # function (below), so without this guard an explicit skill/help request co-occurring with
        # a don't-fix keyword would be over-suppressed into freeflow — the exact failure mode this
        # feature must avoid. Crisis precedence and help-seeking new_skill are preserved.
        lambda state: _intent(state) == "general_chat"
        and bool(state.get("venting_detected"))
        and not state.get("active_skill_id"),
        "freeflow",
    ),
    RouteRule(
        "routing_sf2_acute_intensity",
        _always,
        # Routing-SF-2 (intent-route intensity): acute distress classified as general_chat
        # must still reach skill_select so the acute down-regulation skills (dbt_tipp,
        # grounding_5_4_3_2_1) can keyword-match. intent_route already emits
        # emotional_intensity; routing previously ignored it, sending high-intensity
        # general_chat to freeflow where no skill is ever offered. Placed after the
        # monitoring/psychotic redirects and before the confidence gate: an acute redirect
        # must not depend on classification confidence. Safe fallthrough: no acute keyword
        # match -> skill_select -> freeflow (_route_after_skill_select), unchanged worst case.
        # Guarded on active_skill_id: mid-skill turns fall through to freeflow (preserving the
        # checkpoint), matching the new_skill/skill_continuation handling below and the
        # test_mid_skill_off_topic invariant. (Under R1, "reach skill_select" yields a consent
        # offer of the acute skill, not silent activation — consistent with the offer model.)
        lambda state: _intent(state) == "general_chat"
        and not state.get("active_skill_id")
        and state.get("emotional_intensity", 5) >= ACUTE_INTENSITY_FLOOR,
        "skill_select",
    ),
    RouteRule(
        "node2_prepass_hint",
        _always,
        # v7.2 Node-2 keyword pre-pass HINT: a general_chat turn the classifier would send to freeflow,
        # but whose message deterministically matched a skill trigger (pre-pass), reaches skill_select so
        # the skill can offer/enter per R1. Mirrors the Routing-SF-2 slot+guards exactly: after the
        # safety/monitoring/psychotic redirects, before the confidence gate; guarded on active_skill_id
        # (mid-skill turns fall through, preserving the checkpoint). Hint, not hijack — primary_intent is
        # unchanged; info_request already reaches skill_select on its own, so this targets general_chat.
        lambda state: _intent(state) == "general_chat"
        and not state.get("active_skill_id")
        and bool(state.get("prepass_matched") or []),
        "skill_select",
    ),
    RouteRule(
        "emr_modality_request_redirect",
        lambda: _cfg.MODALITY_REQUEST_ROUTING_ENABLED,
        # EMR redirect (plan 2026-07-28: "an explicit modality request, in a screened context,
        # always resolves against the clinical binding table — regardless of which way the LLM
        # intent classifier lands"). Same slot + guards as the prepass hint above, but for ALL
        # intents that would otherwise miss skill_select (incl. the route-with-release turn,
        # whose classification is unpredictable by design). Guarded on active_skill_id: a
        # mid-skill request is surface-1 (executor) territory and falls through unchanged.
        # Subordinate by ORDER to crisis, the D1/weave redirects, monitoring, the psychotic/HR
        # referral, and the F6 venting hold above — all of them return before this line.
        # Flag OFF -> the channel is None, branch unreachable, routing byte-identical.
        lambda state: not state.get("active_skill_id")
        and bool((state.get("explicit_modality_request") or {}).get("requested")),
        "skill_select",
    ),
    RouteRule(
        "low_confidence_gate",
        _always,
        lambda state: _confidence(state) < 0.6,
        "low_confidence",
    ),
    RouteRule(
        "exit_skill",
        _always,
        lambda state: _intent(state) == "exit_skill",
        lambda state: "skill_executor" if state.get("active_skill_id") else "freeflow",
    ),
    RouteRule(
        "new_skill",
        _always,
        # If a skill is already active, don't re-run selection — skill_select would
        # either pick a different skill (hijack) or find no match and write
        # active_skill_id=None, clearing the checkpoint for the next turn.
        lambda state: _intent(state) == "new_skill",
        lambda state: "skill_executor" if state.get("active_skill_id") else "skill_select",
    ),
    RouteRule(
        "info_request",
        _always,
        lambda state: _intent(state) == "info_request",
        "skill_select",
    ),
    RouteRule(
        "skill_continuation",
        _always,
        lambda state: _intent(state) == "skill_continuation" and bool(state.get("active_skill_id")),
        "skill_executor",
    ),
    RouteRule("default_freeflow", _always, lambda state: True, "freeflow"),
)


def _route_after_intent(state: SageState) -> str:
    return _evaluate_route(ROUTE_AFTER_INTENT, state)


ROUTE_AFTER_SKILL_SELECT: "tuple[RouteRule, ...]" = (
    RouteRule(
        "psychoed_weave_escalation",
        _always,
        # Psychoed Task 8, TOP priority: PSY-WEAVE-1 escalated a weave-pending reply to crisis. This
        # must win over every other branch below (containment, screen, abstain, info_request, active
        # skill) — a live safety escalation is never allowed to be shadowed by a routing decision.
        # skill_select_node sets this only under PSYCHOED_PATHWAYS_ENABLED, so flag-off is unreachable.
        lambda state: bool(state.get("psychoed_weave_escalation")),
        "crisis_response",
    ),
    RouteRule(
        "containment_directive",
        _always,
        # Phase-2 T3: a fired containment directive routes to the containment pathway —
        # knowledge_retrieve seeds the family KB, then the existing knowledge_retrieve→freeflow edge
        # composes the L3/L4 template (validate→psychoeducate→differentiate→refer→engage). Checked
        # FIRST here, which is already DOWNSTREAM of the Node-1 crisis short-circuit: _route_after_safety
        # sends a crisis to crisis_response BEFORE skill_select (hence this router) ever runs, so crisis
        # supremacy over an overlapping containment pattern is STRUCTURAL (AC-CRISIS-SUPREMACY), not a
        # priority compare here. contain also supersedes abstain (belt-and-suspenders vs T2's node-level
        # mutual exclusion). DORMANT until a family declares skill_select_disposition "contain" (T4);
        # containment_directive is None every turn until then, so this is byte-identical to master.
        # The guided-skill (skill_id) variant is deferred: T2 sets active_skill_id=None, so a
        # skill_executor route would be dead — the reference OCD family uses the KB path below.
        lambda state: bool(state.get("containment_directive")),
        "knowledge_retrieve",
    ),
    RouteRule(
        "psychoed_serve",
        _always,
        # Psychoed Task 8: a resolver serve, or the deferred menu-after-weave continuation, routes to
        # knowledge_retrieve the same way an info_request does — the composer renders the psychoed
        # payload / menu there. skill_select_node sets these only under PSYCHOED_PATHWAYS_ENABLED, so
        # flag-off is unreachable and this branch never fires with the flag off.
        lambda state: bool(state.get("psychoed_serve")) or state.get("skill_match_method") == "psychoed_menu_after_weave",
        "knowledge_retrieve",
    ),
    RouteRule(
        "d1_screen_served",
        _always,
        # #338 D1: a SERVED screen question is terminal for this turn. apply_screen_at_route (enforce path) set
        # screen_question_text + active_skill_id=None on an ask_screen decision; the question IS this turn's
        # output. Below containment (crisis > vetoes > containment > screen > routing), above skill routing.
        # Flag-gated upstream: screen_question_text is set only when SAGE_D1_SCREEN (enforce) is on, OR — since
        # EMR Phase 2 surface 2 — when SAGE_MODALITY_REQUEST_ROUTING is on and the section-1a screen is pending
        # (skill_select serves the signed screen question through this same verbatim terminal; audit rows are
        # distinguished by the modality_request_screen_pending path marker). Both flags off -> unreachable,
        # graph byte-identical to master.
        lambda state: bool(state.get("screen_question_text")),
        "screen_response",
    ),
    RouteRule(
        "v2_abstain",
        _always,
        # V2 reranker ABSTAIN (below-τ semantic OR keyword-veto) → Node 3 low_confidence_respond, NOT
        # freeflow (Cardinal Rule 5). The clinician's −4.7pp recall acceptance rests on lost cases being
        # recoverable soft-abstains that land in Node 3's empathic clarification, and the signed
        # soft-abstain-recovery monitoring assumes it. skill_select sets this key only under
        # _rerank_enabled(); _build_state resets it False each turn (per-turn, like path) so a prior
        # turn's abstain never leaks into a later skill turn. Flag-off never sets it → V1 path unchanged.
        lambda state: bool(state.get("skill_select_abstained")),
        "low_confidence",
    ),
    RouteRule(
        "info_request_consult_cards",
        lambda: _cfg.CONSULT_SOURCES_ENABLED,
        # info_request routes to knowledge_retrieve regardless of active skill — the
        # skill_select node preserves active_skill_id, so the skill survives this turn.
        # Psychoed Mechanism-A (2026-07-17 design doc): EXCEPT when skill_select's
        # info_request consult SELECTED a skill this turn (skill_match_method ==
        # "info_request_skill_consult") — that turn routes to skill_executor instead. Keyed
        # on skill_match_method, NOT active_skill_id alone: a pre-existing active_skill_id
        # (preserved by skill_select for the "resume next turn" case) must not, by itself,
        # change this turn's KB routing — only a consult SELECTED THIS turn does.
        # FLAG-GATED upstream: skill_select_node only ever sets skill_match_method to
        # "info_request_skill_consult" when config.INFO_REQUEST_CONSULT_ENABLED is True
        # (default OFF). No code change needed here — this branch is already keyed on that
        # exact string, so with the flag OFF it is unreachable and this function returns
        # "knowledge_retrieve" for info_request exactly as before the consult existed.
        #
        # C1 (SAGE_CONSULT_SOURCES, ruling 2026-07-29): a consult-selected turn detours
        # through cards-only retrieval, then proceeds to skill_executor via the static
        # knowledge_retrieve_cards -> skill_executor edge. SEQUENTIAL insertion, not a
        # parallel branch, deliberately: skill_executor's conditional router
        # (_route_after_skill_executor) must remain the SOLE post-executor authority — a
        # parallel cards branch would carry its own unconditional edge into the join and
        # fire even on a crisis re-escalation diversion, re-opening the state-channel-seam
        # class. Retrieval is a sub-second DB call; topology safety wins over §10 fan-out
        # purity here. Local import so monkeypatch.setattr(config, ...) works in tests.
        lambda state: state.get("primary_intent") == "info_request"
        and state.get("skill_match_method") == "info_request_skill_consult",
        "knowledge_retrieve_cards",
    ),
    RouteRule(
        "info_request_consult_no_cards",
        _always,
        # Same predicate as info_request_consult_cards, minus the CONSULT_SOURCES_ENABLED gate: this
        # row only ever fires when that row's enabled_fn was False (flag off), reproducing the
        # original `if config.CONSULT_SOURCES_ENABLED: return cards; return skill_executor` else-branch.
        lambda state: state.get("primary_intent") == "info_request"
        and state.get("skill_match_method") == "info_request_skill_consult",
        "skill_executor",
    ),
    RouteRule(
        "info_request_plain",
        _always,
        # The explanatory block on info_request_consult_cards above (two rows up) describes
        # this row's behavior, not just that one's -- it explains the general
        # info_request -> knowledge_retrieve routing that this row implements for the
        # non-consult case. See that comment for the full rationale.
        lambda state: state.get("primary_intent") == "info_request",
        "knowledge_retrieve",
    ),
    RouteRule(
        "active_skill_resume",
        _always,
        lambda state: bool(state.get("active_skill_id")),
        "skill_executor",
    ),
    RouteRule("default_freeflow", _always, lambda state: True, "freeflow"),
)


def _route_after_skill_select(state: SageState) -> str:
    return _evaluate_route(ROUTE_AFTER_SKILL_SELECT, state)


ROUTE_AFTER_SKILL_EXECUTOR: "tuple[RouteRule, ...]" = (
    RouteRule(
        "reescalation_within_monitoring",
        _always,
        lambda state: bool(state.get("re_escalation_within_monitoring")),
        "crisis",
    ),
    RouteRule(
        "emr_rehand",
        _always,
        # EMR surface 1 rehand: the executor exited on a request-for-alternative (its own
        # escalation record carries the action) -> the request reaches skill_select, where
        # the shared delivery gate produces the screened binding-table offer. Below crisis
        # (unchanged, first). The action string is only ever written under
        # SAGE_MODALITY_REQUEST_ROUTING, so flag-off routing is byte-identical.
        lambda state: (state.get("escalation_triggered") or {}).get("action") == "exit_with_rehand",
        "skill_select",
    ),
    RouteRule("default_freeflow", _always, lambda state: True, "freeflow"),
)


def _route_after_skill_executor(state: SageState) -> str:
    return _evaluate_route(ROUTE_AFTER_SKILL_EXECUTOR, state)


def _route_after_output_gate(state: SageState) -> str:
    # output_gate is terminal. The banned-opener freeflow re-entry was removed in #58: opener
    # remediation is now an inline rewrite/pass-through inside output_gate (no second generation).
    # Crisis never reaches here (routes to END at safety_check); stylistic retry never applied to it.
    return END


def build_graph(checkpointer=None) -> CompiledStateGraph:
    graph = StateGraph(SageState)

    graph.add_node("safety_check", safety_check_node)
    graph.add_node("intent_route", intent_route_node)
    graph.add_node("low_confidence_respond", low_confidence_respond_node)
    graph.add_node("skill_select", skill_select_node)
    graph.add_node("knowledge_retrieve", knowledge_retrieve_node)
    graph.add_node("knowledge_retrieve_cards", knowledge_retrieve_cards_node)  # C1 cards-only (SAGE_CONSULT_SOURCES)
    graph.add_node("skill_executor", skill_executor_node)
    graph.add_node("freeflow_respond", freeflow_respond_node)
    graph.add_node("output_gate", output_gate_node)
    graph.add_node("crisis_response", _crisis_response_node)
    graph.add_node("medical_response", medical_response_node)
    graph.add_node("high_risk_response", high_risk_response_node)
    graph.add_node("derealization_response", derealization_response_node)  # §1c Part A anxiety-track terminal
    graph.add_node("screen_response", screen_response_node)  # #338 D1 terminal (enforce path)

    graph.set_entry_point("safety_check")

    graph.add_conditional_edges("safety_check", _route_after_safety, {
        "safe": "intent_route",
        "crisis": "crisis_response",
        "medical": "medical_response",
        "high_risk": "high_risk_response",
        "derealization": "derealization_response",
    })
    graph.add_edge("crisis_response", END)
    graph.add_edge("medical_response", END)
    graph.add_edge("high_risk_response", END)
    graph.add_edge("derealization_response", END)

    graph.add_conditional_edges("intent_route", _route_after_intent, {
        "skill_select": "skill_select",
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
        "crisis": "crisis_response",
        "low_confidence": "low_confidence_respond",
        "gate": "output_gate",
    })
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "knowledge_retrieve": "knowledge_retrieve",
        "knowledge_retrieve_cards": "knowledge_retrieve_cards",  # C1: consult turn detour, flag-gated in the router
        "low_confidence": "low_confidence_respond",
        "freeflow": "freeflow_respond",
        "screen_response": "screen_response",   # #338 D1: served screen question → terminal
        "crisis_response": "crisis_response",   # Psychoed Task 8: PSY-WEAVE-1 escalation
    })
    graph.add_edge("screen_response", END)
    graph.add_edge("knowledge_retrieve", "freeflow_respond")
    # C1: cards retrieval is a sequential detour INTO skill_executor, whose conditional router
    # stays the sole post-executor authority (crisis re-escalation etc.) — see the router comment.
    graph.add_edge("knowledge_retrieve_cards", "skill_executor")

    graph.add_conditional_edges("skill_executor", _route_after_skill_executor, {
        "crisis": "crisis_response",
        "freeflow": "freeflow_respond",
        "skill_select": "skill_select",   # EMR surface-1 rehand (exit_with_rehand only)
    })
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_conditional_edges("output_gate", _route_after_output_gate, {
        END: END,
    })

    return graph.compile(checkpointer=checkpointer)
