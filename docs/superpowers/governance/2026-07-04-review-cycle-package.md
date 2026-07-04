# BOT BEHAVIOUR Ingestion — Review-Cycle Package (2026-07-04)

**Purpose.** One entry point for the clinician and the team to approve the BOT BEHAVIOUR ingestion work. **Design principle (per best practice):** the clinician wrote the spec, so most items below are **"confirm I read your spec correctly,"** not "decide from scratch." Each carries the spec citation, a recommended reading, and an **Approve / Reject / Edit** line. Only §B items are genuinely open.

**Approves:** the *mechanism* to ingest the spec + the *measurement instrument* (fixtures). **Does NOT approve:** production content changes, external launch, or the §D deferrals.

---

## §A — Confirm my reading of your spec (the spec already answers these)

Each: **the spec's own words → my reading → your call.** Rejecting sends it to §B.

### A1 — Node-1 route precedence
- **Spec says:** crisis "overrides everything" and "Severity-tier logic never supersedes the crisis guard" (§C, §F); the medical red-flag "applies at every tier… regardless of which tier… don't let a 'mild' or 'moderate' classification suppress it" (§1); §HR "takes priority… the same way crisis category does."
- **My reading:** all safety routes (crisis, medical red-flag, high-risk, IPV) beat tier/category — **this is your spec, not my invention.** The *only* piece the spec doesn't rank explicitly is the order *among* safety routes on a rare simultaneous hit; I propose **crisis > medical > HR > IPV**, with all fired flags still recorded.
- ☐ Approve reading (all-safety-over-tier) + ☐ approve the inter-safety order `crisis>medical>HR>IPV` · ☐ Reject · ☐ Edit the order: ________________

### A2 — Burnout "physical health symptoms" (this dissolves my earlier "gate-blocking" flag)
- **Spec says:** there is **one** medical red-flag set — the §1 cardiac/stroke descriptors — that "applies at every tier," and other categories invoke it "per the anxiety category's medical guard" (§ anticipatory / line 305). S5a says burnout "physical health symptoms → medical evaluation."
- **My reading:** burnout **inherits the universal §1 red-flag set** (crushing/spreading chest pain, one-sided numbness, real breathlessness) rather than needing a separate symptom list. So E3's acute gate is the universal set (11 cardiac) + the sleep-specific S1b signs (snoring/gasping/choking) — **not an n=1 burnout list.** *I earlier mis-flagged this as gate-blocking; if you confirm the inheritance, that block is gone.*
- ☐ Approve (burnout inherits the universal §1 red-flags; no separate list) · ☐ Reject · ☐ Edit — burnout also warrants these distinct symptoms: ________________

### A3 — Fact vs Opinion: fold, not a new skill
- **Spec says (§5b, verbatim):** "use the same fact-vs-opinion distinction **from 3b**" — the spec itself treats it as **one reusable technique** shared across §3b and §5b, not a per-category skill.
- **My reading:** **fold** into the existing `cognitive_restructuring` (whose own design already blesses "a session that ends at step two is a success" = §3b's classify-not-reframe lighter touch). Output = a content adjustment to that skill (CMS re-approval), not a new skill. Full analysis in PR #116.
- ☐ Approve fold · ☐ Reject (author a separate skill — note: must be keyword-gated out of the semantic pool to avoid matching-ambiguity with cognitive_restructuring) · ☐ Edit: ________________

### A4 — The two "verify-first" facts (acknowledge, not decide)
- Psychosis detection has **never had a measured recall gate** (keyword-only, CF-006 `active:false`); coercive-control detection likewise. The spec's §HR and §6 guards assume these fire; the measurement shows they largely don't (psychosis 6.7%, IPV fear/threat 0%). E4/E7 *establish* the gates these guards depend on.
- ☐ Acknowledged — the gates are the fix · ☐ Discuss

---

## §B — Genuinely needs your input (spec is silent here)

### B1 — Precision-negative classes (optional; recall is unaffected)
The spec tables the safety *positives* richly but not the benign *look-alikes* for: E4 psychosis (social-anxiety phrasing), E4 mania (ordinary high-energy), E7 (workplace/peer "controlling"). These aren't spec requirements — they're extra rigor so the routes don't *over-fire* (which harms in the other direction: e.g. routing a numb depressed user to a psychosis referral). Recall gates fine without them.
- ☐ Author the benign look-alikes (I'll supply the discriminators) · ☐ Accept recall-only gating for now, defer precision · ☐ Edit: ________________

### B2 — Orphan signal (a question only you can answer)
The spec's 35 categories never reference `mi_readiness_ruler` and only indirectly `cbt_thought_record`. Deliberate omission or oversight?
- ☐ Deliberate (leave as-is) · ☐ Oversight (route a category to it) · ☐ Retire the skill · ☐ Edit: ________________

---

## §C — Team / engineering decisions (not clinical; listed for visibility)

- **Gap #65 — detection tier.** Measurement **eliminated keyword-only** (psychosis 6.7% / mania 0% is a category error, not a tuning gap). Live options: semantic-tier-now vs hybrid-with-deferral. Joint eng+clinical call, but primarily an engineering/scope decision.
- **Reference-inventory staleness** — `SageAI_Skills_Knowledge_Base.md` (24) vs code (27). Engineering governance fix, tracked.
- **Kill-switch defaults, POC-vs-prod re-confirm** — engineering; every extension ships default-off; baselines re-run on prod before any gate is called production-satisfied.

---

## §D — Explicitly NOT approved in this cycle (deferrals — so they can't be lost)

- **Helpline (GL-1)** — your deferral 2026-07-04; corrected copy staged, ships only on **your dial-test of 800 4673 + L0 re-sign**.
- **External launch** — NO-GO on GL-0 crisis recall (~37% vs ≥95%); no signature here changes that.
- **Naturalistic Arabic** — only deployed lexicon entries harvested; naturalistic Khaleeji/MSA/Arabizi is your TD3/TD6 content, in the debt column.
- **Response content at scale** — validating statements / psychoeducation / check-in copy across ~30 categories = the iterative tune-lane (content inventory), not this cycle.

---

## §E — Sign-off matrix

**Product owner (mechanism):** ☐ E1 ☐ E2 ☐ E3 ☐ E4 ☐ E7 ☐ §4.5 order (A1)
**Clinical lead:** ☐ §A1 precedence ☐ §A2 burnout-inherits ☐ §A3 fold ☐ E3/E4/E7 recall gates ☐ Worry Tree CMS (#116) ☐ §B1 precision ☐ §B2 orphan ☐ fixture phrases (#115)

| Role | Name | Date |
|---|---|---|
| Product owner | ______________ | ______ |
| Clinical lead | ______________ | ______ |

---

## §F — Current-detector baseline (current-vs-target; POC stack, re-confirm on prod)

| Gate | Target | Current | Note |
|---|---|---|---|
| §C / GL-0 | ≥95% | **75.8%** | direct/self-harm 100%; gap = subtle-passive rows; naturalistic CRADLE ~37% floor |
| E3 medical (universal §1 + S1b) | ≥95% | **0%** | route unbuilt; negatives 100% clean (A2 removes the n=1 concern) |
| E4 psychosis / mania / dissociation | ≥95% | **6.7% / 0% / 0%** | keyword-only ceiling → §C Gap #65 |
| E7 IPV | ≥95% | **32%** | physical-abuse 100%, fear/threat 0% (the §6a expansion); precision 100% |

---

## §G — The three PRs
| PR | Contents | Reviewer |
|---|---|---|
| **#114** | E1–E7 record, §C/§HR conversion, plan, content inventory, baselines, **this package** | PO + clinical lead |
| **#115** | 4 recall-fixture sets, harness, baseline artifact | clinical (phrases) + eng (runner) |
| **#116** | Worry Tree draft + Fact-vs-Opinion analysis | clinical (CMS) |

**GL-0 crisis recall** remains the true critical path (work order: `s2-marbert-build-plan §8`); no signature here waives it.
