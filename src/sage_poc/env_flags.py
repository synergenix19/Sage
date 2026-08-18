"""Enumeration of behavior-affecting env flags read OUTSIDE config.py (P2 class closure,
code_review.md 2026-08-17, owner-required).

config.py flags are import-time os.getenv reads, enumerable from the module. The flags
below are read from os.environ at CALL TIME by their owning modules, so they are invisible
to config-based parity stamps — the "V2-off locals false-passed" instrument-defect class
(3rd recurrence: V2-live register, §1a characterization replay, §3a eval harness).

Contract, enforced by scripts/check_env_flag_enumeration.py in CI:
  - every SAGE_*/SKILL_* env read in src/sage_poc outside config.py appears in
    ENUMERATED_ENV_FLAGS (the gate fails naming any gap);
  - effective_env_flags() DELEGATES to the live reader for each flag (never a copied
    expression, never a module constant), so a stamp prints what the serving code
    actually computes. Instruments asserting prod parity MUST include this dict in
    their provenance stamp.
"""
from __future__ import annotations

# Names must stay in lockstep with the actual reads; the CI gate fails on drift in
# either direction (unenumerated read, or stale enumerated name).
ENUMERATED_ENV_FLAGS: frozenset[str] = frozenset({
    "SKILL_ROUTING_V2",         # skill_select._v2_enabled — V2 retrieval-core routing
    "SKILL_RERANK_ENABLED",     # skill_select._rerank_enabled — §4.3 cross-encoder selector
    "SKILL_RERANK_PRECISION",   # skill_rerank_model.active_precision — fp32/int8 (int8 disqualified on safety)
    "SAGE_TEST_USER_IDS",       # tripwire._test_user_ids — tripwire mute allowlist
    "SAGE_TRIPWIRE_WEBHOOK_URL",  # tripwire — L2 ping destination (stamped as configured-or-not, never the URL)
})


def effective_env_flags() -> dict:
    """Effective values as the LIVE readers compute them right now.

    Late imports: env_flags must stay import-cycle-free (config.py and node modules may
    import nothing from here; instruments import this).
    """
    from sage_poc.nodes.skill_select import _v2_enabled, _rerank_enabled  # noqa: PLC0415
    from sage_poc.nodes.skill_rerank_model import active_precision  # noqa: PLC0415
    from sage_poc.safety.tripwire import _test_user_ids  # noqa: PLC0415
    import os  # noqa: PLC0415

    return {
        "SKILL_ROUTING_V2": _v2_enabled(),
        "SKILL_RERANK_ENABLED": _rerank_enabled(),
        "SKILL_RERANK_PRECISION": active_precision(),
        "SAGE_TEST_USER_IDS": sorted(_test_user_ids()),
        "SAGE_TRIPWIRE_WEBHOOK_URL": "configured" if (os.environ.get("SAGE_TRIPWIRE_WEBHOOK_URL", "").strip()) else "unset",
    }
