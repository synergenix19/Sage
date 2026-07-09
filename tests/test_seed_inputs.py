"""Content checks on scripts/register_eval/seed_inputs.json.

Not a rater oracle (see the file's own "note" field) -- this just verifies the
three clinician-authored 2026-07-08 slots (seed-016, seed-024, seed-025) landed
with non-empty text and the expected metadata, and that _load_seed_items now
picks them up (it skips empty-text entries).
"""
import json
from pathlib import Path

from scripts.register_eval.replay_driver import _load_seed_items

_SEED_PATH = Path(__file__).parent.parent / "scripts" / "register_eval" / "seed_inputs.json"

_FILLED = {
    "seed-016": {
        "lang_profile": "khaleeji",
        "text": "الدوام هالأسبوع وايد ضاغط، شغل فوق شغل وما ألحق على شي، وأحس مخي وقف.",
    },
    "seed-024": {
        "lang_profile": "arabizi",
        "text": "wallah el yoom kan wayed taweel, kel wa7ed yabi shay minni.. yaani mo shay kbeer bs abi afadfad shway",
    },
    "seed-025": {
        "lang_profile": "khaleeji",
        "text": "أشعر بضغط شديد في الفترة الأخيرة بسبب العمل… يعني الصراحة تعبت، كل يوم نفس الشي وما أدري من وين أبدي.",
    },
}


def _by_id(data):
    return {entry["id"]: entry for entry in data["inputs"]}


def test_three_target_seeds_have_clinician_authored_text():
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    entries = _by_id(data)
    for seed_id, expected in _FILLED.items():
        entry = entries[seed_id]
        assert entry["source"] == "clinician_authored_2026-07-08"
        assert entry["lang_profile"] == expected["lang_profile"]
        assert entry["text"] == expected["text"]
        assert entry["text"].strip()


def test_three_target_seeds_no_longer_placeholder():
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    entries = _by_id(data)
    for seed_id in _FILLED:
        assert entries[seed_id]["source"] != "PLACEHOLDER_NATIVE_AUTHOR"


def test_three_target_seeds_keep_id_and_intent_en():
    # id/lang_profile/intent_en must be preserved unchanged -- only source/text change.
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    entries = _by_id(data)
    for seed_id in _FILLED:
        entry = entries[seed_id]
        assert entry["id"] == seed_id
        assert "intent_en" in entry and entry["intent_en"]


def test_load_seed_items_now_includes_the_three_filled_seeds():
    items = _load_seed_items()
    ids = {it["source_message_id"] for it in items}
    assert {"seed-016", "seed-024", "seed-025"} <= ids


def test_remaining_placeholders_still_untouched():
    # Out of scope for this pass -- confirms we only filled the three assigned slots
    # and did not accidentally touch/fabricate the other seven PLACEHOLDER entries.
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    entries = _by_id(data)
    still_placeholder = {
        eid for eid, e in entries.items()
        if e["source"] == "PLACEHOLDER_NATIVE_AUTHOR"
    }
    assert still_placeholder == {
        "seed-017", "seed-018", "seed-019", "seed-020",
        "seed-021", "seed-022", "seed-023",
    }
