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
| **C1** | grounding-vs-TIPP co-match tiebreak | **KEEP GROUNDING-FIRST** (V, 2026-07-16) | reaffirms signed `2026-06-13-overwhelm-routing-c1-conflict`; **no code change** |
| **D1** | L58/L101 quality-check screening question (#338) | **IMPLEMENT** (V, 2026-07-16) | build spec below; assembled flow returns for V's tick before deploy |

### C1 ruling — riders (V)
- **(a) Dissociation-marked presentations are UNAFFECTED** — they follow the existing rule (grounding can
  intensify dissociation → *referral*, not grounding, spec L84/L151). This tiebreak governs **acute
  co-matches only**.
- **(b) Revisit trigger:** once D1's screening question is live and verified, "TIPP-leads for explicit
  intensity/overwhelm" becomes reconsiderable — because a contraindication screen then exists.
- **Rationale (V):** TIPP's own script carries physical contraindications (heart condition, irregular
  heartbeat, pregnancy — L194); grounding carries none. Delivery is currently **unscreened** (D1 not
  built), so the contraindication-free option must lead until a screen exists.

### D1 ruling — build spec (V), returns for tick before deploy
- **Trigger is LAYERED (like Node 1), recall-biased:** symptom keywords **+ semantic match** against
  physical-symptom anchor descriptions. A keyword-only trigger inherits the blindness it exists to fix
  ("there's this weird pressure thing happening in my body" lists no symptom). Cost asymmetry is kind —
  a false-positive trigger only asks one gentle clinician-worded question, nearly free — so cast the net
  wide.
- **Response is STRICTLY DETERMINISTIC:** V's verbatim question text + spec-defined answer-routing (no
  clear trigger / sudden onset at rest / first-time / any red-flag quality → medical guard). **No LLM
  discretion anywhere in the safety consequence.** *Semantic breadth in detection, deterministic fidelity
  in response* — Cardinal Rule 4 for the bilingual, paraphrase-rich domain.
- **Ambiguous-answer case is NAMED and routed CONSERVATIVELY:** interpreting the user's answer ("it's
  kind of both?", "لا بس شوي مختلف") is itself a semantic act; **unclear discriminator → treat as
  red-flag-quality → guard**. A screen that misreads a hedged answer just moves the blindness one turn
  downstream.
- **Gate:** the assembled flow (question text + answer-routing) returns to V for tick **before deploy** —
  no second decision needed to START the build.

**NOTE (scope):** D1 is a FOLLOW-UP build (#338), not part of this coordinated deploy. This deploy is
A1 + A2 + A3 + B1. C1 = no code (record reaffirms the signed rule).

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
