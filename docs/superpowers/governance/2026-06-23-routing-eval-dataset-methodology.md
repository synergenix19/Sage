# Routing Eval Dataset — Methodology & Sources (for clinician approval)

**Date:** 2026-06-23
**Status:** DRAFT methodology + seed for clinical approval. Engineering/research drafts; clinician approves. **Approve the APPROACH + seed here before the full set is authored** — cheaper to redirect now than after ~700 cases.
**Produces:** the held-out gate-6 eval set (`held_out=True`) that §2 calibration / §5 flip gate consume to decide if V2 beats V1. Built against the FROZEN A1 boundary (`2026-06-23-A1-boundary-FROZEN.md`).

---

## 1. What this set is (and is not)

- **Held-out evaluation set**, not training/calibration data. It measures the router; it is never tuned to it.
- **Research-grounded synthetic cases** — realistic presentations *informed by* published counseling corpora and clinical literature (sources below), **authored fresh as paraphrases**. **NOT real patient or pilot data** → no PDPL/consent exposure (synthetic test assets ≠ clinical data).
- **Anti-overfit (A2.3):** every utterance is a *paraphrase of the construct*, never a verbatim `target_presentations` string, in either language. Copying the strings the router embeds would report false-green against its own training data.

## 2. Sources (documented, for the audit trail)

| Source | Use |
|---|---|
| Counsel-Chat (HF, MIT; 31 counselor-patient topics) | EN presentation language per construct; surfaces ID-OOS topics (anger-management, addiction → no authored skill) |
| ESConv (1,300 support dialogues; problem/emotion/situation types) | realistic help-seeker framing to ground EN paraphrases |
| CLINC / BANKING77-OOS + arXiv 2106.04564 (ID-OOS method) | construction method: ID-OOS = in-domain, semantically-near, no-intent; paraphrase-built; held-out |
| Arabic idioms-of-distress (Springer 2020); Gulf-dialect PHQ-9 (Almouzini); ArPanEmo (Saudi dialect) | Khaleeji framing must be **somatic/idiomatic**, not translated English — drives the AR drafting + the native-review requirement |

## 3. Cell map (the (lang × stratum) matrix)

| Stratum | Definition | expected_route |
|---|---|---|
| **in_scope** | maps to one of the **25 routable skills** (27 registry − `psychotic_referral` − `post_crisis_check_in`, both excluded as routing targets per A1 §4) | that skill_id |
| **id_oos** | in the mental-health-support **domain** but no authored skill covers it — e.g. anger management, body image, addiction, OCD-specific, perfectionism, parenting stress | ABSTAIN |
| **far_oos** | outside the support domain — weather, coding help, transactions, off-topic chit-chat | ABSTAIN |

Languages: **en** + **ar** (Khaleeji). Crisis is **excluded** as a routing target (A1 rule); crisis-adjacent Khaleeji → task #21, never this set.

## 4. Sizing (per the frozen gates)

- **`ar/id_oos` worst cell: ~65 held-out** (#4 POC arm; the ≤1%/~300 bar is the pre-pilot reopening, not POC).
- **Per-skill in_scope: ≥ 8 held-out paraphrases** (§6.3 min-N for own-threshold eligibility; below it the skill falls back to its cluster threshold).
- Other cells sized to keep BC3's per-cell power floor satisfied where possible; underpowered cells will read `insufficient_to_assert`, not pass (by design).

## 5. ⚠ Clinical decisions to make at approval (not engineering's to settle)

1. **ID-OOS membership** — confirm the listed concerns (anger, body-image, OCD, addiction, perfectionism, parenting) are genuinely uncovered by the 25 skills, not ones you'd map to an existing skill.
2. **The in_scope ↔ id_oos line per skill** — whether a borderline presentation belongs to a skill or should ABSTAIN. This is the routing-quality boundary; clinician owns it.
3. **⚠ Khaleeji authenticity — NATIVE-DIALECT REVIEW REQUIRED.** I author AR candidates with somatic/idiomatic framing, but I **cannot self-certify** dialect authenticity. Clinician approval covers AR **only if native-Khaleeji-competent**; otherwise the AR set routes to a native reviewer (author ≠ reviewer, F6) before it is valid. This is the §3a line — native-dialect competence is non-substitutable.

## 6. Completion plan (staged, fastest-with-quality)

1. **Now:** this methodology + a quality **seed** (a few clusters fully authored EN + ID-OOS + far-OOS + AR candidates) — the template + quality bar.
2. **On approval of approach:** expand to full per-skill min-N (≈8/skill EN) + the ~65 `ar/id_oos` cell, across all 25 skills + ID-OOS + far-OOS. (Parallelizable; can fan out per cluster.)
3. **AR native review** of every Khaleeji cell before sign-off.
4. **Freeze** (CRADLE-style, §6) once clinician + native reviewer sign — then the §2 calibration / §5 flip gate run on real held-out data.

The seed accompanies this doc (`tests/fixtures/routing_eval/dataset_seed.jsonl`). Approve the approach + seed, flag any of §5's clinical decisions, and I author the full set against it.
