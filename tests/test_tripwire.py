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
