# BOT BEHAVIOUR Ingestion — Review-Cycle Package (2026-07-04)

**Purpose.** One entry point for the clinician and the team to review and approve the BOT BEHAVIOUR ingestion work. Start here; it routes you to the three PRs, tells you who signs what, and lists every decision with what it unblocks. **A reviewer should be able to start from this page alone.**

**What this cycle approves:** the *mechanism* to ingest the clinician BOT BEHAVIOUR spec (routing/skill architecture) and the *measurement instrument* (recall fixtures). **What it does NOT approve:** production content changes, external launch, or the deferred items in §6. The architecture holds the words; content is the iterative tune-lane after.

---

## 1. The three PRs and who reviews each

| PR | Contents | Primary reviewer | Nature |
|---|---|---|---|
| **#114 — Mechanism** | E1–E7 approval record, §C/§HR conversion map, ingestion plan, content inventory, measured baselines | **PO** (mechanism) + **Clinical lead** (safety gates + precedence) | Signature request |
| **#115 — Fixtures + harness** | 4 recall-fixture sets (§C/E3/E4/E7), the measurement harness, the baseline artifact | **Clinical lead** (phrase selections) + **Eng** (runner) | Content review |
| **#116 — Worry Tree draft + Fact-vs-Opinion analysis** | Worry Tree skill draft; §3b fold-vs-new recommendation | **Clinical lead** (CMS) | Draft review + one decision |

None blocks another for *review* — all three can be reviewed in parallel.

---

## 2. Sign-off matrix — who signs what

**Product owner (mechanism):**
- ☐ E1 supervisor + `care_pathway` (`switch_skill` action)
- ☐ E2 category/skill-group metadata
- ☐ E3 medical red-flag route (mechanism)
- ☐ E4 high-risk route (mechanism)
- ☐ E7 coercive-control pre-emption (mechanism)
- ☐ §4.5 Node-1 precedence order

**Clinical lead:**
- ☐ E3 recall gate (≥95%, fixtures) — **incl. the burnout enumeration below (§3 item 1)**
- ☐ E4 recall gate (≥95% per class, fixtures)
- ☐ E7 recall gate (≥95%, fixtures)
- ☐ §4.5 precedence order (clinical ratification)
- ☐ Worry Tree skill (CMS approval, #116)
- ☐ Fact-vs-Opinion fold-vs-new decision (#116)
- ☐ Fixture phrase review (#115 — verbatim canonical confirmed; `proposed_variants` promoted or rejected)

Complete when every box is checked. Entries are **independently signable** — sign what you've reviewed.

| Role | Name | Date |
|---|---|---|
| Product owner | ______________ | ______ |
| Clinical lead | ______________ | ______ |

---

## 3. Decision items requiring a clinician answer (typed by urgency)

**⛔ Gate-blocking (1) — a gate cannot be measured until answered:**
1. **Enumerate the S5a burnout physical red-flags.** E3's `burnout_physical` sub-class has n=1 (the spec says "significant physical health symptoms" but names none); a ≥95% gate over n=1 is not a measurement. Engineering did not invent symptoms — the spec gap is the author's. *(PR #115 / record §f.)*

**✎ Non-blocking authoring (1) — recall gates fine; precision needs your negatives:**
2. **Author the under-tabled precision-negative classes:** E4 psychosis (social-anxiety), E4 mania (ordinary high-energy), E7 (non-partner "controlling" / ordinary conflict). The spec tables no benign look-alikes; over-firing here is a harmful miss in the *other* direction. Discriminators are recorded in each fixture. *(PR #115.)*

**◆ Decisions (3):**
3. **§4.5 precedence order** — ratify `crisis > medical > HR > IPV > tier/category`. This is a clinical decision; it unlocks Phase-B routing-order finalization. *(PR #114.)*
4. **Gap #65 — semantic-tier vs hybrid.** The measurement **eliminated keyword-only** (baseline psychosis 6.7% / mania 0% / dissociation 0% — a category error, not a tuning gap). Live options: (b) semantic tier now, or (c) hybrid with production deferral. Joint eng+clinical call. *(PR #114 plan §5.2.)*
5. **Fact-vs-Opinion — fold or new skill.** Recommendation: **fold** into `cognitive_restructuring` (its own design already blesses "ending at step two is a success" = §3b's classify-not-reframe). Flips to NEW only if the high-shame population must be structurally prevented from reaching the reframe. *(PR #116.)*

**ℹ Informing sign-off (3) — facts the gates exist to fix / governance:**
6. **Psychosis detection has never had a measured recall gate** (keyword-only, CF-006 `active:false`). E4 establishes it.
7. **Coercive-control detection likewise unmeasured** (keyword-only). E7 establishes it; §6 skills already declare the guard in prose, which E7 makes deterministic.
8. **Orphan signal + reference-inventory staleness** — the spec never references `mi_readiness_ruler` (deliberate?); `SageAI_Skills_Knowledge_Base.md` lists 24 skills vs 27 in code (governance fix tracked).

---

## 4. Current-detector baseline — what each gate's target sits against today

Measured 2026-07-04 (harness PR #115) on the POC `safety_check`. **Caveat: re-confirm on the production detector config before any gate is declared production-satisfied.**

| Gate | Target | Current (measured) | Note |
|---|---|---|---|
| §C / GL-0 | ≥95% | **75.8%** canonical table | Direct-SI/self-harm 100%; gap = subtle-passive rows (wanting-pain-to-stop 0/2, loss-of-self-trust 0/2). Naturalistic CRADLE ~37% is the harder floor. |
| E3 medical | ≥95% | **0%** | Route unbuilt; negatives 100% clean. `burnout_physical` gate **held** (item 1). |
| E4 psychosis | ≥95% | **6.7%** (1/15) | Keyword-only ceiling → Gap #65 evidence |
| E4 mania / dissociation | ≥95% | **0% / 0%** | No triggers exist |
| E7 IPV | ≥95% | **32%** | Physical-abuse 100%, **fear/threat 0%** (the §6a expansion); precision 100% |

Deployed Arabic lexicon entries fire 100% (validates the path; naturalistic Arabic is TD3/TD6 debt, not covered).

---

## 5. What each approval unblocks (sequencing)

```
Signatures + clinician answers
  ├─ §4.5 ratified ─────────────→ Phase B routing order finalized
  ├─ Gap #65 (b/c) decided ─────→ E4/E7 recall approach fixed
  ├─ burnout enumerated ────────→ E3 burnout_physical gate becomes measurable
  ├─ E3/E4/E7 gates signed ─────→ build the safety routes (kill-switched, default off)
  ├─ E1/E2 signed ──────────────→ build the tier supervisor + category grouping
  ├─ Worry Tree CMS-approved ───→ register + activate the skill
  └─ Fact-vs-Opinion decided ───→ fold (cog_restructuring re-approval) OR new draft

GL-0 crisis recall (S2/MARBERT, per-row work order in s2-marbert-build-plan §8)
  └─ the pilot's TRUE critical path — no signature here waives it; gates external launch.
```
No build step is authorized until its extension entry is signed AND its preconditions clear (ingestion plan §0/§6).

---

## 6. Explicitly NOT approved in this cycle (deferrals — tracked so they can't be lost)

- **Helpline correction (GL-1)** — product-owner deferral 2026-07-04; corrected copy staged as commit-2, **ships only on your dial-test of 800 4673 + L0 re-sign**. Prod stays on `800 46342`/"24/7" (mislabelled-but-reachable, 999 co-listed) under the recorded risk acceptance.
- **External launch** — NO-GO on GL-0 recall (~37% vs ≥95%). No signature here changes that.
- **Naturalistic Arabic** — only deployed lexicon entries are harvested; naturalistic Khaleeji/MSA/Arabizi is TD3/TD6 clinician/native-speaker content, in the debt column.
- **Production-config re-confirmation** — baselines are POC-stack; re-run on prod before any gate is production-satisfied.
- **Response content at scale** — validating statements, psychoeducation, check-in copy across ~30 categories are the iterative tune-lane (content inventory), not this cycle.

---

## 7. Index of artifacts

**#114:** `extensions-e1-e7-approval.md` (the signable anchor) · `crisis-hr-protocol-conversion.md` · `bot-behaviour-ingestion-plan.md` · `bot-behaviour-content-inventory.md` · this package.
**#115:** `tests/fixtures/bot_behaviour/{crisis_sc,medical_e3,hr_e4,ipv_e7}_recall.json` · `scripts/bot_behaviour_recall_baseline.py` · `recall_baseline_2026-07-04.json`.
**#116:** `docs/cms-drafts/worry_tree.draft.json` + the Fact-vs-Opinion analysis (PR description).
**GL-0 work order:** `s2-marbert-build-plan.md §8` (per-row targets).
