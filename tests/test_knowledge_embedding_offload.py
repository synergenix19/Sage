# tests/test_knowledge_embedding_offload.py
#
# F3 (code_review.md 2026-08-17): knowledge retrieval must not run BGE-M3
# inference synchronously on the event loop. Every other request-path
# embedding call site offloads via get_embedding_async / asyncio.to_thread
# (check_user_history.py, output_gate.py, skill_select.py); the knowledge
# repository was the one bypass — blocking every concurrent request
# (including crisis-path turns) for the duration of a CPU encode.

import threading

from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository


class _FakeConn:
    async def fetch(self, *args, **kwargs):
        return []


class _FakeAcquire:
    async def __aenter__(self):
        return _FakeConn()

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def acquire(self):
        return _FakeAcquire()


async def test_search_offloads_embedding_from_event_loop(monkeypatch):
    calls: list[threading.Thread] = []

    def recording_get_embedding(text: str) -> list[float]:
        calls.append(threading.current_thread())
        return [0.0] * 1024

    monkeypatch.setattr(
        "sage_poc.memory.embedding.get_embedding", recording_get_embedding
    )

    repo = PostgresKnowledgeRepository(_FakePool())
    result = await repo._search("how can i sleep better", language="en", top_k=5)

    assert result.abstain is True  # empty rows -> abstain; retrieval path completed
    assert calls, "embedding was never computed"
    loop_thread = threading.current_thread()
    assert all(t is not loop_thread for t in calls), (
        "BGE-M3 inference ran on the event loop thread; it must be offloaded "
        "(get_embedding_async / run_in_executor) like every other request-path "
        "embedding call site"
    )
