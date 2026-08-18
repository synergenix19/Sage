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
