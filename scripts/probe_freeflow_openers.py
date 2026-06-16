"""Phase-B probe ($ small): verify the freeflow OPENER fix (#2) and measure the
advice-after-validation DRAFT (#3) against the REAL production responder (gpt-4o
via OpenRouter). Runs the actual compose_prompt path; the only swap is the L2
general_chat template (baseline live v1.5.0 vs draft general_chat_advicefirst).

Scoring is deterministic ($0): opener anti-patterns the L0/v1.5.0 prompt forbids,
substance-first proxy (content-word overlap), advice markers, question discipline,
length. Raw replies are saved so a human/clinician can read examples.

Output: tests/fixtures/counsel_chat/openers_probe_results.json
Cost: ~80 gpt-4o calls. Requires OPENROUTER_API_KEY.
"""
import asyncio
import json
import re
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv
load_dotenv()  # OPENROUTER_API_KEY for the real responder

from sage_poc.prompts import composer
from sage_poc.prompts.loader import get_intent_template
from sage_poc.llm import get_responder

ROOT = Path(__file__).parent.parent
CC_PATH = ROOT / "tests" / "fixtures" / "counsel_chat" / "counsel_chat_train.jsonl"
OUT_PATH = ROOT / "tests" / "fixtures" / "counsel_chat" / "openers_probe_results.json"

# Opener anti-patterns the prompt explicitly forbids (L0 substance-first; intensity
# high: "Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener").
_ROBOTIC = [
    "it sounds like", "that sounds", "i'm sorry to hear", "i am sorry to hear",
    "i'm so sorry", "i am so sorry", "i'm sorry you", "i hear you", "i can hear",
    "i can only imagine", "that must be", "it must be", "i can understand",
    "i understand how", "i understand that", "thank you for sharing",
    "thank you for trusting", "first of all",
]
_ADVICE = [
    "you could", "you might", "you can try", "one thing that", "one thing you",
    "it might help", "it may help", "what helps", "i'd suggest", "i would suggest",
    "consider ", "try to", "try ", "perhaps you", "maybe you", "a small step",
    "you may want", "it could help", "one approach", "what often helps",
]
_STOP = set("the a an and or but to of in on for with about that this it is are was "
            "were be been being have has had do does did i you he she they we my your "
            "me him her them so just really very much how what when where why who am "
            "feel feeling like dont don't im i'm ive can cant could would should".split())


def _first_sentence(text: str) -> str:
    t = text.strip()
    m = re.search(r"[.!?]", t)
    return t[: m.start() + 1] if m else t


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOP}


def score(reply: str, question: str) -> dict:
    r = reply.strip()
    low = r.lower()
    opener = _first_sentence(r).lower()
    robotic = any(low.startswith(p) or opener.startswith(p) for p in _ROBOTIC)
    opens_q = _first_sentence(r).rstrip().endswith("?")
    overlap = _content_words(_first_sentence(r)) & _content_words(question)
    substance_first = (not robotic) and bool(overlap)
    advice_idx = min([low.find(m) for m in _ADVICE if m in low] or [-1])
    has_advice = advice_idx >= 0
    # advice counts as "after validation" if it does not open the reply
    advice_after_validation = has_advice and advice_idx > len(_first_sentence(r)) - 1
    sentences = len([s for s in re.split(r"[.!?]+", r) if s.strip()])
    return {
        "robotic_opener": robotic,
        "opens_with_question": opens_q,
        "substance_first": substance_first,
        "opener_overlap_terms": sorted(overlap)[:5],
        "has_advice": has_advice,
        "advice_after_validation": advice_after_validation,
        "ends_with_question": r.rstrip().endswith("?"),
        "num_questions": r.count("?"),
        "sentences": sentences,
        "words": len(r.split()),
    }


def _state(message: str, intensity: int) -> dict:
    return {
        "raw_message": message, "message_en": message, "detected_language": "en",
        "primary_intent": "general_chat", "secondary_intent": None,
        "emotional_intensity": intensity, "engagement": 5,
        "clinical_flags": [], "conversation_history": [], "path": [],
        "directive_posture": False, "code_switching": False,
        "therapeutic_profile": None, "active_skill_id": None,
        "offered_skill_ids": None, "crisis_state": "none",
        "user_id": None, "session_id": None, "turn_number": 1,
    }


def _draft_get_intent_template(intent, variant=None):
    """Force the advicefirst draft for general_chat; passthrough otherwise."""
    if intent == "general_chat":
        return get_intent_template("general_chat", variant="advicefirst")
    return get_intent_template(intent, variant=variant)


async def _generate(message: str, intensity: int, mode: str, llm) -> dict:
    st = _state(message, intensity)
    if mode == "draft":
        with patch.object(composer, "get_intent_template", _draft_get_intent_template):
            system_str, user_str, _ = composer.compose_prompt(st)
    else:
        system_str, user_str, _ = composer.compose_prompt(st)
    resp = await llm.ainvoke([
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ])
    reply = resp.content if hasattr(resp, "content") else str(resp)
    return {"reply": reply, **score(reply, message)}


# Crafted heavy / acute disclosures (high intensity) — test the acute exception.
CRAFTED = [
    ("I just found out my dad has cancer and I can't stop shaking.", 8),
    ("Everyone at work got promoted except me and I feel completely worthless.", 7),
    ("My wife left last night and took the kids. I don't know what to do.", 8),
    ("I keep lying awake replaying every mistake I've ever made.", 6),
    ("I snapped at my son again today and I hate the parent I'm becoming.", 6),
    ("I moved to a new city for this job and I have nobody here.", 5),
]


async def main() -> None:
    rows = [json.loads(l) for l in CC_PATH.read_text().splitlines() if l.strip()]
    by_topic: dict[str, str] = {}
    for r in rows:
        t, q = r.get("topic"), (r.get("questionText") or "").strip()
        if t and q and t not in by_topic and 40 < len(q) < 400:
            by_topic[t] = q
    # stratified: first usable question from 22 topics (deterministic)
    sample = [(q, 5, f"cc:{t}") for t, q in list(by_topic.items())[:22]]
    sample += [(m, i, "crafted") for m, i in CRAFTED]

    llm = get_responder()
    results = []
    for idx, (msg, intensity, tag) in enumerate(sample):
        base = await _generate(msg, intensity, "baseline", llm)
        draft = await _generate(msg, intensity, "draft", llm)
        results.append({"tag": tag, "intensity": intensity, "message": msg,
                        "baseline": base, "draft": draft})
        print(f"  [{idx+1}/{len(sample)}] {tag} (i={intensity})")

    # intensity sweep on 3 items
    sweep = []
    for msg, _, tag in [sample[0], sample[1], (CRAFTED[0][0], 0, "crafted")]:
        for i in (2, 5, 8):
            base = await _generate(msg, i, "baseline", llm)
            draft = await _generate(msg, i, "draft", llm)
            sweep.append({"tag": tag, "intensity": i, "message": msg,
                          "baseline": base, "draft": draft})
            print(f"  sweep {tag} i={i}")

    OUT_PATH.write_text(json.dumps({"core": results, "sweep": sweep}, indent=2, ensure_ascii=False))
    print(f"\nwrote -> {OUT_PATH}")

    def rate(items, mode, key):
        return 100 * sum(1 for x in items if x[mode][key]) / len(items)

    print("\n=== OPENER QUALITY (#2)  baseline -> draft ===")
    for key in ["robotic_opener", "substance_first", "opens_with_question"]:
        print(f"  {key:22s}: {rate(results,'baseline',key):5.1f}% -> {rate(results,'draft',key):5.1f}%")
    print("\n=== ADVICE / DISCIPLINE (#3) baseline -> draft ===")
    for key in ["has_advice", "advice_after_validation", "ends_with_question"]:
        print(f"  {key:24s}: {rate(results,'baseline',key):5.1f}% -> {rate(results,'draft',key):5.1f}%")
    acute = [x for x in results if x["intensity"] >= 7]
    if acute:
        print(f"\n=== ACUTE SUBSET (intensity>=7, n={len(acute)}) — advice should STAY LOW ===")
        for key in ["has_advice", "advice_after_validation"]:
            print(f"  {key:24s}: {rate(acute,'baseline',key):5.1f}% -> {rate(acute,'draft',key):5.1f}%")
    import statistics as st
    print(f"\n  median words baseline={st.median(x['baseline']['words'] for x in results):.0f} "
          f"draft={st.median(x['draft']['words'] for x in results):.0f}")


if __name__ == "__main__":
    asyncio.run(main())
