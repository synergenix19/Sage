"""Flag-parity guard for the conformance runner (measure_layer1_fullgraph.py).

Measurement parity = CONFIG parity, not just SHA parity. 2026-07-22 a v5 matrix was run against 2 flags
while prod served 5 (D1_SCREEN / IPV_PREEMPTION / ROUTE_PRECEDENCE had landed live) — a different system
wearing the baseline's name. These tests lock in that the runner (a) auto-derives the flag set from
config.py so the NEXT flag landing is checked without operator recall, and (b) refuses / stamps on
mismatch the same way --sha pins the tree.
"""
import importlib.util
import os

_RUNNER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "scripts/bot_behaviour_audit/measure_layer1_fullgraph.py")
_spec = importlib.util.spec_from_file_location("measure_layer1_fullgraph", _RUNNER)
mlf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mlf)  # importable because main() is behind an __main__ guard


def test_config_vars_auto_include_the_flags_that_were_silently_missed():
    """The exact flags the 07-22 mis-run omitted must be auto-derived from config.py — not a hand list."""
    varmap = mlf._config_sage_vars()
    for must in ("SAGE_D1_SCREEN", "SAGE_IPV_PREEMPTION", "SAGE_ROUTE_PRECEDENCE",
                 "SAGE_HR_NEUTRALITY_GATE", "SAGE_HIGH_RISK_DETECTION", "SAGE_MEDICAL_REDFLAG_GUARD"):
        assert must in varmap, f"{must} not auto-derived from config.py — a landing could slip the guard"


def test_infra_vars_are_excluded_from_parity():
    varmap = mlf._config_sage_vars()
    assert "SAGE_DB_POOL_MAX_SIZE" not in varmap
    assert "SAGE_API_KEY" not in varmap


def test_unavailable_prod_env_is_unverified_not_a_false_pass():
    verdict, local, diffs = mlf._flag_parity(None)
    assert verdict == "UNVERIFIED"
    assert diffs == []


def test_prod_flag_the_run_lacks_is_a_mismatch(monkeypatch):
    """The exact 07-22 failure: prod has SAGE_D1_SCREEN=true, the run does not set it (resolves default)."""
    monkeypatch.delenv("SAGE_D1_SCREEN", raising=False)
    prod_env = {"SAGE_D1_SCREEN": "true"}
    verdict, local, diffs = mlf._flag_parity(prod_env)
    assert verdict == "MISMATCH"
    d1 = [d for d in diffs if d[0] == "SAGE_D1_SCREEN"]
    assert d1 and d1[0][2] == "true" and d1[0][1] != "true"


def test_serving_readback_maps_raw_env_to_sage_vars():
    """/health/version *_raw_env is the SERVING state — the ground truth during a deploy window when
    railway (desired) lags. 2026-07-22: railway said IPV=false while serving raw_env was 'true'."""
    health = {"build_sha": "abc", "ipv_preemption_enabled": True, "ipv_preemption_raw_env": "true",
              "d1_screen_raw_env": "true", "route_precedence_raw_env": "true"}
    served = mlf._map_health_to_sage(health)
    assert served["SAGE_IPV_PREEMPTION"] == "true"
    assert served["SAGE_D1_SCREEN"] == "true"
    assert "SAGE_BUILD_SHA" not in served  # non-raw_env fields are not flags


def test_matching_config_is_verified(monkeypatch):
    varmap = mlf._config_sage_vars()
    # build a prod_env that resolves identically to the current process for every parity var
    prod_env = {k: (os.environ[k] if os.environ.get(k) is not None else d)
                for k, d in varmap.items() if (os.environ.get(k) is not None or d is not None)}
    verdict, local, diffs = mlf._flag_parity(prod_env)
    assert verdict == "VERIFIED", f"unexpected diffs: {diffs}"
