"""W6 routing measured-pass harness — three batteries in one.

1. CONSISTENCY — N runs/phrase through intent_route (real classifier, temp=0) -> primary_intent
   distribution. Settles whether temp-0 GPT-4o-mini varies on skill/mood phrasings (classifier is
   already temperature=0, so this measures residual non-determinism, not a fixable decoding setting).
2. PRECISION  — anecdote set + canonical triggers through intent_route -> skill_select (local) ->
   expected-vs-actual skill, match method, offer-vs-enter.
3. FLOW       — offer->accept path end-to-end (run separately against prod; includes the EN mood
   accept-flow that unblocks W4's prod confirmation).

Run: cd sage-poc && .venv/bin/python scripts/w6_routing_diagnostic.py [consistency|precision] [N]
"""
import sys, asyncio, collections
sys.path.insert(0, "src")

# Consistency + precision phrase sets. (expected_intent, expected_skill_or_None, phrase)
CONSISTENCY = [
    ("mood_check_in", "how are you tracking my mood today"),
    ("mood_check_in", "كيف مزاجي اليوم؟"),
    ("behavioral_activation", "i have no motivation to do anything"),
    ("worry_time", "can't stop worrying, my mind keeps racing"),
    ("grounding_5_4_3_2_1", "i'm having a panic attack right now"),
]
# W6 anecdote set (the reported mismatches) + canonicals.
PRECISION = [
    ("worry_time", "my relationship is falling apart and i keep worrying about money"),  # relationship->money-worry
    ("dbt_tipp", "i'm so overwhelmed i can't think, everything is too much"),            # TIPP
    ("mood_check_in", "i just found out my partner cheated on me"),                       # infidelity -> mood?
    ("grounding_5_4_3_2_1", "i'm having a panic attack right now"),
    ("worry_time", "can't stop worrying, my mind keeps racing"),
]


def _state(phrase, lang):
    return {
        "raw_message": phrase, "message_en": phrase if lang == "en" else "", "detected_language": lang,
        "crisis_state": "none", "clinical_flags": [], "crisis_flags": [], "emotional_intensity": 5,
        "engagement": 5, "therapeutic_profile": {}, "turn_count": 0, "conversation_history": [],
        "path": [], "offered_skill_ids": None, "last_offer_turn": None, "active_skill_id": None,
        "primary_intent": None, "intent_confidence": 1.0,
    }


async def consistency(n):
    from sage_poc.nodes.intent_route import intent_route_node
    print(f"=== CONSISTENCY (N={n} per phrase, temp-0 classifier) ===")
    for exp, phrase in CONSISTENCY:
        lang = "ar" if any(ord(c) > 0x5ff for c in phrase) else "en"
        dist = collections.Counter()
        for _ in range(n):
            r = await intent_route_node({**_state(phrase, lang)})
            dist[r.get("primary_intent")] += 1
        stable = "STABLE" if len(dist) == 1 else "VARIES"
        print(f"  [{stable:6}] {exp:22} {dict(dist)}  | {phrase[:40]!r}")


async def precision():
    from sage_poc.nodes.intent_route import intent_route_node
    from sage_poc.nodes.skill_select import skill_select_node
    from sage_poc.safety.s3_semantic import _ensure_s3_ready
    _ensure_s3_ready()
    print("=== PRECISION (intent_route -> skill_select, local) ===")
    for exp_skill, phrase in PRECISION:
        lang = "ar" if any(ord(c) > 0x5ff for c in phrase) else "en"
        st = await intent_route_node({**_state(phrase, lang)})
        intent = st.get("primary_intent")
        merged = {**_state(phrase, lang), **st}
        if intent in ("new_skill", "info_request") or merged.get("emotional_intensity", 0) >= 8:
            r = await skill_select_node(merged)
            got = r.get("active_skill_id") or (r.get("offered_skill_ids") or [None])[0]
            method = r.get("skill_match_method")
            mark = "✅" if got == exp_skill else "❌"
        else:
            got, method, mark = f"(intent={intent}->freeflow)", "-", "❌"
        print(f"  {mark} exp={exp_skill:22} got={str(got):22} method={method}  | {phrase[:38]!r}")


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "consistency"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    if mode == "consistency":
        await consistency(n)
    elif mode == "precision":
        await precision()


if __name__ == "__main__":
    asyncio.run(main())
