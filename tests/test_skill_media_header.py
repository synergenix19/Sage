"""Lane 2 Item 3 — X-Sage-Skill-Media response header.

Skill-delivered video (SkillStep.media) surfaced on a SEPARATE header, not X-Sage-Sources:
skill media is not a retrieved knowledge_passage, so riding the sources channel would break
its audit invariant (sources subset of knowledge_passage_ids). The new header must inherit
X-Sage-Sources' safety semantics BY TEST: gate_path allowlist (fail-closed), ensure_ascii,
and a default-OFF kill-switch (byte-identical when off).

server.py lives at the repo root, so `from server import ...` (see test_knowledge_source_cards.py).
"""
import json
import pytest
from server import _skill_media_header, _skill_media_entry
from sage_poc.skills.schema import SkillMediaItem


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    # Default the kill-switch ON for these tests; the OFF case is tested explicitly.
    monkeypatch.setenv("SAGE_SKILL_MEDIA_ENABLED", "true")


def _res(gate_path="standard", skill_id="mindfulness_meditation",
         executed_step_id="settle_and_anchor", lang="en"):
    return {"gate_path": gate_path, "active_skill_id": skill_id,
            "executed_step_id": executed_step_id, "detected_language": lang}


def test_emits_for_step_with_media_on_standard():
    hdr = _skill_media_header(_res())
    assert json.loads(hdr) == {
        "type": "video",
        "url": "https://www.youtube.com/watch?v=XInJoYvy_ew",
        "title": "Meditation for Working with Difficulties",
        "provider": "UCLA Health",
    }


def test_killswitch_off_is_byte_identical_none(monkeypatch):
    monkeypatch.setenv("SAGE_SKILL_MEDIA_ENABLED", "false")
    assert _skill_media_header(_res()) is None
    monkeypatch.delenv("SAGE_SKILL_MEDIA_ENABLED", raising=False)   # unset = OFF
    assert _skill_media_header(_res()) is None


def test_allowlist_fail_closed_on_non_standard_paths():
    # Inherits X-Sage-Sources allowlist: crisis/medical/hr/ipv/unknown all suppress.
    for gp in ("crisis", "medical", "hr", "ipv", "jailbreak", "scope_refusal", "future_route", None):
        assert _skill_media_header(_res(gate_path=gp)) is None


def test_none_for_step_without_media():
    assert _skill_media_header(_res(executed_step_id="entry_screen")) is None
    assert _skill_media_header(_res(executed_step_id="observe_and_return")) is None


def test_none_for_missing_language_graceful_en_only():
    # AR/az media not populated yet -> no media emitted (skill still delivers via text).
    assert _skill_media_header(_res(lang="ar")) is None
    assert _skill_media_header(_res(lang="az")) is None


def test_none_without_skill_or_step_or_unknown_skill():
    assert _skill_media_header(_res(skill_id=None)) is None
    assert _skill_media_header(_res(executed_step_id=None)) is None
    assert _skill_media_header(_res(skill_id="no_such_skill")) is None


def test_entry_is_ascii_safe_with_arabic_title():
    # ensure_ascii=True: an Arabic title/provider stays HTTP-header-safe and round-trips.
    item = SkillMediaItem(type="video", url="https://youtu.be/x", title="القلق", provider="مزود")
    hdr = _skill_media_entry(item)
    assert hdr.isascii()
    assert json.loads(hdr)["title"] == "القلق" and json.loads(hdr)["provider"] == "مزود"
