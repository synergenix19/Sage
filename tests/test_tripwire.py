"""#234 — D4 interim L2 tripwire: explicit tested test-user predicate + loud-fallback firing."""
import logging
import httpx
from sage_poc.safety import tripwire


class TestIsTestUser:
    def test_user_in_allowlist_is_test(self, monkeypatch):
        monkeypatch.setenv("SAGE_TEST_USER_IDS", "u-1, u-2 ,u-3")
        assert tripwire.is_test_user("u-2") is True

    def test_user_not_in_allowlist_is_not_test(self, monkeypatch):
        monkeypatch.setenv("SAGE_TEST_USER_IDS", "u-1")
        assert tripwire.is_test_user("real-user") is False

    def test_none_user_is_not_test_fail_loud(self, monkeypatch):
        # Unattributed real crisis must PING, not be silently dropped.
        monkeypatch.setenv("SAGE_TEST_USER_IDS", "u-1")
        assert tripwire.is_test_user(None) is False

    def test_empty_allowlist_nobody_is_test(self, monkeypatch):
        monkeypatch.delenv("SAGE_TEST_USER_IDS", raising=False)
        assert tripwire.is_test_user("anyone") is False


class TestFireTripwire:
    async def test_test_user_is_muted(self, monkeypatch, caplog):
        monkeypatch.setenv("SAGE_TEST_USER_IDS", "qa-1")
        with caplog.at_level(logging.WARNING):
            await tripwire.fire_l2_tripwire(user_id="qa-1", session_id="s", reason="r", severity="high")
        assert "TRIPWIRE" not in caplog.text

    async def test_non_test_no_webhook_logs_loud(self, monkeypatch, caplog):
        # No target => visible-in-logs, never silently muted.
        monkeypatch.delenv("SAGE_TEST_USER_IDS", raising=False)
        monkeypatch.delenv("SAGE_TRIPWIRE_WEBHOOK_URL", raising=False)
        with caplog.at_level(logging.WARNING):
            await tripwire.fire_l2_tripwire(user_id="real", session_id="s", reason="crisis", severity="high")
        assert "L2 TRIPWIRE" in caplog.text

    async def test_non_test_with_webhook_posts(self, monkeypatch):
        monkeypatch.delenv("SAGE_TEST_USER_IDS", raising=False)
        monkeypatch.setenv("SAGE_TRIPWIRE_WEBHOOK_URL", "https://hook.example/x")
        posted = {}

        async def _fake_post(self, url, json=None):
            posted["url"] = url
            posted["json"] = json
            return object()

        monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)
        await tripwire.fire_l2_tripwire(user_id="real", session_id="s1", reason="crisis", severity="high")
        assert posted["url"] == "https://hook.example/x"
        assert "TRIPWIRE" in posted["json"]["text"]

    async def test_never_raises_on_webhook_error(self, monkeypatch):
        monkeypatch.delenv("SAGE_TEST_USER_IDS", raising=False)
        monkeypatch.setenv("SAGE_TRIPWIRE_WEBHOOK_URL", "https://hook.example/x")

        async def _boom(self, url, json=None):
            raise RuntimeError("network down")

        monkeypatch.setattr(httpx.AsyncClient, "post", _boom)
        # Contract: never raises — the review write must not fail on a tripwire error.
        await tripwire.fire_l2_tripwire(user_id="real", session_id="s", reason="r", severity="high")


class TestNotifyReviewRequiredWiring:
    """The notify_review_required -> fire_l2_tripwire wiring. Overrides the conftest autouse mute
    with a spy, so this is the one test that proves the hook is actually invoked (with the flag's
    identity, after the DB write) — the integration point the unit tests above don't cover."""

    async def test_wires_tripwire_after_pool_release(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock
        import sage_poc.memory.notification as notif

        calls = []

        async def _spy(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(notif, "fire_l2_tripwire", _spy)

        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock()))
        conn.execute = AsyncMock()

        await notif.PostgresNotifier(pool).notify_review_required(
            user_id="real-user", session_id="s9", reason="crisis_flags",
            source="layer1_safety", payload={"flags": ["x"]}, severity="high",
        )
        assert conn.execute.await_count == 2   # INSERT + NOTIFY still happen
        assert calls == [{"user_id": "real-user", "session_id": "s9",
                          "reason": "crisis_flags", "severity": "high"}]
