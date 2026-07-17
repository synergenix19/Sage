"""/health/version D1 flag readback (#338) — the endpoint tells the flag state truthfully, so the deploy
smoke can VERIFY (not infer) shadow=on/enforce=off. Same resolved+raw pattern as the other kill-switches."""
import asyncio
import server
from sage_poc import config


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
