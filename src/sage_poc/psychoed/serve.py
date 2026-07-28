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
    parts: list[str] = [man["framing_statement"]]
    blocks: list[str] = []
    weave_asked = False
    menu_offered = False

    if payload.get("route") == "formal_diagnosis":
        parts.append(store.shared_script("diagnosis_guard_stage1"))
    elif man["delivery_shape"] == "menu_first":
        parts.append(man["menu_offer"])
        menu_offered = True
    else:  # answer_first
        bid = payload["block_id"]
        block = store.get_block(bid)
        parts.append(block["content"])
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
