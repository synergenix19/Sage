"""Signed-flag config-as-code register — CI consistency gate (config/prod_flags.yaml).

Why this shape (owner-imposed, binding): all three real SAGE_INFO_REQUEST_CONSULT reversions
(2026-07-28 -> 2026-07-29, two of them SERVED) were VARIABLE-ONLY changes that never triggered
a build — a #258-style build-side gate watches them sail past. The enforcement surface is
therefore the COMMITTED FILE plus an idempotent apply (scripts/apply_prod_flags.py): the only
sanctioned flag-change path is file edit -> PR -> merge -> apply, and this suite is the PR-time
gate on the file itself.

Locked in here:
  1. REGISTER COMPLETENESS — every SAGE_* env var config.py reads (the same parity regex the
     conformance runner uses) must have a row, so a new flag must be CLASSIFIED AT BIRTH.
  2. CLASS TAXONOMY — every row carries class safety|feature (2026-07-28 taxonomy, endorsed).
  3. SIGNED-VALUE CHECK — a signed flag whose value != signed_value WITHOUT an override block
     (rationale + ratification_ref) is a CI FAILURE; an override without ratification_ref is a
     CI FAILURE. Signature without signature_ref is a CI FAILURE.
  4. The apply script REFUSES to apply a register that fails the signed-value check.
  5. SECRETS/PROVENANCE never enter the file (SAGE_API_KEY etc. are not flags).
"""
import importlib.util
import os
import re

import yaml
import pytest

pytestmark = pytest.mark.safety_gate

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTER = os.path.join(_REPO, "config", "prod_flags.yaml")
_CONFIG = os.path.join(_REPO, "src", "sage_poc", "config.py")
_APPLY = os.path.join(_REPO, "scripts", "apply_prod_flags.py")
_WATCHDOG = os.path.join(_REPO, "scripts", "flag_watchdog.py")


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # main() must be behind an __main__ guard
    return mod


def _register():
    with open(_REGISTER, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _config_sage_vars():
    """Same enumeration principle as the parity runner's regex: every SAGE_* getenv OR
    _strict_flag() call in config.py — identical alternation to
    scripts/instrument/graph_evidence.py::config_sage_vars /
    measure_layer1_fullgraph.py::_config_sage_vars (K2.1 migrated the strict-parse
    flags onto the shared _strict_flag() helper, so a flag can be text-derived
    from either idiom). KEYWORD-ORDER-FRAGILE: only the name is needed here, but the
    _strict_flag branch mirrors the other four scanners' pattern for consistency."""
    src = open(_CONFIG, encoding="utf-8").read()
    names = set()
    for m in re.finditer(
        r'os\.getenv\(\s*"(SAGE_[A-Z0-9_]+)"\s*(?:,\s*"([^"]*)")?'
        r'|_strict_flag\(\s*"(SAGE_[A-Z0-9_]+)"(?:\s*,\s*default_on\s*=\s*(True))?',
        src,
    ):
        names.add(m.group(1) or m.group(3))
    return sorted(names)


# ---------------------------------------------------------------------------
# 1. Register completeness: classified at birth
# ---------------------------------------------------------------------------

def test_every_config_sage_flag_has_a_register_row():
    """A flag config.py reads but the register does not list is UNCLASSIFIED — the exact state
    the taxonomy exists to prevent (an undecided safety flag is de facto feature-class)."""
    reg = _register()
    flags = reg["flags"]
    missing = [v for v in _config_sage_vars() if v not in flags]
    assert missing == [], (
        f"config.py reads SAGE_* vars with no register row (classify at birth): {missing}"
    )


def test_every_row_carries_a_two_class_taxonomy_class():
    reg = _register()
    bad = {k: v.get("class") for k, v in reg["flags"].items()
           if v.get("class") not in ("safety", "feature")}
    assert bad == {}, f"rows without a valid class (safety|feature): {bad}"


def test_values_are_strings_or_null_never_yaml_scalars():
    """Raw env values are STRINGS (or null = unset). A bare YAML `true` silently becomes a Python
    bool and would compare unequal to railway's 'true' — the file must stay unambiguous."""
    reg = _register()
    bad = {k: type(v.get("value")).__name__ for k, v in reg["flags"].items()
           if v.get("value") is not None and not isinstance(v.get("value"), str)}
    assert bad == {}, f"non-string values (quote them): {bad}"


def test_secrets_and_deploy_provenance_are_not_in_the_register():
    """The register is committed plaintext and the apply script's write scope. Secrets and the
    per-deploy provenance pin must never be governed (or leaked) by it."""
    reg = _register()
    for forbidden in ("SAGE_API_KEY", "SAGE_BUILD_SHA", "SAGE_TEST_USER_IDS"):
        assert forbidden not in reg["flags"], f"{forbidden} must not be in the register"


# ---------------------------------------------------------------------------
# 2. Signed-value gate on the CURRENT committed file
# ---------------------------------------------------------------------------

def test_committed_file_passes_the_signed_value_check():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    violations = apply_mod.register_violations(_register())
    assert violations == [], f"committed register fails its own gate: {violations}"


def test_info_request_consult_row_records_the_restored_signed_state():
    """Updated in the authorized restore PR (item-1 pre-authorization, 2026-07-29): the row
    previously pinned the CONTENDED state (value false + ratified override) so a restore
    could not sneak in as a side effect. The restore having happened through its own PR,
    the row now pins the RESTORED invariant: value == signed_value, NO override block, and
    the restore evidence carried in signature_ref/note. A future unexplained divergence
    must reappear as an override block (gate check) — never as silent value drift."""
    row = _register()["flags"]["SAGE_INFO_REQUEST_CONSULT"]
    assert row["value"] == "true"
    assert row["signed_value"] == "true"
    assert row["value"] == row["signed_value"]
    assert "override" not in row            # restored state needs no override; drift must re-add one
    assert "Vee B1" in row["signature_ref"] and "PR#362" in row["signature_ref"]
    assert "2026-07-29" in row["signature_ref"]   # retro-confirmation + reaffirmation carried
    assert "RESTORED 2026-07-29" in row["note"]


# ---------------------------------------------------------------------------
# 3. Signed-value gate MECHANISM (not just the current file's content)
# ---------------------------------------------------------------------------

def _reg(rows):
    return {"schema": 1, "flags": rows}


def test_signed_mismatch_without_override_is_a_violation():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_X": {"value": "false", "class": "feature",
                           "signed_value": "true", "signature_ref": "Vee 2026-01-01"}})
    violations = apply_mod.register_violations(reg)
    assert any("SAGE_X" in v and "override" in v for v in violations), violations


def test_signed_match_needs_no_override():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_X": {"value": "true", "class": "feature",
                           "signed_value": "true", "signature_ref": "Vee 2026-01-01"}})
    assert apply_mod.register_violations(reg) == []


def test_override_without_ratification_ref_is_a_violation():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_X": {"value": "false", "class": "feature",
                           "signed_value": "true", "signature_ref": "Vee 2026-01-01",
                           "override": {"rationale": "contended"}}})
    violations = apply_mod.register_violations(reg)
    assert any("SAGE_X" in v and "ratification_ref" in v for v in violations), violations


def test_signed_value_without_signature_ref_is_a_violation():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_X": {"value": "true", "class": "feature", "signed_value": "true"}})
    violations = apply_mod.register_violations(reg)
    assert any("SAGE_X" in v and "signature_ref" in v for v in violations), violations


def test_missing_class_is_a_violation():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_X": {"value": "true"}})
    violations = apply_mod.register_violations(reg)
    assert any("SAGE_X" in v and "class" in v for v in violations), violations


# ---------------------------------------------------------------------------
# 4. Apply refuses on a failing register; diff logic is three-way and named
# ---------------------------------------------------------------------------

def test_apply_refuses_to_apply_a_register_failing_the_signed_check():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    bad = _reg({"SAGE_X": {"value": "false", "class": "feature",
                           "signed_value": "true", "signature_ref": "Vee 2026-01-01"}})
    # plan_apply is the only function that produces variable writes; it must raise on violations.
    try:
        apply_mod.plan_apply(bad, desired={"SAGE_X": "true"})
    except apply_mod.RegisterViolation:
        return
    raise AssertionError("plan_apply did not refuse a register failing the signed-value check")


def test_plan_apply_converges_desired_to_committed_and_only_touches_listed_flags():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({
        "SAGE_A": {"value": "true", "class": "feature"},    # drifted -> set
        "SAGE_B": {"value": "false", "class": "feature"},   # matches -> no-op (idempotent)
        "SAGE_C": {"value": None, "class": "feature"},      # committed unset, railway set -> delete
    })
    desired = {"SAGE_A": "false", "SAGE_B": "false", "SAGE_C": "x",
               "SAGE_API_KEY": "secret", "UNRELATED": "1"}
    sets, deletes = apply_mod.plan_apply(reg, desired=desired)
    assert sets == {"SAGE_A": "true"}
    assert deletes == ["SAGE_C"]


def test_plan_apply_is_idempotent_when_desired_matches():
    apply_mod = _load_module(_APPLY, "apply_prod_flags")
    reg = _reg({"SAGE_A": {"value": "true", "class": "feature"},
                "SAGE_B": {"value": None, "class": "feature"}})
    sets, deletes = apply_mod.plan_apply(reg, desired={"SAGE_A": "true"})
    assert sets == {} and deletes == []


# ---------------------------------------------------------------------------
# 5. Watchdog: alert-first, named-flag report, nonzero on divergence, NO auto-revert
# ---------------------------------------------------------------------------

def test_watchdog_reports_named_divergence_per_side():
    wd = _load_module(_WATCHDOG, "flag_watchdog")
    reg = _reg({"SAGE_A": {"value": "true", "class": "safety"},
                "SAGE_B": {"value": "false", "class": "feature"}})
    rows = wd.divergences(reg, desired={"SAGE_A": "false", "SAGE_B": "false"},
                          serving={"SAGE_A": "true"})
    assert len(rows) == 1
    row = rows[0]
    assert row["flag"] == "SAGE_A"
    assert row["side"] == "desired"          # WHICH side diverged, by name
    assert row["committed"] == "true" and row["observed"] == "false"


def test_watchdog_serving_divergence_is_named_as_serving():
    wd = _load_module(_WATCHDOG, "flag_watchdog")
    reg = _reg({"SAGE_A": {"value": "true", "class": "safety"}})
    rows = wd.divergences(reg, desired={"SAGE_A": "true"}, serving={"SAGE_A": "false"})
    assert [(r["flag"], r["side"]) for r in rows] == [("SAGE_A", "serving")]


def test_watchdog_readback_gap_is_a_gap_not_a_divergence():
    """Until the readback-widening deploy serves, most flags are absent from /health/version.
    Absence from the SERVING readback is a coverage gap (reported), never a false divergence."""
    wd = _load_module(_WATCHDOG, "flag_watchdog")
    reg = _reg({"SAGE_A": {"value": "true", "class": "safety"}})
    rows = wd.divergences(reg, desired={"SAGE_A": "true"}, serving={})
    assert rows == []
    gaps = wd.readback_gaps(reg, serving={})
    assert gaps == ["SAGE_A"]


def test_watchdog_has_no_auto_revert_surface():
    """Alert-first interim per the stand-down decision (2026-07-29 recurrence #3: an automated
    restore against an active contending writer starts a flip-war on production). The watchdog
    module must not import or shell out to anything that can WRITE a railway variable."""
    src = open(_WATCHDOG, encoding="utf-8").read()
    assert "--set" not in src and "variable delete" not in src, (
        "watchdog must never mutate railway variables — alert-first, no auto-revert"
    )


def test_serving_verified_rider_is_only_ever_false():
    """Desired-unverified rider (2026-07-29 ruling 2): rows seeded from the desired side
    that no serving readback has ever confirmed carry serving_verified: false. The rider
    dissolves by DELETING the key once the widened readback serves and the watchdog confirms
    coverage — it may never flip to true, because the register never asserts serving state
    statically; serving verification is the watchdog's job, dynamically, per check."""
    reg = _register()
    for name, row in reg["flags"].items():
        if "serving_verified" in row:
            assert row["serving_verified"] is False, (
                f"{name}: serving_verified may only be false; dissolve the rider by "
                "deleting the key after a serving readback covers the flag"
            )
