"""AD-HOC ($0) routing eval: counsel-chat real therapist Q&A vs Sage's
deterministic layers (safety_check + skill_select). No LLM calls — BGE-M3 only,
local_files_only. Bypasses intent_route (which needs an LLM) and calls
skill_select directly to read the routing signal for each real-world question.

Output: tests/fixtures/counsel_chat/routing_results.jsonl
Per row: topic, crisis fields, production skill decision, AND raw best-skill/score
(below-threshold) so coverage gaps are visible.

This is an exploratory instrument, NOT a CI gate: counsel-chat has no routing
ground truth. English/US/single-turn only — says nothing about Arabic/multi-turn.
"""
import asyncio
import json
from pathlib import Path

from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.skill_select import (
    skill_select_node,
    _ensure_semantic_ready,
    _semantic_match_sync,
    SEMANTIC_THRESHOLD,
)

ROOT = Path(__file__).parent.parent
IN_PATH = ROOT / "tests" / "fixtures" / "counsel_chat" / "counsel_chat_train.jsonl"
OUT_PATH = ROOT / "tests" / "fixtures" / "counsel_chat" / "routing_results.jsonl"


def _make_state(text: str) -> dict:
    return {
        "raw_message": text,
        "detected_language": "en",
        "message_en": text,
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "clinical_flags": [],
        "turn_number": 0,
        "therapeutic_profile": None,
        "s7_result": None,
    }


async def main() -> None:
    rows = [json.loads(l) for l in IN_PATH.read_text().splitlines() if l.strip()]
    # Dedup by questionText — answers repeat the same question across therapists.
    seen: dict[str, dict] = {}
    for r in rows:
        q = (r.get("questionText") or "").strip()
        if q and q not in seen:
            seen[q] = r
    questions = list(seen.values())
    print(f"unique questions: {len(questions)}  (threshold={SEMANTIC_THRESHOLD})")

    _ensure_semantic_ready()
    out = []
    for i, r in enumerate(questions):
        q = (r.get("questionText") or "").strip()
        state = _make_state(q)

        safety = await safety_check_node(state)
        merged = {**state, **safety}  # safety output feeds skill_select
        skill = await skill_select_node(merged)

        # Raw best skill + score regardless of threshold → coverage-gap signal.
        raw_skill, raw_score = _semantic_match_sync(q)

        # CORRECTED FIELDS: safety_check_node returns is_safe / crisis_flags /
        # s3_score (NOT crisis_state or si_explicit — those are downstream/never set
        # at this node). The skill match becomes an OFFER under the R1 engagement
        # layer, so read offered_skill_ids + skill_match_method, not active_skill_id.
        out.append({
            "questionID": r.get("questionID"),
            "topic": r.get("topic"),
            "question": q,
            "q_len": len(q),
            # safety_check (real return keys)
            "is_safe": safety.get("is_safe"),
            "crisis_flags": safety.get("crisis_flags"),
            "s3_score": safety.get("s3_score"),
            # skill_select (offer-model aware)
            "active_skill_id": skill.get("active_skill_id"),
            "skill_match_method": skill.get("skill_match_method"),
            "semantic_score": skill.get("semantic_score"),
            "offered_skill_ids": skill.get("offered_skill_ids"),
            # raw semantic (below-threshold visibility)
            "raw_best_skill": raw_skill,
            "raw_best_score": round(raw_score, 4) if raw_score is not None else None,
            "below_threshold": (raw_score is None or raw_score < SEMANTIC_THRESHOLD),
        })
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(questions)}")

    OUT_PATH.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
    print(f"wrote {len(out)} -> {OUT_PATH}")

    # Quick console summary (corrected)
    crisis = [o for o in out if o["is_safe"] is False]
    s3_helped = [o for o in crisis if (o["s3_score"] or 0) >= 0.8059]
    matched = [o for o in out if o.get("offered_skill_ids") or o.get("active_skill_id")]
    print(f"\nSUMMARY")
    print(f"  crisis-flagged (is_safe=False): {len(crisis)}  (S3 above threshold on {len(s3_helped)})")
    print(f"  matched a skill (offer or direct): {len(matched)}/{len(out)}  ({100*len(matched)//len(out)}%)")
    print(f"  no match (true freeflow): {len(out) - len(matched)}")


if __name__ == "__main__":
    asyncio.run(main())
