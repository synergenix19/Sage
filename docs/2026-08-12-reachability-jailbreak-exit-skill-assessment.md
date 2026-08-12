# Reachability widening — in-branch assessment of `jailbreak` and `exit_skill`

- **date**: 2026-08-12
- **branch**: `fix/psychoed-resolver-reachability` (off master `9c762759`)
- **ticket**: `docs/superpowers/tickets/2026-08-06-psychoed-resolver-intent-reachability.md` (Ticket A)
- **ruling this assessment discharges**: 2026-08-11 (human) — "widen for `general_chat` +
  `scope_refusal`; ASSESS `jailbreak` and `exit_skill` in-branch, and report with evidence
  whether widening them is needed/safe — do NOT widen them without evidence either way"
- **verdict**: **DO NOT WIDEN.** Zero evidence of need; a real, unpriced behavioral cost on
  both labels. Not "no signal, so leave it" — the need question is answered NO by the run's
  own record, and the cost question is answered by a controlled experiment, below.

## 1. The question

The ruled fix widens transit to Node 4 (`skill_select`) for the two intent labels the
2026-08-05 flip-tier record observed intercepting the psychoed resolver. `_route_after_intent`
has two other labels that never reach Node 4 on their own:

| label | master destination | eligible for transit? |
|---|---|---|
| `jailbreak` | `output_gate` (persona reassertion terminal) | not widened — this assessment |
| `exit_skill` (no active skill) | `freeflow_respond` | not widened — this assessment |

## 2. Evidence for NEED: none, and the "none" is measured, not assumed

The flip-tier record's committed console log
(`docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log`) carries a per-row
`real_label` — the label the LIVE classifier assigned each of the 133 F1 doc-verbatim trigger
phrases. Mechanically parsed (same regex the taxonomy doc used, re-run 2026-08-12):

| scope | `info_request` | `general_chat` | `new_skill` | `scope_refusal` | `jailbreak` | `exit_skill` |
|---|---|---|---|---|---|---|
| all 133 F1 rows | 56 | 53 | 21 | 3 | **0** | **0** |
| the 52 MISS rows | 1 (Ticket B collision) | 48 | 0 | 3 | **0** | **0** |

Two readings, both load-bearing:

1. **Zero misses** under either label — the taxonomy's own finding, re-derived here.
2. **Zero occurrences at all**: on 133 doc-verbatim psychoeducation trigger phrases, the live
   classifier never once emitted `jailbreak` or `exit_skill`. This is the stronger statement.
   The absence is not "the misses happened to fall elsewhere"; the labels are not in this
   input class's live output distribution. `info_request` and `new_skill` (77 rows) already
   reach Node 4 on master via their own branches, so `general_chat` + `scope_refusal` (56
   rows) account for **100%** of the observed unreachable set.

Corollary worth recording: 53 rows classified `general_chat` but only 48 of them missed. The 5
that hit did so through the pre-existing narrow `general_chat → skill_select` redirects
(prepass hint, acute-intensity, monitoring). The ruled widening generalizes exactly that
existing move; it does not invent a new kind of edge.

## 3. Evidence for SAFETY: the experiment, and what it costs

The transit set was temporarily widened in-process to
`{general_chat, scope_refusal, jailbreak, exit_skill}` (session-scoped pytest plugin, no
committed code change) and the psychoed + routing + skill-select surface re-run:

```
tests/test_psychoed_fixtures_ci.py tests/test_psychoed_reachability.py tests/test_routing.py
tests/test_psychoed_graph.py tests/test_psychoed_skill_select.py tests/test_psychoed_gate.py
tests/test_psychoed_f5_flow.py tests/test_psychoed_flag_off.py tests/test_skill_select.py
tests/test_nodes.py
→ 2 failed, 837 passed, 3 skipped, 74 xfailed
```

The only two failures were this branch's own scope-boundary pins
(`test_labels_outside_the_ruled_scope_are_not_widened[jailbreak|exit_skill]`), which exist to
detect exactly this. Notably the **F4/F6/F8 nine-label gate sweep stayed green**, including the
`jailbreak` and `exit_skill` labels: no weave-precedence, never-proceed, or leak assertion
changes under the wider set. So the widening is not test-detectably unsafe.

Test-green is not the whole cost. The same trigger phrase, driven full-graph both ways:

| label | ruled (this branch) | if widened |
|---|---|---|
| `jailbreak` | `safety_check → intent_route → output_gate` — the persona-reassertion terminal answers the turn | `safety_check → intent_route → skill_select → knowledge_retrieve → freeflow_respond → output_gate` — **psychoed clinical content is served instead** |
| `exit_skill` | `→ freeflow_respond` — presence | `→ skill_select → knowledge_retrieve → …` — **a psychoeducation block is served in response to a turn asking to stop** |

Both are product/clinical decisions, not routing decisions:

- **`jailbreak`**: a deterministic content serve would pre-empt the persona-reassertion
  decision on an adversarial turn. Ticket A's mandate is that a doc-verbatim phrase must not be
  gated behind an LLM classification — it is not a mandate to let a trigger phrase override the
  adversarial-turn handler. Making a jailbreak-labeled turn answer with clinical content needs
  its own ruling, and would be a strange one to make on zero observed cases.
- **`exit_skill`**: serving a psychoeducation block into a disengagement turn is the same
  defect class `skill_select` already guards against elsewhere (psychoed absorption of an
  explicit request — the EMR surface-1 note in `skill_select.py`). Cost with no measured
  benefit.

## 4. Verdict and how it is held

**Not widened.** The scope boundary is pinned, not merely commented:
`tests/test_psychoed_reachability.py::test_labels_outside_the_ruled_scope_are_not_widened`
fails if a future edit adds either label to `graph._PSYCHOED_TRANSIT_INTENTS`. The pin's
message points back at this document, so the re-open path is "re-run this assessment", never a
silent re-pin.

**Re-open if** a future flip-tier run's per-row `real_label` distribution shows `jailbreak` or
`exit_skill` on trigger-phrase turns at any nonzero rate. That is the measurement that would
turn "no evidence of need" into evidence — and it is already produced by the existing runner,
so no new instrumentation is required to detect it.
