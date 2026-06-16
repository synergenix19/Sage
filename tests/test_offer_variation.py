import sage_poc.nodes.skill_select as skill_select
from sage_poc.nodes.skill_select import _resolve_entry, _SKILLS


def _base_state():
    return {"path": [], "detected_language": "en", "emotional_intensity": 5,
            "declined_skills": []}


def test_offer_made_sets_offer_count_to_one(monkeypatch):
    # Force the offer path: make the skill_matching rule engine fire nothing,
    # so _resolve_entry falls back to _FALLBACK_OFFER_ACTION (offer).
    class _NoFire:
        fired = []
    monkeypatch.setattr(skill_select.rules_engine, "evaluate", lambda *a, **k: _NoFire())

    candidates = list(_SKILLS.keys())[:2]
    result = _resolve_entry(_base_state(), candidates, "keyword", None)

    assert "skill_offer_made" in result["path"]
    assert result["offered_skill_ids"] == candidates
    assert result["offer_count"] == 1
