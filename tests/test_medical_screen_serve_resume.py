"""D1 serve/resume (#338) — the held-skill suspended state + re-entry treatment, red-verified both directions.

GATE 0 acceptance (2026-07-17-d1-serve-resume-gate0-acceptance.md), constraint 1:
- ask_screen STORES the held contraindicated skill; a clear_no answer RESUMES it.
- the re-entry surface: crisis / veto / topic-change on the pending turn all RELEASE the hold.
- PROPERTY: no path leaves screen_pending True after the answer turn (the hold can't outlive one turn).
"""
import hashlib, json, pathlib
import pytest
from sage_poc import config
from sage_poc.safety import medical_screen as ms


def _enforce(mp):
    mp.setattr(config, "D1_SCREEN_ENABLED", True)
    mp.setattr(config, "D1_SCREEN_SHADOW", False)


def _tipp_result():
    return {"active_skill_id": "dbt_tipp", "active_step_id": "entry_screen", "path": ["skill_select"]}


# ── ask_screen stores the held skill (so resume knows what to bring back) ──
def test_ask_screen_stores_held_skill(monkeypatch):
    _enforce(monkeypatch)
    out = ms.apply_screen_at_route({"detected_language": "en"}, _tipp_result())
    assert out.get("screen_pending") is True
    assert out.get("active_skill_id") is None            # TIPP not entered yet — question is served instead
    assert out.get("screen_held_skill") == "dbt_tipp"    # held for resume


# ── the answer turn RESUMES the held skill on clear_no ──
def test_resume_clear_no_reenters_held_skill(monkeypatch):
    _enforce(monkeypatch)
    # answer turn: answering_screen set (graph consumed screen_pending), held skill carried in state
    state = {"detected_language": "en", "answering_screen": True, "screen_held_skill": "dbt_tipp",
             "raw_message": "no, it's the same as always"}
    out = ms.apply_screen_at_route(state, {"active_skill_id": None, "path": ["skill_select"]})
    assert out["active_skill_id"] == "dbt_tipp"           # resumed
    assert out.get("screen_pending") is False             # hold resolved
    assert out.get("session_screen_answer") == "clear_no"


def test_resume_contraindication_disclosed_reroutes_grounding(monkeypatch):
    _enforce(monkeypatch)
    state = {"detected_language": "en", "answering_screen": True, "screen_held_skill": "dbt_tipp",
             "raw_message": "actually I have a heart condition"}
    out = ms.apply_screen_at_route(state, {"active_skill_id": None, "path": ["skill_select"]})
    assert out["active_skill_id"] == "grounding_5_4_3_2_1"  # routed away, NOT the held TIPP
    assert out.get("screen_pending") is False


# ── topic-change / non-answer → evaded → grounding, hold RELEASED, no re-ask nagging ──
def test_topic_change_releases_hold_no_reask(monkeypatch):
    _enforce(monkeypatch)
    state = {"detected_language": "en", "answering_screen": True, "screen_held_skill": "dbt_tipp",
             "raw_message": "anyway, my week at work has been really busy"}
    out = ms.apply_screen_at_route(state, {"active_skill_id": None, "path": ["skill_select"]})
    assert out["active_skill_id"] == "grounding_5_4_3_2_1"  # fail-safe
    assert out.get("screen_pending") is False               # released — not re-asked
    assert out.get("screen_question_text") is None or "screen_question_text" not in out  # no re-ask


# ── PROPERTY: the hold never outlives one turn — any answer-turn utterance clears screen_pending ──
@pytest.mark.parametrize("raw", [
    "no, same as always", "I have a heart condition", "yes it feels different",
    "I don't know honestly", "what's the weather like", "",
])
def test_pending_never_survives_more_than_one_turn(monkeypatch, raw):
    _enforce(monkeypatch)
    state = {"detected_language": "en", "answering_screen": True, "screen_held_skill": "dbt_tipp",
             "raw_message": raw}
    out = ms.apply_screen_at_route(state, {"active_skill_id": None, "path": ["skill_select"]})
    assert out.get("screen_pending") is False, f"hold survived for utterance {raw!r}"


# ── safety_check consumes the persisted pending flag into a per-turn answering signal (structural guarantee) ──
def test_safety_check_consumes_pending_into_answering_signal():
    # the graph-entry consumption: persisted screen_pending -> per-turn answering_screen + pending cleared,
    # so screen_pending is True for EXACTLY the emit turn, regardless of how turn N+1 routes.
    upd = ms.consume_pending_screen({"screen_pending": True})
    assert upd == {"answering_screen": True, "screen_pending": False}
    assert ms.consume_pending_screen({"screen_pending": False}) == {}   # no-op when nothing pending


# ── constraint 2: the terminal emit serves the SIGNED bytes, hash-matched to the manifest ──
def test_served_bytes_hash_match_manifest():
    served = ms.screen_question("en")
    manifest = json.loads((pathlib.Path(__file__).resolve().parent.parent
                           / "docs/superpowers/governance/signed_clinical_fields.json").read_text())
    entry = next(f for f in manifest["fields"] if f["id"] == "d1_screen_question_en")
    # manifest pins sha256 of json.dumps(value) (the _extract convention) — served bytes must reproduce it
    got = hashlib.sha256(json.dumps(served, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert got == entry["sha256"], "served screen bytes drifted from the signed manifest hash"
