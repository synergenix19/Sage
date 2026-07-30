"""Structural + anti-tautology guards for the EMR Phase-0 request-conformance
fixture family (tests/fixtures/conformance/emr_request_family.json).

Fixture-independence rule (E7 lesson, project_e7_verbatim_match_gap): a recall
number computed over fixtures copied from the detector's own lexicon is a
tautology, not a measurement. The family must stay independent of the v3
request-phrase lexicon (rules/data/skill_matching/skill_request_phrases.json)
for the Phase-0 baseline and the Phase-3 re-measurement to mean anything.
"""
import json
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FAMILY = os.path.join(_ROOT, "tests/fixtures/conformance/emr_request_family.json")
_LEXICON = os.path.join(_ROOT, "rules/data/skill_matching/skill_request_phrases.json")

# The observed live transcript (2026-07-28) — the verbatim anchor for case 000.
# Embedded as constants: the source fixture (1a_transcript_replay.json) lives on
# branch 1a-gap-phase0, not master, so the verbatim contract is pinned here.
_OBSERVED_TRANSCRIPT = [
    "I'm feeling anxious",
    "can you tell me how to manage my anxiety",
    "are there any exercises i can do",
]


@pytest.fixture(scope="module")
def family():
    with open(_FAMILY, encoding="utf-8") as f:
        return json.load(f)


def _cases(family, surface=None):
    cases = family["cases"]
    if surface is None:
        return cases
    return [c for c in cases if c["surface"] == surface]


def _all_messages(family):
    return [msg for c in family["cases"] for msg in c["turns"]]


# ---------------------------------------------------------------------------
# Family composition
# ---------------------------------------------------------------------------

def test_family_has_three_surface_trajectories(family):
    surfaces = {c["surface"] for c in family["cases"]}
    for s in ("s1_active_skill_absorption", "s2_cold_request", "s3_over_pending_offer"):
        assert s in surfaces, f"missing surface trajectory {s}"
    assert len(_cases(family, "s1_active_skill_absorption")) == 1
    assert len(_cases(family, "s2_cold_request")) == 1
    assert len(_cases(family, "s3_over_pending_offer")) == 1


def test_family_has_twelve_paraphrases_and_three_controls(family):
    assert len(_cases(family, "paraphrase")) == 12
    assert len(_cases(family, "control")) == 3
    assert len(family["cases"]) == 18


def test_case_ids_unique(family):
    ids = [c["case_id"] for c in family["cases"]]
    assert len(ids) == len(set(ids))


def test_every_case_is_a_multi_field_session(family):
    for c in family["cases"]:
        assert c["turns"], f"{c['case_id']}: empty session"
        assert all(isinstance(t, str) and t.strip() for t in c["turns"])
        assert c.get("spec_expectation"), f"{c['case_id']}: missing spec_expectation"
        assert c.get("provenance"), f"{c['case_id']}: missing provenance line"


# ---------------------------------------------------------------------------
# Case 000: the observed live transcript, VERBATIM
# ---------------------------------------------------------------------------

def test_case_000_is_the_observed_transcript_verbatim(family):
    s1 = _cases(family, "s1_active_skill_absorption")[0]
    assert s1["case_id"].endswith("000")
    assert s1["turns"] == _OBSERVED_TRANSCRIPT, (
        "case 000 must be the observed live transcript VERBATIM — it is the one "
        "naturalistic ground-truth session; do not 'improve' its phrasing")
    assert "live transcript" in s1["provenance"]


def test_s2_uses_the_observed_request_phrase_cold(family):
    """s2 isolates the surface variable (no active skill) by reusing the observed
    request phrase in a cold context."""
    s2 = _cases(family, "s2_cold_request")[0]
    assert s2["turns"][-1] == _OBSERVED_TRANSCRIPT[-1]
    assert len(s2["turns"]) == 2  # disclosure -> request; no psychoed turn between


# ---------------------------------------------------------------------------
# Paraphrase provenance + controls
# ---------------------------------------------------------------------------

def test_every_paraphrase_declares_lexicon_independence(family):
    for c in _cases(family, "paraphrase"):
        assert "lexicon" in c["provenance"].lower(), (
            f"{c['case_id']}: provenance must state lexicon independence explicitly")


def test_paraphrase_requests_are_distinct_from_each_other_and_from_case_000(family):
    requests = [c["turns"][-1].strip().lower() for c in _cases(family, "paraphrase")]
    assert len(set(requests)) == 12, "paraphrase request phrasings must be distinct"
    assert _OBSERVED_TRANSCRIPT[-1].lower() not in requests, (
        "a paraphrase may not duplicate the observed verbatim request")


def test_controls_cover_curiosity_bare_affect_and_info_ask(family):
    controls = {c["case_id"]: c for c in _cases(family, "control")}
    msgs = [" ".join(c["turns"]).lower() for c in controls.values()]
    assert any("why does my body react like this?" in m for m in msgs)
    assert any(c["turns"] == ["anxious"] for c in controls.values())
    assert any("what's the crisis helpline number?" in m for m in msgs)


# ---------------------------------------------------------------------------
# Anti-tautology: fixture independence from the request-phrase lexicon
# ---------------------------------------------------------------------------

def _lexicon_strings(node):
    """Every string anywhere in the lexicon JSON (shape not yet fixed — the v3
    plan's lexicon has not landed; recurse so any future shape is covered)."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _lexicon_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _lexicon_strings(v)


def test_no_fixture_message_equals_a_lexicon_entry(family):
    # The request-phrase lexicon is a v3-plan concept that has NOT landed on master
    # yet (rules/data/skill_matching/ does not exist here). Skip until it lands —
    # this test then arms automatically and enforces fixture independence
    # (recall-fixture-independence rule earned from the E7 verbatim-match gap).
    if not os.path.exists(_LEXICON):
        pytest.skip("skill_request_phrases.json not on this branch yet — "
                    "anti-tautology guard arms automatically when the lexicon lands")
    with open(_LEXICON, encoding="utf-8") as f:
        lexicon = {s.strip().lower() for s in _lexicon_strings(json.load(f)) if s.strip()}
    for msg in _all_messages(family):
        assert msg.strip().lower() not in lexicon, (
            f"fixture message {msg!r} equals a lexicon entry — fixture=pattern "
            "tautology (E7 lesson); rewrite the fixture, never the lexicon")
