# Work item — crisis helpline: centralise + settle the one final number (SAFETY-CRITICAL)

**Status:** PLAN APPROVED (PO, 2026-07-08). **NUMBER APPROVED: `800 46342`** (PO, 2026-07-08) — resolves the G8 *number* question; it stays as-is (no transcription change to `800 4673`). **One item still open before the centralisation edit: `hours` = "24/7"** — the G8 note flags this as FALSE (real hours ~8am–8pm). Centralising propagates the whole entry, so the hours must be confirmed/corrected first; telling a user "free, 24/7" on a crisis line that closes at 8pm is a safety-copy defect. `label` = "MoHAP Counselling Line" assumed unchanged (confirm alongside hours).
**Labels:** safety-critical · GL-1 / G8 · crisis-UX
**Raised:** 2026-07-08, during the Item-3 live browser test (crisis card showed `800 46342`; onboarding shows a *different* number).

## Approval record
- **Number:** `800 46342` — **APPROVED** by PO, 2026-07-08 (this session). G8 "likely transcription error → 800 4673" is **overruled**: the served number is correct.
- **Hours `"24/7"`:** ⏳ **PENDING PO confirmation** — keep-as-is (`24/7`) or correct (e.g. `8am–8pm daily`)? Blocks the centralisation edit.
- **Onboarding LifeLine `4673`:** ⏳ reconcile — intentional second resource, or align to the crisis number?
- **Centralisation mechanism** (choose): (a) **read-from-source** — resolve `config.CRISIS_CONFIG` into crisis_content/skills/L0 at load + frontend build-time inject, delete all literals (true one-place edit; needs a leak-guard so a placeholder can never render raw in a crisis message); or (b) **config-canonical + conformance test** — literals stay but a CI test fails if any of the 11 sites ≠ config (no runtime-templating risk; edit is still N-place but drift is impossible to merge). Recommendation: (a) with the leak-guard, since the goal is the one-place edit; (b) is the safe fallback.

## The three problems
1. **Not centralised — declared, not enforced.** `config.py:CRISIS_CONFIG` says it is "the SINGLE authoritative source … Nothing may re-embed these literals," and ships a `CRISIS_LINE_UAE` back-compat alias "during the migration." The migration was **never finished**: the literal `800 46342` is re-embedded in **11 files / 37 lines**, including a **fully independent hardcode in the frontend card** that does not read the backend. Changing the number today means editing 11 files across both repos; any one drifting diverges silently.
2. **Two different services' numbers are live to users.** Crisis path = **MoHAP `800 46342`**; **onboarding welcome screen = LifeLine Arabia `4673`** (a different org/number). A user sees `4673` at signup and `800 46342` in a crisis. (A third legit resource, **CDA `800 4888`**, also appears in the crisis resources list — not a conflict, but part of the copy.)
3. **The crisis number's correctness is unverified (G8).** `config.py:27` warns `800 46342` is a **likely transcription error** → should be **`800 4673`** ("800-HOPE" / "Mental Support Line"), **and** `hours "24/7"` is **FALSE** for that line (really ~8am–8pm). Unresolved pending a **dial-test**.

## Full hardcode-site inventory (`800 46342`, verified 2026-07-08 — 11 files, 37 lines)
| File | Lines | Role |
|---|---|---|
| `sage-poc/src/sage_poc/config.py` | 1 (`:32`) | **Intended single source** (`CRISIS_CONFIG["number"]`) + `:27` G8 warning. Keep. |
| `sage-poc/src/sage_poc/skills/psychotic_referral.json` | 14 | Referral skill — "verbatim" required (goal/technique/contra/examples, EN+AR) |
| `sage-poc/src/sage_poc/skills/post_crisis_check_in.json` | 6 | Post-crisis check-in skill |
| `sage-poc/src/sage_poc/rules/data/crisis_content/en_uae.json` | 4 | Crisis response_text + resources (EN) |
| `cdai/apps/web/components/chat/crisis-card.tsx` | 4 | **Frontend hardcode** — `UAE_COUNSELLING_LINE`, `tel:800-46342`, aria-labels, button |
| `sage-poc/src/sage_poc/rules/data/crisis_content/ar_uae.json` | 2 | Crisis response_text + resources (AR) |
| `cdai/apps/web/components/chat/__tests__/crisis-card.test.tsx` | 2 | Frontend test pinning the literal |
| `sage-poc/src/sage_poc/skills/psychoed_depression.json` | 1 | Crisis line in contraindications |
| `sage-poc/src/sage_poc/rules/data/prompt_injection/third_party_guidance.json` | 1 | Third-party crisis guidance |
| `sage-poc/src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json` | 1 | Psychotic-symptom adaptation |
| `sage-poc/src/sage_poc/prompts/templates/L0_persona.json` | 1 | L0 persona safety instruction |

**Different-number sites (reconcile, not just replace):**
| `cdai/apps/web/components/onboarding/steps/welcome.tsx` | 2 (`:14` EN, `:23` AR) | **LifeLine Arabia `4673`** — different service than the crisis path |

## Fix sequence (do NOT skip 1–2)
1. **Dial-test** every candidate — establish the ONE correct number + label + real hours. Resolve: is it MoHAP `800 4673`? LifeLine `4673`? Should onboarding and crisis intentionally differ? Is `800 46342` dead/wrong?
2. **Clinical/PO sign-off on the single final number** — a register entry (same discipline as the Item-3 approval). **PO will provide the final number.**
3. **Actually centralise** — make `config.CRISIS_CONFIG` the real single source; have crisis_content, all skills, prompt-injection adaptations, L0, **and the frontend card + onboarding** read from it (build-time inject / generated constant for cdai), deleting every hardcoded literal above so it *cannot* re-diverge. Update the frontend test to assert-from-source, not pin a literal.
4. **Verify** — post-change dial-test + a smoke asserting *every* surface (crisis card, crisis response EN/AR, each referral/skill, onboarding) renders the one signed number, hours, and label.

## Why this matters
A wrong or dead number is worst exactly where it appears — the crisis screen. The current deferral (keep values, behaviour unchanged) was deliberate and stays until the signed number lands; this item exists so the correction, when it comes, is a **one-place edit** and can't leave 11 sites out of sync.
