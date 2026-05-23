import pytest
from sage_poc.memory.repository import MemoryRepository

def test_memory_repository_is_abstract():
    with pytest.raises(TypeError):
        MemoryRepository()

def test_subclass_must_implement_methods():
    class Incomplete(MemoryRepository):
        pass
    with pytest.raises(TypeError):
        Incomplete()
