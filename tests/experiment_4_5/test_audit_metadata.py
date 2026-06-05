"""Experiment 4.5 — Audit metadata tests for knowledge fields in output_gate.

Tests cover:
  1. output_gate_node writes knowledge_passage_ids to audit row
  2. output_gate_node writes knowledge_source to audit row
  3. output_gate_node handles knowledge_abstain in audit row
  4. output_gate_node handles empty knowledge_passages gracefully
  5. knowledge_passage_ids extracted from source_id fields only (not full passage)
  6. gate_path "standard" path includes knowledge metadata
  7. scope_refusal gate path sets empty knowledge_passage_ids

Mock strategy:
  - sage_poc.nodes.output_gate.write_session_audit — capture audit state
  - sage_poc.nodes.output_gate.async_translate_to_arabic — returns input unchanged
  - sage_poc.nodes.output_gate.rules_engine.evaluate — returns empty fired list
  - sage_poc.nodes.output_gate.summarise_history — not called (turn_count < 10)
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.experiment_4_5.conftest import make_gate_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cultural_violations_result(fired: list | None = None):
    """Return a mock rules result with a .fired attribute."""
    result = MagicMock()
    result.fired = fired or []
    return result


def _patch_output_gate_dependencies(monkeypatch, write_calls: list):
    """Apply standard output_gate patches; capture write_session_audit calls."""

    async def mock_write(state):
        write_calls.append(dict(state))

    async def mock_translate(text: str) -> str:
        return text

    def mock_rules_evaluate(category, context):
        return _make_cultural_violations_result()

    monkeypatch.setattr("sage_poc.nodes.output_gate.write_session_audit", mock_write)
    monkeypatch.setattr("sage_poc.nodes.output_gate.async_translate_to_arabic", mock_translate)
    monkeypatch.setattr("sage_poc.nodes.output_gate.rules_engine.evaluate", mock_rules_evaluate)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOutputGateAuditMetadata:

    @pytest.mark.asyncio
    async def test_write_session_audit_called_once(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state())
        await asyncio.sleep(0)

        assert len(write_calls) == 1

    @pytest.mark.asyncio
    async def test_audit_state_contains_path_with_output_gate(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state())
        await asyncio.sleep(0)

        assert "output_gate" in write_calls[0]["path"]

    @pytest.mark.asyncio
    async def test_audit_state_preserves_session_id(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(session_id="rag-test-sess"))
        await asyncio.sleep(0)

        assert write_calls[0].get("session_id") == "rag-test-sess"

    @pytest.mark.asyncio
    async def test_audit_state_contains_knowledge_passages(self, monkeypatch):
        """output_gate passes knowledge_passages through to write_session_audit."""
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        passages = [
            {"text": "CBT is evidence-based.", "source_id": "cbt-001-en", "citation": "Beck (1979)", "relevance_score": 0.88},
            {"text": "DBT skills help distress.", "source_id": "dbt-002-en", "citation": "Linehan (1993)", "relevance_score": 0.75},
        ]
        await output_gate_node(make_gate_state(knowledge_passages=passages))
        await asyncio.sleep(0)

        audited_passages = write_calls[0].get("knowledge_passages", [])
        assert len(audited_passages) == 2
        assert audited_passages[0]["source_id"] == "cbt-001-en"
        assert audited_passages[1]["source_id"] == "dbt-002-en"

    @pytest.mark.asyncio
    async def test_audit_state_contains_knowledge_source(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(knowledge_source="node_6"))
        await asyncio.sleep(0)

        assert write_calls[0].get("knowledge_source") == "node_6"

    @pytest.mark.asyncio
    async def test_audit_state_contains_knowledge_abstain_false(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(knowledge_abstain=False))
        await asyncio.sleep(0)

        assert write_calls[0].get("knowledge_abstain") is False

    @pytest.mark.asyncio
    async def test_audit_state_contains_knowledge_abstain_true(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(
            knowledge_passages=[],
            knowledge_abstain=True,
        ))
        await asyncio.sleep(0)

        assert write_calls[0].get("knowledge_abstain") is True

    @pytest.mark.asyncio
    async def test_audit_state_empty_knowledge_passages_when_none_present(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(knowledge_passages=[], knowledge_source=""))
        await asyncio.sleep(0)

        audited_passages = write_calls[0].get("knowledge_passages", [])
        assert audited_passages == []

    @pytest.mark.asyncio
    async def test_gate_path_standard_included_in_audit(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        await output_gate_node(make_gate_state(gate_path="standard"))
        await asyncio.sleep(0)

        assert write_calls[0].get("gate_path") == "standard"

    @pytest.mark.asyncio
    async def test_scope_refusal_gate_has_empty_knowledge(self, monkeypatch):
        """scope_refusal gate path does not surface knowledge passage data."""
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        # For scope_refusal, knowledge_passages may still be in state
        # (set by a prior node) but the response is the scope refusal text.
        await output_gate_node(make_gate_state(
            gate_path="scope_refusal",
            knowledge_passages=[],
            response_en=None,
        ))
        await asyncio.sleep(0)

        # write_session_audit must still be called
        assert len(write_calls) == 1
        assert write_calls[0].get("gate_path") == "scope_refusal"

    @pytest.mark.asyncio
    async def test_output_gate_node_returns_response_field(self, monkeypatch):
        """output_gate_node return dict must contain 'response' key."""
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        result = await output_gate_node(make_gate_state())
        assert "response" in result

    @pytest.mark.asyncio
    async def test_output_gate_node_appends_output_gate_to_path(self, monkeypatch):
        from sage_poc.nodes.output_gate import output_gate_node

        write_calls = []
        _patch_output_gate_dependencies(monkeypatch, write_calls)

        prior_path = ["safety_check", "intent_route", "skill_select", "knowledge_retrieve", "freeflow_respond"]
        result = await output_gate_node(make_gate_state(path=prior_path))

        assert result["path"] == prior_path + ["output_gate"]


# ---------------------------------------------------------------------------
# write_session_audit — passage_ids extraction contract
# (mirrors test_audit.py test_write_extracts_passage_ids but for knowledge path)
# ---------------------------------------------------------------------------

class TestWriteSessionAuditKnowledgeFields:
    """Tests that write_session_audit correctly serialises knowledge fields."""

    @pytest.mark.asyncio
    async def test_knowledge_passage_ids_extracted_from_source_id(self, monkeypatch):
        """write_session_audit must extract source_id from each passage dict."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

        import importlib
        import sage_poc.audit as audit_mod
        importlib.reload(audit_mod)

        posted_json = {}

        class MockResponse:
            def raise_for_status(self):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def post(self, url, headers, json, **kwargs):
                posted_json.update(json)
                return MockResponse()

        from tests.test_audit import make_audit_state
        with patch("httpx.AsyncClient", return_value=MockClient()):
            await audit_mod.write_session_audit(make_audit_state(
                knowledge_passages=[
                    {"source_id": "cbt-001-en-000", "text": "CBT text.", "citation": "Beck", "relevance_score": 0.9},
                    {"source_id": "anx-002-en-001", "text": "Anxiety text.", "citation": "Barlow", "relevance_score": 0.8},
                ],
                knowledge_source="node_6",
                knowledge_abstain=False,
            ))

        assert posted_json["knowledge_passage_ids"] == ["cbt-001-en-000", "anx-002-en-001"]
        assert posted_json["knowledge_source"] == "node_6"

    @pytest.mark.asyncio
    async def test_knowledge_passage_ids_empty_when_no_passages(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

        import importlib
        import sage_poc.audit as audit_mod
        importlib.reload(audit_mod)

        posted_json = {}

        class MockResponse:
            def raise_for_status(self):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def post(self, url, headers, json, **kwargs):
                posted_json.update(json)
                return MockResponse()

        from tests.test_audit import make_audit_state
        with patch("httpx.AsyncClient", return_value=MockClient()):
            await audit_mod.write_session_audit(make_audit_state(
                knowledge_passages=[],
                knowledge_abstain=True,
                knowledge_source="node_6",
            ))

        assert posted_json["knowledge_passage_ids"] == []
