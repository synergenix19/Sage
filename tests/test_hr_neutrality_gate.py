"""Node-8 HR §5 content-neutrality gate — deterministic ELIMINATION of the ruled fact-in-world frames.

Unlike the interim prompt-nudge (verified as REDUCTION by sampling), this gate is deterministic, so it
is verified as ELIMINATION: the two ruled §5 misses ("experiencing [content]", "feeling like [content]")
ALWAYS route to the signed fallback; the ratified account-frame ALWAYS passes; and the check is a strict
no-op off the HR referral terminal (so it can never false-reject reflective statements in other tracks).
Fixtures include the fallback-render path, which is now user-facing.
"""
from sage_poc.nodes.output_gate import _enforce_hr_neutrality, _hr_neutral_fallback

# The two frames Vee RULED over the §5 line (paranoia#1 + the 1/4 post-interim residual):
_RULED_MISS_EXPERIENCING = ("It sounds like you're experiencing something very distressing with people "
                            "following and watching you. This is important to talk through with a mental "
                            "health professional. 800-HOPE (800-4673) or emergency services 999.")
_RULED_MISS_FEELING_LIKE = ("Feeling like people are following and watching you can be very distressing. "
                            "It's important to have the right support for this. 800-HOPE (800-4673), 999.")
# The ratified account-frame (won 3/4):
_CLEAN_ACCOUNT_FRAME = ("What you're describing sounds really important, and it's something to talk "
                        "through with a mental health professional. 800-HOPE (800-4673), 999.")


def test_ruled_experiencing_frame_is_rejected_to_fallback():
    out, rejected = _enforce_hr_neutrality(_RULED_MISS_EXPERIENCING, is_hr_referral=True, lang="en")
    assert rejected is True
    assert out == _hr_neutral_fallback("en")
    assert "what you're describing" in out.lower()  # fallback is account-framed


def test_ruled_feeling_like_frame_is_rejected_to_fallback():
    out, rejected = _enforce_hr_neutrality(_RULED_MISS_FEELING_LIKE, is_hr_referral=True, lang="en")
    assert rejected is True
    assert out == _hr_neutral_fallback("en")


def test_ratified_account_frame_passes_unchanged():
    out, rejected = _enforce_hr_neutrality(_CLEAN_ACCOUNT_FRAME, is_hr_referral=True, lang="en")
    assert rejected is False
    assert out == _CLEAN_ACCOUNT_FRAME  # byte-identical no-op


def test_off_scope_is_strict_no_op_no_false_reject():
    # A reflective statement in the anxiety/low-mood track — NOT the HR referral — must never be touched.
    reflective = "It sounds like the panic is overwhelming right now. Let's try box breathing together."
    out, rejected = _enforce_hr_neutrality(reflective, is_hr_referral=False, lang="en")
    assert rejected is False
    assert out == reflective


def test_fallback_renders_completely_and_carries_the_number():
    # The reject path is user-facing: the fallback must be a complete, non-empty, account-framed message
    # with the single-sourced helpline + emergency number, never empty / never fail-open.
    for lang in ("en", "ar"):
        fb = _hr_neutral_fallback(lang)
        assert fb and len(fb) > 40
        assert "4673" in fb or "800-HOPE" in fb  # single-sourced from CRISIS_CONFIG
        assert "999" in fb


def test_arabic_drift_rejected_account_frame_passes():
    ar_clean = "ما تصفه مهم وتحتاج فيه دعم من متخصص. خط الدعم النفسي الوطني 800-4673، والطوارئ 999."
    ar_drift = "الناس يراقبونك ويلاحقونك وهذا شيء مقلق جداً. اتصل بخط الدعم 800-4673."
    out_clean, rej_clean = _enforce_hr_neutrality(ar_clean, is_hr_referral=True, lang="ar")
    out_drift, rej_drift = _enforce_hr_neutrality(ar_drift, is_hr_referral=True, lang="ar")
    assert rej_clean is False and out_clean == ar_clean
    assert rej_drift is True and out_drift == _hr_neutral_fallback("ar")


def test_never_fails_open_or_empty_on_reject():
    out, rejected = _enforce_hr_neutrality("people are watching you and it is real", is_hr_referral=True, lang="en")
    assert rejected is True
    assert out.strip()  # never empty


import pytest
from unittest.mock import AsyncMock, patch


def _hr_state(response_en, **kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "en",
        "message_en": "people are following me", "response_en": response_en,
        "raw_message": "people are following me", "is_safe": True, "crisis_state": "none",
        "crisis_flags": [], "clinical_flags": ["psychotic_disclosure"],
        "skill_match_method": "psychotic_disclosure_auto_select",
        "completed_skill_id": "psychotic_referral",
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


_DRIFTED = ("It sounds like you're experiencing something distressing with people following and "
            "watching you. Please reach 800-HOPE (800-4673) or emergency services 999.")


async def _run_gate(state):
    from sage_poc.nodes.output_gate import output_gate_node
    with patch("sage_poc.nodes.output_gate.write_session_audit", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock(), create=True), \
         patch("sage_poc.nodes.output_gate._rewrite_opener", new=AsyncMock(side_effect=lambda *a, **k: a[0])):
        return await output_gate_node(state)


@pytest.mark.asyncio
async def test_output_gate_template_swaps_drifted_hr_referral_when_flag_on(monkeypatch):
    from sage_poc.nodes.output_gate import _hr_neutral_fallback
    import sage_poc.config as cfg
    monkeypatch.setattr(cfg, "HR_NEUTRALITY_GATE_ENABLED", True)
    result = await _run_gate(_hr_state(_DRIFTED))
    assert result["hr_neutrality_rejected"] is True           # audit channel set
    assert result["response"] == _hr_neutral_fallback("en")   # template swapped


@pytest.mark.asyncio
async def test_output_gate_no_op_when_flag_off(monkeypatch):
    import sage_poc.config as cfg
    monkeypatch.setattr(cfg, "HR_NEUTRALITY_GATE_ENABLED", False)
    result = await _run_gate(_hr_state(_DRIFTED))
    assert result["hr_neutrality_rejected"] is False          # inert when flag off
    assert _DRIFTED[:30] in result["response"]                # drifted output passes through unchanged


@pytest.mark.asyncio
async def test_output_gate_no_op_off_hr_path(monkeypatch):
    import sage_poc.config as cfg
    monkeypatch.setattr(cfg, "HR_NEUTRALITY_GATE_ENABLED", True)
    # a normal skill turn (not the HR referral) must never be touched
    result = await _run_gate(_hr_state("Let's try box breathing together.",
                                       skill_match_method="keyword", clinical_flags=[], completed_skill_id="box_breathing"))
    assert result["hr_neutrality_rejected"] is False
    assert "box breathing" in result["response"].lower()
