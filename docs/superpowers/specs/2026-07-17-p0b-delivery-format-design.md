# P0b — `delivery_format` — Design Spec

**Status:** drafting (user directive 2026-07-17). Branch `cdai/p0b-delivery-format` off master@ccdcffc6. **Normative source:** `scratchpad/bot_behaviour_full.md` (full docx re-extraction; the prior plaintext was table-stripped — see `docs/superpowers/governance/2026-07-17-bot-behaviour-source-integrity.md`). **Shape (same as HR/psychoed): build the mechanism inert now; the clinical values ride a signature.** The enum members are the clinician's to ratify at a later touchpoint — NOT today's routing packet.

## Why this exists
The thread's origin complaint: Box Breathing (`Format: Video`) delivered as a wall of text. The doc's Format column tells the renderer *how* to present a chosen skill; the code never reads it. P0b makes `delivery_format` a first-class field the executor honors.

## The field's true semantics (Ruling 2 — this reframes the schema)
`worry_time` and `problem_solving_therapy` carry **different Format values depending on which category invokes them** (worry_time: `Described in one message` §1d vs `Guided conversation` §S1a; PST: `Visual + guided conversation` §1e/§2a/§S3a vs `Guided conversation` §1d/§S5a). Plus §S1b's time-of-day override. **Therefore `delivery_format` is not a property of the skill — it is a property of the (presentation, skill) pair.** The doc has said so all along: Format is a *column in per-category tables*, not a skill-registry attribute. We flattened it because most skills happen to be format-constant.

**The honest schema:**
- **Skill-level `delivery_format`** = the DEFAULT (the degenerate case of the pair-level truth, and the correct value for the ~24 format-constant skills).
- **A Rules-Service override**, keyed by presentation/category (and, for §S1b, time-of-day), that supersedes the default. **Load-bearing from day one** — `worry_time` and PST need it at launch, not when S1b lands; three launch consumers, not one.
- The override lives in the **Rules Service**, where category-conditional logic already lives (cultural rules, step_policy) — not a new mechanism (v7-aligned).
- **Executor consults: override-for-this-(category, time) FIRST, skill default SECOND.** Both clinician-authored, both signed, same governance.

## Axis enforcement — both halves, structural (extends the psychoed incident's ruling)
- Nothing at **routing / node-4 altitude** may read `delivery_format` to select a skill. (Disposition = `target_presentations`, node-4; delivery = `delivery_format`, node-5. Neither in the other's decision.)
- The **override rules MAY read presentation context to select a format**, but MUST NOT read a format to select a skill or route.
- Enforce structurally: `delivery_format` lives in an executor-only module; a test asserts no routing/skill_select module imports it; the `instructional_set.py` convergence test flips `xfail → enforcing` the day the field lands.

---

## THE NORMALIZATION DRAFT (centerpiece — engineering proposes, clinician disposes)
16 verbatim Format cells → a proposed canonical enum. Each **collapse** carries its justification + reversal cost; each **preserved distinction** carries its behavioral consumer; **non-goals** and **disposition-leaks** are pulled OUT of the enum entirely. She confirms each, or names a difference we can't see.

### Proposed canonical enum (7 members)
| enum value | raw Format cells it absorbs | executor consumer (the behavioral consequence) | collapse / preserve call |
|---|---|---|---|
| `video` | `Video` (8); `Video/audio guided` (Body Scan, 1) | play a video, no turn-by-turn text wall | **Collapse** `Video/audio guided`→`video`. **Lost:** an audio-only rendering hint (eyes-closed body scan). **Reversal cost: cheap** (one enum member + a renderer branch, no data migration) → recommend confidently, flag the audio hint for her. |
| `visual_then_guided` | `Visual + guided conversation` (9); `Show visual, then guided conversation` (Worry Tree, 1); `Visual + guided conversation, single instruction, no counting` (Extended Exhale, 1) | show an image/artifact, THEN converse through it | **Collapse** the Worry-Tree and Extended-Exhale variants in — same behavior ("show artifact, then guide"); the "single instruction, no counting" clause is per-skill *presentation prose*, not a format. **Verbatim variants attached for her to confirm synonyms.** |
| `guided_conversation` | `Guided conversation` (20) | pure conversational walkthrough, no media | dominant value; clean. |
| `instructional` | `Instructional` (sleep_hygiene, 1) | bot-led multi-step content walkthrough | preserve — distinct delivery (confirmed = exactly 1 skill; this is the value the `instructional_set.py` convergence test enforces). |
| `single_message` | `Described in one message` (worry_time §1d, 1) | deliver in one message, no multi-turn stepping | preserve — but this is worry_time's §1d value; §S1a says `guided_conversation` → **the pair-level override case**, not a skill-constant. |
| `info_resource` | `Info` (1); `Info — see timing note` (sleep-001, 1) | hand over a factsheet/article as a resource | **Collapse** the two genuine resource cells. The `see timing note` one carries the §S1b time-of-day conditional → the **override seam**, not a distinct format. |
| `staged_iterative` *(flagged — preserve-or-collapse is HER call)* | `Show all domains, then guided completion one at a time` (Life Compass, 1) | show a multi-part artifact, then complete each part iteratively | **Preserve-candidate:** behaviorally distinct from `visual_then_guided` (iterative multi-domain vs one-artifact-then-converse) IF the renderer walks domains one-at-a-time. **If it doesn't, this is a dormant distinction → collapse to `visual_then_guided`.** Needs her ruling + a renderer decision. |

### Pulled OUT of the enum (NOT delivery formats)
- **Disposition-leaks (routing targets in the Format column):** `Give options from 1f` (×2), `Info (6d)` — these name a *routing destination* (go to the 1f/6d menu), i.e. disposition, not delivery. The axis error again, in the doc's own column. They do NOT become `delivery_format` values; the skills they attach to route by `target_presentations`.
- **Non-goal — skill-chain:** `Video, then visual + guided conversation` (§1e, Box Breathing→Worry Tree). This is TWO skills sequenced, each keeping its own format (video; visual_then_guided). Not one mixed-format skill. **Deferred representation** — modeled only when a *second* chain appears (trigger condition), per the original P0b deferred-extension pattern.
- **Non-goal — format-OR:** `Video / guided conversation` (§S5a, PMR-OR-BA). A branch selection resolving to ONE static format at offer time (PMR=video, BA=guided_conversation). Not a single mixed/uncertain format. **Deferred representation** — modeled when a *second* format-OR appears.

### `bare Visual` (Emotions Wheel) — flagged, likely collapse
`Visual` (bare, 1) preserved as a distinct value ONLY IF the Emotions Wheel is *show-and-stop* (no guided follow-up). If it's shown then discussed (the likely reading), it collapses to `visual_then_guided`. **A distinction with no behavioral consumer is a dormant field** — surfaced for her: is the wheel presented without a conversation?

---

## The gaps (Ruling 3 — split by kind)
- **4 skill_ids with no doc Format cell → clinician blockers-with-defaults (P0b's data):** `cbt_thought_record`, `mi_readiness_ruler` (real gaps — propose the format their structure implies: both are stepped guided exercises → default `guided_conversation`, she ratifies/amends). `psychoed_depression`/`psychoed_stress` (no table exists for those answer-first categories — expected; default `guided_conversation` or `info_resource` per her call). (`post_crisis_check_in`, `psychotic_referral` are protocol steps, not offered skills — not gaps.)
- **10 doc pathways with no skill_id → a routed FINDING, not a P0b blocker:** Worry Tree, Extended Exhale, Emotions Wheel, Guided Reflection, Personal Wins Log, Assertiveness Psychoed, Kind Self-Talk, Myths vs Facts, Handling-Setbacks Guide, sleep-001. This is the §7c/§4a class writ large — **doc-library coverage gap**, routed to the same content conversation. **P0b ships against the library that exists**; this list is the library's roadmap, not the schema's dependency.

## v7 / architecture alignment
- Override in the **Rules Service** (category-conditional logic's existing home) — no new conditional mechanism.
- `delivery_format` is **executor-only (node 5)**; disposition (`target_presentations`) stays node-4. Orthogonal, structurally enforced (the ticket `2026-07-17-disposition-delivery-orthogonal-axes.md`).
- Additive schema field; `intent_route`/`skill_select` untouched.

## Governance
- Additive schema field → schema-owner sign-off; the enum members + the per-skill values + the override rules ride `signed_clinical_fields.json` and both validators (CMS form + skill-JSON). **Enum ratification = a later clinician touchpoint, NOT today's routing packet** (don't retro-stuff it). The blockers-with-defaults (4 Format-less skills) + the `staged_iterative`/`bare Visual` calls ride that same touchpoint.

## Build (inert)
Behind `SAGE_DELIVERY_FORMAT` (default OFF, byte-identical when OFF). Schema field + the (presentation, skill) override seam + the executor consult (override-first) + the executor-only enforcement test. **The renderer honors it for the `video`-class skills FIRST** — the literal fix for Box-Breathing-as-text-wall. Per-skill values ship as proposed-pending-ratification (like the CF rules / HR pools). The plan sequences: schema+enforcement → override seam → executor consult → video renderer.
