"""HR-1 Stage 1 detection tests: CF-006 psychosis extension + CF-007 mania_disclosure
+ CF-008 dissociation_disclosure.

CF-006/CF-007/CF-008 ship active=false with no approved_by in the real rule file
(unsigned, pending clinician ratification of the doc's §HR.0 trigger table). To
exercise detection ahead of ratification, this file loads the REAL rule dicts
straight out of clinical_flag_patterns.json (so the test tracks the authored
patterns, not a hand-copied duplicate) and force-activates them locally, exactly
as tests/test_rules_safety_psychotic.py already does for CF-006 alone.

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

_HR_RULE_IDS = {"CF-006", "CF-007", "CF-008"}


def _load_hr_rules() -> list[SafetyRule]:
    """Load CF-006/007/008 straight from the real JSON file, force-activating them.

    This intentionally reads the on-disk rule content rather than re-typing patterns
    in Python, so a future edit to the JSON is exercised by this test without any
    duplication drift. `active` is overridden to True here only, never in the file.
    """
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    rules = []
    for rule_data in raw["rules"]:
        if rule_data["rule_id"] in _HR_RULE_IDS:
            forced = dict(rule_data)
            forced["active"] = True
            rules.append(SafetyRule.model_validate(forced))
    assert {r.rule_id for r in rules} == _HR_RULE_IDS, (
        f"Expected CF-006/CF-007/CF-008 in {_RULES_PATH}, found {[r.rule_id for r in rules]}"
    )
    return rules


_HR_RULES = _load_hr_rules()


def _flags(text_en: str) -> list[str]:
    result = _eval_safety(_HR_RULES, {"text_en": text_en, "text_ar": "", "language": "en"})
    return [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]


_HR_FLAGS = {"psychotic_disclosure", "mania_disclosure", "dissociation_disclosure"}


def _any_hr_flag(text_en: str) -> list[str]:
    return [f for f in _flags(text_en) if f in _HR_FLAGS]


# ── Gating: the file itself must ship inactive and unsigned ─────────────────

def test_hr_rules_ship_inactive_and_unsigned_on_disk():
    """CRITICAL gating (Task 1 brief): CF-006/007/008 must be active=false and carry
    no approved_by key in the real file until clinician ratification. This is the
    forcing function that keeps this branch's unsigned content from going live by
    accident; do not flip it without a ratification record."""
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in raw["rules"]}
    for rule_id in _HR_RULE_IDS:
        rule = by_id[rule_id]
        assert rule["active"] is False, f"{rule_id} must ship active=false pending ratification"
        assert "approved_by" not in rule, f"{rule_id} must omit approved_by until signed off"


def test_hr_patterns_contain_no_em_dash():
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in raw["rules"]}
    for rule_id in _HR_RULE_IDS:
        for pattern in by_id[rule_id]["patterns"]:
            assert "—" not in pattern, f"{rule_id} pattern {pattern!r} contains an em dash"


# ── Psychosis (14) — CF-006 extension ────────────────────────────────────────
# Items 1-4, 6-14 are new; item 5 ("I hear voices") already existed pre-extension.

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

def test_psychosis_14_detached_from_reality():
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
