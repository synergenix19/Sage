# tests/test_psychoed_serve.py
from sage_poc.psychoed import serve, store

def test_menu_first_composition():
    out = serve.compose_turn1({"category": "1f", "block_id": None, "route": "standard",
                               "framing": "abstract", "weave_due": False})
    m = store.manifest("1f")
    assert out["text"] == m["framing_statement"] + "\n\n" + m["menu_offer"]
    assert out["menu_offered"] and not out["weave_asked"] and out["blocks_emitted"] == []

def test_answer_first_abstract():
    out = serve.compose_turn1({"category": "6d", "block_id": "6d-b1", "route": "standard",
                               "framing": "abstract", "weave_due": False})
    m = store.manifest("6d")
    b = store.get_block("6d-b1")["content"]
    assert out["text"] == m["framing_statement"] + "\n\n" + b + "\n\n" + m["menu_offer"]

def test_answer_first_personal_weave_stops_before_menu():
    out = serve.compose_turn1({"category": "3c", "block_id": "3c-b4", "route": "standard",
                               "framing": "personal", "weave_due": True})
    m = store.manifest("3c")
    assert out["text"].startswith(m["framing_statement"])
    assert store.get_block("3c-b4")["content"] in out["text"]
    assert store.shared_script("safety_weave_script") in out["text"]
    assert m["menu_offer"] not in out["text"]          # menu deferred behind the weave
    assert out["weave_asked"] and not out["menu_offered"]

def test_formal_diagnosis_serves_guard_script():
    out = serve.compose_turn1({"category": "3c", "block_id": None, "route": "formal_diagnosis",
                               "framing": "personal", "weave_due": False})
    assert store.shared_script("diagnosis_guard_stage1") in out["text"]
    assert out["blocks_emitted"] == []

def test_s2c_b8_block_guard_not_duplicated():
    out = serve.compose_turn1({"category": "s2c", "block_id": "s2c-b8", "route": "standard",
                               "framing": "abstract", "weave_due": False})
    note = store.get_block("s2c-b8")["psychoed"]["block_guard"]["note"]
    assert out["text"].count(note) == 1   # note is the block's own final sentence; never appended twice


# ─────────────────────────── HIGH-2 (final review): menu-pick serve ───────────────────────────

def test_menu_pick_serves_picked_block_no_framing_no_menu():
    """A 1f menu pick (block_id set, menu_pick True) must serve JUST that block's content plus
    the manifest check-in -- no framing repeat (already delivered on the turn that offered the
    menu) and no menu re-offer (the person already chose). This is the bug HIGH-2 fixes: before
    the fix, serve.compose_turn1 ignored block_id entirely for a menu_first category and always
    re-served the bare menu offer, even when a specific block had been picked."""
    out = serve.compose_turn1({"category": "1f", "block_id": "1f-b4", "route": "standard",
                               "framing": None, "weave_due": False, "menu_pick": True})
    m = store.manifest("1f")
    b = store.get_block("1f-b4")["content"]
    assert out["text"] == b + "\n\n" + m["check_in"]
    assert m["framing_statement"] not in out["text"]
    assert m["menu_offer"] not in out["text"]
    assert out["blocks_emitted"] == ["1f-b4"]
    assert not out["menu_offered"]
    assert not out["weave_asked"]


def test_menu_pick_serve_with_weave_due_asks_weave_not_check_in():
    """When a menu-pick serve ALSO carries weave_due (a personally-framed pick in a
    safety_weave category), the weave question replaces the check-in, same as the answer-first
    branch's weave-vs-menu-offer choice."""
    out = serve.compose_turn1({"category": "1f", "block_id": "1f-b4", "route": "standard",
                               "framing": None, "weave_due": True, "menu_pick": True})
    m = store.manifest("1f")
    b = store.get_block("1f-b4")["content"]
    assert out["text"] == b + "\n\n" + store.shared_script("safety_weave_script")
    assert m["check_in"] not in out["text"]
    assert out["weave_asked"] and not out["menu_offered"]


def test_turn1_menu_first_no_block_still_unchanged():
    """Regression guard: the ORIGINAL turn-1 menu-first composition (block_id None) must be
    byte-identical to before HIGH-2 -- is_menu_pick_serve requires a block_id, so this path is
    untouched."""
    out = serve.compose_turn1({"category": "1f", "block_id": None, "route": "standard",
                               "framing": "abstract", "weave_due": False})
    m = store.manifest("1f")
    assert out["text"] == m["framing_statement"] + "\n\n" + m["menu_offer"]
    assert out["menu_offered"] and not out["weave_asked"] and out["blocks_emitted"] == []
