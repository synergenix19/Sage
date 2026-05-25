"""LLM-callable tool: retrieve validated mental health knowledge (v7 §6.5.2).

Architecture note: this tool shares the same RAG pipeline as Node 6
(knowledge_retrieve) but is invoked by the LLM on demand rather than by the
graph router. The LLM calls this when the user asks a factual question that
requires clinical accuracy — not for emotional support queries.

POC implementation: wraps the static KNOWLEDGE_DICT (10 entries, substring match).
Production target: Azure AI Search hybrid BM25+vector with BGE-M3 reranker,
query rewriting, and citation metadata from a populated knowledge index.

Contract: when abstain=true, the LLM must acknowledge uncertainty and not
fabricate an answer. The abstain flag is the safety valve against hallucination
on clinical facts.
"""
from __future__ import annotations
import json
from langchain_core.tools import tool

from sage_poc.knowledge import lookup_knowledge


@tool
async def knowledge_lookup(query: str) -> str:
    """Look up validated clinical or psychoeducational information.

    Call this when the user asks a factual question about mental health,
    therapy modalities, psychological concepts, or evidence-based treatment.
    Do NOT call for personal/emotional support — only for factual questions
    where clinical accuracy matters (e.g. 'what is CBT?', 'what causes burnout?').

    When the returned JSON has abstain=true, tell the user you don't have
    specific information on that topic. Do not invent clinical facts.

    Args:
        query: The user's factual question (1-2 sentences).
    """
    result = lookup_knowledge(query)
    if result is None:
        return json.dumps({"result": None, "source": None, "abstain": True})
    return json.dumps({"result": result, "source": "knowledge_base_v1", "abstain": False})
