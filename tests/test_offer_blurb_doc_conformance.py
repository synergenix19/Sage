"""OF-1 — the canonical-source offer blurbs carry the doc's verbatim psychoed content.

Scope (per OF-1 Option 1 + Rider 1): ONLY the 5 Mild-Anxiety skills that have a true
"One-line psychoeducation" column in BOT BEHAVIOUR.docx are synced. Merge rule: the
clinician's one-liner is the psychoed CONTENT (verbatim, case-folded for mid-sentence
offer grammar); the house-style what-you-do + duration clause is additive presentation
after it. The other 15 blurbs are deliberate documented house style (PARTIAL, queued to
a sign-off packet) and are intentionally NOT asserted here.

Deroute reconciliation (2026-08-18): mindfulness_meditation is DEROUTED until Vee signs
its registration (sign-off sheet item 3, 2026-07-31; deroute record
docs/superpowers/governance/2026-08-06-body-scan-spv-deroute-record.md, confirmed by Vee
2026-08-11). While derouted it must have NO offer entry at all — asserted below in the
deroute direction. On re-route (signature issued), move its entry from
DEROUTED_DOC_CANONICAL back to DOC_CANONICAL so the verbatim assertion resumes; the
canonical phrase is kept here precisely so re-route cannot silently drop the OF-1 sync.
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
}

# Derouted skills that HAVE a doc canonical phrase: no offer entry may exist while the
# deroute stands (KEYWORD_SEMANTIC_SKIP is the routing side; the absent blurb is the
# offer side). On Vee signature, move the entry back to DOC_CANONICAL — do not delete.
DEROUTED_DOC_CANONICAL = {
    "mindfulness_meditation": "without needing to fix or fight them",
}


def test_five_canonical_blurbs_carry_doc_psychoed_verbatim():
    missing = []
    for skill_id, phrase in DOC_CANONICAL.items():
        blurb = (_OFFERS[skill_id]["description"]["en"] or "").lower()
        if phrase.lower() not in blurb:
            missing.append(f"{skill_id}: missing '{phrase}'")
    assert not missing, "OF-1 canonical sync incomplete:\n" + "\n".join(missing)


def test_derouted_canonical_skills_have_no_offer_entry():
    present = [sid for sid in DEROUTED_DOC_CANONICAL if sid in _OFFERS]
    assert not present, (
        "Derouted skill(s) reappeared in offer_descriptions.json: "
        + ", ".join(present)
        + ". If this is the signed re-route (Vee signature on the registration), move "
        "the entry from DEROUTED_DOC_CANONICAL back to DOC_CANONICAL in this file so "
        "the OF-1 verbatim assertion resumes — do not just delete it. If no signature "
        "exists, this is an unsigned re-route: revert it (deroute record "
        "2026-08-06-body-scan-spv-deroute-record.md)."
    )
