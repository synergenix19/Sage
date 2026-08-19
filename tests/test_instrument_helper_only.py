"""CI-grep enforcement: instrument scripts must not invoke the graph directly.

Instrument-parity standing rule (SIGNED 2026-07-28), rule 1: the graph-invocation
helper (scripts/instrument/graph_evidence.py, extracted from the parity runner) is the
ONLY supported way to invoke the graph for any run whose output feeds a decision, memo,
matrix row, or escalation — it derives the flag set from the serving readback, REFUSES
on readback gaps and deploy windows, and stamps provenance into its output. Scripts
that invoke the graph directly do not produce evidence.

Enforcement pattern: same as scripts/check_state_channels.py — a static scan that makes
the failure class structurally loud at PR time. Any scripts/**/*.py containing a direct
`build_graph(`/`ainvoke(` usage must be either the helper itself, a SANCTIONED runner,
or a FROZEN legacy entry carrying an explicit deprecation marker. A NEW instrument
script tripping this test must go through the helper, not join the allowlist.
"""
import os
import re
import pytest

pytestmark = pytest.mark.safety_gate

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_REPO, "scripts")

_PATTERN = re.compile(r"\bbuild_graph\s*\(|\bainvoke\s*\(")

# The helper module — the only UNconditionally sanctioned home for direct invocation.
_HELPER = "instrument/graph_evidence.py"

# Sanctioned pre-existing runners (reviewer-approved surface):
#   - measure_layer1_fullgraph.py: the parity runner the helper is extracted FROM; it
#     already implements refuse-on-mismatch + provenance stamping.
#   - prod_smoke/: the deploy verification suite (read-only probes; currently contains
#     no direct invocation — sanctioned so its probes may adopt the helper's runner).
#   - characterize_1a_gap.py: pre-existing 1a characterization script (lives on the
#     1a-gap-phase0 branch); allowlisted so that branch can merge, but it MUST carry a
#     deprecation comment (checked below when present) and migrate to the helper.
_SANCTIONED = {
    "bot_behaviour_audit/measure_layer1_fullgraph.py",
    "characterize_1a_gap.py",
}
_SANCTIONED_DIRS = ("prod_smoke/", "instrument/")

# FROZEN legacy direct invokers, pre-dating the rule. Each must carry the deprecation
# marker below. Do NOT add entries: new scripts go through the helper.
_DEPRECATION_MARKER = "DEPRECATED-DIRECT-INVOKE"
_LEGACY = {
    "baseline_format_check.py",
    "benchmark_poc_scenarios.py",
    "bot_behaviour_recall_baseline.py",
    "verify_tiering_recall.py",
    "probe_freeflow_openers.py",   # llm.ainvoke (not the graph) — still not an evidence path
    "benchmark_latency.py",        # docstring mention of graph.ainvoke() trips the grep
}


def _scan():
    hits = []
    for dirpath, _dirs, files in os.walk(_SCRIPTS):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, _SCRIPTS).replace(os.sep, "/")
            if _PATTERN.search(open(path, encoding="utf-8").read()):
                hits.append(rel)
    return hits


def test_no_direct_graph_invocation_outside_helper_and_allowlist():
    offenders = [
        rel for rel in _scan()
        if rel != _HELPER
        and not rel.startswith(_SANCTIONED_DIRS)
        and rel not in _SANCTIONED
        and rel not in _LEGACY
    ]
    assert offenders == [], (
        f"direct build_graph(/ainvoke( usage outside the graph-evidence helper: {offenders}. "
        f"Evidence runs go through scripts/instrument/graph_evidence.py (signed parity rule "
        f"2026-07-28); do NOT extend the allowlist."
    )


def test_legacy_direct_invokers_carry_the_deprecation_marker():
    """The frozen legacy entries are visible debt, not silent permission: each file states
    in-source that it is deprecated and must migrate to the helper."""
    missing = []
    for rel in sorted(_LEGACY):
        path = os.path.join(_SCRIPTS, rel)
        assert os.path.isfile(path), (
            f"stale legacy allowlist entry {rel} — file gone, prune the entry"
        )
        if _DEPRECATION_MARKER not in open(path, encoding="utf-8").read():
            missing.append(rel)
    assert missing == [], f"legacy direct invokers without a deprecation comment: {missing}"


def test_characterize_1a_gap_requires_deprecation_marker_when_present():
    """characterize_1a_gap.py lives on the 1a-gap-phase0 branch; when it lands here it must
    carry the deprecation comment (allowlisted-with-deprecation per the review directive)."""
    path = os.path.join(_SCRIPTS, "characterize_1a_gap.py")
    if not os.path.isfile(path):
        return  # not on this branch yet; the requirement bites at merge time
    assert _DEPRECATION_MARKER in open(path, encoding="utf-8").read(), (
        "characterize_1a_gap.py is allowlisted ONLY with a deprecation comment; "
        "add the marker and migrate it to scripts/instrument/graph_evidence.py"
    )


def test_legacy_allowlist_is_not_silently_growable():
    """The legacy set is FROZEN at the six pre-rule files. If this count changes, the change
    must be a removal (migration to the helper), never an addition."""
    assert len(_LEGACY) <= 6, "legacy allowlist grew — new scripts must use the helper"
