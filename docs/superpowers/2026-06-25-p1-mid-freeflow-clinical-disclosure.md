# Clinical disclosure — P1(mid) freeflow response-shape floor

**To:** Rohan Sarda (clinical lead)
**From:** engineering
**Date:** 2026-06-25
**Type:** Disclosure, not a sign-off request. P1 ships as engineering; no clinical gate. One item below DOES need your bundle re-prioritised.

## What P1 is

A pure-engineering change (branch `feat/p1-mid-freeflow-shape`, `composer.py`) that fixes the cold/terse reply defect (the "my dog hasn't been eating" screenshot). It injects a response-shape floor — acknowledge the named feeling first, then one open question, roughly 40–80 words — **only** on pure-freeflow general-chat turns at the mid band (emotional_intensity 4–6). It does not touch any signed template (L0, general_chat, freeflow_guardrail are byte-unchanged). It contains no normalization sentence (your P2, still parked) and no menu/fork question (P3, still gated on Arabic eval). One plain open question only.

## Why you are being told (two things)

### 1. P1 is now load-bearing on your signed L0 "longer reply" clause

A plain "write 40–80 words" instruction did **nothing** in testing — it was overridden by L0's signed concision cap, *"Keep replies concise, two to four sentences."* P1 only works because it **invokes the exception you already signed**:

> "...two to four sentences unless the person needs more; a heavy disclosure deserves a longer, more present reply even when it is brief..."

Consequence: that clause is now **load-bearing for a new purpose**, and it is clinician-owned (yours). If a future L0 re-authoring tightens the concision cap or drops that exception, P1 silently reverts to cold replies with no engineering signal. We have guarded this in code two ways: a greppable coupling comment at the injection site naming the exact clause, and a CI test (`test_l0_longer_reply_exception_present`) that fails loudly if the clause leaves L0. **Ask:** when you next revise L0, treat that exception as a dependency, not free text.

Side effect worth naming: P1 effectively **widens the range of turns on which your exception fires** — it now fires across freeflow general-chat at intensity 4–6, including lighter mid disclosures (e.g. "low energy, not sure why"), not only heavy ones. We judged this in-scope for "needs more," but you own that clause, so you should know its reach grew.

### 2. The heaviest disclosures get the LEAST present reply — and P1 cannot fix it (this re-prioritises your bundle)

Measured 2026-06-25: a canonical heavy-but-brief disclosure, *"my dad passed away last month and I don't think I've really dealt with it,"* scores **intensity 7 in 6/6 runs**. That routes it to the **high band**, where the guidance is *"do not offer guidance, one focused question, do not paraphrase"* — and where P1 is **excluded by design**. Result: the heaviest disclosure in the test set got a **24-word cold reply**, while ordinary mid disclosures (dog, lonely) get fuller, warmer ones.

This is the **§15.3 conflict** from the D5 conversational-style spec, now measured live. Earlier this week engineering told you §15.3 was "low urgency, a ≥7 acute corner case." **That was wrong, and we're correcting it.** The grief case shows §15.3 is not a corner case — it is *the heavy-disclosure case*, and it produces the coldest output in the system. P1 (correctly) does not touch the acute band, so **only your L0/L2 bundle can fix this.** Recommendation: move the §15.3 validate-first / no-cold-high-band item **up** in the bundle, not down.

## Evidence

- Attribution + floor test, pre/post distributions: the dog case moved from a pre-median of 33 words (0/5 samples clearing 40) to ~39–47 post (straddles the boundary; the shortest case is lifted to the floor, not cleanly over it).
- Arabic: P1-in-Arabic is **engineering-only, confirmed**. Arabic turns generate in English against the *same* L0 (there is no separate Khaleeji L0), so the same exception applies; both Arabic test cases cleared the floor in generation. Delivered Khaleeji runs ~40–49 words (denser than English) — a band-recalibration note for engineering, not a clinical issue.
- Acute exclusion verified end-to-end: crisis (EN + AR) routes `safety_check → crisis_response`, never through freeflow, so P1 cannot fire on the crisis surface.

## Caveat on our read

The L0 concision clause and its exception are not verbatim in the v7 spec; they live in the composer/CMS L0 template. Engineering is asserting this wording from the live template. The principle (L0 is always-on, system-layer, clinician-owned) is the part the spec confirms.
