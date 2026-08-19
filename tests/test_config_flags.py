"""Strict-parse tests for the two default-ON config flags: AUDIT_LOG_ENABLED and
EMBED_CACHE_ENABLED. Mirrors the inverse-polarity strict idiom already established for
SAGE_CRISIS_TIERING (config.py:184-190): only a literal "false" disables; empty/garbage
values warn and keep the signed default ON. The "" row is the Railway empty-string
injection RCA case (see docs/superpowers/governance/2026-07-03-clinician-signoff-packet.md).
"""

import importlib

import pytest

from sage_poc import config


@pytest.fixture(autouse=True)
def _reload_config_after_test():
    """Ensure later tests see defaults regardless of what this module's tests set."""
    yield
    importlib.reload(config)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, True),
        ("true", True),
        ("false", False),
        ("", True),  # Railway empty-string injection — the RCA case
        ("0", True),
        ("garbage", True),
    ],
)
def test_audit_log_flag_strict_default_on(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("SAGE_AUDIT_LOG", raising=False)
    else:
        monkeypatch.setenv("SAGE_AUDIT_LOG", raw)
    from sage_poc import config

    importlib.reload(config)
    assert config.AUDIT_LOG_ENABLED is expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, True),
        ("true", True),
        ("false", False),
        ("", True),  # Railway empty-string injection — the RCA case
        ("0", True),
        ("garbage", True),
    ],
)
def test_embed_cache_flag_strict_default_on(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("SAGE_EMBED_CACHE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("SAGE_EMBED_CACHE_ENABLED", raw)
    from sage_poc import config

    importlib.reload(config)
    assert config.EMBED_CACHE_ENABLED is expected


# --- K2.1 byte-identical-behavior proof -------------------------------------------------
#
# Full parametrized matrix over every flag `_strict_flag()` will migrate (config.py's
# STANDING BANNED-OPS / strict kill-switch parse family), crossed with the canonical
# {unset, "true", "false", "", "TRUE ", "garbage"} raw-value set. This is run GREEN against
# the unmigrated, per-flag hand-rolled parse blocks BEFORE the K2.1 refactor (proving current
# semantics), and re-run GREEN with zero edits AFTER config.py is migrated to `_strict_flag()`
# calls (proving the migration changed no observable behavior — parse can no longer drift
# per-flag, but the flags themselves drift nothing).
#
# Each entry: (attribute name on the config module, env var name, default_on).
# default_on=True  -> inverse-polarity kill-switch: only literal "false" disables.
# default_on=False -> only literal "true" enables.
_STRICT_FLAGS = [
    # The two #486 default-ON blocks.
    ("AUDIT_LOG_ENABLED", "SAGE_AUDIT_LOG", True),
    ("EMBED_CACHE_ENABLED", "SAGE_EMBED_CACHE_ENABLED", True),
    # Default-ON kill-switch (inverse polarity, same family as the two above).
    ("CRISIS_TIERING_ENABLED", "SAGE_CRISIS_TIERING", True),
    # Default-OFF strict kill-switches.
    ("ROUTE_PRECEDENCE_ENABLED", "SAGE_ROUTE_PRECEDENCE", False),
    ("PANIC_GROUNDING_OVERRIDE_ENABLED", "SAGE_PANIC_GROUNDING_OVERRIDE", False),
    ("CARDIAC_ESCALATION_ENABLED", "SAGE_CARDIAC_ESCALATION", False),
    ("MODALITY_REQUEST_ROUTING_ENABLED", "SAGE_MODALITY_REQUEST_ROUTING", False),
    ("GRIEF_DEFERENCE_ENABLED", "SAGE_GRIEF_DEFERENCE", False),
    ("SELFWORTH_FP_EXCLUSION_ENABLED", "SAGE_SELFWORTH_FP_EXCLUSION", False),
    ("THIRD_PARTY_DEFERENCE_ENABLED", "SAGE_THIRD_PARTY_DEFERENCE", False),
    ("IPV_PREEMPTION_ENABLED", "SAGE_IPV_PREEMPTION", False),
    ("HIGH_RISK_TERMINAL_ENABLED", "SAGE_HIGH_RISK_TERMINAL", False),
    ("DEREALIZATION_DETECTION_ENABLED", "SAGE_DEREALIZATION_DETECTION", False),
    ("INFO_REQUEST_CONSULT_ENABLED", "SAGE_INFO_REQUEST_CONSULT", False),
    ("PSYCHOED_PATHWAYS_ENABLED", "SAGE_PSYCHOED_PATHWAYS", False),
    ("CONSULT_SOURCES_ENABLED", "SAGE_CONSULT_SOURCES", False),
]

_STRICT_RAW_VALUES = [None, "true", "false", "", "TRUE ", "garbage"]


def _strict_expected(default_on: bool, raw: str | None) -> bool:
    """Mirrors the strict kill-switch semantics under test (both the current per-flag
    hand-rolled blocks and the post-migration _strict_flag()): default_on=True -> only a
    literal "false" disables; default_on=False -> only a literal "true" enables. Anything
    else (unset/empty/whitespace/garbage) keeps the signed default."""
    if default_on:
        if raw is not None and raw.strip().lower() == "false":
            return False
        return True
    if raw is not None and raw.strip().lower() == "true":
        return True
    return False


@pytest.mark.parametrize("raw", _STRICT_RAW_VALUES)
@pytest.mark.parametrize("attr_name,env_var,default_on", _STRICT_FLAGS)
def test_strict_flag_matrix(monkeypatch, attr_name, env_var, default_on, raw):
    if raw is None:
        monkeypatch.delenv(env_var, raising=False)
    else:
        monkeypatch.setenv(env_var, raw)
    from sage_poc import config

    importlib.reload(config)
    assert getattr(config, attr_name) is _strict_expected(default_on, raw)
