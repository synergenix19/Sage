"""Tier C shape tests — no network. Stub the /health/version GET and assert the flag-readback
logic reads the provenance endpoint's resolved-flag fields (not /health/ready) and PASS/FAILs
against the expected deploy state.
"""
import sys
from pathlib import Path
from unittest.mock import patch

_PROD_SMOKE_DIR = Path(__file__).resolve().parent.parent
if str(_PROD_SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROD_SMOKE_DIR))

import tier_c_regression  # noqa: E402


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def _health_version(route=True, skill=True, ipv=False, **extra):
    body = {
        "build_sha": "deadbeef",
        "route_precedence_enabled": route,
        "skill_media_enabled": skill,
        "ipv_preemption_enabled": ipv,
    }
    body.update(extra)
    return body


def test_flag_checks_pass_when_all_match_expected():
    # Correct prod deploy: route ON, skill ON, ipv OFF -> all three PASS.
    with patch.object(tier_c_regression.httpx, "get", return_value=_FakeResp(_health_version())):
        results = tier_c_regression._flag_checks("http://x")
    assert [r.status for r in results] == ["PASS", "PASS", "PASS"]
    assert all(r.must_pass for r in results)


def test_flag_check_fails_on_drift():
    # ipv accidentally ON -> that check FAILs (a kill-switch left on is a real finding).
    with patch.object(tier_c_regression.httpx, "get", return_value=_FakeResp(_health_version(ipv=True))):
        results = tier_c_regression._flag_checks("http://x")
    by = {r.name: r for r in results}
    assert by["flag_readback[SAGE_IPV_PREEMPTION]"].status == "FAIL"
    assert by["flag_readback[SAGE_SKILL_MEDIA_ENABLED]"].status == "PASS"


def test_flag_check_fails_when_field_missing():
    # A deploy predating the field (or endpoint drift) -> FAIL naming the field, never a silent pass.
    body = _health_version()
    del body["route_precedence_enabled"]
    with patch.object(tier_c_regression.httpx, "get", return_value=_FakeResp(body)):
        results = tier_c_regression._flag_checks("http://x")
    by = {r.name: r for r in results}
    assert by["flag_readback[SAGE_ROUTE_PRECEDENCE]"].status == "FAIL"
    assert "not present on /health/version" in by["flag_readback[SAGE_ROUTE_PRECEDENCE]"].detail


def test_reads_health_version_not_ready():
    captured = {}
    def fake_get(url, **kw):
        captured["url"] = url
        return _FakeResp(_health_version())
    with patch.object(tier_c_regression.httpx, "get", side_effect=fake_get):
        tier_c_regression._flag_checks("http://x")
    assert captured["url"].endswith("/health/version")
