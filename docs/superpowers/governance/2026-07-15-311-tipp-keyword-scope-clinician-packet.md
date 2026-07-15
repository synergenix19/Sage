# #311 TIPP-reachability — keyword scope-correction: clinician tick packet

**Status:** merge-gated on clinician tick. **Branch:** `cdai/r1-acute-anchor-tipp` (from master `79912e7`).
**Commits:** `98be407` (red fixture) · `7710635` (import guard) · `ec11e64` (this fix).
**Measured:** real CPU-pinned BGE-M3, prod-faithful V1 (reranker off, full prod candidate set).

## What this fixes

Filed #311: two textbook TIPP distress-tolerance utterances (prod 43b9b62, register 2026-07-14)
both misrouted away from `dbt_tipp` — one captured at the keyword tier by `grounding`, one at the
semantic tier by `box_breathing`'s §1e anchor. Both now route to `dbt_tipp` **deterministically at
Tier-1 keyword**, moving the decision off a ±0.007 embedding margin onto the auditable keyword tier.

**Architectural basis (not just this bug):** `calibrate_threshold.py` documents that within-cluster
disambiguation — `box_breathing` / `dbt_tipp` / `grounding` are all `somatic_distress` — is Tier-1
keyword's responsibility, **not** the embedding tier. The §1e widening had pushed within-cluster
disambiguation into embeddings; this restores it to the correct tier.

## The delta — clinician-owned CMS content (please tick each)

Every change is transcription-not-invention against the spec source (`bot-behaviour-spec-source-2026-07-08.md`).

### `grounding_5_4_3_2_1` — REMOVE 6 (scope-correction)
Grounding = **Mild tier / dissociation-sensory** (spec L67, L118); acute-flooding routes to **TIPP**
(spec L69 "High → TIPP", L801 "acute high-anxiety distress → redirect to TIPP"). These 6 are
distress-tolerance language that is TIPP's job, not sensory grounding's:

| removed phrase | gloss | true home |
|---|---|---|
| `need to calm down fast` | — | (unowned; semantic) |
| `I need to calm down` | — | (unowned; semantic) |
| `مشاعري أقوى من قدرتي` | emotions stronger than my ability | → dbt_tipp |
| `محتاج أهدى بسرعة` | need to calm down fast | (unowned; semantic) |
| `مشاعري أقوى مني` | emotions stronger than me | → dbt_tipp |
| `مشاعري فوق طاقتي` | emotions above my capacity | → dbt_tipp |

Dissociation/panic-sensory triggers (`panic`, `dissociated`, `derealization`, `nothing feels real`,
`خايف أجنن`, the 5-4-3-2-1 phrases, …) are **untouched**. Guard: grounding stays 3/8 on its own set.

- [ ] **Clinician tick: grounding removals approved**

### `dbt_tipp` — ADD 6

| added phrase | justification |
|---|---|
| `shock my system` | TIPP's own delivery language — spec L194 "shock your system into calming down" |
| `shock your system` | spec L194 (verbatim) |
| `emotions out of control` | scope-consistent with signed `feeling out of control` / `losing control` |
| `مشاعري أقوى من قدرتي` | **moved** from grounding — distress-tolerance's doc-correct home |
| `مشاعري أقوى مني` | **moved** from grounding |
| `مشاعري فوق طاقتي` | **moved** from grounding |

- [ ] **Clinician tick: dbt_tipp additions approved**

## Cross-route evidence (real CPU baseline `79912e7`)

| set | pre-fix | post-fix |
|---|---|---|
| register probes (p1 keyword, p2 semantic) | 0/2 | **2/2 ✅** |
| box_breathing (legit captures) | 8/8 | **8/8** (no collateral) |
| grounding (own set) | 3/8 | **3/8** (removals didn't cost a passing case) |
| stop_technique (own set) | 6/8 | **6/8** |
| venting (F6) + SG-7 dissociation adjacency | — | **new keywords capture neither ✅** |

Gate: `tests/test_tipp_reachability_311.py` — 24 passed, 4 xfailed(strict).

## Two clinician questions (routing logic this workstream will NOT self-authorize)

**Q1 — stop_technique `'spiraling'` scope.** On *"I'm spiraling emotionally and it's escalating by
the second — give me something I can do with **cold water** or my body to bring it down now"*, the
keyword `'spiraling'` routes to STOP (impulse-interruption) even though cold water is TIPP's own
Temperature component. Should `'spiraling'` (emotional escalation) belong to STOP, to dbt_tipp, or
neither (leave to semantic)?

**Q2 — C1 acute-overlap tiebreak** (signed `2026-06-13-overwhelm-routing-c1-conflict`). It forces
`grounding` ahead of `dbt_tipp` on any co-match, on the rationale that grounding is contraindication-
free under unscreened delivery. On *"my panic is peaking and I feel like I'm losing control of how
intense this is"* both match (grounding via `panic`, TIPP via `losing control`) → grounding wins.
For messages explicitly about **intensity/overwhelm** (not dissociation), is gentler-first still the
intended rule, or should TIPP lead? **Changing this is a clinical call; flagged, not touched.**

## Separate findings (NOT bundled here)

1. **c1/c2 semantic pass** — "at a ten out of ten…" and "feelings hit so hard… reset button" miss at
   the semantic tier (dbt_tipp under-anchored for "quick physical reset" language). Deferred to a
   semantic_description increment + `calibrate_threshold.py` re-run. Tracked as xfail(strict).
2. **Threshold drift** — `calibrate_threshold.py` now suggests `SEMANTIC_THRESHOLD = 0.4528` vs live
   `0.4593` (gap 0.0468, gate still passes). Pre-existing master drift, independent of this keyword
   edit (calibrator does not read `target_presentations`). Flagged for the register.

## On merge

Merge gated on Q-independent ticks above. Q1/Q2 do **not** block this PR (register probes are fixed);
they ride as follow-ups. On merge: driven verification, v2-register write-back, #321 dbt_tipp
single-source rides after, and the SG-2 dbt_tipp caveat converts latent → live (the payoff — it now
protects a reachable skill).
