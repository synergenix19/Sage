# Safety relay sign-off — clinician V, 2026-07-16 (PRIMARY RECORD)

**Approver:** V (clinician). **Relayed by:** PO, 2026-07-16. **Status:** APPROVED.
**GL-1:** this record PRECEDES merge and deploy. No crisis-adjacent value ships on conversational
authority; each PR below links here. Amend this record (not a merged artifact) if any decision is
mis-transcribed.

## Scope
One coordinated safety relay covering four PRs, sourced from `bot-behaviour-spec-source-2026-07-08.md`
and verified line-cited in the clinician packets.

## Decisions

| id | item | decision | spec basis / note |
|---|---|---|---|
| **A1** | 11 AR cardiac red-flag renderings (#331) | **APPROVED as-sent** | L58/L92/L131 descriptor classes; FP exclusions doc-mandated (L59) |
| **A2** | 9 AR OCD-compulsion patterns (#335, onto #334 accessor) | **APPROVED as-sent** (dual-clinician) | L150/L177 — OCD-type → professional referral |
| **A3** | grounding −6 / dbt_tipp +6 keyword scope-correction (#324) | **APPROVED as-sent** | grounding=Mild (L67/L120); TIPP=High (L69); "shock your system" (L194) |
| **B1** | fainting red-flag renderings, EN+AR (#331 addendum) | **APPROVED** | L81/L148 — fainting is an emergency symptom; keyword-clean |
| **C1** | grounding-vs-TIPP co-match tiebreak | **KEEP GROUNDING-FIRST** | reaffirms signed `2026-06-13-overwhelm-routing-c1-conflict`; **no code change** |
| **D1** | L58/L101 quality-check screening question (#338) | **IMPLEMENT the question** | spec-correct mechanism; transcription-class wording verbatim in doc; deterministic build |

**Interpretation note (correct before merge if wrong):** "V approved all of this" was recorded as the
sheet's recommendations — C1 = keep grounding-first (the null-code outcome), D1 = implement. If V's
intent on either differed, amend here first: a C1 = "TIPP-leads" ruling requires its own routing PR
(cross-route set re-run) behind this deploy, NOT folded into the approved batch.

## Not covered by this sign-off (explicit)
- **Real-breathlessness** as a keyword: withdrawn — L54 routes panic breathlessness to TIPP; it is a
  CONTEXTUAL-screen concern, folded into D1/#338, not a phrase list.
- **Tier-2 authoring** (full Gulf AR vocabulary #331; reassurance-seeking + intrusive-thought OCD #330):
  clinician-paced, not in this batch.
- **#337/CR-0** EN spec-conformance audit: queued after run #001.

## On merge (GL-1 order)
Record filed (this doc) → each PR body links it → PRs merge once their strict gate (parity + raw-input
+ state-channels) clears → one `deploy_prod.sh` with build-lock + behavioral-signature verification →
standing-suite run #001 → register write-backs → #338 build (per D1) → heightened-monitoring window
(rollback = pre-deploy SHA, recorded at deploy).
