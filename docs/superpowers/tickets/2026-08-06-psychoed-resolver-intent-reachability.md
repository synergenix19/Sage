# Ticket (HIGH): the psychoed resolver's own "never conditional on the router" guarantee is violated one node upstream — transit to skill_select is conditional on intent_route

**Filed:** 2026-08-06 · **Source:** Psychoeducation Phase 3, human adjudication of the
2026-08-05 flip-tier record (`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md`), F1
wiring's 81/133 taxonomized per-row against the run's own console log
(`docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md`) — 51 of 52 misses are one
mechanism, not fixture noise, not annotation
**Status:** open — **BLOCKS per-category Phase-4 flips** until resolved (fix direction
below is directional, not a plan; implementation rides its own branch + normal review)
**Type:** BUG, HIGH — spec §2.1 topology violation, not a CI-tier artifact
**Links:** `docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md` (full 52-row
classification), `docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` (the record this
finding explains), `docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log`
(committed raw evidence, per-row `real_label`), `docs/superpowers/specs/
2026-07-23-psychoeducation-pathways-design.md` §2.1 (violated principle) and §10 entry 16
(register retraction + honest restatement)

## The design principle this violates

Spec §2.1 (`docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md`, "The
psychoed category resolver — Node 4 (`skill_select`)"), quoted verbatim:

> The resolver lives in Node 4, the node v7 designates for deterministic phrase matching
> (Rules Service: "keyword patterns mapping phrases to pathways", rules-first). It runs the
> §0 trigger match **on the raw turn, regardless of `primary_intent`** — deterministic
> recognition is never conditional on the probabilistic router (placing it downstream of
> intent_route would make the trigger tables' reachability conditional on an LLM
> classification: the §5-drift class one node upstream).

This is the Section-1 correction the design fought to establish: a doc-verbatim trigger
phrase must be recognized deterministically, never gated behind an LLM's classification of
the turn.

## The violation

**The principle holds INSIDE Node 4 and is violated ONE NODE UPSTREAM of it.** The resolver
itself runs unconditionally once `skill_select` executes — nothing inside Node 4 consults
`primary_intent` before running the §0 trigger match, exactly as designed. But **transit TO
Node 4 is conditional on `intent_route`'s classification**: `_route_after_intent` sends
`general_chat` and `scope_refusal` turns to `freeflow_respond` / the scope-refusal handler
directly, never to `skill_select`. A turn the live classifier labels either way never reaches
the node the trigger tables live in — the resolver's own "regardless of `primary_intent`"
guarantee is true of a node the turn was never routed to.

This is **exactly the §5-drift class the design doc names in its own §2.1 rationale** —
"placing it downstream of intent_route would make the trigger tables' reachability
conditional on an LLM classification" — realized one node upstream of where the design
doc's own words describe it. The doc correctly guarded against the resolver itself reading
`primary_intent`; it did not (and could not, from inside Node 4) guard against the graph
edge that decides whether Node 4 runs at all.

## Evidence

`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` — full-graph `app.ainvoke`, REAL
`intent_route` + REAL LLM, no node patches, flag parity verified — reports F1 wiring
81/133 (vs. 133/133 at CI tier, where `intent_route` is mocked/pinned per fixture row).
`docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md` taxonomizes all 52 misses directly
from the run's own console log (`docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log`,
committed verbatim, per-row `real_label` visible):

| class | count | mechanism |
|---|---|---|
| `intent_interception_general_chat` | 48 | live classifier labels the turn `general_chat`; `skill_select` never runs |
| `intent_interception_scope_refusal` | 3 | live classifier labels the turn `scope_refusal`; `skill_select` never runs |
| `cross_category_collision` | 1 | different bug, Ticket B — resolver DID run, matched the wrong row |
| **crisis-precedence-involved** | **0** | — |

**51/133 doc-verbatim trigger phrases are invisible to the trigger tables in the real
graph** — not because the phrases or the resolver are wrong, but because the classifier
that decides whether the turn ever reaches Node 4 disagrees with the CI-tier pinned intent
on which of the nine labels the turn carries. Zero of the 52 misses involve crisis, high-risk,
or medical precedence firing ahead of the resolver — the "by-design precedence" reading a
pre-written taxonomy category assumed some misses would fall under was checked against
every row and found to explain none of them (see §10 entry 16, the retraction this finding
forced).

## Why this is a spec conformance violation, not an annotation matter

The human ruling that opened this task was explicit: this is a **spec conformance
violation**, not a question of how the flip-tier record's numbers should be annotated or
footnoted. The §2.1 guarantee is about where in the graph deterministic recognition is
allowed to be gated — the guarantee is false today for every turn the live classifier
sends to `general_chat` or `scope_refusal`, regardless of how the resulting numbers are
described in a report.

## Fix direction (own branch, NOT this plan)

The trigger match must run at a topologically unconditional point for non-crisis turns —
options, not a decision made here:

1. **Route all such turns through `skill_select`.** Change `_route_after_intent` so
   `general_chat` and `scope_refusal` (and any other label that currently bypasses Node 4)
   transit through `skill_select` before falling through to their current handlers — the
   resolver's existing "no hit → existing behavior unchanged" fallthrough (spec §2.1 step 5)
   already describes what happens when nothing matches, so a widened transit set costs
   nothing on the no-hit path.
2. **Hoist the match.** Run the §0 trigger match (or a cheap prefilter for it) at a point
   upstream of `intent_route`'s branching, so a doc-verbatim phrase is recognized before
   any classification decides the turn's fate, with the resolved category threaded into
   whichever node ultimately composes the turn.

**Crisis precedence must be explicitly preserved above whichever fix ships** — nothing in
this ticket proposes touching the safety-route topology (spec §2.3: "Psychoed is the
lowest-precedence pathway in the graph — nothing in the serve branch can pre-empt a safety
route, by topology rather than by rule"). The taxonomy already confirms zero crisis
involvement in the current miss set; a fix that widened Node 4 transit must not change
that.

**Accepting reduced reach instead of fixing this is a ruled-design deviation**, not a
default outcome — it requires a register entry (spec §10, Absolute Rule 1) and clinical
sign-off, exactly as any other named departure from the design doc does. This ticket does
not pre-judge that call; it names the finding and blocks the flip until someone makes it.

## Status

**Open. BLOCKS per-category Phase-4 flips** (spec §7.3's flip preconditions) until this
resolves — either by the topology fix landing, or by an explicit, signed deviation
accepting reduced reach for the affected intent labels. See spec §10 entry 16 for the
register text carrying this forward and the honest restatement of what the 81/133 number
means until it does.
