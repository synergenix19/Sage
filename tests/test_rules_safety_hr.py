"""HR-1 Stage 1 detection tests: CF-009 psychosis-variant expansion + CF-007
mania_disclosure + CF-008 dissociation_disclosure.

CF-006 is the LIVE, SIGNED psychosis rule (active=true, approved_by=clinical_lead)
and must not be force-activated or otherwise mutated by this file; it is exercised
by tests/test_rules_safety_psychotic.py. The new psychosis-variant coverage that a
prior commit (40badf9) wrongly folded into CF-006 lives in CF-009 instead, which
ships active=false with no approved_by (unsigned, pending clinician ratification
of the doc's §HR.0 trigger table). CF-007/CF-008 ship the same way. To exercise
detection ahead of ratification, this file loads the REAL rule dicts straight out
of clinical_flag_patterns.json (so the test tracks the authored patterns, not a
hand-copied duplicate) and force-activates CF-007/CF-008/CF-009 locally, exactly
as tests/test_rules_safety_psychotic.py already does for CF-006 alone (in its own
file, with its own hand-typed fixture, on its own live rule).

Trigger phrases are verbatim from docs/superpowers/specs/
2026-07-15-hr1-high-risk-terminal-design.md § "Verbatim trigger sets (doc §HR.0)"
(itself verbatim from BOT BEHAVIOUR §HR, bot_behaviour.txt L1506-1548).
Control phrases are verbatim from the same spec's § "Must-NOT-fire controls".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule

_RULES_PATH = (
    Path(__file__).parent.parent
    / "src" / "sage_poc" / "rules" / "data" / "safety" / "clinical_flag_patterns.json"
)

# All HR-relevant rules exercised by this file's _flags() helper. CF-006 is
# included as-is (it already ships active=true, signed, in the real file) so
# that psychosis assertions relying on its original master patterns (e.g. the
# bare "i hear voices") keep working; only CF-007/008/009 are force-activated.
_HR_RULE_IDS = {"CF-006", "CF-007", "CF-008", "CF-009"}

# The new, unsigned HR-1 Stage 1 additions: these ship active=false with no
# approved_by in the real file, and are force-activated here for test purposes
# only. CF-006 is deliberately excluded from this set: it must never be
# mutated or re-activated by this file (it is already live).
_FORCE_ACTIVE_IDS = {"CF-007", "CF-008", "CF-009"}


def _load_hr_rules() -> list[SafetyRule]:
    """Load CF-006/007/008/009 straight from the real JSON file.

    This intentionally reads the on-disk rule content rather than re-typing patterns
    in Python, so a future edit to the JSON is exercised by this test without any
    duplication drift. `active` is overridden to True only for CF-007/008/009
    (_FORCE_ACTIVE_IDS), never in the file itself. CF-006 is loaded verbatim: it is
    already active=true and signed in the real file, so no override is applied or
    needed (see module docstring).
    """
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    rules = []
    for rule_data in raw["rules"]:
        if rule_data["rule_id"] in _HR_RULE_IDS:
            if rule_data["rule_id"] in _FORCE_ACTIVE_IDS:
                rule_data = dict(rule_data)
                rule_data["active"] = True
            rules.append(SafetyRule.model_validate(rule_data))
    assert {r.rule_id for r in rules} == _HR_RULE_IDS, (
        f"Expected CF-006/CF-007/CF-008/CF-009 in {_RULES_PATH}, found {[r.rule_id for r in rules]}"
    )
    return rules


_HR_RULES = _load_hr_rules()


def _flags(text_en: str) -> list[str]:
    result = _eval_safety(_HR_RULES, {"text_en": text_en, "text_ar": "", "language": "en"})
    return [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]


_HR_FLAGS = {"psychotic_disclosure", "mania_disclosure", "dissociation_disclosure"}


def _any_hr_flag(text_en: str) -> list[str]:
    return [f for f in _flags(text_en) if f in _HR_FLAGS]


# ── Gating: the new rules ship inactive and unsigned; CF-006 stays live ──────

def test_hr_rules_active_and_signed_on_disk():
    """RATIFIED 2026-07-17 (clinician, consolidated approval sheet A1): CF-007/008/009 are
    now active=true + approved_by=clinical_lead. This was previously the inverse guard
    (must ship inactive+unsigned UNTIL a ratification record); the ratification record now
    exists, the activation map was re-signed under clinical-lead authority, so the guard
    flips to enforcing the ratified-active state. Do NOT deactivate without a record."""
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in raw["rules"]}
    for rule_id in _FORCE_ACTIVE_IDS:
        rule = by_id[rule_id]
        assert rule["active"] is True, f"{rule_id} must be active=true (ratified 2026-07-17)"
        assert rule["approved_by"] == "clinical_lead", f"{rule_id} must carry clinical_lead sign-off"


def test_cf006_ships_live_and_signed_on_disk():
    """CRITICAL regression guard for the 40badf9 defect: CF-006 is the pre-existing,
    clinically signed psychotic_disclosure rule and must stay active=true with
    approved_by=clinical_lead in the real file. A prior commit wrongly flipped
    CF-006 to active=false while folding new variant patterns into it; the variants
    now live in CF-009 instead (see module docstring), and CF-006 must be
    byte-identical to its master patterns."""
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in raw["rules"]}
    cf006 = by_id["CF-006"]
    assert cf006["active"] is True, "CF-006 must stay active=true (live, signed rule)"
    assert cf006["approved_by"] == "clinical_lead", "CF-006 must keep its clinical sign-off"
    assert cf006["patterns"] == [
        "hearing voices",
        "i hear voices",
        "voices in my head",
        "seeing things that aren't there",
        "seeing things that are not there",
        "seeing things no one else sees",
        "people are watching me",
        "someone is following me",
        "أسمع أصوات",
        "في أصوات تكلمني",
        "أشوف أشياء ما أحد يشوفها",
        "أحد يراقبني",
    ], "CF-006 patterns must match master exactly; variants belong in CF-009"


def test_hr_patterns_contain_no_em_dash():
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in raw["rules"]}
    for rule_id in _HR_RULE_IDS:
        for pattern in by_id[rule_id]["patterns"]:
            assert "—" not in pattern, f"{rule_id} pattern {pattern!r} contains an em dash"


# ── Psychosis (15) — CF-009 variant expansion ────────────────────────────────
# Doc §HR.0 lists these as an unnumbered bullet line (no count in the doc); an
# earlier internal count of OURS said 14 and dropped one. Verified BY NAME against
# the bullet list. Items 1-4, 6-15 are new (CF-009, force-activated above); item 5
# ("I hear voices") already existed pre-extension and is covered by the live, signed
# CF-006, loaded as-is (see _load_hr_rules).

def test_psychosis_01_people_following_me():
    assert "psychotic_disclosure" in _flags("people are following me everywhere I go")

def test_psychosis_02_someone_watching_me():
    assert "psychotic_disclosure" in _flags("someone is watching me all the time")

def test_psychosis_03_people_trying_to_hurt_me():
    assert "psychotic_disclosure" in _flags("I feel like people are trying to hurt me")

def test_psychosis_04_cant_trust_anyone():
    assert "psychotic_disclosure" in _flags("I don't think I can trust anyone anymore")

def test_psychosis_05_i_hear_voices():
    assert "psychotic_disclosure" in _flags("I hear voices and it scares me")

def test_psychosis_06_hear_people_talking_no_one_there():
    assert "psychotic_disclosure" in _flags("I hear people talking when no one is there")

def test_psychosis_07_voices_wont_stop():
    assert "psychotic_disclosure" in _flags("the voices won't stop, they're constant")

def test_psychosis_08_see_things_others_dont_see():
    assert "psychotic_disclosure" in _flags("I see things other people don't see")

def test_psychosis_09_people_reading_my_thoughts():
    assert "psychotic_disclosure" in _flags("I think people are reading my thoughts")

def test_psychosis_10_someone_controlling_my_thoughts():
    assert "psychotic_disclosure" in _flags("I think someone is controlling my thoughts")

def test_psychosis_11_tv_sending_messages():
    assert "psychotic_disclosure" in _flags("the TV is sending me messages, I know it")

def test_psychosis_12_everything_feels_like_a_sign():
    assert "psychotic_disclosure" in _flags("everything feels like a sign lately")

def test_psychosis_13_dont_know_whats_real():
    assert "psychotic_disclosure" in _flags("I don't know what's real anymore")

def test_psychosis_14_everyone_against_me():
    # Doc §HR.0 psychosis item 14 of 15 (the doc's bullet list is unnumbered; OUR earlier
    # internal count said 14 and dropped this phrase). Restored; verified by-name.
    assert "psychotic_disclosure" in _flags("I think everyone is against me")

def test_psychosis_15_detached_from_reality():
    assert "psychotic_disclosure" in _flags("I feel detached from reality most days")


# ── Mania (10) — CF-007 ───────────────────────────────────────────────────────

def test_mania_01_havent_slept_but_amazing():
    assert "mania_disclosure" in _flags("I haven't slept for days but I feel amazing")

def test_mania_02_dont_need_sleep():
    assert "mania_disclosure" in _flags("I don't need sleep, I'm fine")

def test_mania_03_mind_million_miles_an_hour():
    assert "mania_disclosure" in _flags("my mind is going a million miles an hour")

def test_mania_04_so_much_energy_known_gap():
    """KNOWN, DELIBERATE GAP: the bare doc phrase 'I have so much energy' does not fire
    on its own. It is a literal substring of the must-NOT-fire control 'I have so
    much energy today after the gym' (see test_control_ordinary_excitement_energy),
    so with keyword-substring matching there is no pattern that can match the bare
    trigger without also matching that control. CF-007 instead requires the energy
    phrase to co-occur with another mania marker (see test_mania_04b below). This
    trades bare-phrase recall for control precision, per the brief's instruction to
    tighten the pattern rather than weaken the control."""
    assert "mania_disclosure" not in _flags("I have so much energy")

def test_mania_04b_so_much_energy_with_mania_marker_fires():
    assert "mania_disclosure" in _flags(
        "I have so much energy and I feel unstoppable, I haven't slept in days"
    )

def test_mania_05_feel_unstoppable():
    assert "mania_disclosure" in _flags("I feel unstoppable right now")

def test_mania_06_feel_invincible():
    assert "mania_disclosure" in _flags("I feel invincible, nothing can touch me")

def test_mania_07_taking_huge_risks():
    assert "mania_disclosure" in _flags("I'm taking huge risks with everything lately")

def test_mania_08_spending_loads_of_money():
    assert "mania_disclosure" in _flags("I've been spending loads of money this week")

def test_mania_09_keep_talking_cant_stop():
    assert "mania_disclosure" in _flags("I keep talking and can't stop, ideas keep coming")

def test_mania_10_thoughts_racing_all_the_time():
    assert "mania_disclosure" in _flags("my thoughts are racing all the time now")


# ── Dissociation (11) — CF-008 ────────────────────────────────────────────────

def test_dissociation_01_dont_feel_real():
    assert "dissociation_disclosure" in _flags("I don't feel real lately")

def test_dissociation_02_nothing_feels_real():
    assert "dissociation_disclosure" in _flags("nothing feels real anymore")

def test_dissociation_03_detached_from_myself():
    assert "dissociation_disclosure" in _flags("I feel detached from myself")

def test_dissociation_04_outside_my_body():
    assert "dissociation_disclosure" in _flags("I feel outside my body sometimes")

def test_dissociation_05_watching_myself():
    assert "dissociation_disclosure" in _flags("I feel like I'm watching myself from far away")

def test_dissociation_06_world_doesnt_feel_real():
    assert "dissociation_disclosure" in _flags("the world doesn't feel real to me")

def test_dissociation_07_everything_like_a_dream():
    assert "dissociation_disclosure" in _flags("everything feels like a dream these days")

def test_dissociation_08_lose_chunks_of_time():
    assert "dissociation_disclosure" in _flags("I lose chunks of time and don't remember")

def test_dissociation_09_disconnected_from_reality():
    assert "dissociation_disclosure" in _flags("I feel disconnected from reality")

def test_dissociation_10_completely_numb_and_absent():
    assert "dissociation_disclosure" in _flags("I feel completely numb and absent")

def test_dissociation_11_dont_know_where_i_am():
    assert "dissociation_disclosure" in _flags("I don't know where I am sometimes")


# ── Must-NOT-fire controls ────────────────────────────────────────────────────
# Every control must fire NO HR-class flag (psychotic_disclosure, mania_disclosure,
# dissociation_disclosure). Where a naive pattern would have caught these, the
# pattern was tightened (never the control) per the brief.

def test_control_grief_numb_since_he_died():
    assert _any_hr_flag("I feel numb since he died") == []

def test_control_grief_nothing_felt_real_since_funeral():
    """Distinguishes from dissociation trigger #2 'nothing feels real' by verb tense
    and possessive contraction: 'nothing's felt real' is not a substring of
    'nothing feels real', and vice versa."""
    assert _any_hr_flag("nothing's felt real since the funeral") == []

def test_control_panic_derealization_everything_felt_unreal():
    assert _any_hr_flag("everything felt unreal during the panic attack") == []

def test_control_panic_derealization_felt_detached_while_panicking():
    """Distinguishes from dissociation trigger #3 'I feel detached from myself' by
    tense ('felt' vs 'feel') and by omitting 'from myself'."""
    assert _any_hr_flag("I felt detached while I was panicking") == []

def test_control_idiom_promotion_doesnt_feel_real():
    """Distinguishes from dissociation trigger #6 'the world doesn't feel real' by
    requiring the full anchored phrase (subject 'the world'), not the bare
    fragment 'doesn't feel real' that the idiom also contains."""
    assert _any_hr_flag("this promotion doesn't feel real") == []

def test_control_idiom_winning_doesnt_feel_real():
    assert _any_hr_flag("winning still doesn't feel real") == []

def test_control_ordinary_excitement_energized_about_project():
    assert _any_hr_flag("I'm so energized about this project") == []

def test_control_ordinary_excitement_energy_after_gym():
    """The hard case: this control is a literal superstring of mania trigger #4
    ('I have so much energy'). CF-007 does not carry a bare 'i have so much
    energy' pattern for exactly this reason (see test_mania_04_so_much_energy_known_gap)."""
    assert _any_hr_flag("I have so much energy today after the gym") == []


# ── Canonical HR drives (spec "Red tests (Stage 1)") ─────────────────────────
# The five presentations named in the design spec's problem statement. Detection
# only (Task 1 scope) — routing to the referral is Task 2/3, not asserted here.

def test_canonical_drive_hears_voices_that_wont_stop():
    assert "psychotic_disclosure" in _flags("I hear voices that won't stop")

def test_canonical_drive_people_following_and_watching():
    assert "psychotic_disclosure" in _flags("People are following me and watching me")

def test_canonical_drive_havent_slept_amazing_unstoppable():
    assert "mania_disclosure" in _flags(
        "I haven't slept for days but I feel amazing and unstoppable"
    )

def test_canonical_drive_people_reading_my_thoughts():
    assert "psychotic_disclosure" in _flags("I think people are reading my thoughts")

def test_canonical_drive_detached_nothing_feels_real():
    assert "dissociation_disclosure" in _flags(
        "I feel completely detached from reality, nothing feels real"
    )


# ── No cross-contamination with crisis detection ─────────────────────────────

def test_hr_flags_are_clinical_not_crisis():
    result = _eval_safety(_HR_RULES, {
        "text_en": "I hear voices and people are following me",
        "text_ar": "",
        "language": "en",
    })
    crisis = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis == [], "HR flags are clinical_flags, not crisis_flags"
