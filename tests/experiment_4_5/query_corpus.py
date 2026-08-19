"""Experiment 4.5 — Query corpus for RAG retrieval accuracy tests.

Each entry maps a natural-language query to:
  expected_topic    : human-readable category label
  expected_source_prefix : expected source_id prefix (e.g. "cbt-", "anxiety-")
                           None means any relevant passage is acceptable
  should_abstain    : True if no relevant article exists in current seed corpus
  language          : "en" or "ar"

The corpus reflects the seeded knowledge_articles rows for the POC.  Update
expected_source_prefix when new seed articles are ingested.

NOTE: These are unit-test corpus fixtures — actual DB calls are mocked.

Prefix refresh 2026-08-19 (ticket 2026-08-19-ivfflat-recall-holes-crisis-adjacent,
sage-poc PR #501): the prefixes "anx-", "mbct-" and "dbt-" named articles that do
not exist in the corpus and had drifted out of any correspondence with it, so the
eval could not gate the retrieval fix the ticket calls for.  Replacements are the
article IDs these queries actually retrieve, measured against prod
(tcekehffneiqcdyhzobi) on 2026-08-19 under an exact vector scan -- i.e. the
behaviour after cdai PR #512 drops the ivfflat index.  Under the ANN index still
serving today two of them return gulf-001 below the abstain gate instead, which is
the defect #512 fixes; pinning to the ANN behaviour would pin the defect.
Raw evidence: Sage_KB_ivfflat_AB_Prod_2026-08-19.json.
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
        expected_source_prefix="therapy-",
        should_abstain=False,
        notes="No exposure-therapy article exists; therapy-001 is the nearest real "
              "passage at cosine 0.450 (prod, exact scan, 2026-08-19). That is the "
              "weakest in-scope hit in the set -- if the abstain gate is recalibrated "
              "into the measured (0.544, 0.617] band alongside cdai PR #512, this "
              "query should flip to should_abstain=True, and that is the correct "
              "closed-RAG answer rather than a regression. Content gap, clinical lane.",
    ),
    QueryCase(
        query="what is mindfulness based cognitive therapy",
        expected_topic="MBCT",
        expected_source_prefix="mindfulness-",
        should_abstain=False,
        notes="No MBCT-specific article; mindfulness-001 at 0.594 (prod, exact scan).",
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
        expected_source_prefix=None,
        should_abstain=False,
        notes="The corpus carries no DBT article. Both the ANN and exact-scan arms "
              "return cbt-001 at 0.498 (prod, 2026-08-19) -- a related-modality "
              "passage, above the current 0.42 gate. Left as None rather than "
              "asserting abstain, because whether this SHOULD abstain depends on the "
              "threshold decision pending with cdai PR #512 and is not measured here.",
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
