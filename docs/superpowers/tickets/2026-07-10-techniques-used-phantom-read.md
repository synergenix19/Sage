# Ticket: `techniques_used` phantom read in step-policy prior_exposure

**Filed:** 2026-07-10 · **Status:** RECLASSIFIED + DEFERRED 2026-07-13 — NOT a within-session defect; dormant cross-session efficiency logic, in-session behaviour is correct (see Correction) · **Type:** ~~DEFECT (within-session)~~ → DORMANT cross-session (part of `therapeutic-profile-persistence-nonfunctional`) · **Verified against:** master `a0721c0`/`6e8f713` · **Links:** `src/sage_poc/nodes/skill_executor.py:556-557,367-368`, skill JSONs `mi_readiness_ruler.json:158`, `act_psychological_flexibility.json:236`, `problem_solving_therapy.json:203`, scope ticket `2026-07-10-therapeutic-profile-persistence-nonfunctional.md`, decision `../governance/2026-07-13-memory-scope-internal-testing-decision.md`

## ⚠️ CORRECTION 2026-07-13 (resolves the conditional; downgrades this ticket)
The original "within-session DEFECT" framing below was **wrong**. Verified: `prior_exposure` IS consumed by three skills — but every use is a **cross-session efficiency optimization**, not within-session behaviour:
- `mi_readiness_ruler.json:158`: `prior_exposure >= 3 → skip_psychoeducation` ("this user has done the readiness ruler before").
- `act_psychological_flexibility.json:236`: `prior_exposure >= 2 → skip_psychoeducation` ("user has used ACT before").
- `problem_solving_therapy.json:203`: same shape.

The code is explicit (`skill_executor.py:367-368`): *"prior_exposure reflects **cross-session** skill usage only… Within a first session, prior_exposure=0 regardless of repetitions."* `corpus_constants.py:38` labels it "skip/efficiency logic."

**Therefore, in-session, `prior_exposure=0` is the CORRECT designed value** — a non-returning user *should* receive the full psychoeducation. The skills degrade **gracefully** (always teach the intro); no wrong or clinically-unsafe behaviour. The always-0 only disables a **returning-user shortcut**, which is a cross-session feature.

**Resolution:** this is not a defect to fix now — fixing it (populating `techniques_used`) = **building cross-session capability**, which the 2026-07-13 ruling defers. Folded into the dormant cross-session set. Revisit only if/when cross-session re-enters scope. The original analysis below is retained for history but is superseded by this correction.

## The datum (code-verified)
`skill_executor.py` computes a skill's `prior_exposure` from a profile field that is never populated:

```
# skill_executor.py:556-557
techniques_used = therapeutic_profile.get("techniques_used") or []
prior_exposure  = techniques_used.count(skill_id)
```

`techniques_used` is:
- **not in the `get_therapeutic_profile` SELECT** (`postgres_repository.py:20-25` selects effective_techniques, ineffective_techniques, distortion_patterns, disclosed_concerns, communication_style, cultural_preferences, mood_trajectory, total_skills_completed, session_count, last_extraction_turn, last_updated_at, observations, persisted_clinical_flags — **no `techniques_used`**), and
- **written by nothing** — a full-repo grep finds `techniques_used` only in `skill_executor.py` (this read + two comments); there is no writer anywhere in `src`.

So `therapeutic_profile.get("techniques_used")` is always `None → []`, and **`prior_exposure` is silently always `0`** for every skill, every user, every turn.

## Why this is a genuine DEFECT (not just dead cross-session scaffolding)
Unlike the other dead profile fields, this one degrades **within-session skill behaviour**: any step-policy branch that reads `prior_exposure` (e.g. "offer a lighter variant / skip the intro if the user has done this skill before") silently never fires. That consequence exists even if cross-session continuity is out of POC scope entirely, because the read sits on the live skill path.

## Disposition (conditional fix)
- **Fix IF** any POC scenario/skill actually exercises `prior_exposure` (a step-policy condition keyed on it). Then the fix is to make the store and reader agree: either add `techniques_used` to the SELECT **and** a writer that appends completed skill_ids, **or** rebase `prior_exposure` on an already-populated field (`total_skills_completed` exists but is a count, not per-skill).
- **Log-and-defer IF** no POC skill reads `prior_exposure` — in which case it is a latent no-op with no demo-visible effect. **State that condition explicitly when deferring**; do not close silently.

**Action needed first:** grep the 20 skill JSONs for any step-policy condition referencing `prior_exposure` to decide fix-vs-defer. This is an engineering decision, not a clinical one.

## Explicitly NOT in scope of this ticket
Wiring up the cross-session profile reads/writes generally — that is the separate scope decision (`2026-07-10-therapeutic-profile-persistence-nonfunctional.md`). This ticket is only the standalone within-session `prior_exposure` no-op.
