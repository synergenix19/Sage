# P0b — `delivery_format` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** the executor honors a skill's `delivery_format` (skill-level default + presentation-keyed Rules-Service override), rendering `video`-format skills as a video handoff instead of a text wall. Flag-gated inert.

**Normative source:** `scratchpad/bot_behaviour_full.md` (the full docx re-extraction — the prior plaintext was table-stripped; see `governance/2026-07-17-bot-behaviour-source-integrity.md`). Design: `specs/2026-07-17-p0b-delivery-format-design.md`.

## Global Constraints
- **Enum (6 shipped, proposed-pending-ratification):** `video`, `visual_then_guided`, `guided_conversation`, `instructional`, `single_message`, `info_resource`. `visual` deferred (no library skill); `staged_iterative` pending the sharpened clinician call (expected collapse). NOT ratified — ships DRAFT like the CF rules.
- **Axis enforcement, both halves, structural:** `delivery_format` is executor-only; NO routing/skill_select/intent_route module may import it (a test asserts this). The override may read presentation→format; nothing may read format→routing.
- **Pair-level:** `delivery_format` is a `(presentation, skill)` property. Skill-level = default; Rules-Service override keyed by presentation (+ time-of-day for §S1b) supersedes. Executor consults override-first.
- **Flag `SAGE_DELIVERY_FORMAT`** (strict idiom, default OFF). OFF = byte-identical to today (executor renders as it does now).
- Enum ratification, per-skill values, the sharpened `staged_iterative` call, the 4 Format-less defaults, and DQ-1/DQ-2 all ride a LATER clinician touchpoint — NOT today's routing packet.

## Task 1: The founding red test (write it first, watch it fail)
**Files:** Test `tests/test_delivery_format.py`.
- [ ] **Step 1: Write the founding assertion — the one this whole thread opened with.** Full-graph (or executor-level, whichever the existing skill-render tests use), flag ON, `box_breathing` (`delivery_format = video`) selected: the delivered response is a **video handoff shape** (a short psychoeducation line → a video reference/link → a check-in), NOT the full text-wall step transcript. Assert on the SHAPE (presence of the video-handoff marker / absence of the full step-by-step body), not exact copy. This test is RED until Tasks 2-4 land — that is correct; it is the deliverable's definition of done.
- [ ] **Step 2: Run — expect FAIL** (executor ignores `delivery_format` today; box_breathing renders as text).
- [ ] Commit `test(p0b): founding red test — box_breathing renders as video handoff, not a text wall`.

## Task 2: Schema field + executor-only enforcement
**Files:** `src/sage_poc/skills/schema.py`; Create `src/sage_poc/skills/delivery_format.py` (the enum + executor-only home); Test `tests/test_delivery_format.py`, extend `tests/test_instructional_set.py`.
- [ ] Add `DeliveryFormat` enum (the 6 shipped values) in an executor-scoped module; add optional `delivery_format` to the `Skill` schema (default None → executor treats None as today's behavior).
- [ ] **Executor-only enforcement test:** assert no module under routing/`skill_select`/`intent_route` imports `delivery_format`/`DeliveryFormat` (grep-in-test or import-graph assertion). This makes the axis fusion unrepresentable.
- [ ] **Flip `instructional_set.py`'s convergence test** from `xfail` to enforcing: `INSTRUCTIONAL_SKILLS == {id for id,s in registry if s.delivery_format == "instructional"}` — now that the field exists, `{sleep_hygiene}` must equal it.
- [ ] Commit `feat(p0b): DeliveryFormat enum + executor-only field + convergence test enforced`.

## Task 3: The (presentation, skill) override seam (Rules Service)
**Files:** `src/sage_poc/rules/` (a `delivery_format_override` category, mirroring the existing category-conditional rule pattern); executor consult; Test.
- [ ] Rules-Service override keyed by presentation/category (data-authored, signed like other rules), with a time-of-day predicate available for §S1b. Ships EMPTY-but-wired (the launch consumers — worry_time/PST/S1b overrides — are data, ratified later; the SEAM is what Task 3 builds).
- [ ] Executor resolves: **override-for-(this presentation, time) FIRST, skill `delivery_format` SECOND, None → today's behavior.** Unit-test the resolution order.
- [ ] Override may read presentation context; a test asserts the override cannot influence routing (one-direction, both halves).
- [ ] Commit `feat(p0b): presentation-keyed delivery_format override seam (Rules Service)`.

## Task 4: Video renderer (makes the founding test green)
**Files:** the executor's render path; config flag; Test.
- [ ] Add `SAGE_DELIVERY_FORMAT` (strict idiom, default OFF). When OFF, the executor render path is byte-identical to today (OFF-byte-identical test).
- [ ] When ON and resolved format is `video`: render the video-handoff shape (psychoed line → video reference → check-in) instead of walking the full step body. The other 5 formats: `guided_conversation` = today's behavior (the common default, so most skills unchanged); `visual_then_guided`/`instructional`/`single_message`/`info_resource` render per their shape (video-first is the priority; the others can be minimal/pass-through in v1 with a comment, since the founding fix is video).
- [ ] **Task 1's founding red test now GREEN.** Regression: existing skill-executor/render tests green; `check_state_channels` clean.
- [ ] Commit `feat(p0b): executor honors delivery_format; video renders as handoff (founding fix)`.

## Task 5: Per-skill values (DRAFT, pending ratification) + the defaults
**Files:** the ~17 mapped skills' JSON (`delivery_format` from the grounding table); the 4 Format-less defaults; Test.
- [ ] Populate `delivery_format` on the cleanly-mapped skills per the grounding per-skill table (video: box_breathing, mindfulness_meditation, safe_place_visualization, PMR, body_scan→video; visual_then_guided: grounding_5_4_3_2_1, stop_technique, dbt_tipp, interpersonal_effectiveness, financial_anxiety; guided_conversation: assertive_communication, grief_loss, behavioral_activation, self_compassion_break, cognitive_restructuring, act_psychological_flexibility, values_clarification[pending staged_iterative]; instructional: sleep_hygiene; single_message: worry_time-default). Mark the file/block DRAFT/pending-ratification.
- [ ] The 4 Format-less skills (`cbt_thought_record`, `mi_readiness_ruler`, `psychoed_depression`, `psychoed_stress`) → default `guided_conversation`, flagged as blockers-with-defaults for the packet.
- [ ] Content-inferred mappings (cognitive_restructuring↔Fact-vs-Opinion, etc.) flagged in-comment for clinician confirmation.
- [ ] Commit `feat(p0b): per-skill delivery_format values (DRAFT, pending ratification)`.

## Post-tasks
- Final whole-branch review: OFF byte-identical; executor-only enforcement holds; convergence test enforcing; founding test green; override seam one-directional.
- Clinician packet (later touchpoint, NOT today's): ratify the 6 enum members, rule on `staged_iterative`, ratify the per-skill values + the 4 defaults, confirm the content-inferred mappings, answer DQ-1/DQ-2.
- Merge inert (flag OFF) per the inert-merge-policy (clinical-content change).
