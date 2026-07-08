"""Deterministic detector for grammatical self-marking of gender in Arabic user
input, for the native-Arabic shadow-measure's "mirror-when-marked, neutral-when-
unknown" gender policy (see shadow_arabic.generate_shadow_arabic): if the user's
OWN message grammatically self-marks their gender, the reply should mirror it; if
unmarked, the reply uses neutral Arabic. detect_gender_marking computes the
gender_marked stratification column (migration 013) — deterministically, from text
markers only. It is NEVER a rater judgment and NEVER an LLM call: same input, same
output, every time.

Scope (Khaleeji/MSA, 1st person only): the primary self-marking signal in Gulf
Arabic first-person self-description is the ة-suffix class of predicate adjectives
/ active participles (تعبانة, حاسة, ...) versus their masculine counterparts
(تعبان, حاس, ...). 1st-person verbs are not gender-marked in Arabic, so verb
agreement is not a signal here; the ة/masculine-stem adjective pair carries the
whole signal.

Not covered (documented, not silently pretended): Arabizi (Latin-script Arabic)
self-marking is not implemented — flagged for a follow-up pass, not "handled
conservatively" via this lexicon. The Emirati 2nd-person ك→ج shift (عليك→عليج) is
a marker of the ADDRESSEE's gender, not the speaker's 1st-person self-marking this
detector targets, so it is out of scope for gender_marked as currently defined.

Conservative by design: any ambiguity (no marker, conflicting markers, or a
marker whose subject may not be the speaker — see the third-party limitation
below) resolves to "none". A wrong gender call is worse than an absent one.

Known limitation (deliberately not worked around here): this is a whole-word
lexicon match, not a parser — it has no subject-tracking, so "أختي تعبانة"
(her being tired, not the speaker) matches the same as "أنا تعبانة" would.
tests/test_gender_marker.py::test_third_party_marking_current_behavior asserts
this honestly rather than faking subject-scoping the implementation doesn't do.
Fixing this needs a Gulf-native linguist / lightweight parse pass — flagged
below, not silently worked around.
"""
from __future__ import annotations

import re

# STARTER lexicon — flag for Gulf-native linguist review; extend, don't treat as
# complete. Covers the 8 highest-frequency self-report emotion/state predicate
# adjectives observed in Khaleeji/MSA user input. Both the ة and ه spelling
# variants are included explicitly (informal Arabic chat frequently uses ه for
# ة); diacritics/tashkeel and tatweel are stripped before matching (see
# _normalize), so shadda-bearing spellings like حاسّة match without a separate
# lexicon entry.
FEMININE_MARKERS: frozenset[str] = frozenset({
    "تعبانة", "تعبانه",
    "حاسة", "حاسه",
    "زعلانة", "زعلانه",
    "مرتاحة", "مرتاحه",
    "خايفة", "خايفه",
    "قلقانة", "قلقانه",
    "متضايقة", "متضايقه",
    "مبسوطة", "مبسوطه",
})

# STARTER lexicon — flag for Gulf-native linguist review; extend, don't treat as
# complete. The masculine counterpart stems of FEMININE_MARKERS (ة/ه suffix
# dropped). "حاس" also covers the shadda-bearing "حاسّ" spelling once diacritics
# are stripped by _normalize.
MASCULINE_MARKERS: frozenset[str] = frozenset({
    "تعبان",
    "حاس",
    "زعلان",
    "مرتاح",
    "خايف",
    "قلقان",
    "متضايق",
    "مبسوط",
})

# Arabic diacritics (harakat, shadda, tanween, sukun) + tatweel (kashida) —
# stripped before matching so e.g. "حاسّة" (with shadda) and "حاسة" (without)
# are treated identically without needing every diacritic variant enumerated
# in the lexicons above.
_DIACRITICS_RE = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")

# Single-letter conjunction proclitics ("و" and, "ف" so/then) that commonly
# attach directly to the following word in Arabic orthography with no space —
# e.g. "وحاسة" ("and [I] feel..."). Stripped (up to two, for the rare doubled
# case like "فو") before lexicon lookup so the attached form still matches.
_PROCLITICS = ("و", "ف")

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _normalize(text: str) -> str:
    return _DIACRITICS_RE.sub("", text)


def _strip_leading_proclitics(token: str) -> str:
    stripped = token
    for _ in range(2):
        if len(stripped) > 2 and stripped[0] in _PROCLITICS:
            stripped = stripped[1:]
        else:
            break
    return stripped


def detect_gender_marking(text: str) -> str:
    """Return "f", "m", or "none" — deterministic, text-markers-only, no LLM.

    "none" whenever there is no clear signal, the signal is conflicting (both a
    masculine and a feminine marker present), or the input is empty. Never
    infers from names, topics, or relationships — grammatical self-marking
    only.
    """
    if not text:
        return "none"

    normalized = _normalize(text)
    tokens = _WORD_RE.findall(normalized)

    found_f = False
    found_m = False
    for token in tokens:
        candidates = {token, _strip_leading_proclitics(token)}
        if candidates & FEMININE_MARKERS:
            found_f = True
        if candidates & MASCULINE_MARKERS:
            found_m = True

    if found_f and found_m:
        return "none"
    if found_f:
        return "f"
    if found_m:
        return "m"
    return "none"
