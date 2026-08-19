"""Deterministic cardiac-ambiguous escalation (Node-1). BUILT INERT 2026-07-31; ACTIVATED (register
change #4). RE-KEYED TO THE SIGNED PHRASING CLASS 2026-08-19 (approval record item 2).

Original class (item-3 ruling, Vee 2026-07-30, PO relay): death-fear AND air-hunger co-occurring
("going to die + can't breathe") STAYS AT CRISIS. That conjunction is KEPT VERBATIM below (superset
discipline — a live safety surface is widened, never narrowed).

2026-08-19 re-sign (item 2, 2026-08-19-vee-approval-record-signature-sheet.md): the #413 escalate
disposition now attaches to the spec's universal red-flag FAMILY (bot-behaviour-spec-source-2026-07-08,
§1a-1c universal red-flag override), not to the corpus-verbatim conjunction alone. Live probe 1C-3
(2026-08-18) demonstrated the gap: the rule fired on the corpus wording but not on the paraphrase
"my heart is hammering, I can't get air, I think something is really wrong with me". The family:

  (1) chest pressure / heaviness (ambiguous even at low intensity — spec: screen, don't assume anxiety)
  (2) crushing / stabbing / searing chest pain
  (3) pain spreading to the arm, jaw, or back
  (4) numbness or weakness on one side of the body
  (5) fear-of-dying / somatic-wrongness framing ("going to die", "something is really wrong with me")
      WITH somatic context: real inability to breathe or a chest-pain/pressure symptom

The signed NOT-boundary: panic-related breathlessness ALONE ("I can't catch my breath I'm so anxious",
hyperventilation in clear panic framing) does NOT auto-escalate — the §1c-A grounding capability
survives. Chest TIGHTNESS phrasing is deliberately absent from every tuple here: "my chest is tight"
is the signed anxiety presentation (§1c-A / spec moderate tier), not the red-flag family. The two §1c
open presence cells ("completely out of control" / "losing my mind right now" shapes) share no term
with any tuple below and are prescribed self_help_skill — they must never fire this rule. Heart-racing
/ pounding phrasing alone is likewise NOT somatic context for arm (5): it is the panic presentation
itself (keeps the ruled must-NOT case "going to die + heart pounding out of my chest" un-escalated).

approved_by: "Vee (clinical lead) 2026-08-19 — PO relay; record:
2026-08-19-vee-approval-record-signature-sheet.md" (item 2). Portability clause (signed per E-1): the
signature attaches to the CLINICAL DISPOSITION at class level; these tuples are the current
deterministic implementation and the paraphrase fixture set
(tests/fixtures/bot_behaviour_audit/cardiac_phrasing_class_2026-08-19.json) is the PERMANENT
evaluation set — a superseding implementation (trained classifier, v7 Node 1) inherits the signature
by passing the same fixtures. Fixture-independence is signed: no fixture may be (or become) one of
this module's pattern strings.

Pattern SOURCE for the original conjunction remains panic_override's _DEATH_FEAR/_AIR_HUNGER tuples
(imported, never copied) so the override's deference and this escalation cannot drift apart. The
widened family fires at Node-1 BEFORE the override's altitude: the flag it sets lands in crisis_flags,
and should_ground_over_crisis refuses any turn carrying crisis_flags — precedence by construction.
medical_redflag_guard (D1) is a SEPARATE surface and is untouched by this module.

EN-only lexicon (the characterized class is English; AR rides the AR track per the standing honesty rule).
"""
from sage_poc.nodes.panic_override import _AIR_HUNGER, _DEATH_FEAR

CARDIAC_FLAG_ID = "cardiac_ambiguous_deterministic"

APPROVED_BY = (
    "Vee (clinical lead) 2026-08-19 — PO relay; "
    "record: 2026-08-19-vee-approval-record-signature-sheet.md"
)

# (1) Chest pressure / heaviness — fires ALONE (spec: universal red-flag override at every tier;
# "ambiguous even at low intensity — screen rather than assume anxiety"). NO tightness phrasing.
_CHEST_PRESSURE_HEAVINESS: tuple[str, ...] = (
    "pressure in my chest", "pressure on my chest", "pressure in the chest", "chest pressure",
    "chest feels heavy", "chest is heavy", "chest feels so heavy", "heaviness in my chest",
    "heavy feeling in my chest", "weight on my chest", "sitting on my chest",
    "pressing on my chest", "pressing down on my chest",
    "elephant on my chest", "elephant sitting on my chest",
)

# (2) Crushing / stabbing / searing chest pain — quality term AND chest-region term must co-occur
# ("crushing anxiety" alone stays with its existing routing; "crushing pain ... chest" escalates).
_CHEST_PAIN_QUALITY: tuple[str, ...] = ("crushing", "crushed", "stabbing", "stabbed", "searing")
_CHEST_REGION: tuple[str, ...] = ("chest", "sternum", "breastbone", "ribs", "ribcage", "rib cage")

# (3) Pain spreading to arm / jaw / back — spread-verb AND site AND pain-context must all co-occur.
_RADIATION_VERBS: tuple[str, ...] = (
    "spreading", "spreads", "spread to", "spread down", "spread into", "radiating", "radiates",
    "radiated", "shooting down", "shooting up", "shooting into", "going down my", "moving down my",
    "moving into my", "travelling down", "traveling down", "travels down",
)
_RADIATION_SITES: tuple[str, ...] = (
    "my arm", "my left arm", "my right arm", "the arm", "my jaw", "the jaw", "my back",
)
_PAIN_CONTEXT: tuple[str, ...] = ("pain", "ache", "aching", "hurts", "hurting", "chest")

# (4) One-sided numbness / weakness — side term AND symptom term must co-occur (spec: "any mention
# of numbness or weakness on one side of the body"). Emotional-numbness phrasing without a side term
# stays with its owner (CF-008 dissociation et al.).
_ONE_SIDED_SITES: tuple[str, ...] = (
    "one side", "left side", "right side", "one arm", "left arm", "right arm", "one leg",
    "left leg", "right leg", "half of my body", "half my body", "half of my face", "half my face",
    "side of my face", "side of my body",
)
_NUMB_WEAK: tuple[str, ...] = (
    "numb", "no feeling in", "can't feel", "cant feel", "cannot feel", "gone weak", "feels weak",
    "feel weak", "is weak", "weakness", "can't move", "cant move", "cannot move", "won't move",
    "wont move", "drooping", "droopy", "drooped",
)

# (5) Somatic-wrongness fear framing — the 1C-3 paraphrase's shape. Fires only WITH somatic context
# (_AIR_HUNGER or a chest-pain/pressure symptom), mirroring the signed "real inability to breathe
# rather than panic-related breathlessness" boundary. Death-fear terms ride the same arm (fear-of-
# dying WITH somatic context); heart-racing phrasing is deliberately NOT somatic context here.
_SOMATIC_WRONGNESS: tuple[str, ...] = (
    "really wrong with me", "seriously wrong with me",
    "something is really wrong", "something's really wrong", "somethings really wrong",
    "something is seriously wrong", "something's seriously wrong",
    "something is very wrong", "something's very wrong", "something is badly wrong",
    "something bad is happening to me", "something bad is happening in my body",
    "wrong with my body", "wrong with my heart",
)
_CHEST_SYMPTOM: tuple[str, ...] = _CHEST_PRESSURE_HEAVINESS + (
    "chest pain", "pain in my chest", "pain in the chest", "pain across my chest",
    "chest hurts", "chest is hurting", "chest really hurts", "ache in my chest", "chest ache",
    "chest aches",
)

# Registry-facing flat pattern set (disposition_ownership.json source). Conjunction-gated arms
# export their DISTINGUISHING sides (sites / quality / symptom / fear terms) — same convention the
# original entry used (it exported _DEATH_FEAR, not _AIR_HUNGER): the distinguishing terms are the
# overlap witnesses that matter for cross-mechanism reconciliation. The bare-context tuples
# (_CHEST_REGION, _PAIN_CONTEXT, _AIR_HUNGER, _CHEST_SYMPTOM extras) are context gates, not triggers.
CARDIAC_CLASS_PATTERNS: tuple[str, ...] = (
    _CHEST_PRESSURE_HEAVINESS
    + _CHEST_PAIN_QUALITY
    + _RADIATION_SITES
    + _ONE_SIDED_SITES
    + _NUMB_WEAK
    + _SOMATIC_WRONGNESS
    + _DEATH_FEAR
)


def cardiac_ambiguous_present(message_en: str, raw_message: str) -> bool:
    """True when the signed cardiac red-flag phrasing CLASS is present in the turn's text
    (case-insensitive substring, same convention as the crisis lexicons). Disposition unchanged:
    escalate_crisis (#413 ruling; re-signed to the class 2026-08-19, approval record item 2)."""
    t = f"{message_en or ''} {raw_message or ''}".lower()

    # Original item-3 conjunction — KEPT VERBATIM (never-disarm superset; single-sourced with
    # panic_override's deference via the imported tuples).
    if any(d in t for d in _DEATH_FEAR) and any(a in t for a in _AIR_HUNGER):
        return True
    # (1) chest pressure / heaviness — standalone red flag at every tier.
    if any(p in t for p in _CHEST_PRESSURE_HEAVINESS):
        return True
    # (2) crushing / stabbing / searing chest pain.
    if any(q in t for q in _CHEST_PAIN_QUALITY) and any(c in t for c in _CHEST_REGION):
        return True
    # (3) pain spreading to arm / jaw / back.
    if (
        any(v in t for v in _RADIATION_VERBS)
        and any(s in t for s in _RADIATION_SITES)
        and any(p in t for p in _PAIN_CONTEXT)
    ):
        return True
    # (4) one-sided numbness / weakness.
    if any(s in t for s in _ONE_SIDED_SITES) and any(n in t for n in _NUMB_WEAK):
        return True
    # (5) fear-of-dying / somatic-wrongness framing WITH somatic context.
    if (any(d in t for d in _DEATH_FEAR) or any(w in t for w in _SOMATIC_WRONGNESS)) and (
        any(a in t for a in _AIR_HUNGER) or any(c in t for c in _CHEST_SYMPTOM)
    ):
        return True
    return False
