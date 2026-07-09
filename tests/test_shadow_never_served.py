import asyncio
import inspect
from unittest.mock import patch, AsyncMock
import sage_poc.nodes.output_gate as og
import sage_poc.state as state_mod
import sage_poc.nodes.freeflow_respond as fr
from tests.test_freeflow_respond import fr_stub_llm

_SENTINEL = "ZZZ_SHADOW_SENTINEL_ﷺ_NEVER_SERVE"


def test_output_gate_never_references_shadow():
    assert "shadow_arabic" not in inspect.getsource(og)


def test_shadow_is_not_a_sagestate_channel():
    # Containment by construction: shadow must never travel in durable state
    assert "shadow_arabic" not in getattr(state_mod.SageState, "__annotations__", {})


def test_freeflow_return_excludes_shadow_keys():
    # freeflow_respond_node must not return any shadow_* key into state
    src = inspect.getsource(fr.freeflow_respond_node)
    # the node writes shadow to the eval table, never returns it
    assert "\"shadow_arabic\"" not in src and "'shadow_arabic'" not in src


def test_sentinel_never_in_served_response(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": _SENTINEL, "prompt_hash": "x"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 3}
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=AsyncMock()):
        out = asyncio.run(fr.freeflow_respond_node(
            {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired",
             "path": [], "user_id": None, "session_id": "s1", "turn_number": 1},
            llm=fr_stub_llm()))
    assert _SENTINEL not in str(out)                         # not in node result / state
    assert out.get("response_en") and _SENTINEL not in out["response_en"]
