# Ticket: resolver's unconditional `_pick_block` produces a phantom block_id on `formal_diagnosis`, false integrity-gate mismatch + phantom block accounting

**Filed:** 2026-07-31 · **Source:** psychoed Phase 3, Task 8 (F10 diagnosis-split fixture family),
first-run characterization while authoring `F10-002` — surfaced by fixture authoring, independently
confirmed by reviewer with a live repro, human-ruled
**Status:** open — fix requires its own branch and normal review (touches the Node-8 integrity gate
and the resolver both); `F10-002` sidesteps the affected category (`1f`, not `3c`) rather than
exercising this path, so no fixture is xfailed against it — this ticket documents a REAL divergence
observed on `3c`/`3c-t5` during investigation, not asserted by any hard-gated row
**Type:** BUG, HIGH-2 class (same class as the already-fixed HIGH-2 finding: a menu-pick/route
whose serve composition doesn't embed a block the resolver nonetheless attached, causing
`output_gate`'s verbatim hash gate to false-positive)
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/task-8-report.md`,
`tests/fixtures/psychoed/f10_diagnosis.jsonl` (`F10-002`'s `source` field cites this ticket),
`tests/test_psychoed_gate.py` (HIGH-2's own menu-pick regression test, `test_menu_pick_end_to_end_
passes_gate_no_false_mismatch` — the precedent this bug repeats for a different route)

## The gap

`resolver.py:219`'s `_pick_block(row["category"], norm)` call is **unconditional** — it runs for
every resolver hit regardless of the matched row's `route` field (`"standard"`, `"direct_diagnostic"`,
`"formal_diagnosis"`). For an answer_first-delivery category (e.g. `3c`), `_pick_block` falls back to
the category's first manifest block when no menu-label match exists — so a `formal_diagnosis` hit
(e.g. `3c-t5`, "do I have depression") still receives a real `block_id` (`3c-b1`) in its `hit` dict,
even though `serve.py`'s `formal_diagnosis` branch (`serve.py` ~L35-36) NEVER reads or embeds that
`block_id` — it composes `framing_statement + diagnosis_guard_stage1` only.

That stale `block_id` still flows downstream into `psychoed_serve.block_id` (`skill_select.py`'s
payload construction) and from there into two independent, unrelated consumers that both assume
"a `psychoed_serve.block_id` means that block's content is genuinely in the response":

1. **`output_gate.py`'s verbatim hash gate** (~L949-996) checks
   `_block_content in final_response` using `psychoed_serve.block_id` alone. Since `3c-b1`'s content
   is never actually in the response, this evaluates false → the gate logs an ERROR-level
   `psychoed_integrity_incident kind=mismatch` and sets `psychoed_gate_action == "reserved"`,
   re-composing via `serve.compose_turn1` again (which produces the SAME, byte-correct text — no
   user-facing corruption, but the audit/incident trail is false on every single
   `formal_diagnosis` serve for this category shape).
2. **`knowledge_retrieve.py`'s outcome-1 fetch** (~L78-87) unconditionally appends `block_id` to
   `psychoed_blocks_served` and counts its family toward `psychoed_family_exposures` whenever
   `block_id` is truthy — regardless of whether `serve.py` actually used it. This pollutes both
   accounting channels with a block the user was never shown.

## Verification (live repro, before filing)

Full-graph, `PSYCHOED_PATHWAYS_ENABLED=true`, category `3c`, turn `"do I have depression"`
(`3c-t5`, route `formal_diagnosis`):

```
psychoed_serve: {'category': '3c', 'block_id': '3c-b1', 'route': 'formal_diagnosis',
                  'framing': 'personal', 'weave_due': True, 'matched_row_id': '3c-t5', ...}
response (full text): framing_statement + diagnosis_guard_stage1 + safety_weave_script
                       (block 3c-b1's own content is NOT present anywhere in it)
ERROR log: psychoed_integrity_incident kind=mismatch block_id=3c-b1
           recomputed_hash=506b4f... emitted_hash=93c5a1...
audit row: psychoed_gate_action == "reserved"
```

Confirmed via `sage_poc.psychoed.store.get_block("3c-b1")["content"] not in result["response"]`
(`True` — genuinely absent) alongside the mismatch log and `"reserved"` audit action.

**Scope note:** the SAME row type on category `1f` (`1f-t3`, menu_first delivery) does NOT reproduce
this: `_pick_block` returns `None` for a menu_first category on this trigger (no natural
answer_first fallback exists), so `psychoed_serve.block_id` is genuinely `None` there and
`output_gate`'s psychoed gate is a complete no-op (`if ... and _psychoed_block_id:` is false). This
is why `F10-002` uses `1f`, not `3c` — not to hide this bug, but because `1f` cleanly isolates the
guard mechanism this ticket's sibling fixture needs to test. This bug is category-shape-dependent
(answer_first + `formal_diagnosis` route), not universal.

## The fix (not here)

**Fix shape (either layer, or both, is a legitimate design choice — not decided here):**
- **Resolver-side:** `_pick_block` should not attach a `block_id` for routes that never consume one
  (`formal_diagnosis`, and by the same logic any future route with the same "composes without
  reading `block_id`" shape) — e.g. skip the call, or null it out, when `row["route"] ==
  "formal_diagnosis"`.
- **Or serve/downstream-side:** `output_gate`'s hash gate and `knowledge_retrieve`'s
  blocks-served/family-exposure accounting could instead consult `serve.compose_turn1`'s own
  `blocks_emitted` return value (already computed, already correctly empty for `formal_diagnosis` —
  see `serve.py`'s `blocks: list[str] = []` accumulator, never appended to on that branch) rather
  than trusting the payload's raw `block_id` field. This is closer to the "assert on behavior, not
  a field that may not reflect what actually happened" discipline this codebase otherwise follows.

Needs its own branch and normal review cycle — this touches the Node-8 integrity gate (a
safety-adjacent surface) and the resolver's core matching path.

**Definition of done includes a permanent regression case:** a `formal_diagnosis` serve on an
answer_first + weave-enabled category must produce `psychoed_gate_action == "pass"` (never
`"reserved"`) and `psychoed_blocks_served` must stay unchanged (never gain a phantom block) —
author this once the fix lands, most naturally as a `3c`/`3c-t5` sibling to `F10-002`.
