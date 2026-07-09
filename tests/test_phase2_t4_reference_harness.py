"""Phase-2 T4 pre-stage — the containment DOWNSTREAM wiring, proven against DUMMY content.

This harness exists so Vee's sign-off becomes a same-day staging run: the signed template bytes
and the ocd-001 article drop into a PROVEN pathway rather than the pathway being assembled after
her rulings. It is NOT building past the gate — the distinction is precise and enforced in code:
  - the flag stays UNDECLARED (no family declares skill_select_disposition 'contain' on master; T2
    dormant tests still hold),
  - the template bytes are an EMPTY placeholder, and _pin_containment_template REFUSES to serve an
    empty template (the load-bearing safety invariant: unsigned content cannot reach a user),
  - nothing here runs the model or a real DB; it proves the WIRING with a dummy directive + dummy
    content, which is exactly the part the signed content plugs into.

Upstream (flag -> containment_directive) is proven by test_phase2_t2/t3. Routing (directive ->
knowledge_retrieve) and AC-CRISIS-SUPREMACY are proven by test_phase2_t3. The LIVE probe set
(AC-SUGGEST-SKILL-OFF, AC-ESCALATION-BOUNDARY against the semantic layer, AC-RENDER) runs at
staging after sign-off — see 2026-07-10-t4-reference-content-drafts.md.
"""
import pytest

from sage_poc.nodes import output_gate as og
from sage_poc.nodes import knowledge_retrieve as kr

_REPLY = "That sounds really hard, and I'm glad you told me."
_DIRECTIVE = {"family": "dummy", "kb_topics": ["dummy_topic_a", "dummy_topic_b"], "rule_id": "dummy_contain"}


# ── Template pin: the unsigned-content safety invariant ───────────────────────────────
def test_pin_dormant_without_directive():
    assert og._pin_containment_template(_REPLY, None, "en") == _REPLY


def test_pin_unsigned_placeholder_never_serves():
    # THE load-bearing invariant: directive present but template is the empty UNSIGNED placeholder
    # -> reply is returned untouched. Serving unsigned clinical content is structurally impossible.
    assert og._CONTAINMENT_TEMPLATE_EN.strip() == "", "template must ship EMPTY (unsigned) on master"
    assert og._pin_containment_template(_REPLY, _DIRECTIVE, "en") == _REPLY


def test_pin_serves_verbatim_once_signed(monkeypatch):
    # simulate the signed bytes landing: the pin appends them verbatim on a containment turn.
    signed = "SIGNED TEMPLATE BYTES (dummy for the harness)."
    monkeypatch.setattr(og, "_CONTAINMENT_TEMPLATE_EN", signed)
    out = og._pin_containment_template(_REPLY, _DIRECTIVE, "en")
    assert out.endswith(signed) and _REPLY in out


def test_pin_idempotent_and_en_only(monkeypatch):
    signed = "SIGNED TEMPLATE BYTES (dummy)."
    monkeypatch.setattr(og, "_CONTAINMENT_TEMPLATE_EN", signed)
    once = og._pin_containment_template(_REPLY, _DIRECTIVE, "en")
    assert og._pin_containment_template(once, _DIRECTIVE, "en") == once, "must not double-append"
    assert og._pin_containment_template(_REPLY, _DIRECTIVE, "ar") == _REPLY, "EN only; AR on the AR track"


# ── knowledge_retrieve: containment seeds the family article by kb_topics, not the message ────
class _Result:
    passages: list = []
    abstain = False
    query_raw = "q"
    query_searched = "q"
    top_similarity = 0.5


@pytest.mark.asyncio
async def test_containment_seed_queries_kb_topics_not_message(monkeypatch):
    captured = {}

    class _Repo:
        def __init__(self, pool):
            pass

        async def retrieve(self, query, language, top_k):
            captured["query"] = query
            return _Result()

    monkeypatch.setattr(kr, "_get_pool", lambda: object())          # non-None pool
    monkeypatch.setattr(kr, "PostgresKnowledgeRepository", _Repo)
    state = {
        "containment_directive": _DIRECTIVE,
        "detected_language": "en",
        "message_en": "a random user message that must NOT drive retrieval",
        "raw_message": "random",
        "path": [],
    }
    await kr.knowledge_retrieve_node(state)
    assert captured["query"] == "dummy_topic_a dummy_topic_b", \
        "a containment turn must seed the family article by kb_topics, not the user message"


@pytest.mark.asyncio
async def test_ac_kb_failsafe_missing_pool_degrades_gracefully(monkeypatch):
    # AC-KB-FAILSAFE (unit slice): KB unavailable on a containment turn -> abstain, no broken block.
    monkeypatch.setattr(kr, "_get_pool", lambda: None)
    out = await kr.knowledge_retrieve_node({"containment_directive": _DIRECTIVE, "detected_language": "en", "path": []})
    assert out["knowledge_abstain"] is True and out["knowledge_passages"] == [], \
        "missing KB must fail safe (abstain, empty passages), never a dangling empty article block"


@pytest.mark.asyncio
async def test_non_containment_turn_unchanged(monkeypatch):
    # dormancy: no directive -> retrieval uses the user message exactly as before (byte-identical path)
    captured = {}

    class _Repo:
        def __init__(self, pool):
            pass

        async def retrieve(self, query, language, top_k):
            captured["query"] = query
            return _Result()

    monkeypatch.setattr(kr, "_get_pool", lambda: object())
    monkeypatch.setattr(kr, "PostgresKnowledgeRepository", _Repo)
    await kr.knowledge_retrieve_node({"detected_language": "en", "message_en": "what is CBT", "raw_message": "what is CBT", "path": []})
    assert captured["query"] == "what is CBT", "non-containment turn must be unchanged (dormant)"
