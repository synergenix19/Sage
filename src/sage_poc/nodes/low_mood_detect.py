"""SS3a low-mood disclosure detection (deterministic, no LLM).

Task 2 of the SS3a low-mood validate-first + woven-safety flow (see
tests/test_low_mood_screen.py for the flow overview). Detects a low-mood /
anhedonia disclosure across the clinician-signed SS3a trigger families:
energy/effort, anhedonia/interest, motivation, social withdrawal, affective
flatness, meaning/going-through-the-motions, explicit ask. Deterministic
family/token-aware matching only, mirroring ocd_compulsion.is_ocd_compulsion
in spirit (no LLM, no semantic matcher, single-sourced clinician vocabulary),
so the interception in skill_select.py can rely on it as a first-class safety
gate.

VOCABULARY SOURCE (pending sign-off): the fire list (list A) and look-alike
list (list B) below are loaded from
rules/data/safety/low_mood_3a_triggers.json, which is a PROPOSED placeholder
pending clinician sign-off, see
docs/superpowers/governance/2026-07-10-low-mood-3a-trigger-set.md for the
source deliverable, both lists, and the discriminator wording. Do not treat a
merge of this scaffold as trigger logic done.

MATCHING DESIGN: the discriminator (from the governance doc) is that SS3a
fires on GLOBAL, PERVASIVE, PERSISTENT loss ("across the board", "lately",
"in general") and must NOT fire on LOCAL, situational, task-specific, or
physical look-alikes ("this one thing", "today", "after X"). Most list-A
phrases are already unambiguous once transcribed verbatim (they already carry
a global object like "anything"/"everything", or have no local-object
look-alike at all) and are matched as direct case-insensitive substrings. A
small number of families are genuinely ambiguous once matching is made
token-robust (so a paraphrase like "I feel *so* numb" still matches the numb
family) and need an explicit local-vs-global check:

- energy ("I don't have the energy[...]"): a bare statement or a "to do
  anything" object fires; a "to <specific task>" object (e.g. "to finish this
  report") does not.
- "nothing [is] fun" (anhedonia paraphrase): a bare/global-marked statement
  fires; a "to do X" object (ordinary boredom, e.g. "nothing fun to do right
  now") does not.
- "can't be bothered": fires unless followed by "to <task>" (a specific,
  local chore, e.g. "to cook tonight").
- "I feel [...] numb" / "I feel [...] flat": anchored on the first-person
  subject ("I feel"), so "my arm feels numb" (a different subject: a body
  part, not "I") does not match.

Extending either list requires a fresh clinical sign-off, not a future
context window's judgment call. The `LOW_MOOD_LOOKALIKE_PHRASES` export
exists purely so tests can assert the precision boundary against the same
data the detector reads, single-sourced (they must never diverge).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "rules" / "data" / "safety" / "low_mood_3a_triggers.json"
)
_data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))

# Public: the verbatim clinician-proposed fire vocabulary (list A) and
# look-alike vocabulary (list B), flattened. Single-sourced from the data
# file so the production copy and any test ground truth cannot diverge.
LOW_MOOD_FIRE_PHRASES: tuple[str, ...] = tuple(
    phrase for family in _data["fire_families"].values() for phrase in family
)
LOW_MOOD_LOOKALIKE_PHRASES: tuple[str, ...] = tuple(
    phrase for category in _data["lookalike_categories"].values() for phrase in category
)

# ---------------------------------------------------------------------------
# Direct literal anchors: list-A phrases with no realistic local-object
# look-alike (either they carry no ambiguous object at all, or the object is
# already a global pronoun baked into the phrase itself). Apostrophe-stripped,
# lowercased, plain substring match.
# ---------------------------------------------------------------------------
_LITERAL_PHRASES: tuple[str, ...] = (
    "even small tasks feel difficult",
    "i cant seem to get going",
    "i just want to stay in bed",
    "i just want to stay under the covers",
    "nothing sounds enjoyable",
    "i dont enjoy the things i used to",
    "i dont look forward to anything",
    "nothing feels rewarding",
    "i dont feel interested in anything",
    "ive lost interest in everything",
    "nothing brings me joy anymore",
    "i dont feel like doing anything",
    "i dont feel motivated",
    "i just dont have the motivation",
    "i have no motivation for anything",
    "i keep putting everything off",
    "i dont want to see anyone",
    "i keep cancelling plans",
    "i just want to be on my own",
    "i dont want to leave the house",
    "i dont want to talk to anyone",
    "i just want to be left alone",
    "i dont really care anymore",
    "i feel disconnected from everything",
    "i feel emotionally drained",
    "i feel empty",
    "i dont feel like myself",
    "im just going through the motions",
    "everything feels pointless",
    "i feel stuck",
    "build a better routine",
)

# ---------------------------------------------------------------------------
# Family/token-aware patterns for the families that need local-vs-global
# scope resolution to stay both recall- and precision-safe, and for the two
# subject-anchored affective-flatness patterns ("I feel numb"/"I feel flat")
# that need filler-word tolerance ("I feel *so* numb").
# ---------------------------------------------------------------------------
_ENERGY_ANCHOR = re.compile(
    r"(?:dont|do not)\s+have\s+(?:the\s+)?energy|(?:have|ive)\s+(?:no|zero)\s+energy|no\s+energy"
)
_FUN_ANCHOR = re.compile(r"nothing\s*(?:is\s+)?fun\b")
_BOTHERED_RX = re.compile(r"cant\s+be\s+bothered\b(?!\s+to\b)")
_GET_OUT_OF_BED_RX = re.compile(r"cant\s+get\s+out\s+of\s+bed")
_EFFORT_RX = re.compile(r"everything\s+feels\s+like\s+(?:such\s+)?an?\s+effort")
_ANYTHING_MOTIVATION_RX = re.compile(
    r"\bi\s+(?:dont|do not)\s+(?:feel\s+like\s+(?:doing\s+)?|want\s+to\s+(?:do\s+)?)(?:anything|everything)\b"
)
_AVOIDING_RX = re.compile(
    r"avoiding\s+(?:people|everyone|everybody|all\s+my\s+friends|my\s+friends)\b"
)
_WITHDRAW_ISOLATE_RX = re.compile(
    r"(?:withdraw(?:ing)?|isolate)\s+(?:myself\s+)?from\s+everyone\b"
)
_NUMB_RX = re.compile(r"\bi\b(?:\s+\S+){0,3}\s+feel\w*(?:\s+\S+){0,3}\s+numb\b")
_FLAT_RX = re.compile(r"\bi\b(?:\s+\S+){0,3}\s+feel\w*(?:\s+\S+){0,2}\s+flat\b")

# Words/phrases that mark the object of an ambiguous anchor as GLOBAL/PERVASIVE
# rather than a specific, local task.
_GLOBAL_MARKERS: tuple[str, ...] = (
    "anything",
    "everything",
    "everyone",
    "everybody",
    "anymore",
    "these days",
    "lately",
    "most days",
    "in general",
    "across the board",
    "all my friends",
)
# Bare trailing markers that, absent a global marker, indicate a transient /
# situational reading (e.g. "no energy today", "nothing fun to do right now").
_LOCAL_BARE_MARKERS: tuple[str, ...] = ("today", "tonight", "right now")
_TO_CLAUSE_RX = re.compile(r"to\s+\S+(?:\s+\S+){0,4}")


def _tail_is_global(tail: str) -> bool | None:
    """Classify the text immediately following a scope-ambiguous anchor.

    Returns True (global -> counts as a fire), False (local -> suppressed),
    or None (no marker present at all -> caller applies the anchor's own
    default, which for a bare clinician-transcribed phrase is to fire).
    """
    tail = tail.strip()
    if not tail:
        return None
    to_match = _TO_CLAUSE_RX.match(tail)
    if to_match:
        clause = to_match.group(0)
        return any(marker in clause for marker in ("anything", "everything"))
    if any(tail.startswith(marker) for marker in _LOCAL_BARE_MARKERS) and not any(
        marker in tail for marker in _GLOBAL_MARKERS
    ):
        return False
    if any(marker in tail for marker in _GLOBAL_MARKERS):
        return True
    return None


def _scope_checked_fires(anchor: re.Pattern[str], text: str) -> bool:
    match = anchor.search(text)
    if not match:
        return False
    tail = text[match.end() : match.end() + 40]
    verdict = _tail_is_global(tail)
    return True if verdict is None else verdict


def _normalize(text: str | None) -> str:
    # Apostrophe-stripped so "don't"/"dont", "can't"/"cant", "I've"/"ive" all
    # normalize to one token shape; every pattern above is written in that
    # stripped form.
    return re.sub(r"[’']", "", (text or "").lower())


def is_low_mood_disclosure(message_en: str) -> bool:
    """True when `message_en` contains an SS3a low-mood trigger.

    Deterministic, no model call, no LLM. Matched against message_en (the
    translated English for Arabic sessions, though the interception in
    skill_select.py gates on detected_language == "en" before calling this).
    Empty/None -> False.
    """
    normalized = _normalize(message_en)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in _LITERAL_PHRASES):
        return True

    if _scope_checked_fires(_ENERGY_ANCHOR, normalized):
        return True
    if _scope_checked_fires(_FUN_ANCHOR, normalized):
        return True
    if _BOTHERED_RX.search(normalized):
        return True
    if _GET_OUT_OF_BED_RX.search(normalized):
        return True
    if _EFFORT_RX.search(normalized):
        return True
    if _ANYTHING_MOTIVATION_RX.search(normalized):
        return True
    if _AVOIDING_RX.search(normalized):
        return True
    if _WITHDRAW_ISOLATE_RX.search(normalized):
        return True
    if _NUMB_RX.search(normalized):
        return True
    if _FLAT_RX.search(normalized):
        return True

    return False
