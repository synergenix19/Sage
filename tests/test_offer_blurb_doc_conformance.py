"""OF-1 — the 5 canonical-source offer blurbs carry the doc's verbatim psychoed content.

Scope (per OF-1 Option 1 + Rider 1): ONLY the 5 Mild-Anxiety skills that have a true
"One-line psychoeducation" column in BOT BEHAVIOUR.docx are synced. Merge rule: the
clinician's one-liner is the psychoed CONTENT (verbatim, case-folded for mid-sentence
offer grammar); the house-style what-you-do + duration clause is additive presentation
after it. The other 15 blurbs are deliberate documented house style (PARTIAL, queued to
a sign-off packet) and are intentionally NOT asserted here.
"""
import json
from pathlib import Path

import sage_poc

_OFFERS = json.loads(
    (Path(sage_poc.__file__).parent / "prompts" / "offer_descriptions.json").read_text()
)["descriptions"]

# skill_id -> the verbatim doc psychoed phrase (BOT BEHAVIOUR.docx) that must be present
DOC_CANONICAL = {
    "box_breathing": "slows your heart rate and signals safety to your nervous system",
    "grounding_5_4_3_2_1": "anchor your attention in the present moment",
    "stop_technique": "create space between a trigger and your reaction",
    "progressive_muscle_relaxation": "physically discharge built-up tension",
    "mindfulness_meditation": "without needing to fix or fight them",
}


def test_five_canonical_blurbs_carry_doc_psychoed_verbatim():
    missing = []
    for skill_id, phrase in DOC_CANONICAL.items():
        blurb = (_OFFERS[skill_id]["description"]["en"] or "").lower()
        if phrase.lower() not in blurb:
            missing.append(f"{skill_id}: missing '{phrase}'")
    assert not missing, "OF-1 canonical sync incomplete:\n" + "\n".join(missing)
