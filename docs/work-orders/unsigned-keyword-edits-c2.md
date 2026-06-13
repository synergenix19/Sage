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

## Status

OPEN — held for the per-keyword pick. Both the revert diff (flagged rows) and the sign-off entry are preparable on decision. Does not block PR #4 merge on its own, but unsigned clinical content shaping live acute routing should not persist into pilot.
