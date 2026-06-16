# Freeflow Opener Verification (#2) + Advice-After-Validation Draft (#3) — Probe Evidence

Date: 2026-06-16
Author: engineering (work session)
Status: EVIDENCE PACKAGE — #3 draft requires clinical sign-off before activation. Nothing shipped to production.

## What this is
A Phase-B probe against the REAL production responder (gpt-4o via OpenRouter, temp 0.7,
the live `_LLM_CONFIGS["responder"]`). It runs the actual `compose_prompt` path; the only
swap between arms is the L2 `general_chat` template.

- **Baseline arm:** live `general_chat.json` v1.5.0 (clinical-approved 2026-06-14).
- **Draft arm:** `general_chat_advicefirst.json` v0.1.0-draft (NOT wired into `compose_prompt`'s
  live variant selection; injected only inside the probe via a monkeypatch on
  `get_intent_template`). Zero production code changed.

Sample: 22 stratified counsel-chat questions (one per topic) + 6 crafted heavy-disclosure
messages = 28 core pairs, plus a 3-item × {2,5,8}-intensity sweep. Scoring is deterministic
(regex heuristics); raw replies saved to `tests/fixtures/counsel_chat/openers_probe_results.json`.
Reproduce: `scripts/probe_freeflow_openers.py`.

Caveats: small n (directional, not powered); single-turn English; the `substance_first`
heuristic is noisy (over-counts) and the `robotic_opener` heuristic UNDER-counts (misses
"It sounds really…" variants), so the true robotic-opener rate is higher than reported.

## Finding #2 — the v1.5.0 substance-first opener fix is NOT landing in behavior

CORRECTED 2026-06-16 with the comprehensive reflective-opener detector
(`scripts/rescore_openers.py`, re-scored from saved replies, $0). The first-pass
detector under-counted: it missed 18 distinct reflective openers, whole families like
"It's understandable to feel…" (×7) and "It sounds really/frustrating…".

| metric (n=28) | baseline | draft |
|---|---|---|
| reflective opener (leads with feeling-reflection / normalization / stock empathy) | **78.6%** | 67.9% |
| substance-first opener (names the specific thing) | 21.4% | 28.6% |
| opens with a question | 0.0% | 0.0% |

PRODUCTION RELEVANCE: the probe ran on gpt-4o. Per the 2026-06-16 product steer
("most likely GPT only in production"), this is now a near-direct production measurement,
not a POC proxy — the finding is first-class. (If the responder ever changes, the Tier-1
deterministic gate below is model-independent and still holds.)

The v1.5.0 file note says its effect is "non-deterministic … gated post-deploy re-probe
required before considering verified." **This is that re-probe, and it fails:** despite L0
("warmth comes from substance, not stock pleasantries") and the high-intensity guidance
("Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener"), gpt-4o opens
reflectively the majority of the time. Verified by eyeballing — these are genuine forbidden
openers, e.g. baseline: "It sounds like you're feeling unheard…", "I'm so sorry to hear that
you've been through such painful experiences", "That sounds really tough".

This is the report's #1 named UX failure ("generic/superficial/robotic"; the primary failure
of Replika/Wysa). It is a model-adherence problem, not a wording problem — the L2 swap does
not fix it (it lives in L0/intensity_guidance, shared by both arms).

### CORRECTION (2026-06-16): a Tier-1 gate ALREADY EXISTS — the issue is coverage + mechanism
The 78.6% above is RAW generation; the probe called the responder directly and BYPASSED
output_gate. output_gate already has `_BANNED_OPENER_RE` + a regenerate-on-detect retry
(added 2026-06-14, docs/superpowers/audits/2026-06-14-stock-opener-rca.md). Measuring the
saved raw generations against the LIVE regex (`scripts/rescore_openers.py` import of
`_BANNED_OPENER_RE`):

| of 28 raw baseline generations | share |
|---|---|
| reflective AND caught by current gate (→ regenerate) | **53%** |
| reflective AND LEAKED past the gate (reaches user) | **25%** |
| non-reflective / substance-first (clean) | 21% |

So the live gate catches ~2/3 of reflective openers; ~25% leak due to PATTERN GAPS, not a
missing mechanism. Leaked families (high-precision, anchored-`^`, safe to add):
- `it sounds (really|very|...)?ADJ` — the regex has `it sounds like` and `that sounds ADJ`
  but not `it sounds ADJ` ("It sounds really challenging/difficult", "It sounds frustrating").
- `it'?s (completely )?(understandable|normal|natural) to feel/that` — not covered at all (7 hits).
- `that sounds like a ...` — the `that sounds` branch requires an adjective from a fixed list,
  so "like a tough cycle / frightening experience" slips through; also "distressing" missing.

Remedy decision (see response): (1) EXPAND `_BANNED_OPENER_PATTERNS` to close the 25% leak —
small, mirrors the existing pattern, uses the now-calibrated detector; vs/and (2) switch the
MECHANISM from regenerate→reshape (your RCA preference for latency/auditability) — justified
because a high model re-offend prior (78.6%) means regenerate often fails twice and hits the
bland `_VETTED_FALLBACK_RESPONSE`, so expanding regenerate patterns alone risks MORE bland
fallbacks. Reshape fixes in-place. Caveat (your flag): reshape must not strip needed
validation under acute distress.
Tier-2 (probabilistic base-rate) and Tier-3 (model A/B) unchanged; under GPT-only production
the gate is the primary guarantee.

## Finding #3 — the advice-after-validation draft works as designed

| metric (n=28) | baseline | draft |
|---|---|---|
| reply contains a concrete suggestion | 42.9% | **60.7%** |
| advice arrives AFTER validation (not opening cold) | 42.9% | 60.7% |
| reply ends with a question | **85.7%** | **10.7%** |
| median words | 60 | 82 |

- All advice in both arms is post-validation (has_advice == advice_after_validation) — the
  validate-before-inform invariant is preserved.
- The draft roughly halves "no concrete help" and collapses the interview feel: baseline ends
  **86%** of replies on a question; the draft, 11%. The L0 length sign-off is respected
  (median 82 words, well under the therapist ~136-word median; a single suggestion, not a list).

### Acute-distress exception HOLDS (the safety-adjacent invariant)

| intensity | has_advice baseline → draft |
|---|---|
| acute subset i≥7 (n=3, core) | 0% → **0%** |
| sweep i=8 (n=3) | 33% → **33%** (no increase from draft) |
| sweep i=5 | 33% → 67% |
| sweep i=2 | 0% → 33% |

The draft increases advice at low/mid intensity only; at acute it adds none. Worked example
(i=8, "I just found out my dad has cancer and I can't stop shaking"): both arms validate +
ask one gentle question, no advice. The draft defers to the existing high-intensity
`intensity_guidance` ("Do NOT offer guidance yet").

### Worked example (i=5, marriage)
- **Baseline:** "It sounds like you're feeling unheard… One approach could be… **How does that
  sound to you?**" (robotic opener + trailing question)
- **Draft:** "It sounds frustrating to feel like you're not being heard. One approach could be
  to choose a calm moment… A direct, gentle conversation can sometimes open up space for
  change." (concrete suggestion, no trailing question; opener still reflective — see #2)

## For the clinical reviewer (#3 sign-off)
1. Confirm "one concrete suggestion after validation, unless acute" is acceptable as the
   DEFAULT non-acute posture (vs current advice-on-explicit-delegation only).
2. Confirm the acute exception wording defers correctly to `intensity_guidance` and that the
   no-trailing-question rule does NOT suppress the gentle safety question on acute turns
   (sweep i=8 showed ends_q 100%→33% — verify acute replies still ask one gentle question; the
   core dad-cancer example did).
3. The draft only governs non-acute conversational posture; crisis surfaces remain owned by
   Node 1 / L0 risk block (unchanged).

## Artifacts
- Draft template: `src/sage_poc/prompts/templates/L2_intents/general_chat_advicefirst.json`
- Probe: `scripts/probe_freeflow_openers.py`
- Raw results: `tests/fixtures/counsel_chat/openers_probe_results.json`
