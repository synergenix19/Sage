"""Phase 0 characterization of the BOT BEHAVIOUR §1a presence_only gap (skill-request delivery).

Replays the observed 3-turn transcript (tests/fixtures/conformance/1a_transcript_replay.json)
through the REAL compiled graph (app.ainvoke, one session thread), reusing the same invocation
pattern as scripts/bot_behaviour_audit/measure_layer1_fullgraph.py (NOT skill_select isolation).

Per turn it dumps: primary_intent, secondary_intent, emotional_intensity, intent_confidence,
full node path (state["path"]), whether skill_select executed, the Tier-1 keyword candidate
list, the Tier-2 semantic best score + skill id vs SEMANTIC_THRESHOLD, offered_skill_ids,
active_skill_id, and the safety channels. Tier-1/Tier-2 readouts are POST-HOC re-runs of the
exact matcher helpers skill_select uses (match_skill_keywords, _semantic_match_with_runner_up)
on the turn's message_en — deterministic, same warmed BGE-M3 index.

Also runs the Phase 0 Q6 probe ("i have crushing chest pain and it's spreading to my arm") on a
SEPARATE session thread and records the full path + user-visible outcome (medical-guard vs
anxiety/freeflow routing).

RAW EVIDENCE ONLY: this script interprets nothing. The decision-gate memo (Task 2) does that.

Usage (flags below mirror the prod serving set; everything else = config.py defaults):
  uv run python scripts/characterize_1a_gap.py [--json <out.json>] [--skip-q6]
"""
import os

# Prod serving flag parity (per prod deploy record, 2026-07-28): these three are true in prod;
# every other flag rides its config.py default. setdefault so an operator export still wins,
# and the resolved set is printed below either way. MUST run before any sage_poc import —
# config.py reads the environment at import time.
os.environ.setdefault("SAGE_HIGH_RISK_DETECTION", "true")
os.environ.setdefault("SAGE_HR_NEUTRALITY_GATE", "true")
os.environ.setdefault("SAGE_INFO_REQUEST_CONSULT", "true")
# F10 (code_review.md 2026-08-17): the V2 routing flags are read from os.environ at CALL
# TIME inside skill_select / skill_rerank_model — NOT config.py — and prod has served
# V2+reranker since 07-08 (V2-live register). Omitting them here was the 3rd recurrence
# of the recorded "V2-off locals false-passed" instrument defect: the replay measured a
# V1/reranker-off router while the header asserted parity. setdefault: operator wins.
os.environ.setdefault("SKILL_ROUTING_V2", "1")
os.environ.setdefault("SKILL_RERANK_ENABLED", "1")
os.environ.setdefault("SKILL_RERANK_PRECISION", "fp32")
# Local-instrument deviation (recorded, non-routing): suppress session_audit writes so a local
# characterization run never inserts rows into the prod Supabase audit table. AUDIT_LOG_ENABLED
# gates nothing on the routing path; write_session_audit also no-ops without SUPABASE_URL.
os.environ.setdefault("SAGE_AUDIT_LOG", "false")

import argparse
import asyncio
import json
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests/fixtures/conformance/1a_transcript_replay.json")
Q6_PROBE = "i have crushing chest pain and it's spreading to my arm"

from sage_poc import config as _c
from sage_poc.graph import build_graph
import sage_poc.nodes.skill_select as ss
from langgraph.checkpoint.memory import MemorySaver

import numpy as np


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


def resolved_flags() -> dict:
    """Every boolean flag config resolved at import, plus the routing constants + models."""
    flags = {
        name: val
        for name, val in sorted(vars(_c).items())
        if name.isupper() and isinstance(val, bool)
    }
    flags["SEMANTIC_THRESHOLD (skill_select)"] = ss.SEMANTIC_THRESHOLD
    flags["CLASSIFIER_MODEL"] = _c.CLASSIFIER_MODEL
    flags["RESPONDER_MODEL"] = _c.RESPONDER_MODEL
    # F10: call-time env flags via the enumerator's LIVE readers (effective values, never
    # module constants) — the stamp can no longer silently omit a routing flag
    # (enforced repo-wide by scripts/check_env_flag_enumeration.py).
    from sage_poc.env_flags import effective_env_flags  # noqa: PLC0415
    flags["env_flags (effective, call-time readers)"] = effective_env_flags()
    return flags


def tier1_keyword_matches(message_en: str, raw_message: str, lang: str) -> dict:
    """POST-HOC: the exact Tier-1 shared matcher skill_select runs (match_skill_keywords)."""
    return ss.match_skill_keywords(message_en.lower(), (raw_message or "").lower(), lang)


def tier2_ranked(message_en: str) -> list:
    """POST-HOC: raw Tier-2 ranked (skill_id, cosine) exactly as _semantic_match_with_runner_up
    computes it before the route decision (max-over-anchors; V2 debias only if flag-on)."""
    ss._ensure_semantic_ready()
    if ss._anchor_embeddings is None or not message_en.strip():
        return []
    emb = ss._embed_model.encode([message_en], normalize_embeddings=True)[0]
    raw = np.dot(ss._anchor_embeddings, np.array(emb, dtype=np.float32))
    skill_scores: dict = {}
    for i, sid in enumerate(ss._anchor_skill_ids):
        s = float(raw[i])
        if s > skill_scores.get(sid, 0.0):
            skill_scores[sid] = s
    if ss._v2_enabled():
        skill_scores = ss._apply_anchor_debias(skill_scores, ss._anchor_counts())
    return sorted(skill_scores.items(), key=lambda x: -x[1])


def tier2_route_decision(message_en: str, lang: str) -> dict:
    """POST-HOC: the full Tier-2 route decision (threshold gate / cluster argmax / abstain)."""
    best, score, runner_up = ss._semantic_match_with_runner_up(message_en, "", lang)
    return {"best_skill_id": best, "best_score": round(score, 4),
            "runner_up": [runner_up[0], round(runner_up[1], 4)] if runner_up else None,
            "SEMANTIC_THRESHOLD": ss.SEMANTIC_THRESHOLD,
            "above_threshold": score >= ss.SEMANTIC_THRESHOLD}


async def drive(app, msg: str, tid: str) -> dict:
    # F11 (code_review.md 2026-08-17): per-turn input built by the SERVING path's own
    # _build_state via a thin adapter over the request shape — never a replicated reset
    # slice. The previous bare {"raw_message", "path"} input bypassed the ~30-key per-turn
    # reset, so turn-N readouts reported turn-N-1's checkpointed values (skill_match_method,
    # semantic_score, ...) whenever a writer node was skipped — the #338 stale-leak class,
    # inside the instrument whose whole job is observing those keys.
    from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike  # noqa: PLC0415
    req = _RequestLike(messages=[_MessageLike(role="user", content=msg)], session_id=tid)
    return await app.ainvoke(
        _build_state(req),
        config={"configurable": {"thread_id": tid}},
    )


def readout(turn_no: int, user_msg: str, r: dict) -> dict:
    message_en = r.get("message_en") or user_msg
    lang = r.get("detected_language") or "en"
    path = r.get("path") or []
    excluded = bool(ss._SEMANTIC_EXCLUSION_RE.search(message_en.lower()))
    block = {
        "turn": turn_no,
        "user_message": user_msg,
        "detected_language": lang,
        "message_en": message_en,
        "primary_intent": r.get("primary_intent"),
        "secondary_intent": r.get("secondary_intent"),
        "intent_confidence": r.get("intent_confidence"),
        "emotional_intensity": r.get("emotional_intensity"),
        "engagement": r.get("engagement"),
        "path": path,
        "skill_select_executed": "skill_select" in path,
        "gate_path": r.get("gate_path"),
        "skill_match_method": r.get("skill_match_method"),
        "semantic_score_in_state": r.get("semantic_score"),
        "skill_select_abstained": r.get("skill_select_abstained"),
        "offered_skill_ids": r.get("offered_skill_ids"),
        "active_skill_id": r.get("active_skill_id"),
        "completed_skill_id": r.get("completed_skill_id"),
        "active_step_id": r.get("active_step_id"),
        "crisis_flags": r.get("crisis_flags"),
        "medical_flags": r.get("medical_flags"),
        "clinical_flags": r.get("clinical_flags"),
        "crisis_tier": r.get("crisis_tier"),
        "venting_detected": r.get("venting_detected"),
        "precedence_winner": r.get("precedence_winner"),
        "fired_safety_routes": r.get("fired_safety_routes"),
        "prepass_matched": r.get("prepass_matched"),
        "abstain_referral": r.get("abstain_referral"),
        "screen_asked": r.get("screen_asked"),
        "screen_question_text": r.get("screen_question_text"),
        "screen_answer_class": r.get("screen_answer_class"),
        "screen_branch_taken": r.get("screen_branch_taken"),
        "screen_shadow_action": r.get("screen_shadow_action"),
        "screen_shadow_answer_class": r.get("screen_shadow_answer_class"),
        "screen_shadow_branch": r.get("screen_shadow_branch"),
        "session_screen_answer": r.get("session_screen_answer"),
        "screen_pending": r.get("screen_pending"),
        "answering_screen": r.get("answering_screen"),
        "knowledge_abstain": r.get("knowledge_abstain"),
        "knowledge_source": r.get("knowledge_source"),
        "posthoc_tier1_keyword_matches": tier1_keyword_matches(message_en, r.get("raw_message") or user_msg, lang),
        "posthoc_semantic_exclusion_guard_hit": excluded,
        "posthoc_tier2_top5": [[sid, round(s, 4)] for sid, s in tier2_ranked(message_en)[:5]],
        "posthoc_tier2_route_decision": tier2_route_decision(message_en, lang),
        "response_en": r.get("response_en"),
    }
    return block


def print_block(title: str, block: dict) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    print(json.dumps(block, indent=2, ensure_ascii=False, default=str))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=FIXTURE)
    ap.add_argument("--json", default=None)
    ap.add_argument("--skip-q6", action="store_true")
    args = ap.parse_args()

    if not os.getenv("OPENROUTER_API_KEY"):
        print("FATAL: OPENROUTER_API_KEY missing — the graph's intent classifier cannot run. "
              "STOP; do not fabricate readouts.", file=sys.stderr)
        sys.exit(2)

    sha = _git_sha()
    fixture = json.load(open(args.fixture))
    flags = resolved_flags()
    prov = {"sha": sha, "case_id": fixture["case_id"], "fixture": os.path.relpath(args.fixture, REPO),
            "instrument": "FULL-GRAPH app.ainvoke, one session thread (measure_layer1_fullgraph pattern); "
                          "tier readouts are post-hoc re-runs of skill_select's own matcher helpers",
            # The artifact carries its own epistemic status (owner condition, 2026-08-18) — same
            # principle as the oracle stamp printing verbatim: the record must not overclaim.
            "epistemic_status": "SINGLE-WINDOW LLM-routed replay: the intent classifier is live and "
                                "unpinned, so LLM-classified rows are evidence-not-bound; pins "
                                "stabilize within-window only, and stability claims require >=2 "
                                "separated windows (window-bounded verification rule). Deterministic-"
                                "tier readouts (keyword matches, semantic scores under the stamped "
                                "config) do not carry this caveat.",
            "resolved_flags": flags}
    print_block("PROVENANCE + RESOLVED FLAG SET", prov)

    t0 = time.time()
    app = build_graph(MemorySaver())
    # Instrument fidelity (same as measure_layer1_fullgraph): prod warms BGE-M3 at startup;
    # pre-warm so every turn is measured with the same semantic layers prod serves.
    ss._ensure_semantic_ready()
    try:
        from sage_poc.safety import s3_semantic as _s3
        _s3._ensure_s3_ready()
    except Exception as e:  # noqa: BLE001
        print(f"(s3 warm note: {str(e)[:100]})", flush=True)
    print(f"[{time.time() - t0:.0f}s] graph built + BGE-M3 warmed", flush=True)

    out = {"provenance": prov, "session_turns": [], "q6_probe": None, "faults": []}

    tid = f"1a-char-{sha[:7]}"
    for i, msg in enumerate(fixture["turns"], start=1):
        try:
            r = await drive(app, msg, tid)
            block = readout(i, msg, r)
        except Exception as e:  # noqa: BLE001
            block = {"turn": i, "user_message": msg, "FAULT": repr(e)[:400]}
            out["faults"].append(block)
        out["session_turns"].append(block)
        print_block(f"TURN {i}/3 (session thread {tid})", block)

    if not args.skip_q6:
        q6_tid = f"1a-q6-{sha[:7]}"
        try:
            r = await drive(app, Q6_PROBE, q6_tid)
            q6 = readout(1, Q6_PROBE, r)
            q6["q6_note"] = ("SEPARATE session; question: does a medical-guard/red-flag pathway fire "
                            "full-graph, or does this route to anxiety skills / freeflow?")
        except Exception as e:  # noqa: BLE001
            q6 = {"user_message": Q6_PROBE, "FAULT": repr(e)[:400]}
            out["faults"].append(q6)
        out["q6_probe"] = q6
        print_block(f"Q6 PROBE (separate thread {q6_tid})", q6)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nJSON written: {args.json}")

    print(f"\nFAULTS: {len(out['faults'])} {'(RUN VOID — partial is not data)' if out['faults'] else '(clean)'}")
    print("ALLDONE")
    sys.exit(1 if out["faults"] else 0)


asyncio.run(main())
