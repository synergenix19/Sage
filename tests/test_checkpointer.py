import pytest
asyncpg = pytest.importorskip("asyncpg", reason="asyncpg not installed — requires Postgres")
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_get_checkpointer_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from sage_poc.memory.checkpointer import get_checkpointer
    with pytest.raises(ValueError, match="DATABASE_URL"):
        async with get_checkpointer():
            pass

@pytest.mark.asyncio
async def test_get_checkpointer_yields_saver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    mock_pool = AsyncMock()
    mock_saver = MagicMock()
    mock_saver.setup = AsyncMock()
    from sage_poc.memory import checkpointer as chk_mod
    import importlib; importlib.reload(chk_mod)
    with patch("asyncpg.create_pool", return_value=mock_pool):
        with patch("sage_poc.memory.checkpointer.AsyncPostgresSaver", return_value=mock_saver):
            async with chk_mod.get_checkpointer() as saver:
                assert saver is mock_saver
                mock_saver.setup.assert_awaited_once()
