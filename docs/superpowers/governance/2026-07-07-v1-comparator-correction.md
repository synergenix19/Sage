# CORRECTION / SUPERSESSION — the V1 comparator freeze

**2026-07-07.** This **supersedes** `2026-07-07-v1-comparator-frozen.md` (which stays in the repo, untouched — the record of the wrong call is part of the audit trail). It moves the V1→V2 anchor from a **lost-corpus historical number** to a **committed-corpus measurement by a validated driver.**

## What was wrong

The Option-A freeze adopted the signed 2026-06-24 number **66/35/100** (324 EN cases: 217/71/36) as the comparator, on the premise it was reproducible against the committed fixtures. **It is not.** The Track-A driver's acceptance gate (the whole reason the driver exists before wiring) proved:

- The committed EN bulk fixtures are **200/64/32 — at the current tree AND at `5e6b86e`, the exact SHA the frozen doc cited.** The 324-case corpus is **not in the repo at any revision.** The frozen doc labeled the 2026-06-24 *tree SHA* an honest soft link; the driver shows the **corpus itself** is unrecovered — the link is broken, not soft.
- This is the **second lost-provenance finding this week** (prod's deployed SHA was `null`; now the measurement corpus). See the governance rule below.

## Why the driver is trusted anyway (the correction is stronger, not weaker)

The driver is **validated faithful** — the failure is the comparator, not the instrument:
- The two **ABSTAIN cells reproduce the comparator almost exactly** (id_oos abstain 35.9% vs 35%, far_oos 100% vs 100%) — the semantic-threshold / `_route_decision` / abstain path is correct.
- The entire divergence is in **in_scope**, explained by three structural surface deltas (below), none attributable to wiring.

The corrected chain — **driver validated via ABSTAIN-cell reproduction → new baseline on the committed corpus at a pinned fixture SHA → the same driver, same corpus, same keyword-offer convention for the V2 run** — is genuinely stronger than a number whose inputs are gone. **The do-not-re-measure lock transfers to the new baseline.**

## The two fixture-hygiene calls (applied before freezing)

1. **8 `mi_readiness_ruler` in_scope cases — EXCLUDED with reason, remap filed to the content track.** These expect a **deprecation-requested** skill absent from `SKILL_REGISTRY` → structurally unrouteable → guaranteed misses that would silently deflate the in_scope baseline. Deciding what they *should* route to now is a **content/clinical question (target_presentations territory), not a driver/engineering decision.** They are dropped from the frozen baseline (case exclusion, **not** a registry or fixture edit) with adjusted stratum counts. **Open item FILED to the content track (no engineering action taken):** the 8 are classic MI ambivalence / readiness-to-change disclosures, and **no clean registered successor exists.** `mi_readiness_ruler.json` is retained-but-deprecated (deprecation executed 2026-07-07 by product + spec-silence, with a **clinician confirm-or-object window still OPEN and git-reversible**); the deprecation doc's own §5 notes MI readiness is a legitimate technique whose absence may be the *spec's* gap, not the skill's obsolescence. Closest registered neighbor `problem_solving_therapy` shares the decisional-balance surface but is a **different technique** (structured problem-solving, not MI) → partial neighbor, not a successor. **Recommendation (proposal, not an edit):** either re-register `mi_readiness_ruler` if the clinician objects within the open window, or add a readiness/ambivalence category to the BOT BEHAVIOUR spec — **not** a remap onto an existing skill. This is a real routing gap for readiness/ambivalence, independent of V2.
2. **Tier-1 catches 40 in_scope where the comparator said "0" — recorded as a known surface delta, NOT a defect.** Cardinal Rule 5 means the baseline measures the whole Node-4 surface (rules-first keyword + semantic fallback). The 40 (28 correct, 12 wrong-skill) reflect `target_presentations` drift since the 2026-06-24 measurement — correct current behavior. Recorded here so Task 5's readers don't re-litigate it.

## The new frozen V1 baseline (committed-corpus)

Driver flags-OFF, mm excluded from candidates (surface-matched), `mi_readiness_ruler`-expecting cases excluded, on the committed fixtures at a pinned SHA:

| cell | metric | V1 (new anchor) |
|---|---|---|
| en/in_scope | recall | **109/192 (56.8%)** |
| en/id_oos | abstain | **23/64 (35.9%)** |
| en/far_oos | abstain | **32/32 (100%)** |

**Pinned provenance:** tree HEAD `69ded58`, fixture-set commit `5e6b86e`. **Reproducible command** (the driver's defaults bake in `exclude_skills={"mindfulness_meditation"}` + `exclude_expected={"mi_readiness_ruler"}`):
```
cd .../sage-poc-v2live && SKILL_ROUTING_V2=0 SKILL_RERANK_ENABLED=0 uv run python -m sage_poc.routing_eval.real_model_driver --json
```
Driver: `src/sage_poc/routing_eval/real_model_driver.py`. **The do-not-re-measure lock now binds THIS baseline** (109/192, 23/64, 32/32 @ fixtures `5e6b86e`).

## Surface consistency (stated once)

The new baseline runs on the **reconciled tree with `mindfulness_meditation` registered**, and Task 5's V2 run will use the **identical surface** — so the V1→V2 comparison is **internally consistent regardless of the #139 ruling.** If the ruling **de-registers mm before Task 5 executes**, re-run *both* sides on the post-ruling surface; the absolute numbers shift slightly but the paired methodology holds.

## Task 5 acceptance (restated against the new anchor)

V2 flags-ON, same committed corpus, same driver, same convention — **beats-per-stratum vs this new V1 baseline, not matches-a-historical-point:** id_oos abstain lifts materially from **35.9%** (the ~86–90% band per the offline result; the single-pass-vs-5-fold-CV caveat stands), in_scope not below the new V1 baseline beyond stated tolerance, far_oos holds 100%.

## Non-blocking recovery

One bounded ask to the 2026-06-24 measurement author/machine for the original 324-case corpus. If it surfaces, it is **corroboration of this anchor — never a competing anchor.** Not on the critical path.

## GOVERNANCE RULE (earned by this incident)

**Any number that gates a deploy MUST cite a committed fixture SHA, and the corpus is part of the artifact. A measurement whose inputs aren't in the repo is an anecdote, not a gate.** (Second lost-provenance finding in one week.) This sentence also goes into the Task 10 deploy runbook.

## Supersession — "V1 of record" is now V1+veto (2026-07-08)

The baseline in this document (in_scope 109/192 = 56.8%, id_oos 23/64 = 35.9%, far_oos 32/32 = 100%) is the **pre-veto** V1. The chain since:

1. **Pre-veto baseline** — this document (id_oos 35.9%), measured before the OCD-compulsion veto existed.
2. **Veto hotfix** — the deterministic OCD-compulsion veto shipped to prod (`bc3cb4b`, arm-independent) and was folded into the driver's `routed_of` (`8abdaa8`). It ABSTAINS disclosed compulsions that used to misroute.
3. **Post-veto V1 of record** — flags-off on the committed driver now measures **id_oos 30/64 = 46.9%** (in_scope 56.8% and far_oos 100% are veto-invariant). This is what production runs and what the V2 re-verdict compared against (`2026-07-08-v2-reverdict-FLIP.md`).

The pre-veto 35.9% is **superseded, not competing** — same discipline as the Task-2 corpus correction. **Task 12's prod measurement compares V2 against the post-veto V1 numbers (id_oos 46.9%, in_scope 56.8%, far_oos 100%)** — stated explicitly here so nobody re-derives the delta against the stale 35.9% and reads a wrong id_oos gain.
