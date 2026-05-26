"""Knowledge package — backward-compatible re-export of static lookup.

After Track 2, the knowledge_lookup tool uses PostgresKnowledgeRepository.
Composer.py L4 block reads from state (knowledge_passages) rather than
calling lookup_knowledge directly. The static exports here remain for any
test fixtures or fallback paths that still reference them.
"""
from sage_poc.knowledge.static import lookup_knowledge, KNOWLEDGE_DICT

__all__ = ["lookup_knowledge", "KNOWLEDGE_DICT"]
