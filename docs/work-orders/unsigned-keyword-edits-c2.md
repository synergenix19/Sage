# Work Order — C2: Unsigned Keyword Edits, Per-Keyword Sign-off or Revert

**Date opened:** 2026-06-13
**Owner:** Clinical lead (per-keyword sign-off or revert)
**Source:** PR #4 audit (`project_unaudited_keyword_changes`) → batched clinical session item C2
**Default:** revert-unless-signed. **Held, not bulk-reverted** — the batch contains a clearly-correct fix alongside the flagged concerns, so a blanket revert would re-break correct collision fixes (look-before-overwrite). The lead picks per keyword.

## The edits (commits d234ec6, 8433410 — both in master and the feature branch)

| Skill | Keyword added | Why it was added | Audit/clinical note | Recommend |
|---|---|---|---|---|
| `cbt_thought_record` | `thought record`, `thought records` | the technique's own name was missing; was routing to worry_time via semantic | clearly correct — the skill's own name | **Sign** |
| `box_breathing` | `i need to breathe` | beats dbt_tipp `can't calm down`; explicit breathing intent | consistent with C1 (reserve box_breathing for *explicit* breathing requests) | **Sign** |
| `box_breathing` | `need to breathe right now` | explicit breathing intent | consistent with C1 | **Sign** |
| `box_breathing` | `do with my breathing` | beats grounding `anxious right now` | **flagged (audit highest-priority).** Ambiguous, not an explicit request; under C1's grounding-default this is the case most in tension — "what do I do with my breathing" mid-panic is arguably the ambiguous panic-symptom register that should route to grounding | **Revert (or sign with reasoning)** |
| `progressive_muscle_relaxation` | `shoulders are so tight`, `shoulders are tight` | reversed-collision fix | benign somatic-tension phrasing for PMR | **Sign** |
| `interpersonal_effectiveness` | `setting limits in` | beats AC `setting limits` (14ch) for "setting limits in this relationship…" → IE not general assertiveness | **flagged (audit highest-priority).** Clinically a GIVE/DEARMAN (IE) vs general-assertiveness (AC) boundary call — the lead should confirm the routing intent | **Sign or revert (lead's routing call)** |

## Decision (per keyword)

For each row: ☐ Sign (record reason) / ☐ Revert. The two flagged rows (`box_breathing` "do with my breathing"; `interpersonal_effectiveness` "setting limits in") are the ones that actually need a judgment; the rest are recommend-sign.

- Reasoning for any sign: ____________________
- On decision → engineering: signs = add `approved_by` provenance to the governance record; reverts = remove the specific keyword(s) from `target_presentations` (one commit, re-run the wrong-skill routing suite to confirm no collision regression on the kept keywords).

## Disposition (recorded 2026-06-13)

Per the decision "sign the name case, route the two real judgment calls" — NOT a blanket revert (reverting a skill's own name would manufacture a regression to satisfy a procedure).

- **SIGNED (kept, provenance recorded here):**
  - `cbt_thought_record` "thought record", "thought records" — the skill's own technique name; trivial sign, never a revert candidate.
  - `box_breathing` "i need to breathe", "need to breathe right now" — explicit breathing requests; consistent with the C1 affirmation that explicit-breathing language owns box_breathing.
  - `progressive_muscle_relaxation` "shoulders are so tight", "shoulders are tight" — benign somatic-tension phrasing for PMR.
- **ROUTED to clinician (still pending; the only real judgment calls):**
  - `box_breathing` "do with my breathing" — leans SIGN: "what do I do with my breathing" is an explicit breathing reference, consistent with C1 (explicit-breathing owns box_breathing). Clinician confirms.
  - `interpersonal_effectiveness` "setting limits in" — the one to SCRUTINIZE MOST for over-broad matching (GIVE/DEARMAN routing vs general assertiveness). Clinician's routing call.

No code change to skill JSONs (the signed keywords stay as-is). If the clinician reverts either routed keyword, that is a one-line `target_presentations` removal + a wrong-skill-routing-suite re-run to confirm no collision regression on the kept keywords.

## Status

PARTIALLY CLOSED — signed keywords disposed; two routed keywords pending the clinician's per-keyword call. Does not block PR #4 merge; the two pending keywords should be resolved before pilot (unsigned clinical content shaping live acute routing).
