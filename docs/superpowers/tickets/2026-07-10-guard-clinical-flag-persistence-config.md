# Ticket: GUARDRAIL — do not enable `flag_lifecycle_config` cross-session persistence until the lifecycle covers CF-006

**Filed:** 2026-07-10 · **Status:** open — **GUARDRAIL / locked config (not a bug to fix)** · **Type:** clinical-safety guardrail · **Verified against:** master `a0721c0` · **Links:** `src/sage_poc/rules/data/flag_lifecycle_config.json`, `src/sage_poc/prompts/composer.py:360` (`_FLAG_DESCRIPTIONS`), `project_clinical_flag_lifecycle`, scope ticket `2026-07-10-therapeutic-profile-persistence-nonfunctional.md`

## The rule
**Do not flip any `cross_session_persistence` value in `flag_lifecycle_config.json` from `false` to `true`** until the flag-lifecycle model is extended to cover `psychotic_disclosure` (CF-006) and given expiry/active-vs-historical semantics. Today all six are `false`; keep them there.

## Why this is a guarded config, not a toggle (the psychotic_disclosure inconsistency)
Enabling persistence is **not** a uniform behaviour change — it fires two *different* code paths depending on the flag, and one is silent:

- The five original Category-A flags (`substance_use`, `trauma_indicator`, `eating_concern`, `medication_mention`, `domestic_situation`) have entries in `_FLAG_DESCRIPTIONS` (`composer.py:360`). When seeded cross-session, they render as **L5 user-context prose the response model reads** (e.g. "This user has indicated trauma history…"). So flipping the config **injects a persisted clinical label into the LLM prompt next session.**
- `psychotic_disclosure` (CF-006, added 2026-06-03) has **no `_FLAG_DESCRIPTIONS` entry** — it postdates the 2026-05-27 flag-lifecycle taxonomy (`project_clinical_flag_lifecycle` lists only the five). So when seeded it produces **no prose**; it silently seeds routing (psychotic_referral) instead.

Root cause: CF-006 was added to the config's persistence map but never folded into the lifecycle design or the L5 description set. The result is that "enable persistence" means *five flags become model-visible memory and the sixth becomes an invisible routing seed* — an inconsistency the original design never reviewed. That makes the flip a **latent clinical-safety incident**, not a feature toggle.

## Compounding reasons to hold
- No flag has expiry / decay / active-vs-historical differentiation — a persisted `trauma_indicator` or `psychotic_disclosure` would live forever with no review date (the inverse stale-state risk).
- Persisting these flags cross-session also lands crisis-adjacent clinical data on non-sovereign POC infra — see the scope/retention ticket and findings #3/#4/#5.

## Preconditions before this guardrail may be lifted (all required)
1. `psychotic_disclosure` reconciled: either given a reviewed `_FLAG_DESCRIPTIONS` entry (so its cross-session behaviour is intentional and consistent) or an explicit decision that it must NOT surface as prose — documented, not implicit.
2. Flag lifecycle model extended with expiry / active-vs-historical semantics (the existing known design gap).
3. Clinical sign-off on what a returning user should see from each persisted flag.
4. Data-residency / retention posture resolved (scope ticket).

Until all four: **config stays all-`false`. This is a decision, not an oversight — do not "enable for testing."**
