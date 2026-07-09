# behavioral_activation Exemplar Enrichment — DRAFT for clinician confirm/trim (§3a fix)

**Purpose:** the reranker scores natural depression/withdrawal phrasing below τ and vetoes the legitimate BA route (#202). This draws the boundary conservatively so the clinician's review is a 30-second trim, not from-scratch authoring. **Every phrase is provenanced.** Sources: `SPEC` = pinned BOT BEHAVIOUR oracle `56fde86` §3a (lines 462-476) / §7b; `AUDIT` = Layer-1 suppressed utterance (fixture `depression_pathway_ba_paraphrases.jsonl`); `NEW` = clinician-net-new candidate.

**⚠️ Mechanism note for the fix (engineering, not clinical):** `_keyword_rerank_veto` scores `(utterance, skill.semantic_description)` — NOT `target_presentations`. So "isolating myself" is already in target_presentations yet still vetoed. The enrichment must land where the reranker reads it: either (A) enrich BA's **semantic_description** with a recognition clause, or (B) a small mechanism change so the reranker scores against target_presentations exemplars. The gate + probe pair validate whichever; τ is never touched. The BINS below are the clinical content; the field is the engineering call at fix time.

## Bin (a) — ROUTE TO behavioral_activation (clear withdrawal/anhedonia the reranker is wrongly suppressing)
| phrase | provenance |
|---|---|
| I've lost interest in everything | AUDIT |
| I just don't feel like doing anything anymore | AUDIT / SPEC 472 |
| I've been isolating myself | AUDIT / SPEC 474 |
| I keep cancelling plans and avoiding people | AUDIT / SPEC 474 |
| Nothing sounds enjoyable | SPEC 470 |
| I don't enjoy the things I used to | SPEC 470 |
| I don't look forward to anything | SPEC 470 |
| I don't want to see anyone | SPEC 474 |
| I don't want to leave the house | SPEC 474 |
| I'm withdrawing from everyone | SPEC 474 |
| No energy to do anything | NEW (SPEC 472 adjacent) |
| Stopped seeing my friends | NEW (SPEC 474 adjacent) |
| Everything feels like effort | NEW (energy, not hopelessness) |

## Bin (b) — STAY ABSTAIN (deliberately EXCLUDED — the reranker is right to be cautious; not clawed back)
| phrase | why excluded | provenance |
|---|---|---|
| I don't care about anything / what's the point of any of it | passive-SI adjacency → crisis/abstain, NOT BA (trace: "don't care about anything" escalated to crisis) | AUDIT trace |
| I feel numb and disconnected / nothing feels real | numbness + dissociation → different pathway / referral | SPEC 522 |
| I've withdrawn since [a loss/bereavement] | grief withdrawal → grief skill S2a/S2b, softened framing, NOT plain BA | SPEC 521 |

## Bin (c) — AMBIGUOUS → CLINICIAN'S CALL (the point of the touchpoint)
| phrase | tension | 
|---|---|
| I don't really care anymore | SPEC 476 lists it as §3a flat/numb, but it's SI-adjacent — BA or abstain? |
| I feel empty | flat/numb §3a symptom vs dissociation (SPEC 476 vs 522) |
| Everything feels pointless | already a BA exemplar, but borderline hopelessness |

## Language coverage — EN-only, AR explicitly deferred (per-language honesty)
This draft is **EN-only** (the audit corpus was EN). BA's target_presentations already carries some AR withdrawal phrases (`ما أقدر أقوم`, `ما عندي خلق`). The AR counterpart of this enrichment is **filed with the Arabic follow-up track** (`2026-07-07-arabic-reranker-tau-followup.md`), not shipped silently EN-only. Recorded so the fix does not widen the EN/AR asymmetry without a note.

## The clinician's ask (~30 sec)
Confirm bin (a) routes to BA; confirm bin (b) stays abstain (or move any); **rule bin (c)** — that's the boundary edit that matters.


## SIGN-OFF (2026-07-08)
**Clinical lead: APPROVED.** ① all three bin-(c) phrases → **stay abstain** ('I don't really care anymore', 'I feel empty', 'everything feels pointless' — the last removed from BA target_presentations). ② bins (a)/(b) confirmed. ③ rendered semantic_description confirmed. Recognition clause = bin (a) only. PO present (Rohan).


## SHIPPED 2026-07-09 — prod master 7f2b30d; behaviorally verified (depression→BA, passive-SI→crisis). Gate cleared.
