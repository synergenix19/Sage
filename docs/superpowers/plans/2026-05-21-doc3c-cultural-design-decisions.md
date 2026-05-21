# Doc 3c: Cultural Adaptation — Deferred Design Decisions

**Status:** Design note only — not an implementation plan. Both items require architectural decisions before implementation can begin.

**Date:** 2026-05-21  
**Covers:** v7 §5.5 gap Items 7 and 13 (full resolution)

---

## Item 7: Gender-Appropriate Address

**What it requires:** When the user's gender is known, inject an instruction for the LLM to use the correct Arabic gendered forms in its response. Arabic is grammatically gendered — using masculine defaults when addressing a woman sounds clinically detached and signals the AI isn't paying attention.

**Why it's deferred:** The Rules Service engine is stateless — it receives a `context` dict and applies deterministic matching. Gender is not in the message text; it lives in the user's therapeutic profile (not yet modelled in `SageState`). Options:

**Option A — Add `user_gender` to SageState (preferred)**  
Add `user_gender: str | None = None` to `SageState`. Pass it in the `cultural` evaluation context. Add a new `CulturalRule.trigger_type = "state_field_match"` with `condition_field: "user_gender"` and `condition_value: "female"`. Inject: `"GENDERED ADDRESS: The user identifies as female. Use feminine grammatical forms in Arabic responses (ِكِ، أنتِ، وأنتِ feeling...) — not masculine defaults."`.

**Option B — Infer from Arabic grammatical markers in message**  
Detect feminine grammatical patterns in `raw_message` (ت attached verb suffixes, ِكِ pronoun, كِ possessive). This is probabilistic and unreliable for short messages. Not recommended.

**Decision required:**
1. Will the therapeutic profile (user gender) be populated in the POC, or is this Full Build scope?
2. If POC scope: who sets `user_gender` — the user onboarding flow, or inferred from conversation?

**When to implement:** After confirming user gender is available in state. Estimated 1 day (schema + 1 new trigger_type + 1 JSON rule + 3 tests).

---

## Item 13: Non-Muslim Expat Handling (Full Resolution)

**What it requires:** When a user signals they are not Muslim (mentions church, Christmas, Bible, Hindu/Sikh/Buddhist worship, etc.), CU-IS-001 must not fire. The partial fix in Doc 3a Task 2 narrows CU-IS-001 to Islam-specific keywords (removing "god", "faith", "prayer") — this eliminates the primary false-positive case. The remaining gap is active suppression: if both Islamic AND non-Islamic religious signals appear (e.g., a user who mentions both "church" and uses "allah" as an exclamation), the system has no way to determine the user's tradition.

**Current state after Doc 3a Task 2:**
- "I pray to God every day" → CU-IS-001 does NOT fire (✅ fixed by keyword narrowing)
- "I feel my faith in allah is fading" → CU-IS-001 fires (✅ correct)
- "I went to church and feel allah has blessed me" → BOTH CU-IS-001 and CU-RG-001 fire

**Full resolution options:**

**Option A — Non-Muslim suppression rule (suppresses CU-IS-001)**  
Add `CU-NM-001`: when non-Islamic religious keywords detected (church, bible, christmas, temple, hindu, sikh, etc.), emit a `crisis_suppress`-style action that suppresses `CU-IS-001`. Requires extending the suppression mechanism beyond the `safety` category — it currently only suppresses within `safety`. New: `cultural_suppress` action type.

**Option B — Mutually exclusive rule conditions (preferred for simplicity)**  
Add `not_keywords` field to `CulturalRule` — a list of keywords that, if present, prevent the rule from firing. CU-IS-001 gets `not_keywords: ["church", "christmas", "bible", "temple", "hindu", "sikh", "buddhist"]`. Engine checks: if any `not_keywords` appear in message, skip the rule.

**Option C — Defer entirely (pragmatic for POC)**  
Doc 3a Task 2 already eliminates the main false-positive case (generic "pray to God"). The edge case of a user who mentions both traditions is rare enough to accept as a known limitation for the POC, documented in `SAFETY_RULES_REVIEW.md`.

**Decision required:**
1. Is the residual edge case (cross-tradition religious language) in scope for POC?
2. If yes: Option A (suppression generalisation) or Option B (not_keywords field)?
3. Option B is simpler but adds schema complexity; Option A is more powerful but touches the suppression architecture.

**When to implement:** After design decision above. Estimated 1–2 days depending on option chosen.

---

## Summary

| Item | Gap | Pre-condition for implementation |
|------|-----|----------------------------------|
| 7 — Gender address | `user_gender` not in `SageState` | Confirm therapeutic profile is in scope; design onboarding flow |
| 13 — Non-Muslim full | Suppression or not_keywords mechanism not built | Choose Option A, B, or C above |

Neither item blocks the Doc 3a or Doc 3b delivery. Both should be revisited at the start of Full Build planning.
