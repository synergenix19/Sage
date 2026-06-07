# Skill Routing Audit v5 — Phase 1 Taxonomy

**Date:** 2026-06-07  
**Scope:** 27 EN skills; 27 AR skills; KB endpoint (4 probes, all PASS)  
**Skill count:** 27 total · 2 flag-gated/untestable (post_crisis_check_in, psychotic_referral) · **25 directly testable**  
**Final scores:** EN 12/25 (48%) · AR 13/25 (52%) · KB 4/4 (100%)  
**Method:** Serial (concurrency=1), 5–6 turns per skill, production endpoint  
**Connection-leak fix applied pre-run:** asyncio.wait_for + PgBouncer pool exhaustion (commit 5acbf04)  
**Keyword fix applied mid-run:** `safe_place_visualization` "safe place" added (commit ebd6bb5) — audit result predates fix  

---

## EN Results (25 directly testable; 2 flag-gated skills excluded — see Coverage Gap below)

| Index | Skill | EN Result | Mechanism | Harm-on-miss | Fix tier |
|-------|-------|-----------|-----------|--------------|----------|
| 0 | cbt_thought_record | PASS | — | — | — |
| 1 | grounding_5_4_3_2_1 | PASS | — | — | — |
| 2 | sleep_hygiene | PASS | — | — | — |
| 3 | post_crisis_check_in | not directly testable | Flag-triggered auto-select (crisis_state: monitoring); no direct keyword path by design | — | Audit harness: set up crisis state first |
| 4 | box_breathing | PASS | — | — | — |
| 5 | mood_check_in | PASS | — | — | — |
| 6 | behavioral_activation | PASS | — | — | — |
| 7 | worry_time | PASS | — | — | — |
| 8 | mi_readiness_ruler | DRIFT → PMR | Intent-route: ambivalent motivation → general_support; skill_select bypassed | HIGH — MI is the technique for pre-contemplative ambivalence; freeflow misses the therapeutic frame | Post-Gitex: intent_route redesign |
| 9 | stop_technique | DRIFT → cbt_thought_record | **Test artifact**: trigger phrase "intrusive thoughts" is a cbt_thought_record [0] keyword; not a routing system failure | N/A | Re-run with clean phrase |
| 10 | progressive_muscle_relaxation | PASS | — | — | — |
| 11 | safe_place_visualization | DRIFT → worry_time | **Keyword gap**: "safe place" absent; only "safe space" variants present | MEDIUM | **FIXED** ebd6bb5 |
| 12 | dbt_tipp | DRIFT → mi_readiness_ruler | Intent-route: acute escalating distress → general_support; skill_select bypassed | **CRITICAL** — sole purpose-built physical down-regulation skill; freeflow during distress spiral is clinically inadequate | Post-Gitex: intensity signal |
| 13 | psychoed_anxiety | DRIFT → box_breathing | Intent-route: "what is anxiety" → info_request → KB; late physical-symptom drift into box_breathing | LOW-MEDIUM | Post-Gitex: intent_route |
| 14 | psychoed_depression | DRIFT → cbt_thought_record | Intent-route: info_request/freeflow; never activated; drifted turn 4 | LOW-MEDIUM | Post-Gitex: intent_route |
| 15 | psychoed_stress | PARTIAL → DRIFT (financial_anxiety) | Activated turns 1–2 correctly; lost skill lock when turn 3 used work/deadline language matching financial_anxiety keywords | LOW | Keyword de-conflict: financial_anxiety |
| 16 | values_clarification | DRIFT (freeflow, no activation) | Intent-route: exploratory values framing → info_request/general_support; freeflow LLM generated on-topic content without skill being selected; both headers absent confirms skill_select never ran | LOW (UX) / HIGH (audit) | Post-Gitex: intent_route |
| 17 | assertive_communication | DRIFT → interpersonal_effectiveness | **Keyword gap**: trigger phrase landed in interpersonal_effectiveness semantic territory; assertive_communication keywords too narrow; routes to interpersonal_effectiveness [21] (HIGHER index — not a precedence issue) | MEDIUM | Keyword expansion for assertive_communication |
| 18 | self_compassion_break | DRIFT → cbt_thought_record | **Dominant shadower**: self-criticism/compassion language captured by cbt_thought_record [0], 18 positions ahead | MEDIUM — CBT addresses cognition, not self-compassion; different mechanism | Best-match scoring in skill_select |
| 19 | mindfulness_body_scan | PASS | — | — | — |
| 20 | cognitive_restructuring | DRIFT → worry_time | **Dominant shadower**: catastrophizing language captured by worry_time [7], 13 positions ahead | MEDIUM — worry scheduling ≠ cognitive restructuring | Best-match scoring in skill_select |
| 21 | interpersonal_effectiveness | PASS | — | — | — |
| 22 | financial_anxiety | PASS | — | — | — |
| 23 | grief_loss | PASS | — | — | — |
| 24 | psychotic_referral | Expected freeflow + CRISIS_DETECTED | **No keyword path by design**: empty target_presentations; activates ONLY via `psychotic_disclosure` clinical flag (skill_select.py:115-131). Turn 1 freeflow is expected. Turn 2 CRISIS_DETECTED is correct safety behavior. Turn 3 post_crisis_check_in is correct follow-up. Not a routing bug — a clinical design gap (Turn 1 freeflow is uncontrolled before flag is set) | MEDIUM — no harm but no structured referral on Turn 1 | Clinical design: add Turn 1 path or explicitly own that referral starts on Turn 2 |
| 25 | problem_solving_therapy | DRIFT → behavioral_activation | **Dominant shadower**: "problem" language captured by worry_time [7], 18 positions ahead; then drifted to BA | HIGH — PST is a structured technique; freeflow + BA is supportive but not PST | Best-match scoring in skill_select |
| 26 | act_psychological_flexibility | DRIFT → financial_anxiety | **Dominant shadower**: worry_time [7] captures action/values framing on Turn 1; ACT [26] never reached | HIGH — only acceptance-based flexibility skill; technique mismatch when replaced by scheduling or financial support | Best-match scoring in skill_select |

### EN Scorecard (of 25 directly testable)

- **PASS:** 12 of 25 (48%)
- **DRIFT — dominant shadower:** 4 (self_compassion_break, cognitive_restructuring, problem_solving_therapy, act_psychological_flexibility)
- **DRIFT — intent-route:** 6 (mi_readiness_ruler, dbt_tipp, psychoed_anxiety, psychoed_depression, psychoed_stress, values_clarification)
- **DRIFT — keyword gap:** 2 (safe_place_visualization [FIXED], assertive_communication)
- **Test artifact:** 1 (stop_technique — not a system failure; re-run needed)

> **⚠ Framing note:** 48% is an internal engineering metric on a deliberately adversarial test harness — every skill probed cold with a single turn-1 trigger phrase, no conversational lead-in, no clinical flag pre-set. It is not "the system correctly serves users half the time." Real users arrive with conversational context, multi-turn history, and varied phrasing; several of the routing failures here would self-correct after turn 2 or 3 of a natural conversation. This number should not escape into a stakeholder or Gitex deck as a product quality score — it is a coverage measurement for the routing layer under worst-case cold-start conditions.

### Coverage Gap — Two Flag-Gated Skills

**post_crisis_check_in [3]** and **psychotic_referral [24]** cannot be reached by the cold-probe harness. Both require a clinical flag to be pre-set (`crisis_state: monitoring` and `psychotic_disclosure` respectively) before skill_select will route to them. Neither has been directly validated — their steps, completion logic, and header emission are untested in both EN and AR. The AR run incidentally routed *into* post_crisis_check_in as a downstream landing point for psychotic_referral's crisis path, but that is not a direct probe of post_crisis_check_in and does not constitute a pass.

These are the two most safety-adjacent skills in the library. The audit harness backlog should include a flag-seeded test path: pre-set the relevant flag, then probe the skill directly in both languages. Until that exists, the statement "all 27 skills audited" is not accurate for these two.

---

## Failure Taxonomy — Five Buckets

### Bucket 1 — Test Artifact (1 case)

The failure is in the audit instrument, not the routing system.

| Skill | Problem | Evidence |
|-------|---------|----------|
| stop_technique | Trigger phrase "intrusive thoughts" is a cbt_thought_record [0] keyword; shadowed at first position before reaching stop_technique [9] | cbt_thought_record activated Turn 1; stop_technique's own keywords would have worked with a clean phrase |

**Action:** Re-run with e.g. "thought stopping technique" — not a code fix.

---

### Bucket 2 — Keyword Gap (2 cases)

Skill_select was reached; keyword loop found no match in the TARGET skill (though another skill may have matched). Fix is adding or sharpening the target skill's own keywords.

**Distinguishing feature:** assertive_communication routes to interpersonal_effectiveness at index [21], which is HIGHER than assertive_communication at [17]. Registry precedence cannot be the cause. Pure keyword miss. This is the diagnostic control that separates this bucket from Bucket 3.

| Skill | Missing coverage | What matched instead | Fix |
|-------|-----------------|---------------------|-----|
| safe_place_visualization | "safe place" absent; only "safe space" variants | worry_time [7] via semantic fallback | **DONE** ebd6bb5 |
| assertive_communication | Trigger phrase hit interpersonal_effectiveness semantic territory; assertive_communication keywords too narrow for natural entry phrases | interpersonal_effectiveness [21] (semantic) | Add "I can't say no", "I give in too easily", "passive aggressive", "people pleaser", "can't set limits" |

**Note on psychoed_stress mid-skill drift:** activates correctly on turn 1, then loses skill lock when turn 3 language matches financial_anxiety. Fix is keyword de-conflict (remove generic work/deadline phrases from financial_anxiety), not a keyword gap on psychoed_stress itself.

---

### Bucket 3 — Dominant Shadower (4 cases)

Skill_select was reached. The target skill HAS matching keywords for the trigger phrase, but a skill at a lower registry index matches FIRST. Registry-order-as-tiebreaker is the structural root.

**Two confirmed dominant shadowers:**
- `cbt_thought_record [0]` — swallows cognitive/self-critical language for all downstream skills
- `worry_time [7]` — swallows planning/problem/challenge/action language for all downstream skills

| Target skill | Shadowed by | Index gap | Mechanism |
|-------------|-------------|-----------|-----------|
| self_compassion_break [18] | cbt_thought_record [0] | 18 | Self-criticism language hits cbt_thought_record before self_compassion_break |
| cognitive_restructuring [20] | worry_time [7] | 13 | Catastrophizing/unhelpful-thought language hits worry_time before cognitive_restructuring |
| problem_solving_therapy [25] | worry_time [7] | 18 | "Problem" language hits worry_time before PST |
| act_psychological_flexibility [26] | worry_time [7] | 19 | Values/action-oriented language hits worry_time before ACT |

**The fix:** Score ALL Tier-1 keyword matches before committing, then select by best match (longer/more-specific phrase, more keywords hit, or a weight), not by first-found index. This is a single change to the keyword matching loop in `skill_select.py:141-153`. It dissolves all four dominant-shadower failures at once without touching the skills' keyword content.

**Why not reorder the registry?** Reordering moves the shadow to different victims; it doesn't fix the structural problem. **Why not trim shadowers' keywords?** Whack-a-mole — every phrase removed risks breaking the shadower's own legitimate activations. Best-match scoring is the correct architectural fix.

**Size estimate:** The matching loop is 12 lines (lines 141-153 in skill_select.py). Change: collect all matches, score by keyword length (longer = more specific), return highest-scoring. Edge case: tie-breaking. Estimate: 30-50 lines of change + tests. Smaller than intent_route work.

---

### Bucket 4 — Intent-Route Gap (5+ cases)

Skill_select was never reached. Intent_route classified the turn as `general_support`, `info_request`, or `continue_skill`, bypassing the matching layer entirely. This is upstream of everything in Buckets 2 and 3 — adding keywords or fixing scoring in skill_select has zero effect on these cases.

**Severity ranked by harm-on-miss:**

| Skill | Misclassification | Correct classification | Harm-on-miss |
|-------|-------------------|----------------------|--------------|
| dbt_tipp | Acute escalating distress → general_support | Should be `new_skill` — high-intensity, non-crisis, purpose-matched technique | **CRITICAL**: sole physical down-regulation skill; freeflow is clinically inadequate for a distress spike |
| mi_readiness_ruler | Ambivalent/pre-contemplative motivation → general_support | Should be `new_skill` — ambivalence IS the canonical MI entry | HIGH: MI is the therapeutic framework for motivational ambivalence |
| values_clarification | Exploratory values framing → info_request/general_support | Should be `new_skill` | MEDIUM: freeflow LLM generates plausible content but no step tracking, no audit trail |
| psychoed_anxiety | Educational "what is anxiety" → info_request | Correct for pure educational asks; wrong when there's a concurrent distress need | LOW-MEDIUM: KB response is adjacent; continuity gap |
| psychoed_depression | Similar | Similar | LOW-MEDIUM |

**Root design problem:** Intent_route is intensity-blind. It categorizes topic but not emotional intensity or therapeutic need. Acute distress expressions, ambivalent motivation signals, and low-engagement educational questions collapse into the same `general_support` or `info_request` output class. Adding keywords to skills doesn't help because skill_select isn't reached.

**Fix options (rank-ordered by engineering cost and clinical benefit):**

1. **(Best leverage, medium cost)** Deterministic override rule: if the turn's content matches a skill's Tier-1 keywords with high confidence AND safety_check passed AND intent_route returned `general_support`, re-classify as `new_skill`. Effectively: let the keyword layer adjudicate ambiguous intent classifications. Does not require touching the intent classifier.

2. **(Architecturally cleanest, higher cost)** Add an `emotional_intensity` signal upstream of intent_route that biases classification toward `new_skill` for high-intensity non-crisis presentations.

3. **(Lower cost for specific cases)** Add explicit high-precision trigger phrases to mi_readiness_ruler and dbt_tipp that intent_route is known to classify as `new_skill` even today (phrases that are unambiguously skill-invocations, not distress expressions).

---

### Bucket 5 — Clinical/Structural Design (2 cases)

Neither a keyword problem nor a classifier problem. The skill's architecture or the audit's test approach is the gap.

**psychotic_referral:**
- Empty `target_presentations` confirmed. The skill can only activate via the `psychotic_disclosure` clinical flag auto-select (skill_select.py:115-131). A user cannot trigger it through a natural turn-1 statement.
- Turn 1 freeflow is by design. CRISIS_DETECTED on Turn 2 is correct safety behavior. post_crisis_check_in on Turn 3 is the correct follow-up.
- **Clinical design question:** Can psychotic_referral ever run in a natural conversation, or will crisis detection always preempt it for acute presentations? If the answer is "the flag gets set before skill_select runs on the same turn," the Turn 1 freeflow is harmless. If the flag is set on Turn N and referral doesn't start until Turn N+1, there's a one-turn gap of unstructured response.
- **Route to clinical review** — not a code fix.

**psychoed_stress mid-skill drift:**
- Skill activates correctly (Turn 1 PASS). Loses lock mid-execution when user's Turn 3 language overlaps financial_anxiety keywords.
- Two fix options: (a) keyword de-conflict on financial_anxiety (remove generic work/deadline language); (b) add a skill-lock mechanism in the executor that resists re-routing once a skill has been active for N turns.
- Option (a) is a one-commit fix; option (b) is a design change.

---

## Systemic Findings

### SF-1: Dominant Shadower Structure (top post-Gitex item)

**Summary:** Two skills at low registry indices (cbt_thought_record [0], worry_time [7]) function as semantic attractors that capture turn-1 traffic belonging to at least 4 other skills. The failure mechanism is registry-order-as-tiebreaker in the keyword loop: first-match wins, regardless of match specificity. This is distinct from every intent_route failure (where skill_select is bypassed entirely) — here, skill_select is reached but picks wrong.

**Why it's the top item:** Single change to skill_select.py (12 lines: collect all Tier-1 matches, rank by specificity, return best) clears 4 DRIFT failures at once and operates in the layer already being maintained. Smaller than intent_route work; higher failure-count impact.

**Scale confirmed:** worry_time shadows 3 skills (cognitive_restructuring, PST, ACT); cbt_thought_record shadows 1 confirmed (self_compassion_break) plus is the landing point for 3 other drifts. Both attractors also score high on semantic similarity for adjacent content, so the problem propagates through both the keyword and semantic tiers.

**Bilingual behavior is language-dependent, not language-symmetric.** SF-1 is language-agnostic as an architectural property (registry-order-as-tiebreaker), but the specific collision pattern varies: cognitive_restructuring AR *passes* because Arabic cognitive vocabulary is naturally segregated from Arabic worry vocabulary; EN fails for the same skill. This means validating the best-match-scoring fix on EN alone is insufficient. The regression suite for the SF-1 fix must assert correct routing in *both* languages — a scoring change that cleanly resolves EN shadowing could inadvertently perturb the AR cases that currently pass by accident of vocabulary segregation.

### SF-2: Intent_route Intensity Blindness

**Summary:** Intent_route categorizes topic but not emotional intensity or therapeutic need. At least 5 skills fail because their canonical presentations (acute distress, ambivalent motivation, exploratory self-reflection) are classified as `general_support` or `info_request` before skill_select runs. No keyword fix helps because the matching layer is never reached.

**Priority below SF-1** because the fix is more expensive (touches the intent classifier or requires a new upstream signal) and the failure patterns from this bucket tend to produce adjacent-but-not-harmful responses (user gets KB, freeflow, or a nearby skill). Exception: dbt_tipp, where the harm-on-miss is categorically high.

**dbt_tipp escalation path:** Even after SF-1 is fixed, dbt_tipp remains unreachable for intent_route-classified `general_support` turns. The intensity signal or override rule must specifically cover acute escalating distress in addition to the keyword fix.

### SF-3: worry_time Keyword Surface Area

**Summary:** worry_time's `target_presentations` includes generic problem/challenge/planning language that belongs to multiple other skills' domains. A single de-confliction pass on worry_time's keyword list (replacing generic phrases with worry-scheduling-specific ones) would reduce the attractor effect and likely resolve 2–3 of the SF-1 shadowing cases even before best-match scoring is implemented.

This is a prerequisite for SF-1: even with best-match scoring, if worry_time has a keyword that is longer or more specific than a competing skill's keyword for the same input, worry_time still wins. Both fixes are needed.

**Important:** The worry_time de-confliction in the Fix Now table below is an **interim mitigation** — it reduces the attractor blast radius before the scoring fix lands and is shippable today. It is not a substitute for SF-1. Once the de-confliction removes the visible failures, the structural first-match-wins problem remains for any future high-index skill and any overlap not manually caught. SF-1 must not be closed because the immediate drift failures went away.

### SF-4: Output Gate Banned Opener Tax

**Summary:** 12 banned-opener detections in the audit window (9× "It sounds like", 3× "That sounds challenging"). Each triggers a full LLM regeneration, doubling that turn's wall-clock latency. Frequency estimate: ~1 in 10 turns.

**Impact on p95 KPI:** At 1 in 10 turns regenerating, the model is producing these banned openers as a default register. The system prompt steering is insufficient. Fix: (a) strengthen the system prompt opener guidance, or (b) audit the banned opener list to determine if some phrases should be reformulated rather than added to a blocklist.

### SF-5: Audit-Trail Attribution Gap on Skill Completion Turns (PDPL compliance)

**Summary:** On the turn a skill marks `skill_complete=True`, the executor correctly clears `active_skill_id=None` to free the next turn's routing. But this single field carries two semantically distinct meanings: (1) **control state** — which skill is active going forward (correctly nulled), and (2) **audit attribution** — which skill produced this response (must persist). The same null propagates to every downstream consumer of `active_skill_id`:

- `audit.py:107` — `active_skill_id` column in the audit row is `None` for the completion turn
- `output_gate.py:319` — `active_skill` in the session record is `None`
- `output_gate.py:371` — `skills_used=[]` for the completion turn
- `server.py:308` — `X-Sage-Skill-Id` header is empty string for the completion turn

**This is structural, not random.** It reproduces on every skill completion, in both EN and AR. The "appears in both languages → structural" reasoning that elevated SF-1 applies identically here. The completion turn is the most clinically important turn to attribute — it marks where the technique concluded — yet it is the one turn whose audit record systematically loses skill attribution.

**PDPL relevance:** The v7 spec and PDPL section require "every response traceable to model version, skill ID, retrieval IDs, and cultural rules." A systematic null on all completion turns is a compliance gap, not a UX nit. Before pilot user exposure, all skill activations must be traceable.

**Fix:** Split `active_skill_id` into two fields at the source:

```python
# skill_executor.py line 611 — current
"active_skill_id": None if result.get("skill_complete") else skill_id,

# Fixed — add companion field for audit attribution
"active_skill_id":     None if result.get("skill_complete") else skill_id,
"completed_skill_id":  skill_id if result.get("skill_complete") else None,
```

Then in each consumer, use `active_skill_id or completed_skill_id` for any read that is for attribution purposes (audit log, headers, skills_used). `active_skill_id` remains the control-routing field and still clears correctly.

Also requires: adding `completed_skill_id: Optional[str]` to `SageState`.

**Size:** ~10 lines across 4 files + 1 state field. This is a Fix Now item, not post-Gitex.

### SF-6: grief_loss Arabic — cultural_and_faith_frame Unreachable (CRITICAL-cultural)

**Summary:** grief_loss is the only skill in the audit to PASS in EN and FAIL in AR. The failure is not cosmetic: the `cultural_and_faith_frame` step — Islamic and faith-based framing for grief, including Quranic verses, dua, and cultural grief rituals — does not execute for Arabic-speaking users. It is unreachable because the Arabic routing surface does not connect to the skill.

**Why this deserves its own finding:** This is not a keyword gap in a list of keyword gaps. grief_loss's `cultural_and_faith_frame` step exists *specifically* for the Gulf Arabic-speaking population this product serves. The step was authored, clinically reviewed (A7 approval confirmed), and validated in the A7 sign-off package. The population for whom it would be most meaningful — an Arabic-speaking user disclosing grief in their native language — is precisely the population who cannot access it. For a CDA-facing, UAE-national product, this is the most on-brand failure in the audit and the one a clinical reviewer or policy stakeholder would identify first.

**Mechanism:** AR turns 1–5 were routed as freeflow (intent_route bypass — SF-2 pattern). Turn 6's guilt/anger phrasing matched financial_anxiety's Arabic keywords instead of grief_loss's. The Arabic keyword surface on grief_loss is insufficiently broad to capture the range of Khaleeji grief expressions (guilt, anger at God, survivor guilt, familial obligation weight, financial burden of mourning).

**Fix:** Arabic keyword expansion for grief_loss, with native-speaker review. Similar to safe_place_visualization AR. Collision check against financial_anxiety's Arabic keywords required before adding. Route to clinical lead + Arabic content reviewer for the keyword set — not an engineering decision alone.

**Priority:** Before pilot user exposure. Route to clinical review now so the expansion has time for sign-off.

---

## Fix Prioritization

### Tier A — Compliance / Safety (ship regardless of milestone)

One item. It is ready, it is ~10 lines, and it should not wait for a scoping decision.

| Item | Action | Status |
|------|--------|--------|
| **SF-5: Audit attribution gap** | Add `completed_skill_id` field to `SageState`; update `skill_executor.py:611`, `audit.py:107`, `output_gate.py:319/371`, `server.py:308` to use `active_skill_id or completed_skill_id` for attribution reads | **DONE** — pending commit |

### Tier B — Before Any User Exposure (not required for a demo freeze)

These matter only if real users will touch the system. For a Gitex demo with a controlled skill set, they can wait. For a pilot: mandatory.

| Item | Skill | Action |
|------|-------|--------|
| **dbt_tipp interim fix (SF-2 escalation)** | dbt_tipp | Add high-precision trigger phrases that intent_route already classifies as `new_skill` (Bucket 4 option 3 — does not fix SF-2 generally but makes the one CRITICAL skill reachable without the full classifier redesign). Bilingual: EN and AR. |
| **SF-6: grief_loss AR keyword expansion** | grief_loss | Arabic keyword expansion for grief_loss with native-speaker + clinical review; collision check against financial_anxiety Arabic keywords. Route to clinical lead now for sign-off lead time. |
| **Harness: flag-seeded tests for post_crisis_check_in + psychotic_referral** | Both | Pre-set crisis_state/psychotic_disclosure flags, then probe both skills directly in EN and AR. Coverage gap, not a product fix. |
| Keyword gap AR | safe_place_visualization | Add "مكان آمن", "أحتاج مكان آمن", "أبي مكان آمن" to target_presentations; EN fix (ebd6bb5) is English-only |
| Keyword gap EN | assertive_communication | Add "I can't say no", "I give in too easily", "passive aggressive", "people pleaser", "can't set limits" |
| Keyword de-conflict (SF-3 interim) | worry_time | Remove generic problem/challenge/planning phrases; replace with worry-scheduling-specific ones — interim mitigation for SF-1, not a substitute |
| Keyword de-conflict | financial_anxiety | Remove work/deadline overlap with psychoed_stress |

### Tier C — Audit Harness Corrections (no product change)

These do not fix anything in the product. They re-run specific tests with cleaner probe phrases so the next audit has accurate data.

| Item | Action |
|------|--------|
| stop_technique EN | Re-run with "thought stopping" — current phrase is a cbt_thought_record [0] keyword (test artifact) |
| stop_technique AR | Redesign AR phrase — current phrase hits worry_time [7] (different shadower, same artifact class) |
| cbt_thought_record AR | Re-run with non-crisis self-blame phrasing — current phrase triggers CRISIS_DETECTED before skill_select |
| post_crisis_check_in + psychotic_referral | Harness change (flag-seeded, see Tier B above) |

### Post-Gitex (design review or multi-session)

| Item | Skills affected | What | Priority |
|------|----------------|------|----------|
| **Best-match scoring in skill_select (SF-1)** | self_compassion_break, PST, ACT (+ future high-index skills) | Replace first-match loop with scored selection; validate regression in **both EN and AR** — "passes EN" is not "done" | **#1** — highest leverage, smallest change |
| worry_time keyword de-confliction (complement to SF-1) | cognitive_restructuring, PST, ACT, psychoed_stress | Remove or narrow generic phrases in worry_time target_presentations | **#2** — prerequisite for scoring fix to work cleanly |
| Intent_route intensity signal / override rule (SF-2) | dbt_tipp, mi_readiness_ruler, values_clarification | Intensity-based bypass or keyword-tier override on general_support classifications | **#3** — larger change; dbt_tipp interim (Tier B) buys time |
| psychotic_referral Turn 1 path | psychotic_referral | Clinical decision: own the one-turn gap or add a flag-before-routing mechanism | Clinical review |
| Semantic threshold calibration | All semantic fallback cases | Recalibrate after SF-1/SF-3; keyword changes will shift the threshold landscape | After SF-1 and SF-3 |
| Output gate opener tax (SF-4) | All skills | System prompt revision or opener list audit | Medium |
| Skill-lock mechanism | psychoed_stress | Add N-turn lock in executor | Low |
| Connection pool characterization | Infrastructure | Concurrency sweep post-Gitex | Pre-pilot |

---

## AR Pass

Status: **Complete** as of 2026-06-07. All 25 directly testable skills audited in both languages.

**AR outcomes answered three questions:**
1. **SF-1 is confirmed structural (language-agnostic)** but the blast radius is language-dependent. worry_time shadowing is bilingual for PST [25] and ACT [26]; cognitive_restructuring AR passes because Arabic cognitive and worry vocabulary are naturally segregated. Fix validation must cover both languages.
2. **Arabic keyword byte-integrity holds.** No encoding failures across the run; Arabic keyword matching worked correctly wherever keywords were present.
3. **Crisis short-circuit vs shadowing is distinguishable by path array.** Two AR test artifacts (cbt_thought_record, stop_technique) tripped CRISIS_DETECTED before skill_select ran — Arabic distress language is linguistically more intense. These are probe-design failures, not routing failures. The genuine SF-1 AR cases (PST, ACT) were confirmed via path array showing worry_time capture at skill_select, not crisis intercept.

| # | Skill | AR Result | Notes |
|---|-------|-----------|-------|
| 0 | cbt_thought_record | DRIFT → mi_readiness_ruler | **Test artifact**: Arabic trigger phrase triggered CRISIS_DETECTED (self-blame phrasing too crisis-adjacent) |
| 1 | grounding_5_4_3_2_1 | PASS | All 5 sensory steps correct order |
| 2 | sleep_hygiene | PASS | Skill ID header dropped after turn 2 (consistent mid-execution header drop) |
| 3 | box_breathing | PASS | Completed gracefully; user reported relief |
| 4 | mood_check_in | PASS | score_mood → explore_mood correct |
| 5 | behavioral_activation | PASS | activity_audit → identify_small_step correct; skill ID header dropped mid-skill (consistent pattern) |
| 6 | worry_time | PASS | schedule_worry → sort_and_act correct |
| 7 | mi_readiness_ruler | DRIFT → box_breathing then mi_readiness_ruler | **Different mechanism from EN**: Turn 2 box_breathing activated (physical/stress language in Arabic phrase), then eventually drifted to mi_readiness_ruler at importance_ruler. EN went to PMR and stayed. AR may be a Bucket 3 shadowing failure (if Turn 1 reached skill_select) rather than Bucket 4 intent-route miss — path array needed to confirm |
| 8 | stop_technique | DRIFT → worry_time | **Test artifact** (same class as EN), different shadower: Arabic phrase hit worry_time [7] where EN phrase hit cbt_thought_record [0] |
| 9 | progressive_muscle_relaxation | PASS | entry_screen held for readiness check; breathe_and_settle → upper_body correct |
| 10 | safe_place_visualization | FAIL (invisible — no headers, 5 turns) | **AR-specific keyword gap**: Arabic trigger phrase didn't match existing Arabic keywords (too construction-specific); EN "safe place" fix (ebd6bb5) is English-only; freeflow LLM generated on-topic Arabic content. Fix: add Arabic "مكان آمن" variants |
| 11 | dbt_tipp | DRIFT → mi_readiness_ruler | **Confirmed bilingual**: same destination as EN. Turn 1 freeflow (intent_route bypass); Turn 2 Arabic phrasing shifted to action-readiness register ("wanting to try something physical") → mi_readiness_ruler keyword capture. CRITICAL severity applies in both languages |
| 12 | psychoed_anxiety | DRIFT → grounding_5_4_3_2_1 | **Confirmed bilingual**: turns 1–3 freeflow (intent_route bypass, same as EN); turn 4 physical symptom Arabic phrasing hit grounding keywords. EN landed on box_breathing; landing skill varies by Arabic keyword match but root cause identical |
| 13 | psychoed_depression | DRIFT → stop_technique | **Confirmed bilingual**: turns 1–2 freeflow; turn 3 Arabic rumination phrasing hit stop_technique Arabic keywords. EN drifted to cbt_thought_record; language-specific keyword surfaces determine landing skill, root cause identical. Side note: stop_technique Arabic keywords are functional (captured correctly here) — EN test artifact obscured this |
| 14 | psychoed_stress | PASS (delayed) | Turns 1–3 freeflow (intent_route bypass); Turn 4 Arabic phrasing matched psychoed_stress Arabic keywords; skill activated and held. EN activated on Turn 1 but drifted mid-skill; AR delayed but stable. Both sub-optimal, same SF-2 root cause for initial bypass |
| 15 | values_clarification | FAIL (invisible — no headers, 6 turns) | **Confirmed bilingual**: same as EN — intent_route bypass → freeflow Arabic on-topic content; no activation in either language |
| 16 | assertive_communication | PASS | Activated Turn 1 via Arabic keywords (understand_assertiveness → practice_the_formula → plan_a_real_situation). **Validates EN Bucket 2 diagnosis**: Arabic coverage works; EN keyword set is the specific gap. Header drop from Turn 3 onward is SF-5, not routing |
| 17 | self_compassion_break | DRIFT → cbt_thought_record | **SF-1 confirmed structural in AR**: cbt_thought_record [0] captured Arabic self-criticism language on Turn 1; identical to EN. Registry-order-as-tiebreaker is language-agnostic |
| 18 | mindfulness_body_scan | PASS | Immediate Turn 1 activation; all 5 steps in correct order — matches EN |
| 19 | cognitive_restructuring | PASS (delayed — Turn 2) | **worry_time shadowing does NOT reproduce in AR**: Arabic cognitive vocabulary is segregated from Arabic worry vocabulary; EN failure is English-specific. Turn 1 freeflow (intent_route); Turn 2 Arabic keywords matched correctly. cbt_thought_record shadowing confirmed bilingual; worry_time shadowing is EN-specific for this skill |
| 20 | interpersonal_effectiveness | PASS | Turn 1 activation; clarify_goal → choose_approach correct; header drop from Turn 3 = SF-5 |
| 21 | financial_anxiety | PASS | Turn 1 activation; normalize_and_validate → psychoeducate_and_separate correct; header drop Turn 3 = SF-5 |
| 22 | grief_loss | DRIFT → financial_anxiety | **EN/AR divergence** — EN PASS; AR turns 1–5 freeflow (intent_route bypass), turn 6 guilt/anger phrasing hit financial_anxiety. Arabic grief keyword coverage gap: cultural_and_faith_frame step is unreachable in AR. A7 approval confirmed content is correct; routing is the gap |
| 23 | psychotic_referral | DRIFT → post_crisis_check_in | **Consistent with EN**: Turn 1 professional_referral step ran with no X-Sage-Skill-Id header (SF-5 — completion turn attribution gap). Turn 2 Arabic psychotic disclosure triggered crisis detection → post_crisis_check_in. Same structural behavior as EN: flag-only activation path, Turn 1 freeflow, Turn 2 crisis intercept. Not a new finding — confirms pattern is bilingual |
| 24 | problem_solving_therapy | DRIFT → worry_time | **SF-1 confirmed bilingual for PST**: worry_time [7] captured Arabic problem/challenge language on turns 1 and 3 (schedule_worry, sort_and_act steps). PST never activated. Identical mechanism to EN. worry_time shadowing of PST is language-agnostic |
| 25 | act_psychological_flexibility | DRIFT → financial_anxiety (via worry_time) | **SF-1 confirmed bilingual for ACT**: Turn 1 worry_time (schedule_worry), turns 3–4 drifted further to financial_anxiety. ACT never activated. Same multi-hop pattern as EN. worry_time captures Arabic action/values language on Turn 1 before further session drift |

### AR Scorecard (of 25 directly testable)

- **PASS:** 13 of 25 (52%) — grounding_5_4_3_2_1, sleep_hygiene, box_breathing, mood_check_in, behavioral_activation, worry_time, PMR, assertive_communication, mindfulness_body_scan, cognitive_restructuring (Turn 2), interpersonal_effectiveness, financial_anxiety, psychoed_stress (Turn 4)
- **DRIFT — dominant shadower (SF-1):** 3 (self_compassion_break, PST, ACT — cbt_thought_record and worry_time shadowing bilingual for these three)
- **DRIFT — intent-route (SF-2):** 5 (mi_readiness_ruler, dbt_tipp, psychoed_anxiety, psychoed_depression, values_clarification — all confirmed bilingual)
- **DRIFT — keyword gap (Arabic-specific):** 2 (safe_place_visualization [pending fix], grief_loss [SF-6 — CRITICAL-cultural])
- **Test artifact:** 2 (cbt_thought_record [crisis phrase → different shadower than EN], stop_technique [worry_time instead of cbt_thought_record])

### AR vs EN Divergences

| Skill | EN | AR | Divergence explanation |
|-------|----|----|----------------------|
| cognitive_restructuring | DRIFT → worry_time | PASS (Turn 2) | Arabic cognitive vocabulary is segregated from Arabic worry vocabulary; EN failure is English-specific |
| assertive_communication | DRIFT → interpersonal_effectiveness | PASS | Arabic keyword set covers the entry phrase; EN keyword set is the specific gap |
| grief_loss | PASS | DRIFT → financial_anxiety | Arabic grief keyword coverage gap; guilt/anger turn 6 phrasing hit financial_anxiety Arabic keywords |
| psychoed_stress | DRIFT (mid-skill) → financial_anxiety | PASS (delayed Turn 4) | EN activates Turn 1 and loses lock; AR bypasses skill_select turns 1–3 then activates stably on Turn 4 |
| mi_readiness_ruler | DRIFT → PMR | DRIFT → box_breathing then mi_readiness_ruler | Same SF-2 root; Arabic phrasing hit different intermediate skill; final drift destination language-specific |
| stop_technique | DRIFT → cbt_thought_record [0] | DRIFT → worry_time [7] | Test artifact in both cases; Arabic phrase hit worry_time instead of cbt_thought_record — confirms both are dominant shadowers, language shapes which one intercepts |

### SF-1 AR Confirmation Summary

- **Fully bilingual** (worry_time shadowing): PST [25], ACT [26]
- **Fully bilingual** (cbt_thought_record shadowing): self_compassion_break [18]
- **EN-specific** (worry_time shadowing): cognitive_restructuring [20] — Arabic cognitive vocabulary naturally segregated from Arabic worry vocabulary
- **Implication**: SF-1 is a structural architectural property (registry-order-as-tiebreaker, language-agnostic), but the specific skills affected differ between EN and AR due to Arabic vocabulary domain segregation. The fix (best-match scoring) is still the correct structural solution for both languages.

### KB Endpoint (info_request path)

All 4 test requests (EN-1 CBT explanation, EN-2 professional help guidance, AR-1 CBT in Arabic, AR-2 anxiety help-seeking in Khaleeji Arabic) returned HTTP 200 with substantive responses (337–479 chars). No [[SERVER_ERROR]]. Khaleeji Arabic KB responses confirmed fluent. info_request bypass path is functioning correctly in both languages.
