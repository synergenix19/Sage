"""Experiment 4.5 — Query corpus for RAG retrieval accuracy tests.

Each entry maps a natural-language query to:
  expected_topic    : human-readable category label
  expected_source_prefix : expected source_id prefix (e.g. "cbt-", "anx-", "mbct-")
                           None means abstain is acceptable
  should_abstain    : True if no relevant article exists in current seed corpus
  language          : "en" or "ar"

The corpus reflects the seeded knowledge_articles rows for the POC.  Update
expected_source_prefix when new seed articles are ingested.

NOTE: These are unit-test corpus fixtures — actual DB calls are mocked.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class QueryCase:
    query: str
    expected_topic: str
    expected_source_prefix: str | None
    should_abstain: bool
    language: str = "en"
    notes: str = ""


# ---------------------------------------------------------------------------
# English queries — known topics (should retrieve, not abstain)
# ---------------------------------------------------------------------------

KNOWN_QUERIES_EN: list[QueryCase] = [
    QueryCase(
        query="what is cognitive behavioral therapy",
        expected_topic="CBT",
        expected_source_prefix="cbt-",
        should_abstain=False,
    ),
    QueryCase(
        query="how does CBT work for depression",
        expected_topic="CBT for depression",
        expected_source_prefix="cbt-",
        should_abstain=False,
    ),
    QueryCase(
        query="what is exposure therapy",
        expected_topic="exposure therapy / anxiety",
        expected_source_prefix="anx-",
        should_abstain=False,
    ),
    QueryCase(
        query="what is mindfulness based cognitive therapy",
        expected_topic="MBCT",
        expected_source_prefix="mbct-",
        should_abstain=False,
    ),
    QueryCase(
        query="evidence based treatments for anxiety",
        expected_topic="anxiety treatment",
        expected_source_prefix=None,   # any relevant passage acceptable
        should_abstain=False,
    ),
    QueryCase(
        query="what are grounding techniques for panic attacks",
        expected_topic="grounding / panic",
        expected_source_prefix=None,
        should_abstain=False,
    ),
    QueryCase(
        query="what is dialectical behavior therapy",
        expected_topic="DBT",
        expected_source_prefix="dbt-",
        should_abstain=False,
    ),
    QueryCase(
        query="how does sleep hygiene affect mental health",
        expected_topic="sleep hygiene",
        expected_source_prefix=None,
        should_abstain=False,
    ),
]

# ---------------------------------------------------------------------------
# Arabic-language queries — translation-normalised path
# (message_en field carries the English translation; language="ar")
# ---------------------------------------------------------------------------

KNOWN_QUERIES_AR: list[QueryCase] = [
    QueryCase(
        query="ما هو العلاج المعرفي السلوكي",
        expected_topic="CBT (Arabic query, English corpus)",
        expected_source_prefix="cbt-",
        should_abstain=False,
        language="ar",
        notes="Arabic query must be translated to English before retrieval. "
              "knowledge_retrieve_node always calls repo.retrieve(..., language='en').",
    ),
    QueryCase(
        query="كيف يساعد العلاج النفسي في علاج الاكتئاب",
        expected_topic="therapy for depression (Arabic query)",
        expected_source_prefix=None,
        should_abstain=False,
        language="ar",
        notes="Depression treatment — should retrieve via English message_en translation.",
    ),
]

# ---------------------------------------------------------------------------
# Out-of-scope queries — should abstain
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_QUERIES: list[QueryCase] = [
    QueryCase(
        query="what is the cure for cancer",
        expected_topic="out-of-scope: oncology",
        expected_source_prefix=None,
        should_abstain=True,
        notes="No oncology content in corpus — must return abstain=True.",
    ),
    QueryCase(
        query="how do I invest in cryptocurrency",
        expected_topic="out-of-scope: finance",
        expected_source_prefix=None,
        should_abstain=True,
        notes="Finance query — must return abstain=True.",
    ),
    QueryCase(
        query="recipe for chocolate cake",
        expected_topic="out-of-scope: cooking",
        expected_source_prefix=None,
        should_abstain=True,
        notes="Cooking query — must return abstain=True.",
    ),
]

# ---------------------------------------------------------------------------
# Edge-case queries
# ---------------------------------------------------------------------------

EDGE_CASE_QUERIES: list[QueryCase] = [
    QueryCase(
        query="",
        expected_topic="empty query",
        expected_source_prefix=None,
        should_abstain=True,
        notes="Empty string should return abstain=True without raising.",
    ),
    QueryCase(
        query="a" * 1000,
        expected_topic="very long query",
        expected_source_prefix=None,
        should_abstain=True,
        notes="Excessively long query — system must not raise.",
    ),
    QueryCase(
        query="CBT",
        expected_topic="single-word known topic",
        expected_source_prefix="cbt-",
        should_abstain=False,
        notes="Single keyword — should still retrieve relevant passage.",
    ),
]

ALL_QUERIES: list[QueryCase] = (
    KNOWN_QUERIES_EN
    + KNOWN_QUERIES_AR
    + OUT_OF_SCOPE_QUERIES
    + EDGE_CASE_QUERIES
)
