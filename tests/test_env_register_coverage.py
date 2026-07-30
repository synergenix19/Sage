"""Full-surface register coverage — CI gate for scripts/check_env_register_coverage.py.

Extends the birth-classification principle of test_prod_flags_register.py from
"SAGE_* reads in config.py" to EVERY literal env read in the serving source (src/ + server.py).
The SKILL_* routing trio evaded the narrower gate for 22 days (2026-07-08 flip -> 2026-07-30
K3/K4 diagnosis) because both the prefix filter and the single-file scope excluded it.
"""
import importlib.util
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO, "scripts", "check_env_register_coverage.py")


def _mod():
    spec = importlib.util.spec_from_file_location("check_env_register_coverage", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_served_env_read_is_row_or_allowlisted():
    m = _mod()
    violations = m.coverage_violations(m.load_register(), m.served_env_reads())
    assert violations == [], "\n".join(violations)


def test_v2_routing_trio_is_registered():
    """The specific 2026-07-30 gap must never reopen: the pair that determines whether the
    keyword tier's matches actually serve, plus the safety-pinned precision."""
    m = _mod()
    rows = m.load_register()["flags"]
    for name in ("SKILL_ROUTING_V2", "SKILL_RERANK_ENABLED", "SKILL_RERANK_PRECISION"):
        assert name in rows, f"{name} lost its register row"
        assert rows[name].get("class") in ("safety", "feature")


def test_dichotomy_is_exclusive_and_reasons_present():
    m = _mod()
    reg = m.load_register()
    rows = set(reg["flags"].keys())
    allow = reg.get("infra_allowlist") or {}
    assert rows.isdisjoint(allow.keys())
    assert all(isinstance(r, str) and r.strip() for r in allow.values())
