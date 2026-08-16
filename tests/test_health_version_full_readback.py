"""/health/version FULL flag readback — closes the remaining serving-readback coverage holes.

The instrument-parity standing rule (SIGNED 2026-07-28) makes a readback gap a HARD ERROR
for evidence runs: a flag in config.py not covered by the serving readback cannot be
asserted at measurement time (the 2026-07-23 cosine confound). This suite locks in that
EVERY parity-relevant SAGE_* var config.py reads is exposed as resolved + *_raw_env —
same pattern as the existing fields (test_health_version_d1_readback.py): resolved value
is the RUNNING process's config module state (what fires), raw_env is the provenance
string, and unset raw_env is null, NEVER fabricated.
"""
import asyncio
import re
import os

import server
from sage_poc import config


def _version():
    return asyncio.run(server.health_version(None))


_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Same enumeration + denylist as the conformance runner's parity guard
# (scripts/bot_behaviour_audit/measure_layer1_fullgraph.py::_config_sage_vars).
_PARITY_INFRA_DENYLIST = {
    "SAGE_DB_POOL_MAX_SIZE", "SAGE_HTTP_MAX_CONNECTIONS", "SAGE_HTTP_MAX_KEEPALIVE",
    "SAGE_CHECKPOINT_POOL_MAX_SIZE", "SAGE_AUDIT_LOG", "SAGE_WARMUP_BGE",
    "SAGE_EMBED_CACHE_ENABLED", "SAGE_TEST_USER_IDS", "SAGE_API_KEY",
}


def _parity_vars():
    src = open(os.path.join(_REPO, "src", "sage_poc", "config.py"), encoding="utf-8").read()
    return sorted({m.group(1) for m in re.finditer(r'os\.getenv\(\s*"(SAGE_[A-Z0-9_]+)"', src)}
                  - _PARITY_INFRA_DENYLIST)


def _served_sage_vars(v):
    """The parity guard's serving map: *_raw_env field -> SAGE_ var name."""
    return {"SAGE_" + k[: -len("_raw_env")].upper() for k in v if k.endswith("_raw_env")}


# ---------------------------------------------------------------------------
# The load-bearing closure test: readback coverage == the parity var set.
# A NEW config.py flag that lands without a readback field fails here at birth.
# ---------------------------------------------------------------------------

def test_every_parity_var_is_covered_by_the_serving_readback():
    served = _served_sage_vars(_version())
    missing = [var for var in _parity_vars() if var not in served]
    assert missing == [], (
        f"config.py parity vars with NO /health/version *_raw_env readback "
        f"(refuse-on-gap would hard-error an evidence run): {missing}"
    )


def test_audit_log_off_state_is_loudly_visible():
    """SAGE_AUDIT_LOG ruled safety-class 2026-07-28: 'an OFF state must be LOUDLY visible
    in /health/version' — so it is readback-covered despite being parity-denylisted."""
    v = _version()
    assert "audit_log_enabled" in v
    assert "audit_log_raw_env" in v


# ---------------------------------------------------------------------------
# Resolved values come from the config MODULE (what actually fires), not an
# env re-parse — same contract as the existing fields.
# ---------------------------------------------------------------------------

def test_model_vars_report_resolved_module_values(monkeypatch):
    monkeypatch.setattr(config, "CLASSIFIER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setattr(config, "RESPONDER_MODEL", "openai/gpt-4o")
    monkeypatch.setattr(config, "TRANSLATOR_MODEL", "openai/test-translator")
    monkeypatch.setattr(config, "FALLBACK_RESPONDER_MODEL", "openai/test-fb-resp")
    monkeypatch.setattr(config, "FALLBACK_CLASSIFIER_MODEL", "openai/test-fb-cls")
    monkeypatch.setattr(config, "RESISTANCE_MODEL", "openai/test-resistance")
    v = _version()
    assert v["classifier_model"] == "openai/gpt-4o-mini"
    assert v["responder_model"] == "openai/gpt-4o"
    assert v["translator_model"] == "openai/test-translator"
    assert v["fallback_responder_model"] == "openai/test-fb-resp"
    assert v["fallback_classifier_model"] == "openai/test-fb-cls"
    assert v["resistance_model"] == "openai/test-resistance"


def test_model_raw_env_null_when_unset_not_fabricated(monkeypatch):
    for var in ("SAGE_CLASSIFIER_MODEL", "SAGE_RESPONDER_MODEL", "SAGE_TRANSLATOR_MODEL",
                "SAGE_FALLBACK_RESPONDER_MODEL", "SAGE_FALLBACK_CLASSIFIER_MODEL",
                "SAGE_RESISTANCE_MODEL"):
        monkeypatch.delenv(var, raising=False)
    v = _version()
    # resolved values still report the module defaults; raw_env is null, never fabricated
    assert v["classifier_model_raw_env"] is None
    assert v["responder_model_raw_env"] is None
    assert v["translator_model_raw_env"] is None
    assert v["fallback_responder_model_raw_env"] is None
    assert v["fallback_classifier_model_raw_env"] is None
    assert v["resistance_model_raw_env"] is None


def test_threshold_and_gate_vars_report_resolved_values(monkeypatch):
    monkeypatch.setattr(config, "KNOWLEDGE_ABSTAIN_THRESHOLD", 0.015)
    monkeypatch.setattr(config, "SKILL_RUNNER_UP_MIN", 0.5)
    monkeypatch.setattr(config, "SKILL_RUNNER_UP_MARGIN", 0.05)
    monkeypatch.setattr(config, "SKILL_OFFER_COOLDOWN_TURNS", 2)
    monkeypatch.setattr(config, "SKILL_OFFER_COOLDOWN_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", False)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)
    monkeypatch.setattr(config, "NATIVE_ARABIC_SHADOW_ENABLED", False)
    v = _version()
    assert v["knowledge_abstain_threshold"] == 0.015
    assert v["skill_runner_up_min"] == 0.5
    assert v["skill_runner_up_margin"] == 0.05
    assert v["skill_offer_cooldown_turns"] == 2
    assert v["skill_offer_cooldown_enabled"] is True
    assert v["d5_acuity_gate_enabled"] is False
    assert v["d5_acuity_floor"] == 8
    assert v["native_arabic_shadow_enabled"] is False


def test_kill_switch_flags_report_resolved_values(monkeypatch):
    monkeypatch.setattr(config, "HIGH_RISK_TERMINAL_ENABLED", False)
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"1f", "s2c"}))
    v = _version()
    assert v["high_risk_terminal_enabled"] is False
    assert v["psychoed_pathways_enabled"] is True
    assert sorted(v["psychoed_categories"]) == ["1f", "s2c"]   # JSON-serializable list


def test_medical_referral_text_raw_env_unset_is_null(monkeypatch):
    monkeypatch.delenv("SAGE_MEDICAL_REFERRAL_TEXT", raising=False)
    v = _version()
    assert v["medical_referral_text_raw_env"] is None
    # resolved copy still reported (the safety terminal's actual wording)
    assert "998" in v["medical_referral_text"]


def test_unset_new_flag_raw_envs_are_null_not_fabricated(monkeypatch):
    for var in ("SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD", "SAGE_SKILL_RUNNER_UP_MIN",
                "SAGE_SKILL_RUNNER_UP_MARGIN", "SAGE_SKILL_OFFER_COOLDOWN_TURNS",
                "SAGE_SKILL_OFFER_COOLDOWN_ENABLED", "SAGE_D5_ACUITY_GATE",
                "SAGE_D5_ACUITY_FLOOR", "SAGE_NATIVE_ARABIC_SHADOW",
                "SAGE_HIGH_RISK_TERMINAL", "SAGE_PSYCHOED_PATHWAYS",
                "SAGE_PSYCHOED_CATEGORIES", "SAGE_AUDIT_LOG"):
        monkeypatch.delenv(var, raising=False)
    v = _version()
    for field in ("knowledge_abstain_threshold_raw_env", "skill_runner_up_min_raw_env",
                  "skill_runner_up_margin_raw_env", "skill_offer_cooldown_turns_raw_env",
                  "skill_offer_cooldown_enabled_raw_env", "d5_acuity_gate_raw_env",
                  "d5_acuity_floor_raw_env", "native_arabic_shadow_raw_env",
                  "high_risk_terminal_raw_env", "psychoed_pathways_raw_env",
                  "psychoed_categories_raw_env", "audit_log_raw_env"):
        assert v[field] is None, f"{field} must be null when unset, never fabricated"


def test_skill_media_enabled_alias_matches_parity_var_name():
    """The legacy field is skill_media_raw_env -> maps to 'SAGE_SKILL_MEDIA', which is NOT
    the real env var (SAGE_SKILL_MEDIA_ENABLED) — so the parity map missed it. The
    correctly-named twin closes that hole; the legacy field stays for its consumers."""
    v = _version()
    assert "skill_media_enabled_raw_env" in v
    assert v["skill_media_enabled_raw_env"] == v["skill_media_raw_env"]
