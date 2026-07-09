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

First-person-anchor guard (reduce-then-quantify): a marker only counts as
self-marking when a first-person anchor (أنا/إني/صرلي/عندي…) sits within a small
window of it, and never when a third-person possessor immediately precedes it
("أختي تعبانة" -> "none", the sister, not the speaker). This REDUCES the
third-party false-positive before the 431-message run, as a condition of record;
the residual rate is then quantified over that run. It is a heuristic, not a
parser: the anchor and possessor lists are STARTER sets flagged for Gulf-native
linguist review, and it is deliberately biased toward "none" — a pronoun-dropped
self-mark with no nearby anchor (e.g. bare "تعبانة اليوم") resolves to "none"
rather than risk a wrong gender. False-negatives (-> neutral) are the accepted
cost of not false-positiving (-> wrong gender).
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

# First-person-anchor guard (reduce-then-quantify, per architect condition of record).
# A gendered predicate adjective only counts as SELF-marking if a first-person anchor
# sits near it; otherwise -> "none". Biased toward false-negatives (-> neutral) over
# false-positives (-> wrong gender), per "a wrong guess is worse than neutrality."
# STARTER set — flag for Gulf-native linguist review; extend, don't treat as complete.
_FIRST_PERSON_ANCHORS: frozenset[str] = frozenset({
    "أنا", "انا", "إني", "اني", "إنني", "انني",
    "عندي", "صرلي", "صارلي", "نفسي", "ليتني", "ياليتني", "لي",
})

# Third-person possessors ("my sister/brother/mother/friend/…"): when one sits
# IMMEDIATELY before a gendered marker, the marker describes THAT person, not the
# speaker (e.g. "أختي تعبانة") — reject even if a first-person anchor is elsewhere.
# STARTER set — flag for Gulf-native linguist review; extend, don't treat as complete.
_THIRD_PERSON_POSSESSORS: frozenset[str] = frozenset({
    "أختي", "اختي", "أخوي", "اخوي", "أخي", "اخي",
    "أمي", "امي", "أبوي", "ابوي", "أبي", "ابي",
    "زوجتي", "زوجي", "بنتي", "ولدي", "ابني",
    "صديقتي", "صديقي", "صاحبتي", "صاحبي", "ربيعتي", "ربيعي", "رفيجتي", "رفيجي",
})

# Window (in tokens, each side) within which a first-person anchor must appear for a
# marker to count as self-marking.
_ANCHOR_WINDOW = 3


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

    def _anchored(i: int) -> bool:
        lo, hi = max(0, i - _ANCHOR_WINDOW), min(len(tokens), i + _ANCHOR_WINDOW + 1)
        window = tokens[lo:i] + tokens[i + 1:hi]
        return any(
            t in _FIRST_PERSON_ANCHORS or _strip_leading_proclitics(t) in _FIRST_PERSON_ANCHORS
            for t in window
        )

    def _third_party(i: int) -> bool:
        if i == 0:
            return False
        prev = tokens[i - 1]
        return prev in _THIRD_PERSON_POSSESSORS or _strip_leading_proclitics(prev) in _THIRD_PERSON_POSSESSORS

    found_f = False
    found_m = False
    for i, token in enumerate(tokens):
        candidates = {token, _strip_leading_proclitics(token)}
        is_f = bool(candidates & FEMININE_MARKERS)
        is_m = bool(candidates & MASCULINE_MARKERS)
        if not (is_f or is_m):
            continue
        # A marker whose immediate predecessor is a 3rd-person possessor describes
        # someone else; a marker with no nearby first-person anchor is unattributed —
        # both resolve to no self-marking (biased toward "none").
        if _third_party(i) or not _anchored(i):
            continue
        found_f = found_f or is_f
        found_m = found_m or is_m

    if found_f and found_m:
        return "none"
    if found_f:
        return "f"
    if found_m:
        return "m"
    return "none"
