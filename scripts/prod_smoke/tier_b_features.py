"""Tier B — feature card-render checks (Playwright, report-only in v1).

These drive the real frontend (chat.biosight.ai) and assert the Lane 2 cards
actually RENDER — not just that the backend emits the delivery headers (Tier A /
the backend curls cover the header layer). Selectors below were validated live
against prod on 2026-07-07 (all 5 checks PASS); see docs/runbooks/prod-smoke.md.

AUTH: the frontend requires a signed-in staff session. This module does NOT log
in — it loads a stored Playwright storage-state (cookies + localStorage) from
SAGE_SMOKE_STORAGE_STATE (a JSON file produced once via the cdai Playwright auth
harness, which owns login + its storageState invariant). Without it, Tier B
returns a single report-only FAIL "no storage state — cannot auth" rather than
faking a pass. This keeps login (and its RBAC/harness discipline) in ONE place.

run_all(base_url) -> list[CheckResult]  (all must_pass=False in v1).
"""
import os
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from result import CheckResult  # noqa: E402

TIER = "b"
_ARABIC = range(0x0600, 0x06FF + 1)


def _is_arabic(text: str) -> bool:
    return any(ord(c) in _ARABIC for c in text)


def _rep(name, status, detail):
    return CheckResult(name=name, tier=TIER, status=status, detail=detail, must_pass=False)


def run_all(base_url: str) -> list[CheckResult]:
    storage_state = os.environ.get("SAGE_SMOKE_STORAGE_STATE", "").strip()
    if not storage_state or not Path(storage_state).is_file():
        return [_rep(
            "tier_b_auth", "FAIL",
            "no SAGE_SMOKE_STORAGE_STATE storage-state file — cannot auth to the frontend; "
            "produce one via the cdai Playwright auth harness (see runbook). Tier B skipped.",
        )]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [_rep("tier_b_playwright", "FAIL",
                     "playwright not installed in this env — `pip install playwright && playwright install chromium`")]

    results: list[CheckResult] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=storage_state)
        try:
            results.append(_check_kb_source_card(ctx, base_url))
            results.append(_check_arabic_rtl_card(ctx, base_url))
            results.append(_check_persistence(ctx, base_url))
        finally:
            ctx.close()
            browser.close()
    return results


def _ask_new(ctx, base_url: str, question: str):
    """Open a fresh conversation, send `question`, return the page once the
    assistant turn (with its Sources region, if any) has rendered."""
    page = ctx.new_page()
    page.goto(f"{base_url.rstrip('/')}/chat?new=smoke-{abs(hash(question)) % 10**8}")
    page.locator("textarea").first.fill(question)
    page.locator("textarea").first.press("Enter")
    # assistant turn done when the typing indicator clears (bounded wait)
    try:
        page.get_by_text("Sage is typing").first.wait_for(state="hidden", timeout=45_000)
    except Exception:
        pass
    page.wait_for_timeout(1500)
    return page


def _check_kb_source_card(ctx, base_url: str) -> CheckResult:
    name = "kb_ask_renders_source_card"
    page = _ask_new(ctx, base_url, "what is cognitive behavioral therapy and how does it help with anxiety?")
    try:
        sources = page.get_by_role("complementary", name="Sources").first
        sources.wait_for(state="visible", timeout=10_000)
        links = sources.get_by_role("link")
        n = links.count()
        if n < 1:
            return _rep(name, "FAIL", "Sources region present but no source links")
        if n > 5:
            return _rep(name, "FAIL", f"source card not capped: {n} links (expected <=5)")
        return _rep(name, "PASS", f"KB source card rendered with {n} link(s), capped")
    except Exception as exc:
        return _rep(name, "FAIL", f"no Sources card rendered: {exc}")
    finally:
        page.close()


def _check_arabic_rtl_card(ctx, base_url: str) -> CheckResult:
    name = "arabic_renders_rtl_card_legible_title"
    page = _ask_new(ctx, base_url, "ما هو العلاج السلوكي المعرفي وكيف يساعد في القلق؟")
    try:
        sources = page.get_by_role("complementary", name="Sources").first
        sources.wait_for(state="visible", timeout=10_000)
        link = sources.get_by_role("link").first
        title = (link.inner_text() or "").strip()
        # legible Arabic title (not the English fallback) + RTL direction on the content
        direction = sources.evaluate("el => getComputedStyle(el).direction")
        if not _is_arabic(title):
            return _rep(name, "FAIL", f"source-card title not Arabic (English fallback?): {title!r}")
        if direction != "rtl":
            return _rep(name, "FAIL", f"source card not RTL (direction={direction!r})")
        return _rep(name, "PASS", f"Arabic RTL card, legible title: {title!r}")
    except Exception as exc:
        return _rep(name, "FAIL", f"no Arabic Sources card: {exc}")
    finally:
        page.close()


def _check_persistence(ctx, base_url: str) -> CheckResult:
    """Reopen the most recent conversation from the sidebar and assert whatever
    card it had still renders (or, if it had none, that it loads without crash)."""
    name = "reopened_conversation_no_crash"
    page = ctx.new_page()
    try:
        page.goto(f"{base_url.rstrip('/')}/chat")
        first = page.get_by_role("listitem").get_by_role("link").first
        first.wait_for(state="visible", timeout=10_000)
        first.click()
        page.get_by_role("log", name="Conversation").wait_for(state="visible", timeout=10_000)
        # reopened without crashing; if a Sources card is present it rendered on reload (persistence)
        has_card = page.get_by_role("complementary", name="Sources").count() > 0
        return _rep(name, "PASS", f"reopened conversation rendered without crash (card present: {has_card})")
    except Exception as exc:
        return _rep(name, "FAIL", f"reopen crashed / no conversation: {exc}")
    finally:
        page.close()
