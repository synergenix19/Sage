"""D4 interim safety valve (#234): a single 'dumb' notification when an L2 clinical-review flag is
written for a NON-TEST user.

The review queue is DEFERRED / logs-only (D4). The clinician's logs-only signature was contingent
on this tripwire existing: until a non-test-user L2 notification fires in production, that condition
is not met. Deliberately dumb — one outbound notification per qualifying flag, no workflow, no
triage UI (that is the deferred flow design). Non-fatal: never blocks the review write.

Two design invariants from the D4 ruling:
  1. The test-user predicate is EXPLICIT and TESTED. A tripwire that fires on QA/e2e runs gets muted
     within a week, and a muted tripwire is worse than none.
  2. The no-target fallback is a LOUD log, not silence — a missing webhook degrades to visible-in-logs,
     never silently-muted. The PO names the recipient (D4 gave the mechanism, not the address).
"""
import logging
import os

_log = logging.getLogger(__name__)


def _test_user_ids() -> frozenset[str]:
    raw = os.environ.get("SAGE_TEST_USER_IDS", "")
    return frozenset(u.strip() for u in raw.split(",") if u.strip())


def is_test_user(user_id: str | None) -> bool:
    """True iff user_id is in the SAGE_TEST_USER_IDS allowlist (QA / e2e / synthetic). The tripwire
    must NOT fire for these. A None/empty user_id is treated as NON-test (fail-loud: an unattributed
    real crisis should ping, never be silently dropped)."""
    if not user_id:
        return False
    return user_id in _test_user_ids()


async def fire_l2_tripwire(*, user_id: str | None, session_id: str, reason: str, severity: str) -> None:
    """Fire the interim tripwire for a non-test-user L2 flag. Best-effort; NEVER raises.

    POSTs a Slack-compatible payload to SAGE_TRIPWIRE_WEBHOOK_URL if configured; otherwise logs at
    WARNING so the signal is visible-in-logs and cannot be silently muted."""
    if is_test_user(user_id):
        return
    text = (
        f"[SAGE L2 TRIPWIRE] non-test clinical-review flag — severity={severity} "
        f"session={session_id} user={user_id} reason={reason}"
    )
    url = os.environ.get("SAGE_TRIPWIRE_WEBHOOK_URL", "").strip()
    if not url:
        _log.warning(
            "%s (SAGE_TRIPWIRE_WEBHOOK_URL unset — logs-only; PO must name the recipient)", text
        )
        return
    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json={"text": text})
    except Exception as exc:  # noqa: BLE001 — tripwire is non-fatal by contract
        _log.warning("[tripwire] webhook POST failed (%s); flag still logged: %s", exc, text)
