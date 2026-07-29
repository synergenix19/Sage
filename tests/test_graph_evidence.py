"""Tests for the parity graph-invocation helper (scripts/instrument/graph_evidence.py).

The helper is the ONLY supported way to invoke the graph for evidence (signed
instrument-parity standing rule, 2026-07-28). These tests lock in the three
mechanical behaviours the rule names:

  1. refuse-on-gap  — a flag config.py reads that neither the /health/version
     serving readback nor railway (desired) can assert is a HARD ERROR, never a
     silent default;
  2. header completeness — every artifact carries full provenance (resolved flag
     set, build SHA, classifier model + pins + seed-honor signal, N, degraded
     turn count) so a non-parity artifact is distinguishable at read time;
  3. N-sample record shape — the distributional rider from the Node-2 bistability
     finding: per-sample per-turn records with the routing evidence keys.

NO test here touches the network: readback and railway are always mocked/injected.
"""
import asyncio
import importlib.util
import os

import pytest

_HELPER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts/instrument/graph_evidence.py",
)
_spec = importlib.util.spec_from_file_location("graph_evidence", _HELPER)
ge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ge)  # importable: main() is behind an __main__ guard


# ---------------------------------------------------------------------------
# Shared fabricated inputs (never a real prod readback)
# ---------------------------------------------------------------------------

def _mock_readback(**extra):
    """A minimal fabricated /health/version payload (mock — tests never hit prod)."""
    health = {
        "build_sha": "deadbeefcafe",
        "build_sha_source": "SAGE_BUILD_SHA",
        "crisis_tiering_raw_env": "true",
        "high_risk_detection_raw_env": "true",
        "hr_neutrality_gate_raw_env": "true",
        "info_request_consult_raw_env": "true",
        "route_precedence_raw_env": "true",
        "d1_screen_raw_env": None,
        "classifier_seed": None,
        "classifier_seed_raw_env": None,
        "openrouter_provider_pin": None,
        "openrouter_provider_pin_raw_env": None,
        "audit_classifier_provenance_raw_env": "true",
    }
    health.update(extra)
    return health


def _desired_matching(**extra):
    """A railway (desired) payload CONSISTENT with _mock_readback — a quiesced prod.
    (An inconsistent desired is the deploy-window case, tested separately.)"""
    desired = {
        "SAGE_CRISIS_TIERING": "true",
        "SAGE_HIGH_RISK_DETECTION": "true",
        "SAGE_HR_NEUTRALITY_GATE": "true",
        "SAGE_INFO_REQUEST_CONSULT": "true",
        "SAGE_ROUTE_PRECEDENCE": "true",
        "SAGE_AUDIT_CLASSIFIER_PROVENANCE": "true",
    }
    desired.update(extra)
    return desired


_SMALL_MAPPING = {
    "SAGE_CRISIS_TIERING": None,
    "SAGE_HIGH_RISK_DETECTION": "false",
    "SAGE_HR_NEUTRALITY_GATE": "false",
    "SAGE_INFO_REQUEST_CONSULT": None,
    "SAGE_ROUTE_PRECEDENCE": None,
    "SAGE_D1_SCREEN": "false",
    "SAGE_CLASSIFIER_SEED": None,
    "SAGE_OPENROUTER_PROVIDER_PIN": "",
    "SAGE_AUDIT_CLASSIFIER_PROVENANCE": "false",
}


# ---------------------------------------------------------------------------
# 1. Flag enumeration (reuses the runner's regex approach)
# ---------------------------------------------------------------------------

def test_config_vars_auto_derived_from_config_py():
    varmap = ge.config_sage_vars()
    for must in ("SAGE_HIGH_RISK_DETECTION", "SAGE_HR_NEUTRALITY_GATE",
                 "SAGE_INFO_REQUEST_CONSULT", "SAGE_D1_SCREEN",
                 "SAGE_CLASSIFIER_SEED", "SAGE_OPENROUTER_PROVIDER_PIN",
                 "SAGE_AUDIT_CLASSIFIER_PROVENANCE"):
        assert must in varmap, f"{must} not auto-derived from config.py"


def test_infra_vars_excluded_from_parity():
    varmap = ge.config_sage_vars()
    assert "SAGE_DB_POOL_MAX_SIZE" not in varmap
    assert "SAGE_API_KEY" not in varmap
    assert "SAGE_AUDIT_LOG" not in varmap


# ---------------------------------------------------------------------------
# 2. Refuse-on-gap (standing rule 1: hard error, not a default)
# ---------------------------------------------------------------------------

def test_refuses_on_config_flag_absent_from_readback_no_railway():
    """A fabricated config flag not covered by the (mocked) readback, railway
    unavailable → the helper must REFUSE with an explicit message naming the flag."""
    mapping = dict(_SMALL_MAPPING)
    mapping["SAGE_FABRICATED_TEST_FLAG"] = "false"  # not in any readback field
    with pytest.raises(ge.ParityRefusal) as exc:
        ge.derive_flag_set(_mock_readback(), desired=None, mapping=mapping)
    msg = str(exc.value)
    assert "SAGE_FABRICATED_TEST_FLAG" in msg
    assert "REFUS" in msg.upper()


def test_refusal_message_lists_every_gap_var():
    mapping = dict(_SMALL_MAPPING)
    mapping["SAGE_FAKE_A"] = None
    mapping["SAGE_FAKE_B"] = "true"
    with pytest.raises(ge.ParityRefusal) as exc:
        ge.derive_flag_set(_mock_readback(), desired=None, mapping=mapping)
    assert "SAGE_FAKE_A" in str(exc.value) and "SAGE_FAKE_B" in str(exc.value)


def test_gap_covered_by_railway_desired_does_not_refuse():
    """Railway (desired) is the secondary coverage source — same semantics as the
    measure_layer1_fullgraph parity gate: railway is prod's only env source, so a
    var railway does not set runs the config default. Coverage is recorded per-var
    so readback holes stay VISIBLE in the artifact."""
    mapping = dict(_SMALL_MAPPING)
    mapping["SAGE_FABRICATED_TEST_FLAG"] = "false"
    derived = ge.derive_flag_set(
        _mock_readback(), desired=_desired_matching(SAGE_FABRICATED_TEST_FLAG="true"),
        mapping=mapping)
    assert derived["resolved_env"]["SAGE_FABRICATED_TEST_FLAG"] == "true"
    assert derived["coverage"]["SAGE_FABRICATED_TEST_FLAG"] == "railway_desired"


def test_var_unset_everywhere_with_railway_available_resolves_to_default():
    mapping = dict(_SMALL_MAPPING)
    mapping["SAGE_FABRICATED_TEST_FLAG"] = "false"
    derived = ge.derive_flag_set(_mock_readback(), desired=_desired_matching(),
                                 mapping=mapping)
    # prod runs the config default -> local must too (env entry unset -> None)
    assert derived["resolved_env"]["SAGE_FABRICATED_TEST_FLAG"] is None
    assert derived["effective"]["SAGE_FABRICATED_TEST_FLAG"] == "false"
    assert derived["coverage"]["SAGE_FABRICATED_TEST_FLAG"] == "railway_default"


def test_readback_covered_vars_are_sourced_from_serving():
    """Serving readback is authoritative (2026-07-22: railway lagged the running
    process mid-restart) — readback-exposed vars are never taken from railway."""
    derived = ge.derive_flag_set(
        _mock_readback(), desired=_desired_matching(), mapping=dict(_SMALL_MAPPING))
    assert derived["coverage"]["SAGE_HIGH_RISK_DETECTION"] == "serving_readback"
    assert derived["resolved_env"]["SAGE_HIGH_RISK_DETECTION"] == "true"


# ---------------------------------------------------------------------------
# 3. Deploy-window refusal (serving != desired)
# ---------------------------------------------------------------------------

def test_refuses_on_deploy_window():
    with pytest.raises(ge.ParityRefusal) as exc:
        ge.derive_flag_set(
            _mock_readback(), desired=_desired_matching(SAGE_HIGH_RISK_DETECTION="false"),
            mapping=dict(_SMALL_MAPPING))
    msg = str(exc.value)
    assert "SAGE_HIGH_RISK_DETECTION" in msg
    assert "deploy" in msg.lower()


def test_railway_unavailable_is_loud_but_proceeds_when_readback_covers_all():
    """Task-specified behaviour: railway unavailable -> state it and proceed
    readback-only, loudly. (Only possible when the readback covers every var.)"""
    mapping = {k: _SMALL_MAPPING[k] for k in (
        "SAGE_CRISIS_TIERING", "SAGE_HIGH_RISK_DETECTION", "SAGE_HR_NEUTRALITY_GATE",
        "SAGE_INFO_REQUEST_CONSULT", "SAGE_ROUTE_PRECEDENCE", "SAGE_D1_SCREEN",
        "SAGE_CLASSIFIER_SEED", "SAGE_OPENROUTER_PROVIDER_PIN",
        "SAGE_AUDIT_CLASSIFIER_PROVENANCE")}
    derived = ge.derive_flag_set(_mock_readback(), desired=None, mapping=mapping)
    assert derived["railway_desired_available"] is False
    assert derived["deploy_window_checked"] is False
    assert any("railway" in n.lower() for n in derived["notes"])
    # unset-in-prod raw_env (None) means the local env must be UNSET, not defaulted-in
    assert derived["resolved_env"]["SAGE_D1_SCREEN"] is None
    assert derived["effective"]["SAGE_D1_SCREEN"] == "false"


# ---------------------------------------------------------------------------
# 4. Header completeness (standing rule 2: the artifact carries its provenance)
# ---------------------------------------------------------------------------

def _derived_ok():
    return ge.derive_flag_set(_mock_readback(), desired=_desired_matching(),
                              mapping=dict(_SMALL_MAPPING))


def test_header_block_contains_every_required_field():
    header = ge.header_block(
        _derived_ok(), _mock_readback(), n_per_fixture=10,
        degraded_turn_count=0, fingerprints=["fp_abc123"])
    for field in ge.REQUIRED_HEADER_FIELDS:
        assert field in header, f"header missing required field {field!r}"
    assert header["build_sha"] == "deadbeefcafe"
    assert header["n_per_fixture"] == 10
    assert header["degraded_turn_count"] == 0
    # full resolved flag set, not a subset
    assert set(header["resolved_flag_set"]) == set(_SMALL_MAPPING)


def test_header_seed_honor_signal_states():
    d = _derived_ok()
    rb = _mock_readback()
    on = ge.header_block(d, rb, n_per_fixture=1, degraded_turn_count=0,
                         fingerprints=["fp_x", "fp_x"])
    assert on["seed_honor"]["status"] == "fingerprint_stable"
    assert on["seed_honor"]["distinct_fingerprints"] == ["fp_x"]

    mixed = ge.header_block(d, rb, n_per_fixture=1, degraded_turn_count=0,
                            fingerprints=["fp_x", "fp_y"])
    assert mixed["seed_honor"]["status"] == "fingerprint_varied_backend_mix"

    absent = ge.header_block(d, rb, n_per_fixture=1, degraded_turn_count=0,
                             fingerprints=[None, None])
    assert absent["seed_honor"]["status"] == "fingerprint_absent_provider_did_not_echo"


def test_header_seed_honor_unavailable_when_provenance_flag_off():
    mapping = dict(_SMALL_MAPPING)
    rb = _mock_readback(audit_classifier_provenance_raw_env=None)
    desired = _desired_matching()
    del desired["SAGE_AUDIT_CLASSIFIER_PROVENANCE"]
    d = ge.derive_flag_set(rb, desired=desired, mapping=mapping)
    h = ge.header_block(d, rb, n_per_fixture=1, degraded_turn_count=0, fingerprints=[])
    assert h["seed_honor"]["status"] == "unavailable_provenance_flag_off"


def test_rendered_header_md_carries_flags_sha_and_counts():
    header = ge.header_block(_derived_ok(), _mock_readback(), n_per_fixture=10,
                             degraded_turn_count=3, fingerprints=[])
    md = ge.render_header_md(header)
    assert "deadbeefcafe" in md
    assert "SAGE_HIGH_RISK_DETECTION" in md
    assert "N per fixture" in md and "10" in md
    assert "Degraded turns" in md and "3" in md


def test_write_artifact_prepends_header(tmp_path):
    header = ge.header_block(_derived_ok(), _mock_readback(), n_per_fixture=10,
                             degraded_turn_count=0, fingerprints=[])
    out = tmp_path / "artifact.md"
    ge.write_artifact(str(out), header, "# Body\n\ncontent\n")
    text = out.read_text()
    assert text.index("deadbeefcafe") < text.index("# Body")
    for field in ("Build SHA", "Resolved flag set", "Classifier model"):
        assert field in text


# ---------------------------------------------------------------------------
# 5. N-sample driver record shape (bistability rider)
# ---------------------------------------------------------------------------

class _FakeApp:
    """Stands in for the compiled graph; returns canned per-turn states."""

    def __init__(self, canned):
        self.canned = canned  # list per turn-index
        self.calls = []       # (thread_id, raw_message)

    async def ainvoke(self, payload, config):
        self.calls.append((config["configurable"]["thread_id"], payload["raw_message"]))
        idx = (len(self.calls) - 1) % len(self.canned)
        return dict(self.canned[idx])


_TURN_OK = {
    "primary_intent": "new_skill", "secondary_intent": None, "intent_confidence": 0.9,
    "path": ["safety_check", "intent_route", "skill_select", "skill_respond"],
    "offered_skill_ids": ["box_breathing"], "active_skill_id": None,
    "completed_skill_id": None, "skill_match_method": "keyword",
    "classifier_system_fingerprint": "fp_1",
}
_TURN_DEGRADED = {
    "primary_intent": "general_chat", "secondary_intent": None, "intent_confidence": 0.5,
    "path": ["safety_check", "intent_route", "freeflow_respond"],
    "offered_skill_ids": None, "active_skill_id": None,
    "completed_skill_id": None, "skill_match_method": None,
    "classifier_system_fingerprint": None,
}

REQUIRED_RECORD_KEYS = {"turn", "primary_intent", "secondary_intent", "confidence",
                        "path", "offered_skill_ids", "active_skill_id",
                        "skill_match_method"}


def test_run_fixture_shape_n_samples_by_turns():
    app = _FakeApp([_TURN_OK, _TURN_OK])
    result = asyncio.run(ge.run_fixture(app, ["hello", "any exercises?"], n=3,
                                        thread_prefix="t-shape"))
    assert result["n"] == 3
    assert len(result["samples"]) == 3
    for sample in result["samples"]:
        assert len(sample["records"]) == 2
        for i, rec in enumerate(sample["records"], start=1):
            assert REQUIRED_RECORD_KEYS <= set(rec), f"missing keys: {REQUIRED_RECORD_KEYS - set(rec)}"
            assert rec["turn"] == i
    # each sample must be an independent session: distinct thread ids across samples
    tids = {tid for tid, _ in app.calls}
    assert len(tids) == 3


def test_run_fixture_counts_degraded_turns():
    """Static-fallback signature: general_chat at confidence EXACTLY 0.5."""
    app = _FakeApp([_TURN_DEGRADED, _TURN_OK])
    result = asyncio.run(ge.run_fixture(app, ["a", "b"], n=2, thread_prefix="t-deg"))
    assert result["degraded_turn_count"] == 2  # turn 1 of each of the 2 samples
    assert result["samples"][0]["records"][0]["degraded"] is True
    assert result["samples"][0]["records"][1]["degraded"] is False


def test_degraded_signature_is_exact():
    assert ge.is_degraded("general_chat", 0.5) is True
    assert ge.is_degraded("general_chat", 0.51) is False
    assert ge.is_degraded("new_skill", 0.5) is False
    assert ge.is_degraded("general_chat", None) is False


# ---------------------------------------------------------------------------
# 6. .env re-injection guard (config.py load_dotenv() runs at import)
# ---------------------------------------------------------------------------

def test_export_refuses_when_env_file_would_reinject_a_divergent_value(tmp_path, monkeypatch):
    """load_dotenv() SETS vars we popped; a .env value differing from the derived
    effective state silently defeats 'unset means prod default' -> hard refusal."""
    envf = tmp_path / ".env"
    envf.write_text("SAGE_D1_SCREEN=true\n")  # derived says unset -> default 'false'
    derived = _derived_ok()
    with pytest.raises(ge.ParityRefusal) as exc:
        ge.export_env(derived, env_file=str(envf))
    assert "SAGE_D1_SCREEN" in str(exc.value)
    assert ".env" in str(exc.value)


def test_export_notes_but_allows_env_file_value_equal_to_default(tmp_path):
    envf = tmp_path / ".env"
    envf.write_text("SAGE_D1_SCREEN=false\n")  # equals the config default -> benign
    derived = _derived_ok()
    ge.export_env(derived, env_file=str(envf))
    assert any("SAGE_D1_SCREEN" in n for n in derived["notes"])


def test_export_sets_and_unsets_the_process_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SAGE_D1_SCREEN", "true")       # stale local value must be UNSET
    monkeypatch.delenv("SAGE_HIGH_RISK_DETECTION", raising=False)
    envf = tmp_path / ".env"
    envf.write_text("")
    derived = _derived_ok()
    ge.export_env(derived, env_file=str(envf))
    assert "SAGE_D1_SCREEN" not in os.environ
    assert os.environ["SAGE_HIGH_RISK_DETECTION"] == "true"
    assert os.environ["SAGE_AUDIT_LOG"] == "false"     # recorded local-instrument deviation


def test_allow_deploy_window_is_loud_and_serving_authoritative():
    """Smoke/diagnostic escape: divergence stamped, resolution stays SERVING-side."""
    derived = ge.derive_flag_set(
        _mock_readback(), desired=_desired_matching(SAGE_HIGH_RISK_DETECTION="false"),
        mapping=dict(_SMALL_MAPPING), allow_deploy_window=True)
    assert derived["resolved_env"]["SAGE_HIGH_RISK_DETECTION"] == "true"  # serving wins
    assert any("DEPLOY WINDOW OVERRIDDEN" in n for n in derived["notes"])


def test_header_carries_local_tree_sha_and_flags_divergence_from_serving_sha():
    header = ge.header_block(_derived_ok(), _mock_readback(), n_per_fixture=1,
                             degraded_turn_count=0, fingerprints=[])
    assert "local_tree_sha" in header and header["local_tree_sha"]
    # the mocked serving sha 'deadbeefcafe' never matches the real local tree
    assert any("LOCAL tree" in n for n in header["parity_notes"])
    assert "Local tree SHA" in ge.render_header_md(header)
