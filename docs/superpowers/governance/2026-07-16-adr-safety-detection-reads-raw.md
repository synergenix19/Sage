# ADR 2026-07-16 — Safety detection reads raw input (language contract)

**Status:** accepted. **Enforcement:** `scripts/check_safety_reads_raw.py` (CI, required unit-gate).
**Motivating incidents:** #329 (AR medical red-flag bypass, live), #330 (AR OCD-compulsion bypass, live).

## The invariant

> **All safety-critical detection — crisis lexicon, clinical flags, iatrogenic vetoes, red-flag
> guards, contraindication triggers — operates on the RAW user input in its original language.
> Translated text (`message_en`) exists for therapeutic processing and LLM rendering only, and is
> NEVER a safety-detection input.**

This rule was implicit in v7's language-flow design (Node 1 = MARBERT + lexicon on the original
Arabic), but was never stated as a constraint — which is why it drifted. An unstated invariant
can't be enforced.

## Why (the evidence)

- **#329:** an Arabic cardiac red-flag ("crushing chest pain spreading to my arm") routed to a
  relaxation exercise — the guard's phrase list was EN-only and the AR→EN translation paraphrase-
  missed it. Fixed by reading raw + native AR phrases (`detect_medical_redflag` already got raw).
- **#330:** an Arabic OCD compulsion routed to an ACT self-help skill — `is_ocd_compulsion` read
  only translated `message_en`, so the raw never reached the deterministic matcher.
- **The harm_intrusive near-miss is the exhibit for fragility:** the same translated-path detector
  *happened* to fire on an AR intrusive-harm disclosure — because translation preserved the signal
  *that time*. A paraphrasing translator will eventually launder a compulsion or intrusive-thought
  phrasing into innocuous English. Detection must not be hostage to translation quality on
  distress-register Khaleeji (exactly what TD4 exists to worry about).

## Mechanism (safe path = only path)

A single accessor, `state.safety_text(state)`, returns `raw_message` (a declared SageState
channel). Safety detectors call it; new detectors inherit raw by construction. Conforming a drifted
detector becomes "switch to the accessor," not a bespoke signature change.

## Raw-vs-translated audit (2026-07-16)

| detector | input field | status | ticket |
|---|---|---|---|
| `detect_medical_redflag` | message_en **+ raw** | ✅ conforming (reads raw) | #329 (AR patterns landed) |
| `is_ocd_compulsion` | **raw** via `safety_text` | ✅ conformed (this ADR's branch) | #330 |
| `is_harm_intrusive` | message_en only | ❌ drifted — allowlisted | #330 (translation catches today; conform when AR patterns land) |
| `evaluate_s7` (post-crisis) | message_en only | ❌ drifted — allowlisted | #330-audit (review pending) |
| `ipv_preempt_active` | message_en → raw fallback | ⚠️ translated-primary | flag-off; #330 |
| `check_s3_bilingual` | message_en **+ text_ar** | ✅ bilingual (reads raw AR) | — (TODO: check_s3 non-bilingual path, s3_semantic.py:14) |
| rules engine (crisis / passive_si / clinical_flag) | lang-tagged (raw for AR rules) | ✅ conforming by construction | — |

Two new drift rows surfaced by the audit itself (`evaluate_s7`, `ipv_preempt`) — same shape as the
parity audit finding three more EN-only files. Tracked, allowlisted-with-ticket, not silently absorbed.

## Enforcement + umbrella

`check_safety_reads_raw.py` fails CI if a safety detector call passes `message_en` without raw;
exceptions are allowlisted **with a ticket** (never a bare reason). Armed by a blocking demonstration
before declaring live (a gate never seen blocking isn't armed).

This is one facet of the standing umbrella: **bilingual parity is an architectural invariant, not a
per-file property** — and, as the #337/CR-0 audits showed, the drift is from the spec in *both*
languages, not only Arabic.

**End-state claim (the sentence the DPIA and clinical governance consume):**

> Every safety detector is (1) **spec-complete in EN** [#337 / CR-0 spec-conformance audits],
> (2) **parity-complete in AR** [the armed parity gate, #329], and (3) **behaviorally verified
> equivalent in both** [prod drives + the standing suite, #328].

Three checkable properties, three enforcement mechanisms, one sentence. When all three stand the claim
is **auditable rather than aspirational** — the form the clinical-governance story has been converging
on since the first EN-only file surfaced. (Note: property (1) subsumes not just phrase coverage but
implemented *mechanisms* — e.g. the L58/L101 quality-check screen, #338, an SG-2-class gap where the
spec assumes a screening question the keyword-only guard never built.)
