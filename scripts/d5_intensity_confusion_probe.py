"""D5 condition 4 — intensity-classifier confusion probe, scoped to the 6-vs-7 boundary.

The question is NOT a generic "floor 7 vs 8" A/B. Floor 7 is recommended on a Psychological
First Aid basis (stabilize before explore) that is largely floor-direction-independent. The
useful question this probe answers is narrower:

    How often, and in WHICH DIRECTION, does the live intensity classifier confuse 6 and 7?

- If it UNDER-rates genuine acuity (true-7 predicted as 6), that is the important finding: the
  gate may need to fire lower, or the classifier needs work — a bigger deal than 7-vs-8.
- If it OVER-rates (true-6 predicted as 7), floor 8 gains a case (you'd be flattening some
  moderately-distressed users who'd benefit from a question).

STATUS: this is the MEASUREMENT HARNESS. The ground-truth intensity labels below are
PROVISIONAL (engineering-seeded) and are NOT valid for a sign-off decision until a clinician
validates them. The harness is the deliverable; the labeled set is the gate. Do not read the
output numbers as a clinical result — read them as a demonstration that the instrument works
and a first look at classifier direction.

Run: .venv/bin/python scripts/d5_intensity_confusion_probe.py
"""
import asyncio, json, re
from collections import defaultdict
from sage_poc.nodes import intent_route
from sage_poc.llm import get_classifier, get_fallback_classifier
from sage_poc.resilience import resilient_invoke

# PROVISIONAL labels (intended intensity) clustered around the 6-7 boundary.
# NEEDS CLINICIAN VALIDATION before any floor decision rests on it.
SEED = [
    # intended 6 (moderate distress, not peak)
    (6, "en", "Work has been stressful and I'm pretty worn down, but I'm getting through it."),
    (6, "en", "I had a rough week and I keep feeling on edge about everything."),
    (6, "en", "I'm frustrated with myself lately, I feel like I keep falling short."),
    (6, "en", "Things feel heavy right now and I'm tired of pushing through."),
    (6, "ar", "الأسبوع كان صعب وأحس بضغط، بس أمشي حالي."),
    # intended 7 (high distress, below peak)
    (7, "en", "I feel like I'm failing at everything and I can't seem to get anything right."),
    (7, "en", "I'm overwhelmed and it feels like it's all falling apart around me."),
    (7, "en", "I can't shake the feeling that I'm letting everyone down and it's crushing me."),
    (7, "en", "Everything feels like too much and I don't know how much more I can take."),
    (7, "ar", "أحس إني فاشل في كل شي وما أقدر أسوي أي شي صح."),
    # anchors: intended 5 (mild) and 8 (peak) to check the boundary isn't globally shifted
    (5, "en", "I'm a bit down today but mostly okay."),
    (8, "en", "I'm completely broken, I can't function, everything is unbearable right now."),
]

async def classify_intensity(message_en, language):
    state = {"message_en": message_en, "raw_message": message_en, "detected_language": language,
             "conversation_history": [], "path": []}
    messages = [
        {"role": "system", "content": intent_route.INTENT_SYSTEM},
        {"role": "user", "content": intent_route.build_intent_prompt(state)},
    ]
    raw = await resilient_invoke(get_classifier(), messages, node="intent_route",
                                 fallback_llm=get_fallback_classifier())
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    try:
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {}
    # _safe_int mirrors intent_route's parsing
    try:
        return int(data.get("emotional_intensity"))
    except (TypeError, ValueError):
        return None

async def main():
    print("# D5 intensity-classifier confusion probe (6-vs-7 direction)")
    print("PROVISIONAL labels — NOT clinician-validated; harness demonstration only.\n")
    rows = []
    for true_i, lang, msg in SEED:
        pred = await classify_intensity(msg, lang)
        rows.append((true_i, lang, pred, msg))
        print(f"  true={true_i} [{lang}] pred={pred}  | {msg[:70]}")
    # Direction analysis at the 6-7 boundary
    print("\n## 6-vs-7 boundary direction")
    under = sum(1 for t, _, p, _ in rows if t == 7 and p is not None and p < 7)   # true-7 rated lower
    over = sum(1 for t, _, p, _ in rows if t == 6 and p is not None and p > 6)    # true-6 rated higher
    n7 = sum(1 for t, _, p, _ in rows if t == 7 and p is not None)
    n6 = sum(1 for t, _, p, _ in rows if t == 6 and p is not None)
    print(f"  true-7 under-rated (<7): {under}/{n7}   <- if high, gate may need to fire lower / classifier needs work (the important finding)")
    print(f"  true-6 over-rated (>6):  {over}/{n6}    <- if high, floor 8 gains a case")
    print("\n## interpretation rule (per clinician)")
    print("  under-rating dominates -> 7 clearly right (a labeled 7 may really be an 8); consider firing lower.")
    print("  over-rating dominates  -> 8 has a case (avoid flattening moderate distress).")
    print("\nNEXT: replace SEED with a clinician-validated labeled set before this informs the floor pin.")

asyncio.run(main())
