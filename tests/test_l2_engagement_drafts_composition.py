"""Deterministic evidence that the L2 engagement DRAFTS encode rule (a*).

These do NOT call an LLM. They assert the draft template CONTENT carries the
rule's instructions (single conditional bridge, no affect assumption,
ABSTAIN-as-recovery, grounding, single-question discipline, no em dashes, and
list-directive compatibility). This is the test evidence that can be produced
WITHOUT the OpenRouter key.

The LLM-OUTPUT behaviour (does the model actually produce a bridge, avoid
assumed distress, etc.) is the separate PromptFoo eval
(2026-07-07-l2-engagement-promptfoo.yaml), which requires OPENROUTER_API_KEY and
is run by the owner/CI before the review session.
"""
import json
from pathlib import Path

_DRAFTS = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "drafts"

INFO = "2026-07-07-info_request-v2.0.0-draft.json"
NEW = "2026-07-07-new_skill-v1.1.0-draft.json"
EXIT = "2026-07-07-exit_skill-v1.1.0-draft.json"
LOWC = "2026-07-07-low_confidence-v1.1.0-draft.json"
ALL = (INFO, NEW, EXIT, LOWC)


def _draft(name: str) -> dict:
    return json.loads((_DRAFTS / name).read_text())


def _content(name: str) -> str:
    return _draft(name)["content"]


def test_no_em_or_en_dashes_in_any_draft():
    for n in ALL:
        c = _content(n)
        assert "—" not in c and "–" not in c, f"{n} contains an em/en dash (mirrors into output)"


def test_drafts_are_unapproved_and_not_promoted():
    for n in ALL:
        d = _draft(n)
        assert d["approved_by"] is None, f"{n} must stay approved_by:null until sign-off"
        assert d["status"] == "draft-pending-review", f"{n} wrong status"


def test_info_request_encodes_rule_a_star():
    c = _content(INFO).lower()
    # exactly one conditional bridge, offered not assumed
    assert "one short, open invitation" in c
    assert "offered and never assumed" in c
    # preserves the do-not-pad CORE (no affect assumption / no unsolicited sympathy)
    assert "do not assume the person is struggling" in c
    assert "did not ask for" in c
    # grounding + ABSTAIN as recovery
    assert "ground the answer" in c
    assert "do not invent clinical facts" in c
    assert "that same invitation is the recovery" in c
    # single-question discipline
    assert "at most one question" in c


def test_info_request_bridge_is_affect_neutral():
    c = _content(INFO).lower()
    # invites what is behind the question / what helps — not an assumption of distress
    assert "what is behind the question" in c or "what would help next" in c
    # must NOT hardcode affect-assumptive sympathy
    for bad in ("that must be", "i'm sorry you", "that sounds really hard", "you must be feeling"):
        assert bad not in c, f"info_request draft hardcodes affect-assumptive phrasing: {bad!r}"


def test_info_request_does_not_forbid_list_structure():
    # 'plain, warm language' constrains VOICE not STRUCTURE, so it must coexist with
    # the L4 light_structure_directive (numbered list). Guard that no clause bans lists.
    c = _content(INFO).lower()
    for bad in ("prose only", "do not use a list", "no lists", "must be prose", "full sentences only"):
        assert bad not in c, f"info_request draft fights the L4 list directive: {bad!r}"


def test_new_and_exit_inherit_conditional_invitation():
    for n in (NEW, EXIT):
        c = _content(n).lower()
        assert "invitation" in c, f"{n} missing the conditional invitation"
        assert "do not assume" in c, f"{n} missing the no-assumption guard"
        assert "at most one question" in c, f"{n} missing single-question discipline"


def test_low_confidence_keeps_clarifying_contract_and_no_second_bridge():
    c = _content(LOWC).lower()
    assert "clarifying question" in c
    assert "two sentences" in c
    # its clarifying question IS the bridge — must NOT add an info-style invitation close
    assert "invitation" not in c, "low_confidence must not add a second bridge"
