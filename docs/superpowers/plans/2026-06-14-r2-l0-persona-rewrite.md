# R2 — L0 Persona Rewrite (engagement/UX) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Rewrite the always-included L0 persona so Sage's conversation is warmer, more
natural, and more engaging (the competitive bar is ChatGPT/Claude) **without weakening any
safety, clinical, or format guardrail.** R2 is the engagement layer's persona half — R1/R3/R5
are merged (PR #4); R2 is the remaining "R2 (L0 rewrite)" item.

**Architecture:** L0 is `prompts/templates/L0_persona.json` (currently v1.4.0,
`authored_by: sage_clinics`, `approved_by: null`, `role: system`, `always_include: true`,
word_budget 150), loaded by `composer._build_l0_system_block()` as the first of the 6 layers
(L0–L5) on every freeflow/skill turn. No code change is required to swap content — this is a
**template-content** change plus its validation harness.

**Ownership (critical):** the persona is **clinical-authored content**. Engineering does NOT
write the prose. Engineering provides the rewrite brief (from research), the behavioral A/B +
safety-regression harness, the governance wiring, and the integration. Clinical authors the
content and signs it off. This mirrors 05a (PMR) and the C1/B.2/B.3 content discipline.

**Tech stack:** JSON template; `composer.py`; pytest; an A/B persona-eval script.

---

## Inputs to read first
- `docs/superpowers/proposals/2026-06-12-engagement-layer-recommendations.md` (the engagement
  deep-research: follow-up style, warmth, matching user energy, offering options vs open
  questions, pacing; what ChatGPT/Claude/therapy-bots do; the engagement-vs-fidelity tradeoff).
- `docs/SageAI_architecture_current.md` §5.6 (6-layer composition, L0 always-included).
- Current `L0_persona.json` v1.4.0 (preserve its hard constraints — see below).

## Hard constraints the rewrite must PRESERVE (non-negotiable; these are regression gates)
- **Format rules:** plain prose; commas/short sentences not dashes (em dashes mirror into
  output — see [em-dash feedback]); no emojis; no markdown. These already live at the top of L0.
- **Safety/persona integrity:** must not weaken crisis dereferral, jailbreak/persona-override
  resistance, or scope boundaries. The persona sets tone but must never instruct around the
  deterministic safety layer.
- **No language-coercion bug:** must NOT re-introduce a "MUST respond in Arabic" style directive
  (the CU-DM-001 regression). Bilingual behavior stays as the L0 Arabic extension defines it.
- **Word budget / L1 interaction:** L0 word count feeds `_compute_l1_budget` headroom; a longer
  persona shrinks L1 history. Keep L0 within budget or adjust the budget deliberately, tested.

---

## File structure
- Modify: `src/sage_poc/prompts/templates/L0_persona.json` — new version (v2.0.0),
  `status: draft-pending-review`, `approved_by: null` until signed.
- Create: `scripts/persona_ab_eval.py` — runs a fixed turn-set through `freeflow_respond`
  composition with old vs new L0, captures both responses for scoring.
- Tests: `tests/test_persona_l0.py` (structural/constraint regression), extend safety/format
  regression coverage.
- No change expected in `composer.py` (it just loads the template) — confirm with a test.

---

## Clinical / scoring gates (BLOCKING)
- [ ] **G1 — rewrite brief:** engineering distills the research into a persona requirements brief
  (engagement behaviors to add: warmth, one focused follow-up, energy-matching, named-option
  offers, pacing) + the preserved constraints above. Clinical reviews the brief.
- [ ] **G2 — authored content:** clinical authors v2.0.0 prose (EN + the Arabic extension),
  honoring the format + safety constraints. Engineering integrates verbatim.
- [ ] **G3 — behavioral eval passes:** engagement dimensions improve on the A/B set AND the
  safety/format regression is clean (see Tasks 3–4). Two-rater scoring per the established
  human-scoring protocol (≥2 raters, calibrated) on the engagement deltas.
- [ ] **G4 — clinical sign-off:** `approved_by` set + status flipped from draft-pending-review.

---

## Task 1 — Versioned draft scaffold (no prose authored by engineering)
**Files:** `L0_persona.json`, `tests/test_persona_l0.py`
- [ ] Copy v1.4.0 → set `version: 2.0.0`, `status: draft-pending-review`, `approved_by: null`.
  Leave content as a clearly-marked placeholder for clinical authoring (do NOT ship engineering
  prose as the persona). Until G2, the production loader keeps v1.4.0.
- [ ] Test: `test_l0_persona_constraints` asserts the (authored) content contains the format
  guardrails (no `**`, no emoji, dash-avoidance instruction) and no "respond in Arabic"
  coercion string. Run → fails on the placeholder (expected until G2).

## Task 2 — Persona A/B eval harness
**Files:** `scripts/persona_ab_eval.py`
- [ ] Build a fixed representative turn-set (open chat, low/high intensity, side-topic, "I don't
  know — suggest something", a benign emotional disclosure). For each, compose the freeflow
  prompt with old L0 and with the candidate L0 and capture both model responses to a JSONL.
- [ ] Output is for human rating (G3) — the script does not self-score engagement.

## Task 3 — Safety + format regression (automated, must stay green)
**Files:** `tests/test_persona_l0.py`, reuse existing safety/format suites
- [ ] Run the curated safety-surface unit-gate + the format/style checks with the candidate L0
  active in a test fixture; assert crisis deferral, jailbreak resistance, and the format rules
  are unchanged. The persona rewrite must not move any safety/format assertion.

## Task 4 — Two-rater engagement scoring (human, gated)
- [ ] ≥2 calibrated raters score the A/B JSONL on the engagement dimensions (warmth, focused
  follow-up, energy-matching, optionality, naturalness) using BARS anchors. Record inter-rater
  agreement. Engagement must improve materially with safety/format held — else iterate G2.

## Task 5 — Sign-off + ship
- [ ] On G3 + G4: set `approved_by`, flip status, bump production to v2.0.0. Commit per the
  one-change-per-commit discipline. Monitor early transcripts post-deploy.

---

## Scope / priority note (do not let this blur the safety line)
R2 is **engagement**; it does **not** touch crisis detection and does **not** change the pilot
no-go. Per the 2026-06-14 lock pass + the re-pointed pilot gate, **pilot remains a no-go on the
crisis-recall floor (CRADLE 38% / self-harm 19.6%, S2 unbuilt, Arabic unmeasured)** regardless of
how good the persona becomes. R2 can proceed in parallel with the safety critical path (S2/MARBERT
#18, Arabic bench #21, PMR #16), but a better persona is not pilot-readiness — the crisis layer is.

## Self-review checks
- L0 prose is clinical-authored, never engineering-authored (ownership gate G2). ✔
- Every preserved constraint has a regression test (Task 3 + test_l0_persona_constraints). ✔
- Engagement improvement is human-scored ≥2 raters, not self-asserted (G3/Task 4). ✔
- Pilot no-go explicitly restated so R2 momentum doesn't carry a pilot decision. ✔
