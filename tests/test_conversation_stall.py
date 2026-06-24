"""Deterministic conversational-stall detector (F-stall-guard).

The trigger MUST be computed in code — the LLM never decides whether a stall
happened (it only renders the change-of-tack downstream). These tests pin the
deterministic trigger. The specific thresholds are a PROVISIONAL heuristic pending
validation against real transcripts; the determinism is not provisional.
"""
from sage_poc.conversation_stall import detect_stall


def test_three_consecutive_low_content_turns_is_a_stall():
    # The Parenting-session pattern: "not sure" x3+ with no progress.
    assert detect_stall(["not sure", "not sure", "not sure"]) is True


def test_two_low_content_turns_is_not_yet_a_stall():
    # A run of 3 is required; two is normal back-and-forth.
    assert detect_stall(["not sure", "not sure"]) is False


def test_short_skill_flow_confirmations_are_not_a_stall():
    # Validation against prod session aa0a9256 (t5-t8): short affirmatives /
    # answers during a skill flow are engagement, not a stall. Only genuine
    # non-answers count toward the run.
    assert detect_stall(["okay sure", "lets start", "no"]) is False
    assert detect_stall(["lets start", "no", "still angry"]) is False


def test_near_verbatim_repeat_of_current_turn_is_a_stall():
    # The Sleep-session pattern: the user resends the same substantive point.
    repeated = "we are just very different people and constantly disagree"
    assert detect_stall(["I feel distant from my friend", repeated, repeated]) is True


def test_varied_substantive_conversation_is_not_a_stall():
    assert detect_stall([
        "my kids are breaking things and yelling",
        "I try to speak calmly but they won't listen",
        "I feel overwhelmed and angry",
    ]) is False


def test_empty_or_short_history_is_not_a_stall():
    assert detect_stall([]) is False
    assert detect_stall(["not sure"]) is False
    assert detect_stall(None) is False
