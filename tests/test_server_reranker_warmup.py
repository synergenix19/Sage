"""Startup reranker head-control — readiness-BLOCKING positive control.

Blocker-2 fix (2026-06-25 deploy prep): the reranker was absent from startup, so a silent
headless-load (the CrossEncoder-headless bug class) on the deploy target would route confident-wrong
with NO error. The fix wires head_loaded_ok() into startup as a readiness-BLOCKING gate — a headless
load must take the instance OUT of rotation (raise → _bge_ready stays False → /health/ready 503), NOT
warn-and-continue (the known warmup-silent-failure anti-pattern). These tests pin that it blocks.

Fast: head_loaded_ok is monkeypatched, so no 2.2GB model load.
"""
import pytest


def test_warmup_reranker_blocks_on_headless_load(monkeypatch):
    # head_loaded_ok() False (headless / no separation) MUST raise so readiness is withheld.
    import server
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    monkeypatch.setattr("sage_poc.nodes.skill_rerank_model.head_loaded_ok", lambda: False)
    with pytest.raises(RuntimeError, match="head-control FAILED"):
        server._warmup_reranker()


def test_warmup_reranker_passes_when_head_loaded(monkeypatch):
    # head_loaded_ok() True → returns cleanly (no raise), readiness can proceed.
    import server
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    monkeypatch.setattr("sage_poc.nodes.skill_rerank_model.head_loaded_ok", lambda: True)
    server._warmup_reranker()  # must not raise


def test_warmup_reranker_skips_when_disabled(monkeypatch):
    # Reranker off → skip entirely, never load/probe the model (V1 path unaffected).
    import server
    monkeypatch.delenv("SKILL_RERANK_ENABLED", raising=False)
    called = {"probed": False}
    def _should_not_run():
        called["probed"] = True
        return True
    monkeypatch.setattr("sage_poc.nodes.skill_rerank_model.head_loaded_ok", _should_not_run)
    server._warmup_reranker()  # must not raise
    assert called["probed"] is False, "head control must not run when reranker disabled"


# ── Observability: the head-control result must be HUMAN-VERIFIABLE, not just enforced ──
# Blocker-2 enforced readiness-blocking (503 on headless) but the success signal was an INFO log line
# the app logger suppresses → the prod runbook's "logs show head-control passed" gate was unsatisfiable.
# Fix: a structured status surfaced on /health/ready so the gate is a direct readable check.

def test_warmup_reranker_sets_status_passed(monkeypatch):
    import server
    monkeypatch.setattr(server, "_reranker_status", "pending", raising=False)
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    monkeypatch.setattr("sage_poc.nodes.skill_rerank_model.head_loaded_ok", lambda: True)
    server._warmup_reranker()
    assert server._reranker_status == "passed"


def test_warmup_reranker_sets_status_failed(monkeypatch):
    import server
    monkeypatch.setattr(server, "_reranker_status", "pending", raising=False)
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    monkeypatch.setattr("sage_poc.nodes.skill_rerank_model.head_loaded_ok", lambda: False)
    with pytest.raises(RuntimeError):
        server._warmup_reranker()
    assert server._reranker_status == "failed", "a headless load must record 'failed' (queryable), not just raise"


def test_warmup_reranker_sets_status_disabled(monkeypatch):
    import server
    monkeypatch.setattr(server, "_reranker_status", "pending", raising=False)
    monkeypatch.delenv("SKILL_RERANK_ENABLED", raising=False)
    server._warmup_reranker()
    assert server._reranker_status == "disabled"


def test_health_ready_surfaces_reranker_head_control(monkeypatch):
    # The prod runbook's HARD GATE check, now directly satisfiable: /health/ready 200 body carries the
    # head-control result as a structured field (no reliance on suppressed INFO logs / Railway log API).
    import asyncio, server
    monkeypatch.setattr(server, "_bge_ready", True, raising=False)
    monkeypatch.setattr(server, "_reranker_status", "passed", raising=False)
    body = asyncio.run(server.health_ready())
    assert body.get("reranker_head_control") == "passed", "health/ready must surface the head-control result"
