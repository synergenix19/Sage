# Clinical-routing finding: acute-overwhelm routing to dbt_tipp vs grounding (C1 conflict)

**Date:** 2026-06-13
**Status:** OPEN — needs clinical adjudication before any code change reaches master
**Surfaced by:** PR #4 (engagement R1/R3/R5) rebase verification
**Scope:** PRODUCTION (origin/master) — NOT introduced by PR #4 or the rebase

## Two distinct sub-questions for the clinical lead

This doc holds **two** related-but-distinct questions. Same skill pair (grounding vs
dbt_tipp), same person to decide, but they need **different reasoning**:

- **Sub-question A (English, mechanical):** one English phrase caught in a longest-match
  keyword trap. A tiebreak fix is sufficient. Currently RED and visible in the unit-gate.
- **Sub-question B (Arabic, categorical):** whether an entire Arabic acute-vocabulary
  bucket was assigned to the most-activating technique. Not a tiebreak edge case — a
  bucketing call. Currently GREEN and looks settled; only the test markers connect it to
  this decision.

## Sub-question A — one-line for the clinical lead

Production routes "I feel completely overwhelmed, my head is spinning" to **dbt_tipp**
(the most-activating acute technique) instead of **grounding_5_4_3_2_1**, which
contradicts the C1 decision that ambiguous panic/overwhelm should default to grounding
(lower activation risk). The PR #4 rebase surfaced this; it did not cause it.

## Evidence (ground truth)

`tests/test_nodes.py::test_selects_grounding_for_overwhelmed_phrasing` asserts the
phrase routes to grounding. It fails **identically** on all three of:

- `origin/master` (a1a5a1b) — production. → `dbt_tipp`
- pre-rebase feat tip (e9079ca). → `dbt_tipp`
- rebased feat (PR #4). → `dbt_tipp`

Because the result is identical everywhere, the rebase/merge is **clean** with respect
to this behavior. The test has been **red on master**, uncaught, because `test_nodes.py`
is not in the unit-gate's curated suite (see "Gate-coverage gap" below).

## Root cause (mechanism)

Tier-1 keyword matching ranks candidates by **longest matched keyword** (the SF-1 fix,
already on master). For this phrase:

| skill | matched keyword | length |
|-------|-----------------|--------|
| grounding_5_4_3_2_1 | `spinning` | 8 |
| dbt_tipp | `overwhelmed` | 11 |

Longest-match → `dbt_tipp` wins → `candidates[0] = dbt_tipp` → routed/offered first.

This is the interaction between two independently-correct decisions:
- **SF-1 longest-match ranking** (clinically approved) — fixes registry-order shadowing.
- **C1** — ambiguous overwhelm should default to grounding (less activating; dbt_tipp is
  the member we excluded from the acute auto-substitution pool for exactly this reason).

`overwhelmed` is a dbt_tipp Tier-1 keyword (present since early dbt_tipp work; the 2026-06-08
keyword expansions f649dab/994bc15 were "interim"/"additive"). Under longest-match, that
keyword outranks grounding's `spinning` whenever both appear.

## Why this is narrow (the fix does not endanger the 2026-06-08 decision)

Decision 25634a3 (2026-06-08, clinically approved): acute flooding like "I can't calm
down" must route to **dbt_tipp**, not grounding. Verified the overlap set:

- `"i can't calm down"` → **only dbt_tipp** keyword-matches (grounding's variant was removed
  by 25634a3). Routes to dbt_tipp regardless of any tiebreak. **Unaffected.**
- `"overwhelmed ... spinning"` → **both** grounding and dbt_tipp match. Only here does the
  tiebreak decide.

So a tiebreak that prefers grounding **only when grounding and dbt_tipp both keyword-match**
satisfies C1, preserves 25634a3, and leaves SF-1 longest-match intact for every other skill
pair.

## Proposed fix (pending clinical confirmation) — NOT yet applied

Recommended (most surgical, reviewable): when the Tier-1 keyword candidate set contains
**both** `grounding_5_4_3_2_1` and `dbt_tipp`, prefer grounding as the primary candidate
(it is the lower-activation acute technique per C1). This is a clinical-priority tiebreak
scoped to the acute overlap, not a change to the longest-match algorithm and not a keyword
edit. The red test becomes the proof.

Alternative (clinical-content path): remove/re-bucket `overwhelmed` from dbt_tipp so it no
longer wins ambiguous overwhelm — this is a `target_presentations` edit and needs the same
sign-off as any clinical-content change; it also has wider blast radius than the tiebreak.

**This change touches production safety-routing and adjudicates between two signed
decisions (C1 vs the dbt_tipp keyword set). It must not be bundled into the engagement
PR #4, and must not reach master without clinical sign-off.**

## Sub-question B — Arabic acute-vocabulary bucketing (categorical, GREEN, needs the lead)

Distinct from A. The Arabic skill-routing tests assert that a set of Arabic acute phrases
route to **dbt_tipp**. Mechanically these are NOT the longest-match trap of A — each phrase
matches dbt_tipp **only** (no grounding keyword overlap), so the Sub-question-A tiebreak fix
leaves them unchanged. The question is therefore not mechanical but **categorical**: was an
entire Arabic acute-vocabulary bucket assigned to the most-activating technique (dbt_tipp)
when C1 might place some of it in grounding?

Phrases in scope (from `tests/test_skill_select.py`), with engineering-informed leans —
**input for the lead to weigh, not a decision**:

| Arabic phrase | gloss | engineering lean (lead decides) |
|---|---|---|
| `محتاج أهدى بسرعة` | "I need to calm down fast" | leans **acute-flooding** (→dbt_tipp): rapid-downregulation request |
| `التنفس ما يساعد` | "breathing doesn't help" | leans **acute-flooding** (→dbt_tipp): failed first-line technique, asks for stronger |
| `التنفس ما كافي` | "breathing isn't enough" | leans **acute-flooding** (→dbt_tipp): same — TIPP's actual indication |
| `أحتاج شيء أقوى من التنفس` | "I need something stronger than breathing" | leans **acute-flooding** (→dbt_tipp) |
| `مشاعري أقوى من قدرتي` | "feelings stronger than my ability to handle them" | **most ambiguous — flag hardest**; reads closer to ambiguous overwhelm (C1 → grounding) |

Why this needs a trip-wire: A is red and visible; B is **green and looks settled**. If the
lead re-buckets acute-overwhelm vocabulary toward grounding, the Arabic tests asserting
dbt_tipp become wrong and **nothing else flags them**. The `C1/#15 TARGET NOTE` markers on
`test_dbt_tipp_keyword_arabic` and `test_dbtipp_interim_ar_phrase_routes_via_keyword` are the
only thread connecting these tests to this decision — they point here. If the lead re-buckets
any of the above toward grounding, update those test assertions accordingly.

## Gate-coverage gap (RESOLVED for the gate; root finding stands)

`test_nodes.py` previously sat **outside** the unit-gate (#9) curated suite, so Sub-question A
was red in production invisibly. **Fixed on the PR #4 branch (2026-06-13):** `test_nodes.py`
is now in the unit-gate, which consequently goes RED solely on Sub-question A — documented on
PR #4. A master-wide gate expansion should ride with the Sub-question-A fix PR so the coverage
is permanent, not branch-local.

## Engineering-informed evidence synthesis (INPUT for the clinical lead — not a decision)

Requested by the clinical lead 2026-06-13. This is a literature synthesis to inform the
two sub-questions; the bucketing call remains the lead's. Epistemic note: evidence below is
from clinical/DBT secondary sources, not Sage's own data — weight accordingly.

**What the evidence says about TIPP vs 5-4-3-2-1:**

1. **TIPP is a first-line skill for *extreme, confirmed* crisis arousal** — emotion at 9–10/10,
   urge to act on a harmful impulse, "emotion mind threatens to overwhelm." It works by
   interrupting physiological arousal (cold-water dive reflex → parasympathetic). It is the
   *escalation* skill when lower-intensity coping is insufficient.
2. **5-4-3-2-1 grounding is the circuit-breaker for acute anxiety/panic onset and dissociation**
   (originally trauma-flashback grounding). Sensory engagement; works across hyper- AND
   hypo-arousal.
3. **Window of tolerance:** match calming skills to hyperarousal (panic, racing, "spinning"),
   activating/sensory skills to hypoarousal (numbness, dissociation). Ambiguous presentations
   sit between — arousal level is the discriminator, and it is exactly what is unknown here.
4. **TIPP carries real medical contraindications** (cardiac, eating disorders, beta-blockers,
   cold allergy; intense-exercise risk). 5-4-3-2-1 has none.
5. **Autonomous-delivery caveat (decisive for an unscreened chatbot):** self-help apps deliver
   the same intervention to all users *without* the clinician's continuous evaluation that DBT
   assumes. Recommending cold water / intense exercise to a medically unscreened user is a
   documented safety concern. For *ambiguous* presentations the lower-risk skill is the safer
   autonomous default. This is the evidentiary basis for C1's "lower activation risk," extended
   to "lower medical risk under autonomous delivery."

**Recommendation, per sub-question:**

- **Sub-question A — affirm C1; implement the tiebreak.** "Overwhelmed, head spinning" has no
  extremity marker (no 9–10, no failed-technique, no impulse-to-harm) and "spinning" is
  panic/derealization-adjacent — i.e. ambiguous arousal. For an unscreened autonomous turn,
  grounding is the appropriate lower-risk default. Evidence supports grounding-preferred on the
  grounding∩dbt_tipp overlap. (Engineering fix is narrow and ready; sign-off authorizes it.)

- **Sub-question B — split the Arabic bucket, do not treat it as one decision:**

  | Arabic phrase | gloss | evidence-based lean |
  |---|---|---|
  | `التنفس ما يساعد` / `التنفس ما كافي` / `أحتاج شيء أقوى من التنفس` | "breathing doesn't help / isn't enough / I need something stronger than breathing" | **KEEP → dbt_tipp.** This is TIPP's *literal* stepped indication: the user reports paced breathing failed and asks for escalation; temperature/exercise are "stronger than breathing." Correctly bucketed. |
  | `محتاج أهدى بسرعة` | "I need to calm down fast" | **dbt_tipp acceptable (lower confidence).** Urgency signals acute distress (TIPP's rapid-reset purpose) but no extremity/failed-technique marker. Defensible; the weakest of the keep-TIPP set. |
  | `مشاعري أقوى من قدرتي` | "feelings stronger than my ability to handle them" | **RE-BUCKET → grounding (recommend).** Generic overwhelm, no somatic/arousal/failed-technique marker — the most C1-ambiguous phrase; matches A's logic. Safer as grounding under autonomous delivery. (Matches the lead's own "flag hardest" instinct.) |

- **Cross-cutting safety recommendation (separate from routing, for the lead to weigh):**
  whatever routes to dbt_tipp should, under autonomous unscreened delivery, **lead with the
  lowest-risk TIPP components (paced breathing / paired muscle relaxation)** and/or carry a brief
  contraindication note **before** suggesting cold water or intense exercise (cardiac, eating
  disorder, beta-blocker, cold allergy). This is the autonomous analog of the clinician's
  continuous evaluation DBT assumes, and a dbt_tipp *skill-content* question — not a routing fix.
  Connects to the existing constraint that chatbot-autonomous delivery of some protocols is not
  yet validated.

**Sources:** DBT TIPP indications/components — dialecticalbehaviortherapy.com, emotionallysensitive.com,
manhattancbt.com; TIPP contraindications — manhattancbt.com, ncbi.nlm.nih.gov (PMC6870536);
5-4-3-2-1 indications & hyper/hypo-arousal matching — simplypsychology.com, illuminatedthinking.co.uk;
window of tolerance — psychologytools.com, ptsduk.org; unscreened self-help app safety —
PMC5688908, PMC7025360.

## Clinical-lead decisions (2026-06-13) — APPROVED, relayed via product owner

The discriminator is accepted: **arousal level + confirmation of extremity; under autonomous
delivery, lower medical risk is the default for ambiguous presentations.**

1. **A (English #15) — APPROVED → grounding.** Implement the grounding∩dbt_tipp tiebreak.
   Own signed master PR, sibling to #6/#8. `approved_by: clinical_lead, 2026-06-13`.
2. **B.1 — APPROVED, KEEP → dbt_tipp:** `التنفس ما يساعد` / `التنفس ما كافي` /
   `أحتاج شيء أقوى من التنفس` (failed-first-line / "stronger than breathing" = TIPP's literal
   stepped indication). No change. `approved_by: clinical_lead, 2026-06-13`.
3. **B.2 — APPROVED, RE-BUCKET → grounding:** `مشاعري أقوى من قدرتي` ("feelings stronger than
   my ability") — generic overwhelm, no arousal/somatic/failed-technique marker; the most
   C1-ambiguous phrase. Move to grounding. `approved_by: clinical_lead, 2026-06-13`.
4. **B.3 — HELD pending one confirmation:** `محتاج أهدى بسرعة` ("need to calm down fast").
   The lead's own discriminator points to **grounding** (urgency is not extremity; no
   failed-technique marker), not the "lower-confidence dbt_tipp" the prior bucketing implies.
   **Question back to the lead:** "Is urgency *alone* sufficient to route to the escalation
   skill, or does this fall to the lower-risk default like the other ambiguous cases?" Until a
   confident call, the test target is **unchanged (dbt_tipp)** and NOT implemented toward
   grounding — a "lower-confidence" assertion on an acute-routing safety surface is an audit risk.

### Open follow-ups surfaced by the decisions (for the lead, not auto-resolved)

- **EN/AR consistency:** B.2 moves the Arabic phrase only. The English generic-overwhelm
  neighbors in dbt_tipp (`emotions are too much`, `feelings are unbearable`, `I can't handle
  this`) were NOT adjudicated. By the same discriminator they may also belong in grounding.
  Flag for the lead; not changed here.
- **Recalibration:** B.2 moves a Tier-1 `target_presentations` keyword only — no
  `semantic_description`/`semantic_anchors` change — so per the calibration protocol it does
  NOT trigger `calibrate_threshold.py`. Noted for verification, not assumed silently.

## Structural finding — reactive phrase-by-phrase adjudication leaves neighbors unreviewed

The C1 thread has cleaned acute routing one phrase at a time, at the points where a test
happened to assert something. Every generic-overwhelm phrase in `target_presentations` that
**no test asserts** keeps its original (possibly wrong) bucket, unreviewed, until a future
test or a real user trips it. The thread already produced visible inconsistencies:

- B.2 moved `مشاعري أقوى من قدرتي` → grounding, but the near-twins **`مشاعري أقوى مني`**
  ("feelings stronger than me") and **`مشاعري فوق طاقتي`** ("feelings beyond my capacity")
  still sit in dbt_tipp.
- B.3 moved Arabic `محتاج أهدى بسرعة` → grounding, but the English twins **`need to calm down
  fast`** / **`I need to calm down`** still sit in dbt_tipp.
- The #15 keyword **`overwhelmed`** / `I'm overwhelmed` still routes dbt_tipp on a bare match —
  the A tiebreak only catches the grounding∩dbt_tipp *overlap*, not a lone "I'm overwhelmed".

### Proposed proactive fix (one comprehensive clinical pass, not more reactive patches)

Enumerated dbt_tipp `target_presentations` (post A/B.2/B.3), bucketed by the lead's
discriminator. **Candidates are engineering-flagged input; the lead adjudicates the whole list
at once.** Nothing below is re-bucketed without that sign-off.

**KEEP dbt_tipp — failed-first-line / explicit escalation:** `breathing isn't working`,
`breathing is not enough`, `too intense to breathe through`, `need something stronger than
breathing`, `breathing won't help right now`, `need an intense physical reset`, `need something
much stronger`, `bring my body down`; AR `التنفس ما يساعد`, `التنفس ما كافي`, `أحتاج شيء أقوى من التنفس`.

**KEEP dbt_tipp — confirmed extremity / urge-to-act / scale / explicit skill request:**
`urge to act out`, `I'm about to explode`, `emotions are at a ten`, `I'm too activated`,
`flooded`, `TIPP`, `tipp technique`, `distress tolerance`, `cold water technique`;
AR `أشعر إني سأنفجر`, `غاضب جداً` (borderline).

**KEEP dbt_tipp — acute inability (signed 25634a3, "can't calm down"):** `can't calm down`,
`cant calm down`; AR `ما أقدر أتحكم`, `ما أتحمل` (borderline).

**CANDIDATES for grounding (ambiguous overwhelm, no failed-first-line/extremity marker — the
"invisible" bucket the lead should rule on):**
- EN: `overwhelmed`, `I'm overwhelmed`, `im overwhelmed` (bare-match #15 residue);
  `need to calm down fast`, `I need to calm down` (B.3 English twins — immediate inconsistency);
  `emotions too intense`, `emotions are too much`, `unbearable feelings`, `feelings are
  unbearable`, `I can't handle this`, `cant handle this`, `I'm losing it`, `im losing it`;
  borderline `feeling out of control`, `losing control` (could read as extremity).
- AR: `مشاعري أقوى مني`, `مشاعري فوق طاقتي` (near-twins of the moved B.2 phrase — immediate
  inconsistency); `شعور طاغي` (overwhelming feeling).

### Lock the corpus going forward (test design — NOT asserting current buckets)

A bucket-lock regression test should assert each acute-cluster phrase against the bucket the
**lead decides** in the audit — authored *after* the audit, not now (asserting today's
un-adjudicated buckets would "bless" the very state under question, the same trap the Arabic
offer tests fell into). Going forward, a new acute-cluster keyword requires a recorded bucket
decision + its lock-test entry, so neighbors can't re-enter the corpus unreviewed. Tracked as
its own task; this is the proactive replacement for reactive phrase-by-phrase cleanup.

### Audit status (2026-06-14) — first tranche shipped in PR #12; worklist needs the lead's ruling

**DONE (signed-precedent EN/AR consistency completions, in PR #12):**
- `مشاعري أقوى مني`, `مشاعري فوق طاقتي` → grounding (B.2 twins)
- `need to calm down fast`, `I need to calm down` → grounding (B.3 EN twins)
- `test_acute_cluster_bucket_lock` seeded over DECIDED phrases only (a move now needs sign-off
  + a governance entry). `test_dbt_tipp_keyword_match` message updated (old compound straddled
  the new boundary).

**WORKLIST — needs the lead's per-phrase ruling (engineering lean noted; NOT shipped):**
Implementing the audit surfaced two reasons these are not clean mechanical moves:
1. **Distress-intolerance vs ambiguous-overwhelm coin-flips.** `unbearable feelings` / `feelings
   are unbearable`, `I can't handle this` / `cant handle this`, `emotions too intense` /
   `emotions are too much` use distress-*tolerance* language (TIPP's own domain) yet lack an
   extremity/failed-line marker. Genuine clinical coin-flips — engineering will not guess them.
2. **`overwhelmed` family is FP-entangled.** `overwhelmed` / `I'm overwhelmed` / `im overwhelmed`
   is a dbt_tipp keyword **specifically to block a sleep_hygiene semantic false-positive**
   (`test_overwhelmed_and_anxious_matches_dbt_tipp` asserts it → dbt_tipp today — itself a
   #15-sibling that contradicts C1). Moving it to grounding is *probably* right per C1 and the
   keyword would still block the sleep FP from grounding, but it re-touches a signed FP guard,
   so it needs an explicit ruling + FP re-verification, not a blind move.
3. **Control-loss** (`feeling out of control`, `losing control`) is extremity-adjacent (the
   out-of-control/urge-to-act state TIPP targets) — engineering lean: KEEP dbt_tipp.

Recommended ruling (lead to confirm each): overwhelmed family → grounding (FP re-verified);
`I'm losing it`/`im losing it`, `شعور طاغي` → grounding; the distress-intolerance trio → lead's
call; control-loss → keep dbt_tipp. On ruling, each moves + gains a bucket-lock entry in one pass.

## Item 4 — dbt_tipp content safety under autonomous delivery (PRE-PILOT, highest severity)

**This is broader than any bucketing decision and ranks above them.** It protects *every* user
who reaches dbt_tipp by *any* path — including the unambiguous ones nobody disputes.

Recommending **cold-water immersion or intense exercise** to a **medically unscreened** user
(cardiac, eating disorder, beta-blockers, cold allergy) is a real harm surface that exists
regardless of routing. DBT presumes a clinician's continuous evaluation; an autonomous chatbot
has none. The autonomous analog:

- dbt_tipp `entry_screen` + step ordering must **lead with the lowest-risk components**
  (paced breathing, paired muscle relaxation), and
- carry a **contraindication note** *before* the cold-water / intense-exercise components.

This is **skill-authored clinical content** (entry_screen + steps), so it is a **separate
clinically-authored, signed work item** — NOT a routing fix and NOT something engineering
authors. Severity: **pre-pilot blocker** on the same logic as the S2-7 contraindication concern —
an unscreened user getting a cold-water instruction should not be live during a pilot. Tracked as
its own task; flagged to the clinical lead at that severity, not as a footnote.

### Engineering assessment of the CURRENT dbt_tipp content (2026-06-14) — changes what's needed

dbt_tipp **already has** much of this, which narrows the actual work:
- **Step 0 `entry_screen` already exists** and is the contraindication gate: it asks one
  physical-readiness question *before* any physical component, and its `contraindications` /
  `completion_criteria` hold + redirect (to box breathing / grounding) on cardiac, pacemaker,
  arrhythmia, disability, injury, or disordered eating — naming the cold-water/bradycardia and
  electrolyte risks explicitly. So "screen before cold water" (Item 4 part b) is **largely
  satisfied today.**
- **`cultural_overrides`** already give cold-water alternatives (wrists/neck for hijab/niqab)
  and modest-exercise alternatives.
- **What is NOT done (the real residual):** step *order* still leads with `temperature`
  (cold water) → `intense_exercise` → `paced_breathing`. Item 4 part (a) wants paced
  breathing first. There is **no PMR step** to add.

**The residual is a genuine clinical tradeoff, not a mechanical edit.** Standard TIPP leads
with Temperature precisely because the dive reflex is the fastest interrupt for *confirmed
extreme* arousal — which, after the routing fixes, is now mostly what reaches dbt_tipp.
"Lead with low-risk" trades that speed for safety. With the entry_screen already gating
contraindications, the marginal safety gain of reordering vs the efficacy cost is a clinical
call, and reordering requires **rewriting the step transitions** (clinical authoring). So
engineering will **not** unilaterally reorder the live crisis protocol. **Decision needed from
the lead:** given the entry_screen gate already exists, is the step-reorder still wanted (and if
so, clinical authoring produces the reordered sequence + transitions), or does the existing gate
suffice for pilot? Engineering can apply a signed, authored reorder mechanically once provided.

## Disposition

- Sub-question A test left **red and unchanged** (assertion is correct per C1; tracked baseline).
  Now covered by the unit-gate (red, documented on PR #4).
- Sub-question B Arabic tests assert **dbt_tipp-direct** (entry-mechanism realigned for the
  Arabic-exclusion gate) with `C1/#15 TARGET NOTE` markers pointing here; assertions unchanged
  pending the lead's bucketing call.
- No production routing/keyword change applied. Both sub-questions await clinical adjudication;
  the signed answer authorizes a **separate** master PR (sibling of #6/#8), never inside PR #4.
