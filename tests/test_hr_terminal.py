"""HR-1 Stage 2 Task 2 — SAGE_HIGH_RISK_TERMINAL kill-switch + the §HR fixed-copy
constants (docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md,
"Fixed copy" section). Config data only: assert on the constant VALUES, never
via the LLM.

The flag uses the same strict, inverted-default idiom as ROUTE_PRECEDENCE_ENABLED
(config.py:170-178): only a literal "true" (case-insensitive, whitespace-stripped)
enables; unset / empty / whitespace / any other garbage -> OFF. This is what
survives Railway's empty-string env-injection bug.
"""
import importlib

import sage_poc.config as config


def test_high_risk_terminal_default_off_with_no_env_set():
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


def test_strict_idiom_only_literal_true_enables(monkeypatch):
    # Values that must NOT enable the flag, including truthy-looking garbage and
    # the Railway empty-string injection case.
    for off_value in ("1", "yes", "", "false", "on", "  ", "truex"):
        monkeypatch.setenv("SAGE_HIGH_RISK_TERMINAL", off_value)
        importlib.reload(config)
        assert config.HIGH_RISK_TERMINAL_ENABLED is False, repr(off_value)

    # Case-insensitive / whitespace-tolerant literal "true" DOES enable (matches
    # the ROUTE_PRECEDENCE_ENABLED idiom's .strip().lower() == "true" semantics).
    for on_value in ("true", "TRUE", " true ", "True"):
        monkeypatch.setenv("SAGE_HIGH_RISK_TERMINAL", on_value)
        importlib.reload(config)
        assert config.HIGH_RISK_TERMINAL_ENABLED is True, repr(on_value)

    # Restore clean default state for any tests that import config afterward.
    monkeypatch.delenv("SAGE_HIGH_RISK_TERMINAL", raising=False)
    importlib.reload(config)
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


def test_unset_defaults_off_after_reload(monkeypatch):
    monkeypatch.delenv("SAGE_HIGH_RISK_TERMINAL", raising=False)
    importlib.reload(config)
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


# --- §HR fixed copy (verbatim) ---

def test_distress_question_verbatim_anchor():
    assert config.HR_DISTRESS_QUESTION == (
        "On a scale of 0 to 10, how distressing is this for you right now?"
    )
    assert "0 to 10" in config.HR_DISTRESS_QUESTION


def test_supportive_message_verbatim():
    assert config.HR_SUPPORTIVE_MESSAGE == (
        "Thank you for telling me what's going on for you. What you're describing "
        "sounds really difficult, and I want to make sure you get support from "
        "someone who can help properly with this."
    )


def test_lower_redirect_contains_see_a_doctor_anchor():
    assert "doctor or mental health professional" in config.HR_REDIRECT_LOWER


def test_reask_is_gentle_and_content_neutral():
    # Single re-ask: still carries the 0-10 question, does not probe the experience
    # itself (no "why", "what happened", "tell me more").
    assert "0 to 10" in config.HR_REASK
    for probing_phrase in ("why", "what happened", "tell me more"):
        assert probing_phrase not in config.HR_REASK.lower()


def test_no_em_dashes_in_any_copy_constant():
    # Project convention: em dashes never appear in copy that reaches the LLM/user.
    for name in (
        "HR_DISTRESS_QUESTION",
        "HR_SUPPORTIVE_MESSAGE",
        "HR_REDIRECT_LOWER",
        "HR_REASK",
    ):
        value = getattr(config, name)
        assert "—" not in value, f"{name} contains an em dash"


def test_higher_redirect_not_hardcoded_composes_from_crisis_pathway():
    # The 999/ER branch must NOT duplicate a literal resource list in config;
    # it composes from select_crisis_resources()/CRISIS_CONFIG (single-sourced
    # crisis directory), same as the rest of the crisis pathway.
    assert hasattr(config, "select_crisis_resources")
    assert hasattr(config, "CRISIS_CONFIG")
    if hasattr(config, "HR_REDIRECT_HIGHER_LEAD"):
        assert "—" not in config.HR_REDIRECT_HIGHER_LEAD
        # A lead-in template must not itself contain a resource number/link —
        # those come exclusively from the crisis pathway.
        assert "999" not in config.HR_REDIRECT_HIGHER_LEAD
