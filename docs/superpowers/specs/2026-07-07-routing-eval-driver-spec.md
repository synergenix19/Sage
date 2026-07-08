# Spec — Real-Model Routing Driver (Track A) + its acceptance gate

**Status:** SPEC (the one design decision before code, per Phase 1 direction). **Owner:** engineering. **Blocks:** Task 5 (re-gate) and Task 12 (prod measurement) of `make-v2-semantic-routing-live.md`.

## Why this exists

`gate_runner`/`cross_validation` are abstract over routing (injected `routed_of`); the `routing_eval` fixtures carry **synthetic** scores (`fixtures.py:9`). No committed driver supplies a **real-model** `routed_of` over the bulk fixtures, and no `--target prod` path exists. This driver is that instrument — and because it produces **safety-relevant numbers**, it carries the same "authoritative but wrong" risk that disqualified a from-scratch scorer for Task 2. The mitigation is the acceptance gate below.

## Core principle — ONE scoring source of truth

The driver **does not score**. It supplies a faithful `routed_of(record: EvalRecord) -> str` (a `skill_id` or `ABSTAIN`) by running the **live routing decision** over `record.utterance`, and feeds it to the **existing** `gate_runner.compute_metrics_by_stratum` / `harm_gate`. Every scoring rule stays where it already lives:

| Rule | Definition (cite in driver header — do NOT reimplement) |
|---|---|
| routing-quality row filter | `gate_runner.py:48-49` — `held_out and not flag_bearing and case_kind not in _PATH_ASSERTION_KINDS` |
| blended/comorbid correctness | `gate_runner.py:52-55` — `acceptable_routes` membership else `expected_route` |
| recall / abstain denominators | `gate_runner.py:57-59` — non-blended single-answer cases only |
| per-stratum grouping | `gate_runner.py:82-94` — `held_out and not flag_bearing`, grouped by `(lang, stratum)` |
| harm gate | `gate_runner.py:107-120` — `harm_severity ∈ (critical, iatrogenic, safety_net)` must land on `_SAFE_TERMINALS` |

If a scoring rule ever needs to change, it changes in `gate_runner`, and both the driver and the signed gate move together. The driver reimplementing any of these is the failure mode this spec forbids.

## The `routed_of` contract — faithful to the live path

`routed_of(r)` must reproduce the **full live tier pipeline** for `r.utterance`, not a semantic-only shortcut, because the frozen comparator was measured on the full Tier-1+Tier-2 pipeline ("Tier-1 keyword caught 0" is an *observed outcome* on these fixtures, not a licence to skip Tier-1):

1. Compute `message_en` from `r.utterance` (EN fixtures: identity; the driver is EN-first — AR routing is the follow-up plan).
2. **Tier 1** — the live keyword match (`skill_select` keyword tier) over `target_presentations`.
3. **Tier 2** — the live bi-encoder scoring (`_ensure_semantic_ready` / max-over-anchors) → ranked `(skill_id, score)`, then **the live `_route_decision(ranked, lang, message_en)`** — NOT a reimplemented threshold. Flags-off = V1; flags-on (`SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1`) = V2 (adds the exemplar candidate set + cross-encoder rerank).
4. A `None`/no-route decision → return `ABSTAIN`; otherwise the chosen `skill_id`.

**Design decision (the point of this spec):** `routed_of` calls the **live `skill_select` decision functions** (reuse `_route_decision` and the live scoring helpers, e.g. via `_semantic_match_sync` for Tier 2 plus the live keyword tier), so the routing logic is shared with production. The driver wires tiers; it must not re-derive the routing *decision*. Any residual divergence is caught by the acceptance gate.

## THE ACCEPTANCE GATE (double duty)

**The driver is not trusted until, run flags-off on the same case set, it reproduces the frozen V1 comparator: `in_scope 144/217 (66%)`, `id_oos 25/71 (35%)`, `far_oos 36/36 (100%)`** (`2026-07-07-v1-comparator-frozen.md`).

- **Case set must match the measurement's**, including its decontamination: the 2026-06-24 run **excluded 5 provenance-shared cases**. The driver must run the *same* set (apply the same exclusion) — if the current bulk fixtures don't yield exactly `217/71/36` after exclusion, that mismatch is itself a **finding** (the fixture set drifted from the measurement), reported, not smoothed over.
- **Tolerance:** exact cell counts are the target. State a tolerance of **0 cases** on `far_oos` (36/36 is a ceiling) and **≤1 case** per cell on `in_scope`/`id_oos` only if a documented nondeterminism source (e.g. embedding tie-break) is identified and cited; otherwise exact. Do **not** widen tolerance to force a pass.
- **STOP-and-diagnose on miss:** a non-reproduction is one of two findings — (a) the driver's routing/wiring diverges from the live path, or (b) the canonical 2026-06-24 measurement had an **unstated condition** (a specific tree, a fixture subset, a preprocessing step). Both are real findings. Resolving (b) also **retroactively hardens link (i)** of the Task 2 bridge — the honestly-labeled soft link becomes independently corroborated by reproduction.

Only once the gate is green is any **flags-on V2 number** the driver produces trusted (Task 5), and only then does the V1→V2 delta mean anything.

## Scope discipline

- Lives in `src/sage_poc/routing_eval/` as **offline tooling**. Runs **fixtures only** — never live user data (PDPL: synthetic assets only).
- Increment 1 (**this spec's gate**): local, flags-off, reproduce 66/35/100.
- Increment 2: flags-on V2 numbers over the same fixtures → feeds Task 5.
- Increment 3 (**Task 12 instrument**): `--target prod` mode — route each fixture utterance through the **deployed prod endpoint** (or a prod-parity local run of the deployed tree) and score via the same `gate_runner`. `scripts/functional_multiturn_prod.py` may seed this (unverified). Built after Increment 1 is green.

## Out of scope / guardrails

- No AR routing (follow-up plan; AR fails closed to V1 per Task 6b).
- No scoring logic in the driver (see Core principle).
- The driver is a measurement instrument, not a gate author — it never changes `expected_route`, dispositions, or tolerances.
