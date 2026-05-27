"""Phase B: Deterministic gate isolation tests for CUO-ID-001.

Tests the output_gate cultural_output evaluation in isolation — no LLM, no full graph.
Covers:
  B-1: True positive exact match
  B-2: True positive variant forms (including Arabic output patterns)
  B-3: True negative safe responses
  B-4: True negative referral language (critical clinical regression guard)
  B-5: Hash determinism (PDPL audit requirement)
"""
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(response_en: str, gate_path=None):
    return {
        "gate_path": gate_path,
        "path": [],
        "detected_language": "en",
        "message_en": "test message",
        "response_en": response_en,
        "is_safe": True,
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "turn_count": 0,
        "conversation_summary": None,
        "session_id": "sess-audit",
        "user_id": "user-audit",
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "s7_result": None,
        "s7_method": None,
        "third_party_crisis": False,
        "escalation_triggered": None,
    }


async def _run_gate(response_en: str, gate_path=None):
    """Run output_gate_node with live rules engine (no LLM mock needed)."""
    from sage_poc.nodes.output_gate import output_gate_node
    state = _make_state(response_en, gate_path)
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        return await output_gate_node(state)


# ---------------------------------------------------------------------------
# B-1: True positive — exact match
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_b1_exact_match_therapist_claim():
    """B-1: 'I am a therapist and I'm here to help' must trigger CUO-ID-001 substitution."""
    result = await _run_gate("I am a therapist and I'm here to help.")
    assert result["identity_substitution_rule_id"] == "CUO-ID-001", (
        "B-1 FAIL: CUO-ID-001 must fire on 'I am a therapist'"
    )
    assert result["original_response_hash"] is not None
    assert len(result["original_response_hash"]) == 16, (
        "B-1 FAIL: original_response_hash must be 16-char sha256 prefix"
    )
    assert "wellness companion" in result["response"], (
        "B-1 FAIL: substituted response must contain 'wellness companion'"
    )
    assert "I am a therapist" not in result["response"], (
        "B-1 FAIL: original identity claim must not reach the user"
    )


# ---------------------------------------------------------------------------
# B-2: True positive — variant forms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("response,label", [
    ("As your therapist, I suggest we work through this together.", "as-your-therapist"),
    ("I'm a licensed counsellor and I'm here to support you.", "im-a-counsellor"),
    ("As a coach, I can tell you that this takes practice.", "as-a-coach"),
    ("I'm a counselor — let me help you work through this.", "im-a-counselor-em-dash"),
    ("I'm a mental health professional and I'll guide you.", "im-a-mhp"),
    ("As a therapist, my role is to support your wellbeing.", "as-a-therapist"),
    ("I am a coach and together we will work on this.", "i-am-a-coach"),
    ("I'm a life coach here to help you achieve your goals.", "im-a-life-coach"),
    ("As a psychologist, I can offer you some perspective.", "as-a-psychologist"),
    ("I am a psychologist with experience in anxiety.", "i-am-a-psychologist"),
    ("أنا معالجك وأنا هنا لمساعدتك", "arabic-im-your-therapist"),
    ("أنا مستشارك النفسي", "arabic-im-your-counsellor"),
    ("أنا أخصائي في الصحة النفسية", "arabic-im-a-specialist"),
])
async def test_b2_variant_forms(response, label):
    """B-2: All variant identity claims must trigger CUO-ID-001."""
    result = await _run_gate(response)
    assert result["identity_substitution_rule_id"] == "CUO-ID-001", (
        f"B-2 FAIL [{label}]: CUO-ID-001 must fire on: {response!r}"
    )
    assert "wellness companion" in result["response"], (
        f"B-2 FAIL [{label}]: substituted response must contain 'wellness companion'"
    )


# ---------------------------------------------------------------------------
# B-3: True negative — safe responses that must NOT trigger CUO-ID-001
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("response,label", [
    ("I'm a wellness companion here to support you.", "wellness-companion"),
    ("Let's explore that together.", "explore-together"),
    ("That sounds really difficult. Can you tell me more?", "empathy-probe"),
    ("Many people find CBT helpful for managing anxious thoughts.", "cbt-education"),
    ("What's been going on for you lately?", "open-question"),
    ("I hear you. That sounds exhausting.", "validation"),
    ("I'm Sage, and I'm here to listen.", "sage-self-intro"),
])
async def test_b3_safe_responses_not_blocked(response, label):
    """B-3: Safe, correct responses must pass through CUO-ID-001 without substitution."""
    result = await _run_gate(response)
    assert result["identity_substitution_rule_id"] is None, (
        f"B-3 FAIL [{label}]: False positive — CUO-ID-001 must NOT fire on: {response!r}"
    )
    assert result["original_response_hash"] is None, (
        f"B-3 FAIL [{label}]: original_response_hash must be None when no substitution"
    )
    assert result["response"] == response, (
        f"B-3 FAIL [{label}]: Response must pass through unmodified, got: {result['response']!r}"
    )


# ---------------------------------------------------------------------------
# B-4: True negative — CRITICAL: referral language must NOT trigger CUO-ID-001
#
# If these fire, the system cannot fulfill its clinical obligation to refer
# users to professional help. A false positive here is a clinical safety
# regression worse than the identity problem the rule was written to fix.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("response,label", [
    (
        "I'd recommend speaking with a therapist about this — they can provide "
        "the kind of ongoing support that goes beyond what I'm able to offer.",
        "recommend-therapist"
    ),
    (
        "A trained counsellor could help you work through this in more depth.",
        "recommend-counsellor"
    ),
    (
        "It might be worth speaking with a psychologist or psychiatrist "
        "to get a professional assessment.",
        "recommend-psychologist"
    ),
    (
        "Cognitive behavioural therapy (CBT) is something therapists use to help "
        "with these kinds of thought patterns.",
        "psychoeducation-cbt"
    ),
    (
        "Many counsellors and coaches use this technique in their practice.",
        "psychoeducation-counsellors"
    ),
    (
        "If you're looking for ongoing support, connecting with a licensed therapist "
        "would be a great next step.",
        "referral-licensed"
    ),
])
async def test_b4_referral_language_not_blocked(response, label):
    """B-4 CRITICAL: Referral language must pass through CUO-ID-001 without substitution.

    Patterns in CUO-ID-001 are scoped to self-identification ('I am a', 'I'm a',
    'as a', 'as your') and must NOT fire when the word 'therapist'/'counsellor'
    appears in a third-person referral context.
    """
    result = await _run_gate(response)
    assert result["identity_substitution_rule_id"] is None, (
        f"B-4 CLINICAL SAFETY FAIL [{label}]: CUO-ID-001 fired on referral language.\n"
        f"Input: {response!r}\n"
        f"This is a false positive — the system cannot refer users to professional help."
    )
    assert result["original_response_hash"] is None, (
        f"B-4 FAIL [{label}]: No substitution should have occurred."
    )


# ---------------------------------------------------------------------------
# B-5: Hash determinism (PDPL Art. 6 requirement)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_b5_hash_is_deterministic():
    """B-5: Hashing the same original response twice must produce identical hashes.

    Required for PDPL Art. 6 — if a user challenges a substitution, the audit
    trail must reproducibly prove what the original response was.
    """
    original = "I am a therapist and I'm here to guide you through this."
    result_1 = await _run_gate(original)
    result_2 = await _run_gate(original)

    assert result_1["original_response_hash"] == result_2["original_response_hash"], (
        "B-5 FAIL: SHA-256 hash of the same original response must be identical "
        f"across invocations. Got: {result_1['original_response_hash']!r} vs "
        f"{result_2['original_response_hash']!r}"
    )


@pytest.mark.asyncio
async def test_b5_hash_matches_sha256_of_original():
    """B-5: Stored hash must match sha256(original_text)[:16] — verifies reconstruction."""
    original = "I am a therapist and I'm here to help."
    result = await _run_gate(original)

    expected_hash = hashlib.sha256(original.encode()).hexdigest()[:16]
    assert result["original_response_hash"] == expected_hash, (
        f"B-5 FAIL: Stored hash {result['original_response_hash']!r} does not match "
        f"sha256({original!r})[:16] = {expected_hash!r}"
    )


# ---------------------------------------------------------------------------
# B-6: Rule file completeness (Phase A gap verification)
# ---------------------------------------------------------------------------

def test_b6_cuo_id_001_covers_required_patterns():
    """B-6: Verify CUO-ID-001 covers every pattern the audit spec requires."""
    import json
    from pathlib import Path

    path = (
        Path(__file__).parent.parent
        / "src/sage_poc/rules/data/cultural_output/wellness_identity.json"
    )
    data = json.loads(path.read_text())
    patterns = data["rules"][0]["patterns"]
    patterns_lower = [p.lower() for p in patterns]

    required = [
        "i am a therapist",
        "i'm a therapist",
        "as a therapist",
        "i am a counsellor",
        "i'm a counselor",
        "as your counsellor",
        "i am a coach",
        "i'm a life coach",
        "as a psychologist",
        "i am a mental health professional",
    ]
    missing = [r for r in required if r not in patterns_lower]
    assert not missing, (
        f"CUO-ID-001 is missing required patterns: {missing}"
    )
