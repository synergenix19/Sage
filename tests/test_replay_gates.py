import asyncio
from unittest.mock import AsyncMock, patch

from scripts.register_eval.replay_gates import gate_fire_summary, replay_gates_on_row


def test_summary_counts_and_rate():
    rows = [{"cultural_fired": ["general_cultural"], "banned_opener": False, "format_tokens": []},
            {"cultural_fired": [], "banned_opener": True, "format_tokens": ["*"]},
            {"cultural_fired": [], "banned_opener": False, "format_tokens": []}]
    s = gate_fire_summary(rows)
    assert s["n"] == 3 and s["cultural_fires"] == 1 and s["banned_opener_fires"] == 1
    assert s["any_gate_fire_rate"] == round(2/3, 4)


def test_banned_opener_matches_after_lstrip():
    # Live gate (nodes/output_gate.py) matches _BANNED_OPENER_RE.match(response_en.lstrip()).
    # This pins that the replay mirrors the lstrip, not just the pattern: a leading newline
    # before a banned opener must still fire, exactly as it does on the live turn.
    row = {"shadow_arabic_text": "x", "message_en": "", "clinical_flags": []}
    with patch(
        "sage_poc.language.async_translate_to_english",
        new=AsyncMock(return_value="\n  It sounds like you are struggling."),
    ):
        out = asyncio.run(replay_gates_on_row(row))
    assert out["banned_opener"] is True  # live gate lstrips; replay must too
