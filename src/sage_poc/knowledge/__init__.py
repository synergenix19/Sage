"""Knowledge package.

Retrieval is served by PostgresKnowledgeRepository (Track 2); the freeflow L4 block reads
`knowledge_passages` from state rather than any in-process lookup. Import the repositories from
their own modules directly.

The legacy static EN-only lookup (`knowledge/static.py`, `lookup_knowledge` / `KNOWLEDGE_DICT`) was
REMOVED 2026-07-10 (audit #7): it had no production caller, and if ever rewired as a "fallback" it
would have served English canned text to Arabic users — a latent foot-gun with no upside.
"""
