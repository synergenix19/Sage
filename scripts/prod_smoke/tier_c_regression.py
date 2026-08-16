"""Tier C — regression checks: deployed-flag readback + response-header regression.

This is the Task 1 slice of the prod smoke suite. It reuses the request and
header conventions from scripts/functional_test_production.py (the
X-Sage-Api-Key header built from SAGE_API_KEY) rather than reimplementing
them — see the import below.
"""
import sys
import time
import uuid
from pathlib import Path

import httpx

from result import CheckResult

# functional_test_production.py lives one directory up, in scripts/.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from functional_test_production import HEADERS  # noqa: E402 — reuse, do not fork

TIER = "c"

# Deploy-flag readback via GET /health/version (auth-gated — it returns the RESOLVED value and raw
# env for each kill-switch: crisis_tiering_enabled, skill_media_enabled, route_precedence_enabled,
# ipv_preemption_enabled). /health/ready deliberately carries only readiness signals, not flags, so
# this reads the provenance endpoint instead. Each entry: (env-var label for the check name, the
# /health/version field, the expected RESOLVED state on a correct prod deploy).
_FLAG_CHECKS = (
    ("SAGE_ROUTE_PRECEDENCE", "route_precedence_enabled", True),
    ("SAGE_SKILL_MEDIA_ENABLED", "skill_media_enabled", True),
    ("SAGE_IPV_PREEMPTION", "ipv_preemption_enabled", False),
)

_NON_KB_CHAT_MESSAGE = "I had a pretty good day today, just wanted to check in."


def _evaluate_flag(label: str, field: str, expected_on: bool, body: dict) -> CheckResult:
    if field not in body:
        return CheckResult(
            name=f"flag_readback[{label}]",
            tier=TIER,
            status="FAIL",
            detail=f"{field!r} not present on /health/version — deploy predates the field, or endpoint drift",
            must_pass=True,
        )
    observed = body[field]
    ok = bool(observed) == expected_on
    return CheckResult(
        name=f"flag_readback[{label}]",
        tier=TIER,
        status="PASS" if ok else "FAIL",
        detail=f"/health/version.{field}={observed!r} (expected {'on' if expected_on else 'off'})",
        must_pass=True,
    )


def _flag_checks(base_url: str) -> list[CheckResult]:
    try:
        # /health/version is auth-gated (GL-5) — reuse the shared X-Sage-Api-Key HEADERS.
        resp = httpx.get(f"{base_url}/health/version", headers=HEADERS, timeout=15.0)
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:
        detail = f"GET /health/version failed: {exc}"
        return [
            CheckResult(name=f"flag_readback[{label}]", tier=TIER, status="FAIL", detail=detail, must_pass=True)
            for label, _field, _exp in _FLAG_CHECKS
        ]

    return [_evaluate_flag(label, field, exp, body) for label, field, exp in _FLAG_CHECKS]


def _chat_header_regression(base_url: str) -> CheckResult:
    """Report-only: a plain non-KB chat turn should carry neither the KB-sources
    header nor the skill-media header. Not must_pass — this is a regression
    tripwire, not a release-blocking check.
    """
    name = "chat_no_sources_no_skill_media_on_plain_turn"
    session_id = f"smoke-tierc-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    payload = {
        "messages": [{"role": "user", "content": _NON_KB_CHAT_MESSAGE}],
        "session_id": session_id,
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            with client.stream("POST", f"{base_url}/chat", headers=HEADERS, json=payload) as resp:
                resp.read()
    except Exception as exc:
        return CheckResult(name=name, tier=TIER, status="FAIL", detail=f"HTTP error: {exc}", must_pass=False)

    if resp.status_code != 200:
        return CheckResult(
            name=name, tier=TIER, status="FAIL",
            detail=f"HTTP {resp.status_code}: {resp.text[:120]!r}", must_pass=False,
        )

    present = [
        h for h, seen in (
            ("X-Sage-Sources", "x-sage-sources" in resp.headers),
            ("X-Sage-Skill-Media", "x-sage-skill-media" in resp.headers),
        ) if seen
    ]
    if present:
        return CheckResult(
            name=name, tier=TIER, status="FAIL",
            detail=f"unexpected header(s) present on plain turn: {present}", must_pass=False,
        )
    return CheckResult(name=name, tier=TIER, status="PASS", detail="neither header present, as expected", must_pass=False)


def flag_readback(base_url: str) -> list[CheckResult]:
    """Tier C entry point: flag readback (must-pass) + header regression (report-only)."""
    results = _flag_checks(base_url)
    results.append(_chat_header_regression(base_url))
    return results
