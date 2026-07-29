"""Deterministic turn-1 psychoed composition (spec §4.1). No LLM. All copy from
the store. Weave turn-boundary rule: when the weave fires, the menu is deferred
to the following turn, contingent on a clear-negative (PSY-WEAVE-1)."""
from __future__ import annotations
import json
from pathlib import Path
from sage_poc.psychoed import store

_TPL = json.loads(
    (Path(__file__).resolve().parents[3] / "data" / "psychoed" / "serve_templates.en.json").read_text()
)

def compose_turn1(payload: dict) -> dict:
    cat = payload["category"]
    man = store.manifest(cat)
    join = _TPL["join"]
    blocks: list[str] = []
    weave_asked = False
    menu_offered = False

    bid = payload.get("block_id")
    # HIGH-2 (final review): a menu picked off an already-offered menu carries a block_id even
    # though the CATEGORY's delivery_shape stays "menu_first" (that field describes the
    # category's turn-1 shape, not this reply's shape) -- resolver.resolve's active_category
    # branch sets menu_pick=True for exactly this case. Also true whenever a block_id is present
    # on a menu_first category regardless of the menu_pick flag (a menu_first category never
    # legitimately serves a block on any OTHER path, so a block_id there always means "the person
    # picked a topic"). Either signal means "serve the picked block, not the menu again": spec
    # §1f close -- serve topic then check-in, with NO framing repeat (the framing already ran on
    # the turn that offered the menu) and NO menu re-offer (the person already chose).
    is_menu_pick_serve = bid is not None and (
        payload.get("menu_pick") or man["delivery_shape"] == "menu_first"
    )

    if payload.get("route") == "formal_diagnosis":
        parts: list[str] = [man["framing_statement"], store.shared_script("diagnosis_guard_stage1")]
    elif is_menu_pick_serve:
        block = store.get_block(bid)
        parts = [block["content"]]
        blocks.append(bid)
        guard = block["psychoed"].get("block_guard")
        if guard and guard["note"] not in block["content"]:
            parts.append(guard["note"])   # single-sourcing: only if not already the final sentence
        if payload.get("weave_due"):
            parts.append(store.shared_script("safety_weave_script"))
            weave_asked = True
        else:
            parts.append(man["check_in"])  # serve topic then check-in -- no menu re-offer
    elif man["delivery_shape"] == "menu_first":
        parts = [man["framing_statement"], man["menu_offer"]]
        menu_offered = True
    else:  # answer_first
        block = store.get_block(bid)
        parts = [man["framing_statement"], block["content"]]
        blocks.append(bid)
        guard = block["psychoed"].get("block_guard")
        if guard and guard["note"] not in block["content"]:
            parts.append(guard["note"])   # single-sourcing: only if not already the final sentence
        if payload.get("weave_due"):
            parts.append(store.shared_script("safety_weave_script"))
            weave_asked = True            # menu deferred (spec §4.1)
        else:
            parts.append(man["menu_offer"])
            menu_offered = True

    if payload.get("weave_due") and payload.get("route") == "formal_diagnosis" and not weave_asked:
        parts.append(store.shared_script("safety_weave_script"))
        weave_asked = True

    return {"text": join.join(parts), "blocks_emitted": blocks, "weave_asked": weave_asked,
            "menu_offered": menu_offered, "template_version": _TPL["version"]}
