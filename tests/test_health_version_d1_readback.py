"""/health/version D1 flag readback (#338) — the endpoint tells the flag state truthfully, so the deploy
smoke can VERIFY (not infer) shadow=on/enforce=off. Same resolved+raw pattern as the other kill-switches."""
import asyncio
import server
from sage_poc import config
import pytest

pytestmark = pytest.mark.safety_gate


def _version():
    return asyncio.run(server.health_version(None))


def test_reports_both_d1_flags(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    v = _version()
    assert v["d1_screen_enabled"] is False        # enforce OFF — told, not inferred
    assert v["d1_screen_shadow"] is True          # shadow ON
    assert "d1_screen_raw_env" in v               # raw env surfaced too (provenance)
    assert "d1_screen_shadow_raw_env" in v


def test_reports_enforce_on(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", False)
    v = _version()
    assert v["d1_screen_enabled"] is True
    assert v["d1_screen_shadow"] is False


# ---------------------------------------------------------------------------
# Parity refuse-on-gap prerequisite: previously-documented coverage holes.
# Same resolved+raw pattern; resolved value is the RUNNING process's module-level
# config (what fires), never a request-time env re-read.
# ---------------------------------------------------------------------------

def test_reports_consult_and_hr_flags_resolved(monkeypatch):
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)
    monkeypatch.setattr(config, "HR_NEUTRALITY_GATE_ENABLED", False)
    v = _version()
    assert v["info_request_consult_enabled"] is True    # told by the process, not inferred
    assert v["high_risk_detection_enabled"] is True
    assert v["hr_neutrality_gate_enabled"] is False
    assert "info_request_consult_raw_env" in v          # raw env surfaced too (provenance)
    assert "high_risk_detection_raw_env" in v
    assert "hr_neutrality_gate_raw_env" in v


def test_consult_and_hr_flags_reflect_off_state(monkeypatch):
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", False)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", False)
    monkeypatch.setattr(config, "HR_NEUTRALITY_GATE_ENABLED", True)
    v = _version()
    assert v["info_request_consult_enabled"] is False
    assert v["high_risk_detection_enabled"] is False
    assert v["hr_neutrality_gate_enabled"] is True


def test_consult_and_hr_raw_env_report_unset_as_null(monkeypatch):
    for var in ("SAGE_INFO_REQUEST_CONSULT", "SAGE_HIGH_RISK_DETECTION",
                "SAGE_HR_NEUTRALITY_GATE"):
        monkeypatch.delenv(var, raising=False)
    v = _version()
    assert v["info_request_consult_raw_env"] is None    # null, not fabricated
    assert v["high_risk_detection_raw_env"] is None
    assert v["hr_neutrality_gate_raw_env"] is None


# ---------------------------------------------------------------------------
# Determinism pins + provenance flag (this branch): resolved + raw, same pattern.
# ---------------------------------------------------------------------------

def test_reports_determinism_pins_resolved(monkeypatch):
    monkeypatch.setattr(config, "CLASSIFIER_SEED", 4242)
    monkeypatch.setattr(config, "OPENROUTER_PROVIDER_PIN", "openai")
    monkeypatch.setattr(config, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setenv("SAGE_CLASSIFIER_SEED", "4242")
    monkeypatch.setenv("SAGE_OPENROUTER_PROVIDER_PIN", "openai")
    monkeypatch.setenv("SAGE_AUDIT_CLASSIFIER_PROVENANCE", "true")
    v = _version()
    assert v["classifier_seed"] == 4242                 # resolved int, not the raw string
    assert v["classifier_seed_raw_env"] == "4242"
    assert v["openrouter_provider_pin"] == "openai"
    assert v["openrouter_provider_pin_raw_env"] == "openai"
    assert v["audit_classifier_provenance_enabled"] is True
    assert v["audit_classifier_provenance_raw_env"] == "true"


def test_determinism_pins_report_null_when_unset(monkeypatch):
    monkeypatch.setattr(config, "CLASSIFIER_SEED", None)
    monkeypatch.setattr(config, "OPENROUTER_PROVIDER_PIN", None)
    monkeypatch.setattr(config, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", False)
    for var in ("SAGE_CLASSIFIER_SEED", "SAGE_OPENROUTER_PROVIDER_PIN",
                "SAGE_AUDIT_CLASSIFIER_PROVENANCE"):
        monkeypatch.delenv(var, raising=False)
    v = _version()
    assert v["classifier_seed"] is None                 # null, not fabricated
    assert v["classifier_seed_raw_env"] is None
    assert v["openrouter_provider_pin"] is None
    assert v["openrouter_provider_pin_raw_env"] is None
    assert v["audit_classifier_provenance_enabled"] is False
    assert v["audit_classifier_provenance_raw_env"] is None


# ---------------------------------------------------------------------------
# 2026-07-29 RCA: the last serving-vs-desired readback holes. cosine_abstain_threshold
# was the 8/10 conformance confound; panic_grounding_override (Part A) and
# derealization_detection (#369) are routing flags whose SERVED state was previously
# unverifiable in the readback (guard fell back to railway DESIRED). Same resolved+raw pattern.
# ---------------------------------------------------------------------------

def test_reports_cosine_panic_derealization_resolved(monkeypatch):
    monkeypatch.setattr(config, "COSINE_ABSTAIN_THRESHOLD", 0.42)
    monkeypatch.setattr(config, "PANIC_GROUNDING_OVERRIDE_ENABLED", True)
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", False)
    monkeypatch.setenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.42")
    v = _version()
    assert v["cosine_abstain_threshold"] == 0.42                 # resolved float (what actually gates)
    assert v["cosine_abstain_threshold_raw_env"] == "0.42"       # raw env surfaced (guard reads this)
    assert v["panic_grounding_override_enabled"] is True
    assert v["derealization_detection_enabled"] is False
    assert "panic_grounding_override_raw_env" in v
    assert "derealization_detection_raw_env" in v


def test_new_readback_raw_env_null_when_unset(monkeypatch):
    for var in ("SAGE_COSINE_ABSTAIN_THRESHOLD", "SAGE_PANIC_GROUNDING_OVERRIDE",
                "SAGE_DEREALIZATION_DETECTION"):
        monkeypatch.delenv(var, raising=False)
    v = _version()
    assert v["cosine_abstain_threshold_raw_env"] is None         # null, not fabricated
    assert v["panic_grounding_override_raw_env"] is None
    assert v["derealization_detection_raw_env"] is None


def test_guard_maps_new_readback_fields_to_sage_vars():
    """The parity guard's _map_health_to_sage must turn the new readback fields into the exact
    SAGE_ names config.py reads — else the guard still can't assert them (the coverage hole persists)."""
    import importlib.util, os as _os
    runner = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                           "scripts/bot_behaviour_audit/measure_layer1_fullgraph.py")
    spec = importlib.util.spec_from_file_location("mlf", runner)
    mlf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mlf)
    served = mlf._map_health_to_sage({
        "cosine_abstain_threshold_raw_env": "0.42",
        "panic_grounding_override_raw_env": "true",
        "derealization_detection_raw_env": "false",
    })
    assert served["SAGE_COSINE_ABSTAIN_THRESHOLD"] == "0.42"
    assert served["SAGE_PANIC_GROUNDING_OVERRIDE"] == "true"
    assert served["SAGE_DEREALIZATION_DETECTION"] == "false"
