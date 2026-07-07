import inspect
import sage_poc.nodes.output_gate as og
import sage_poc.state as state_mod
import sage_poc.nodes.freeflow_respond as fr


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
