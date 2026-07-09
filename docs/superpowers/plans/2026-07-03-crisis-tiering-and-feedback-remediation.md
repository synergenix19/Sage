# Plan — Crisis Tiering & Tester-Feedback Remediation (2026-07-03)

**Status:** DRAFT for clinical review — no code changed yet.
**Owner (eng):** _tbd_ | **Clinical reviewers:** _tbd_ | **Product:** _tbd_
**Inputs:** `Sage_Feedback_RCA_2026-07-03.md` (production evidence) + deep-research evidence base (§B below).
**Governance:** F1/F2/F4 touch the crisis/safety path → **no crisis-gating or crisis-copy change ships without clinical sign-off** (per project rule). This plan is written to be ratified section-by-section.

**v7 alignment:** reviewed against `docs/SageAI_architecture_current.md` on 2026-07-03. The tiering in §C is a **formal v7.1 amendment to §5.1 OR-fusion** (Absolute Rule 1) — see **§J** for the full alignment delta and the eight review amendments incorporated. Scope guards (§H) preserve Cardinal Rule 4 (deterministic detection, never softened) and the crisis-recall ≥95% KPI (§G).

---

## A. Goal & guiding principle

Fix the 6 findings from the 2026-06-22→07-01 tester round while honouring the product reality: **Sage is a wellness companion, not an emergency service.** The user's steer — *"crisis can be a little subtle in favour of good UX"* — is **supported by the clinical evidence with one hard boundary**: you may (and should) soften the *response* to low-level distress, but you must **not** weaken *detection of, or hard signposting for, active suicidal ideation with intent/plan/means*. The evidence is blunt that the common failure in this field is chatbots doing *too little*, too late — so the safe way to be "more subtle" is to add a **warm middle tier**, not to raise crisis thresholds blindly.

**One-line design change:** replace today's **binary** {normal ↔ RED-emergency} with a **3-tier graded response**, and fix the state-stickiness, Arabic generation-fidelity, and routing/tuning issues around it.

---

## B. Clinical evidence base (verified research — cite these to clinicians)

All claims below survived 3-vote adversarial verification. Full report + adversarial notes in the research transcript. Caveat flags are preserved so clinicians can weight them.

| # | Evidence | Confidence | Source |
|---|----------|-----------|--------|
| B1 | **Stepped/stratified care is the authoritative model**: deliver least-intensive effective support first, escalate only when clinically required (NICE, Zero Suicide "least restrictive care", CAMS, JAACAP 2025 stratified stepped-care RCT). Severity-matched, not uniform, response. | High | CAMS; JAACAP 2025 (Asarnow et al.) |
| B2 | **A warm "emergency mode" that keeps the user in supportive dialogue beats abrupt termination + generic hotline dump.** Sustained engagement, brief clarification of intent, and (human-delivered) safety planning are associated with de-escalation/reduced ideation (Gould 2007; Stanley-Brown SPI ~43% reduction). | High | medRxiv 2026 emergency-mode; Gould 2007; Stanley-Brown |
| B3 | **False-positive cost is real and quantified**; pushing to zero-miss sensitivity drives FPR to ~40–49%. Alarm fatigue is itself a recognised **safety hazard** (desensitization → missed real alarms). | High | medRxiv 2026 (n=200); APSF alarm-fatigue |
| B4 | **BUT the dominant real-world failure is UNDER-response**: of 29 chatbots on C-SSRS-style escalations, **none** met adequate safety criteria; only **17%** ever asked about active SI; most refer to help only at the highest risk level. | High | Nature Sci Rep 2025; medRxiv 2023 |
| B5 | **Crisis-resource localization is a common failure** (~10% gave the correct country's emergency number unprompted; most defaulted to US). ⚠️ **This describes our own system:** production emitted `800 46342`, a likely transcription error for the correct **`800 4673` (800-HOPE, "Mental Support Line")** — single-source the verified national line + co-listed 999 (pending **G8**), do not "keep and enforce" the current constant. | High | Nature Sci Rep 2025 |
| B6 | **Published product precedent (Woebot) OFFERS resources rather than forcing full signposting** for concerning language, and explicitly frames itself as "not a crisis service." Direct precedent for offer-not-force + non-clinical scope framing. | High | Woebot safety page |
| B7 | **A dedicated safety-filter layer outperforms a base LLM** and is deliberately tuned for sensitivity (Verily BH filter: 0.99 sens / 0.99 spec). Architect crisis detection as a specialized layer, not the chat model. Validates Sage's S1/S3 + planned S2/MARBERT direction. | High (vendor caveat) | Verily arXiv 2510.12083 |
| B8 | **Validated Arabic screening instruments are FORMAL MSA**, established in a Gulf/Saudi sample via 5-step forward/back-translation; validation does **not** cover Khaleeji/Levantine dialect. **Paraphrasing scale anchors into dialect breaks fidelity.** | High | AlHadi 2017 (Arabic PHQ) |
| B9 | **Safety floor confirmed by harm data**: media-reported AI-chatbot psychiatric harms cluster at the acute/severe end (suicide deaths, hospitalization) → active SI / self-harm / plan / means / command hallucinations must **never** be softened. Emerging US law (NY/CA 2026) now *requires* chatbots to detect+address SI and disclose non-human status. | High | JMIR 2026; state-law extract |

**Open questions the research could NOT settle (→ become clinician/compliance decisions in §E):**
- Fixed dialect vs mirroring the user's dialect for MH chat — *no evidence either way*.
- Exact UAE DoH/MoHAP regulatory scope + documentation standard for a non-clinical wellness app.
- Whether C-SSRS/PHQ-9 are validated in Khaleeji/Levantine dialect specifically (they are not, in our sources).
- A *validated* protocol for exiting a monitoring state — the literature describes entry/continuation, not step-down.

**Refuted claims (do NOT cite):** Woebot detector as "continually-monitored NLP" (0-3); two "mandatory clinician-in-the-loop / three-tier human-escalation" blog claims (0-3). We are not asserting a human-in-the-loop live-chat requirement.

---

## C. The proposed tiered crisis model (core clinical artifact to ratify)

> This table is the single most important thing for the clinician team to review, edit, and sign. Everything in §D implements whatever this table says.

| Tier | Trigger (detection) | Response | Signposting | State |
|------|--------------------|----------|-------------|-------|
| **T0 — Normal** | No safety signal | Normal supportive companion / skills | None | `none` |
| **T1 — Warm concern (NEW)** | Sub-crisis distress: hopelessness, "I feel low/empty/worthless", passive statements *without* intent/plan/means. Today's **solo-S3** and low-severity signals land here. | Stay in warm dialogue: validate, gently explore, **offer** resources ("would it help if I shared a support line?") — do **not** force. Continue the conversation. | **Offered, not forced** (B2, B6) | `supportive` (new, non-locking) |
| **T2 — Acute crisis** | Active SI with intent/plan/means; explicit self-harm; command hallucinations; S1 `si_explicit`/`si_passive` keyword hits; S7 `NEW_CRISIS`. | Immediate, unambiguous crisis response; brief intent clarification permitted; do not proceed with skills. | **Forced** UAE Mental Support Line `800 4673` (8am–8pm) + `999` for out-of-hours/emergency — final wording pending **G8** (B5, B9) | `monitoring` (existing) |

**Design rules derived from evidence:**
1. **Detection stays sensitive; only the *response* is graded.** We are NOT raising S1/S3 thresholds to hide true SI (B4, B7). We are re-routing *sub-crisis* detections to T1 instead of T2.
2. **The T2 floor is non-negotiable** and defined by the clinician team (B9). S3-solo (no S1 corroboration) on English mild-distress → **T1**, not T2. S3 continues to gate **T2** for Arabic/Arabizi where S1 coverage is weak (keeps the Arabic command-hallucination catch we found in prod).
3. **No abrupt termination.** T1 and monitoring turns must be conversational, never a repeated canned card (B2).
4. **UI invariant (v7 UI/UX Rule 5):** the T1 "offer" must never add friction to reaching crisis resources — the crisis card / support line stays one tap away in the UI regardless of tier. T1 changes the *conversational* posture, not resource *accessibility*.

**This tiering makes the deterministic layer consistent with the already-ratified persona.** `L0_persona.json` v2.2.0 (clinical sign-off 2026-06-14) already states: *"ordinary sadness, stress, or feeling overwhelmed is not a crisis and needs warmth, not a safety check."* Today that principle is contradicted by Node 1: S3 deterministically routes "I feel hopeless / burdened and low" to `crisis_response` **before L0 ever runs** (crisis_response bypasses freeflow/output_gate). W1 aligns the deterministic layer with the signed-off L0 philosophy — it does not invent a new stance.

---

## D. Workstreams (each maps to an RCA finding)

### W1 — F1: stop routing ordinary distress to RED  ⟶ **P0, clinical sign-off**
**Problem (verified):** `"i am feeling hopeless"` and `"it feels like a burden and it is making me feel so low"` fired **solo `["s3_semantic"]`** → full RED card. `safety_check.py:152-159` appends `s3_semantic`; `:217` sets `is_safe=False`. S3 is labelled "advisory" (commit `b8bca3e`) but still gates.

**Fix:** introduce the tier split so S3-solo (English, no S1 corroboration) resolves to **T1**, not T2.
- **Tier boundary lives in DATA, not Python (v7 §5.5 Rules Service; review amendment #2a).** The signal→tier mapping is authored as a versioned, clinician-editable JSON rule under `rules/data/safety/` (e.g. a `tier_routing.json` category, or a `tier` field added to each safety signal definition), evaluated by `rules_engine` — the same pattern as `false_positive_exclusions.json`. `safety_check.py` **reads** the resolved tier; it does not hardcode the boundary as constants. This keeps every G1 refinement a clinician rule-edit, not an engineering change (clinician autonomy over engineering convenience).
- Data model: `si_explicit`/`si_passive`/S7-NEW_CRISIS ⟶ T2; S3-solo on EN ⟶ T1; S3 on AR/AZ ⟶ T2 (unchanged, coverage-load-bearing per in-file warning). All expressed as rule data.
- `graph.py:_route_after_safety` (150-155): route T2 → `crisis_response`; T1 → normal graph with a `supportive_posture` flag (warm + offer-resources), **not** the crisis node.
- Recalibrate: add the confirmed FP phrases ("I feel hopeless/low/empty/worthless/burden") to the S3 FP calibration set; re-run `scripts/calibrate_s3_threshold.py`; re-run the CRADLE + `verify_arabic_safety.py` recall checks to prove **no true-SI recall lost**.

**SageState schema delta (review amendment #2b/#3) — must be documented as a schema extension, not slipped in:**
- New fields: `crisis_tier: Literal["none","T1","T2"]`; extend `crisis_state` enum with a non-locking `"supportive"` value (T1); `supportive_posture: bool`. These are additions to the enriched-state model (T1 is conceptually adjacent to Clinical Flags + Engagement). Add the delta to the `SageState` schema and to `docs/SageAI_architecture_current.md` §on state.
- **Audit (PDPL right-to-object traceability):** the T1-vs-T2 decision **is** a classification decision and must be logged in the `output_gate` / `write_session_audit` row: `crisis_tier`, the `rule_id` that set it, and the path. Extend the audit spec the same way it already records crisis classification. A `crisis_response` turn already audits directly (`graph.py`) — ensure T1 turns audit their tier too.

**Escalation-taxonomy mapping (review amendment #4).** Map T1 into the existing severity language rather than letting a parallel taxonomy drift: **T1 ≈ an L2-adjacent state** (warm posture). Note precisely: skills' `escalation_matrix.L1` is read at runtime, but **L2–L4 are STORED_ONLY today** (validated, not routed — arch §on skill fields), so this is taxonomy alignment, not wiring into a live L2–L4 router. **Recommended:** a T1 turn may optionally write a `flag_for_review` clinical flag so repeated T1s accumulate a pattern — this also closes the untested **SF-4 cumulative-distress** gap. Whether T1 writes a flag every time, or only on repetition, is a **clinician decision (G1)**.

**Clinician decisions:** ratify the exact T1 vs T2 boundary (§C table) and the T1 copy/offer wording; decide the T1 `flag_for_review` policy. **Recall floor:** confirm the pilot-gate invariant (crisis recall must not drop) still holds post-change.

**Tests:** new `test_crisis_tiering.py` — T1 phrases resolve to `supportive` (not crisis); T2 phrases still RED; all existing `si_explicit` cases unchanged; Arabic S3 command-hallucination still T2. Safety-surface CI gate must pass.

### W2 — F2: sticky/canned crisis  ⟶ **P1, clinical input**
**Problem (verified):** after a crisis fire, next turn (`"i dont want to"`, empty `crisis_flags`) still returned the identical card (`gate_path=crisis`). Monitoring turns re-surface canned content → "stopped responding." A resolve path exists (`skill_executor.py:531/667` → `crisis_state="resolved"`) but the UX in-between is a repeated card.

**Fix (evidence B2 — warm continuation, not repetition):**
- Make monitoring turns **conversational**: `post_crisis_check_in` should vary and engage, not repeat the signpost; keep the resources available but not as the whole message.
- Add a **step-down** from `monitoring` → `supportive`/`none` when S7 reads clear de-escalation for N turns AND no new S1/S3 fire (S7 re-escalation stays armed the whole time). Design the criteria conservatively **for clinician sign-off** (the literature gives no validated exit protocol — B/open-questions).
- Keep the `_EMPTY_MONITORING_FALLBACK` guard (`output_gate.py:407`) so a monitoring turn is never silent.

**S7 spec addendum + invariant (review amendment #5).** S7 (`post_crisis_classifier.py`) is a POC extension beyond the v7 S1–S6 set; it needs a one-page addendum (which model, deterministic-or-not, latency). **Invariant to hold and test:** deterministic detection (S1/S2/S3) runs **every turn independent of `crisis_tier` and S7**. S7 is *additive only* — it may re-escalate within monitoring (existing `NEW_CRISIS` → `crisis_response`, line 121) and it **gates relaxation/step-down**, but it is **never the sole path to escalation**, and an S7 failure/timeout can never suppress or downgrade an S1/S3 fire (Cardinal Rule 4). Step-down requires S7-clear **AND** no deterministic fire — never S7 alone.

**Tests (encode the invariant, don't just state it):** in `test_crisis_tiering.py` / W2 tests, add explicit assertions that (1) an S7 timeout/exception during `monitoring` does **not** downgrade or suppress a same-turn S1/S3 fire (still routes T2); (2) step-down requires S7-clear **AND** no deterministic fire — S7-clear alone with an S1/S3 hit stays `monitoring`; (3) S7 `NEW_CRISIS` can escalate but is never the *only* thing consulted. These are the literal Cardinal Rule 4 assertions.

**Clinician decisions:** de-escalation criteria (how many clear turns? what counts as "clear"?); monitoring-turn copy.

### W3 — F3: empty responses  ⟶ **P1, eng-only (verify + harden)**
**Problem (verified):** 4 length-0 replies, **all week of 06-22**, `node_path … output_gate_banned_opener_retry`. **Already fixed by #58 (2026-06-25)** empty fail-safe (`output_gate.py:406-415, 481-493`); **zero empties after 06-25**.
**Fix:** (a) add a regression test asserting no empty user-visible response on the banned-opener retry path; (b) add **one retry-with-backoff** on the primary generation *before* the generic vetted line, so users get substance, not just "I'm here with you…"; (c) confirmed no clinical sign-off needed (no crisis-copy change). **Latency guard (review amendment #8):** the extra retry must be checked against the **<3s p95 latency KPI** — bound the backoff (single retry, hard timeout) and measure p95 in staging before merge; if it breaches, prefer the vetted line over a second LLM round-trip.

### W4 — F4: Arabic mood-rating corruption  ⟶ **P1, eng + AR clinical review**
**Problem (verified):** prod output *"1 = وايد زين and 10 = وايد زين"* (both "very good"). Skill template `mood_check_in.json:41` is **correct** (`1=صعب جدا, 10=ممتاز`); the **compose/translate layer corrupted the anchors**. Evidence B8: paraphrasing validated-instrument anchors into dialect **breaks fidelity** — so this is both a bug and a policy point.
**Fix:**
- **Pin** scale-anchor text as non-paraphrasable: the numeric-anchor clause must be emitted verbatim from the (clinically approved) template, not re-worded by the LLM/translation step. Route rating scales and any screening-instrument wording through a "do-not-paraphrase" channel.
- Add an `output_gate` guard that **rejects a rating scale whose low/high anchors are non-monotonic / identical** and falls back to the pinned template.
- **Policy (B8):** clinical instrument wording (rating anchors, any future C-SSRS/PHQ) uses **validated formal Arabic**, not dialect paraphrase. Log this as a standing rule.
**Clinician decisions:** approve the pinned formal-Arabic anchor wording; decide whether the *conversational wrapper* around the scale may be Khaleeji while the *anchors* stay formal.

### W5 — F5: dialect & literal translation  ⟶ **P2, product + clinical decision**
**Problem (verified):** bot forces Khaleeji to a Levantine/Egyptian speaker (even said so); literal renders ("grounding → للتواصل مع الأرض"; literal 5-4-3-2-1).

**Correction to review amendment #7 (spec-checked 2026-07-03).** The review states v7 "already specifies dialect mirroring" and that fixed-Khaleeji is a deviation. The spec does **not** support that reading:
- `L0_persona.json` v2.2.0 (clinical sign-off 2026-06-14): *"a warm **Khaleeji** wellness companion"* and *"Match their **register, their tone and level of formality**"* — the sign-off note explicitly scopes register-matching to **tone/formality**, not sub-dialect.
- `CU-DM-001` (`dialect_mirroring.json` v1.2.0, `authored_by: sage_clinics`) description: *"**Khaleeji register calibration** for Arabic sessions."*

So "dialect mirroring" is a misleading rule **name**: it calibrates responses **to Khaleeji**, it does not mirror the user's Levantine. **Fixed Khaleeji is therefore the architecturally sanctioned baseline**, and the tester's experience is spec-consistent, not a spec violation. (`therapeutic_profile.communication_style {code_switching, preferred_language}` governs EN/AR/Arabizi **language** selection, not Levantine-vs-Khaleeji register.) Moving to hybrid/MSA is a genuine **v7 amendment to L0 + CU-DM-001** and needs the same persona-change governance — it is not a "return to intended design." W5 therefore correctly remains a **product/clinical decision (G6)**; the research also could not resolve fixed-vs-mirroring.

**Options to put to the team:**
- (a) Keep fixed Khaleeji (status quo) — simplest, but the tester felt it "off."
- (b) **Register-neutral MSA-leaning** conversational Arabic (broadly acceptable across Gulf+Levant; aligns with B8's formal-Arabic validation).
- (c) Light **dialect-mirroring** of the *conversational* layer only, with clinical instrument wording still formal (hybrid).
**Independent fix regardless of (a/b/c):** improve translation fidelity (the "literal/off" complaint) in the compose/translate path — glossary for therapy terms (grounding, defusion, TIPP) so they aren't literally translated. Ties to open ticket `2026-06-24-arabic-question-stacking-translate-after-gate`.

**Residual spec action (accepted from review — add to G6 deliverable).** The v7 spec §5.6.1 L0 row literally reads *"Dialect mirroring rules,"* while the implementation (CU-DM-001 = "Khaleeji register calibration") and the L0 sign-off note (register-matching scoped to tone/formality) mean fixed Khaleeji. **That wording ambiguity is exactly what produced the two conflicting readings in review.** Whatever G6 decides, the v7.1 amendment must **rename/clarify the §5.6.1 spec text** so spec wording, rule name, and persona sign-off agree — "Khaleeji register calibration" if (a) holds, or updated semantics if (b)/(c) wins. Cheap; prevents re-litigation.

### W6 — F6: behaviour/tuning cluster  ⟶ **P2, eng + content**
Verified sub-items and fixes:
| Item | Fix | Touchpoint |
|------|-----|-----------|
| Redundant mood check-in ("i told u stressed") | Skill steps should consume already-stated affect / skip answered steps | `skill_executor.py` step-advance logic; `mood_check_in.json`/`mi_readiness_ruler` step completion criteria |
| Premature solutions / "all at once" (teen, AR loss-of-passion) | Inquire-before-prescribe; cap list length; gate `directive_posture` behind ≥1 inquiry turn | `intent_route.py` / composer posture; `info_request` path |
| Repetitive / circles back | Anti-repetition on offers + freeflow; track offered/covered content in state | offer model; `skill_select.py` |
| Relationship → "money-worry" skill | Routing precision (financial-anxiety skill over-matched a relationship problem) | `skill_matching` rules; ties to `project_skill_keyword_collision` |
| Anger — TIPP not executed | Verify `dbt_tipp` selection + step execution to completion | routing + `skill_executor.py` |
| `mood_check_in` chosen for infidelity disclosure | Review skill-selection appropriateness for relational-trauma openers | `skill_select.py` |

---

### W7 — Helpline single-source + correction  ⟶ **P0-blocking for crisis-copy, needs G8 + L0 re-sign**
**Problem (verified):** the crisis number is **duplicated** across `config.py` (constant), `graph.py:57-59` (EN + AR fallback strings), `output_gate.py:276`, the `crisis_content` rules, and **hardcoded inside `L0_persona.json` prompt text** — and the value in circulation (`800 46342`) is a likely transcription error for **`800 4673` (800-HOPE, "Mental Support Line")**. Current copy also falsely claims **"free, 24/7"** for what is an **8am–8pm** line.
**Fix (product directive — "configurable everywhere"):**
- One config object: `{ number: "800 4673", label: "Mental Support Line", hours: "8am–8pm daily", emergency: "999" }` — consumed by every crisis-copy site incl. L0 (L0 references it, does not embed digits).
- Correct the "24/7" wording; **co-list 999** for out-of-hours (the support line's limited hours make this a safety point, not a nicety).
- Regression test: assert the verified number + label render, and that **no literal helpline digits appear anywhere outside the single config source**.
**Gates:** value swap + L0 edit ship together under **G8** (clinician/compliance dial-test) **and a fast-track L0 v2.2.0 re-sign** (correcting a number inside a signed-off persona is a persona change). The centralization *refactor* (dedupe → single source, value still pinned to the verified number) is the concrete first diff.

---

## E. Clinician / compliance sign-off register

These are the decisions that block their respective workstreams. Suggest a single 60-min review to clear them.

| ID | Decision | Blocks | Owner |
|----|----------|--------|-------|
| G1 | **Ratify the T0/T1/T2 boundary** (§C) — especially: does bare "hopeless"/"low"/"burden" belong in T1? What exactly defines the T2 floor? | W1 | Clinical lead |
| G2 | **T1 copy + offer wording** (warm, offer-not-force resources) | W1 | Clinical + content |
| G3 | **Recall-floor confirmation**: agree that no change may reduce measured true-SI recall (S3 stays T2 for AR/AZ; EN solo→T1 only) | W1 | Clinical + eng |
| G4 | **De-escalation / monitoring step-down criteria** | W2 | Clinical lead |
| G5 | **Pinned formal-Arabic rating anchors**; formal-vs-dialect policy for instrument wording | W4 | AR clinical reviewer |
| G6 | **Dialect strategy** fixed/MSA/hybrid (W5 option a/b/c). **Deliverable also includes** renaming/clarifying the ambiguous v7 §5.6.1 L0 "Dialect mirroring rules" spec wording to match whatever is decided (prevents re-litigation). | W5 | Product + clinical |
| G7 | **Regulatory/scope confirmation** (UAE DoH/MoHAP non-clinical wellness posture; disclosure "not a crisis service"; audit expectations). May need external/legal input. | scope-wide | Compliance |
| **G8** | **Helpline — RE-SEQUENCED 2026-07-03: blocks EXTERNAL/pilot exposure, NOT internal testing (product-owner risk acceptance in the sign-off packet; residual risk = mislabelled-not-dead 800 46342 (IWRC) + correct 999). Hard release gate for any exposure beyond the internal cohort. (see §J.3).** Decision: `800 4673` (800-HOPE, "Mental Support Line"); `800 46342` treated as a transcription error. Scope: (a) clinician+compliance **dial-test both** + confirm hours (**8am–8pm, not 24/7**); (b) **correct the false "24/7" copy** + keep **999 co-listed** for out-of-hours; (c) **collapse to one configurable source** (number+label+hours), incl. inside L0 (see **W7**); (d) **L0 fast-track re-sign** (the number lives in signed-off L0 v2.2.0 → its correction is a persona change); (e) regression test pins number+label and forbids stray literals. | all crisis-copy | Clinical + compliance |

---

## F. Sequencing & priority

0. **P0-BLOCKING — W7 / G8** (helpline correction + single-source) — **must clear before any crisis-copy change (W1, W2, W4) merges.** The centralization refactor can start immediately; the value swap + L0 re-sign gate on the G8 dial-test.
1. **P0 — W1** (crisis tiering) — highest user-harm + safety-relevant; gated on G1–G3. Do this first, behind a flag, with the recall regression proving no SI loss.
2. **P1 — W3** (empty-response verify+harden) — eng-only, no gate; do immediately in parallel.
3. **P1 — W4** (Arabic rating) — eng + G5.
4. **P1 — W2** (sticky crisis) — gated on G4; naturally lighter once W1 stops false entries.
5. **P2 — W6** (tuning cluster) — parallelizable, mostly eng+content.
6. **P2 — W5** (dialect) — gated on product decision G6.

**Rollout discipline (per project norms):** feature-flag the tiering; one commit per finding for atomic revert; land on a branch; do **not** admin-bypass branch protection; verify against the safety-surface CI gate and a fresh CRADLE + Arabic-safety run before merge; smoke-test EN+AR in staging before prod (`railway up`).

---

## G. Validation strategy (how we prove it worked, to clinicians)

- **Safety regression (blocking):** existing `si_explicit`/`si_passive` corpus + CRADLE self-harm set + `verify_arabic_safety.py` must show **equal-or-better** true-SI recall after W1. This is the guarantee that "more subtle" did not become "misses real crises" (directly answers B4's warning).
- **FP regression:** a new "sub-crisis distress" suite (hopeless/low/burden/empty, EN + AR) must resolve to **T1**, not T2.
- **Arabic fidelity:** golden-transcript test on the pinned rating anchors (monotonic, formal); glossary check on therapy terms.
- **Helpline regression (W7/G8):** assert the verified number + label ("Mental Support Line") render in EN + AR crisis copy, that "24/7" no longer appears, that 999 is co-listed, and that **no literal helpline digits exist outside the single config source**.
- **S7 invariant tests (W2):** the three Cardinal-Rule-4 assertions from W2 (S7 timeout can't suppress S1/S3; step-down needs S7-clear AND no deterministic fire; S7 never sole escalation).
- **Replay the tester battery:** re-run the 13 feedback scenarios in staging and diff against the RCA transcripts; attach before/after to the clinician sign-off packet.
- **Post-deploy monitor:** query prod weekly for (a) T2 fires with S3-solo/EN (should be ~0), (b) any empty responses (should be 0), (c) monitoring-turn counts (should fall).

---

## H. What we are explicitly NOT doing (scope guard)
- Not lowering S1 crisis thresholds or removing S3 (detection stays sensitive — B4/B7).
- Not softening any active-SI / plan / means / command-hallucination response (B9).
- Not adding autonomous chatbot-delivered safety planning (evidence supports human-delivered only — B2 caveat).
- Not shipping any crisis-path change without G1–G4 sign-off.

## I. Appendix — primary sources
Nature Sci Rep 2025 (chatbot SI handling) · medRxiv 2026 emergency-mode & FP/FN trade-off · medRxiv 2023 escalation study · Verily arXiv 2510.12083 (BH safety filter) · CAMS stepped-care · JAACAP 2025 stratified stepped-care RCT · Woebot safety page · AlHadi 2017 (Arabic PHQ validation) · APSF alarm-fatigue · Gould 2007 / Stanley-Brown SPI · JMIR 2026 (AI psychiatric harms).

---

## K. SIGNED build spec (clinical sign-off 2026-07-03) — implement exactly this

Clinician approved with concrete, POC-sized forms. This section is the authoritative build spec; where it differs from earlier prose above, **§K wins**. No new services, no schema beyond the approved delta, no extra sign-off cycles; all copy changes ride the single G8/L0 re-sign.

| Gate | Build exactly this |
|------|--------------------|
| **G1** | Three entries in `rules/data/tier_routing/tier_routing.json`: `s1_any → T2`, `s3_solo ∧ lang=en → T1`, `s3 ∧ lang∈{ar,az} → T2`. **No per-phrase rules** — phrase tuning stays in the S3 FP calibration set. |
| **G1b** | One session counter `t1_count`. On the **2nd** T1 turn in a session, write **one** `flag_for_review(severity=low)`. Once per session — no windowing. |
| **G2** | Signed warm frame as an **~40-word L2-style posture instruction** injected when `supportive_posture=true` (validate → ≤1 gentle question → offer-not-force line). **Reuse the existing freeflow path — do NOT build a T1 skill.** |
| **G3** | No new work — block the tiering PR on the existing safety-surface CI gate + CRADLE/Arabic runs, like any other. |
| **G4** | `STEP_DOWN_CLEAR_TURNS = 2` (single named constant, POC — not rule data). 2 consecutive S7-clear turns ∧ no S1/S3 fire → `monitoring → supportive`; never to `none` in-session. |
| **G5** | Anchor clause = **literal string constant sourced from `mood_check_in.json`, concatenated after generation (never sent through the LLM)**. `output_gate` guard = one comparison: low anchor ≠ high anchor. No general do-not-paraphrase channel (only one instrument exists). |
| **G6** | **Keep fixed Khaleeji (option a) for POC.** Ship only: (1) therapy-term **glossary** (grounding, defusion, TIPP, 5-4-3-2-1) in the translate path; (2) fix the **one L0 line** that falsely claims to match the user's dialect (never claim to mirror what you don't). Revisit MSA/hybrid at Full Build. |
| **G7** | No eng action; compliance runs in parallel. |
| **G8** | `CRISIS_CONFIG = {number: "800 4673", label: "Mental Support Line", hours: "8am–8pm daily", emergency: "999"}` in `config.py`; every crisis-copy site (graph, output_gate, rules, L0) interpolates from it. **Value swap ships after dial-test + L0 fast-track re-sign, in one commit.** Regression: correct number+label render EN/AR, "24/7" absent, 999 present, grep asserts no helpline digits outside `config.py`. |

**Clinician-added requirements (R-series), trimmed to POC:**
| R | Disposition |
|---|-------------|
| **R1 — VERA-MH benchmark** | Keep, lightweight. Run once per release vs staging; attach scorecard to sign-off packet. **Not** CI-blocking (CRADLE + Arabic recall remain the blocking gates). |
| **R2 — Multi-turn battery** | Exactly **two** scripted 5-turn sequences (one EN, one AR), T0→T1→T2, asserting transition points. Add to `test_crisis_tiering.py`. No matrix. |
| **R3 — Safe messaging** | (1) One-time copy review of static T2/monitoring templates against the checklist during the G8 re-sign. (2) **One regex ban-list rule** at `output_gate` for LLM-generated T1/monitoring turns (method-detail terms + "commit suicide" phrasing → vetted-line fallback) — one entry in the existing cultural-rules pattern. |
| **R4 — T2 card copy** | Two additions folded into the G8/L0 re-sign: a **non-human disclosure** sentence + concrete **"talk to a real person now"** framing. Zero extra sign-off cycles. |
| **R5 — WhatsApp channel** | **CUT.** `CRISIS_CONFIG` has no `channels` field; call-only card. Trivial to add later (one key, one line). |
| **R6 — Reporting-ready audit** | Free — already satisfied by the planned `crisis_tier` + `rule_id` audit columns. Do not remove them. |
| **R7 — Lived-experience review** | Defer to Full Build. |

**Net new test surface (whole plan):** one tiering test file (`test_crisis_tiering.py`), two multi-turn sequences (R2), one helpline regression (G8), one anchor guard (G5), one ban-list rule (R3), plus the S7-invariant assertions (W2).

---

## J. v7 alignment delta & architecture-review response (2026-07-03)

Reviewed against `docs/SageAI_architecture_current.md`. Eight amendments from architecture review are incorporated above; this section is the traceable record.

### J.1 — The one genuine deviation: v7.1 amendment to §5.1 OR-fusion
v7 §5.1 / line 120: *"S1 or S3 fires (is_safe=False) → `crisis_response` regardless of crisis_state"* (binary OR-fusion). The §C tiering amends this: S3-solo/EN resolves to **T1** (warm), not `crisis_response`. This is **not a bug fix — it is a Layer-1 fusion-logic amendment** and must be ratified as **v7.1** with the §5.1 spec text updated so spec and code do not diverge (Absolute Rule 1). It is **motivated and pre-anticipated**: the Intelligence Evaluation flagged this exact failure as **SF-6** (FP harms: broken rapport, alarm fatigue, distrust) at CRITICAL priority; the L0 persona (signed off 2026-06-14) already encodes the same principle; production evidence confirms it. Scope guards (§H) keep detection deterministic and the T2 floor absolute (Cardinal Rule 4); the ≥95% recall KPI is protected by the §G blocking regression.

### J.2 — Amendments incorporated
| # | Amendment | Where applied |
|---|-----------|---------------|
| 1 | Record tiering as formal **v7.1 amendment to §5.1**; update spec text on merge | header, §J.1 |
| 2a | Express T1/T2 boundary as **data-driven rules** (`rules/data/safety/`), not Python constants | W1 |
| 2b/3 | **SageState schema delta** (`crisis_tier`, `supportive`, `supportive_posture`) + **log tier in audit** (PDPL traceability) | W1 |
| 4 | **Map T1 into the escalation taxonomy** (≈L2-adjacent; L2–L4 STORED_ONLY today) + optional `flag_for_review` on T1 (closes SF-4) | W1 |
| 5 | **S7 spec addendum + invariant**: additive only; relaxes/step-down only; never sole escalation gate; cannot suppress S1/S3 | W2 |
| 6 | **G8 helpline** single-source + regression test (see J.3) | G8, §J.3 |
| 7 | **Corrected** — spec baseline *is* fixed Khaleeji; hybrid/MSA is itself a v7 amendment, not a return to intent | W5 |
| 8 | **Latency check** on W3 retry vs <3s p95 KPI | W3 |

### J.3 — Helpline discrepancy (G8) — RE-SEQUENCED 2026-07-03: blocks EXTERNAL exposure only
> **Re-sequencing (product-owner risk acceptance, sign-off packet):** G8 no longer blocks internal-testing crisis-copy. Internal phase keeps emitting `800 46342`/"24/7"; residual risk accepted (bound: `999` correct + co-listed, `800 46342` connects to a real service (IWRC), mislabelled not dead). The dial-test + commit-2 + L0 re-sign are now a **hard release gate for any exposure beyond the internal cohort** (pilot/clinician-external/CDA demo/live). W7 commit-2 stays fully staged, cherry-pick-ready. The requirements below are unchanged — only *when* they gate changed.
**Product-owner decision (2026-07-03):** the correct national line is **`800 4673` (800-HOPE), the UAE "Mental Support Line."** Working hypothesis: **`800 46342` is a transcription/attribution error** (plausibly a mis-keying of "HOPE" = 4-6-7-3) that propagated from the signed-off L0 into the code constant. This makes evidence **B5** (wrong-helpline localization as a dominant industry failure) a description of **our own production system** — hence G8 is HIGH and blocks all crisis-copy work.

Audit found two numbers in circulation: **`800 46342`** — the live `CRISIS_LINE_UAE` constant (`config.py:25`), emitted by `crisis_response` (`graph.py:57-59`) and L0 v2.2.0 (~87 refs); **`800 4673` / `800-HOPE`** — ~49 refs across docs/benchmarks (the correct one).

**Required actions (all under G8):**
1. **Clinician + compliance dial-test BOTH numbers**; confirm which connects to the Mental Support Line, and confirm **hours/scope**. Known: the line is **not 24/7 — 8am–8pm daily** — which (a) changes crisis-copy wording and (b) strengthens keeping **999 co-listed** for out-of-hours.
2. **Correct the false "free, 24/7" claim** in current copy (`graph.py:57`, and any L0/rules text) — it is inaccurate for an 8am–8pm line and is itself a crisis-copy defect surfaced by this finding.
3. **Collapse to a single source, configurable everywhere** (product directive): one config object — number + **label ("Mental Support Line", not misattributed)** + hours + the co-listed 999 — consumed by `graph.py`, `output_gate.py`, the `crisis_content` rules, **and** `L0_persona.json` (today the number is hardcoded inside the L0 prompt text). Nothing may embed the literal number/hours again. See the new **W7** for the centralization task.
4. **L0 fast-track re-sign:** because the erroneous number lives inside signed-off **L0 v2.2.0**, correcting it **is a persona change** and needs a fast-track clinical re-sign, not just an eng edit. Add to G8 scope.
5. **Regression test** pins the verified number **and its label**, and asserts no literal helpline digits appear outside the single config source.
6. **Clinician-content scope (found during W7 commit-1).** The number is embedded in **clinician-authored JSON**, pinned to `config.CRISIS_LINE_UAE` by `test_corpus_integrity.py`. Per Cardinal Rule 4 these are content, not code, so their edits ride the **G8 fast-track re-sign** alongside L0. Affected files to enumerate in the G8 packet:
   - `rules/data/crisis_content/en_uae.json`, `rules/data/crisis_content/ar_uae.json` (primary crisis card + the false "24/7")
   - `skills/psychoed_depression.json`, `skills/psychotic_referral.json`, `skills/post_crisis_check_in.json` (escalation_matrix crisis line)
   **Do NOT introduce placeholder templating into the skill JSONs** — that is schema scope creep beyond §K. `test_corpus_integrity.py` (which fails the moment the config value diverges from the JSONs) is the correct POC forcing function: flip the config value in commit-2 and it lists every JSON still on the old number.

Value swap + centralization ship **together**, gated on 1 & 4. All `999` references are consistent and unaffected.

### J.4 — Confirmed-aligned (no change needed)
W4 (pinned Arabic anchors) = Cardinal Rule 3 ("LLM renders language, nothing else") applied to instruments, matching Node 8's deterministic post-check role + TD4/TD6. W2 (warm monitoring) fills the SF-3 gap (post-crisis handling was undefined). §G validation implements SF-1 (passive-SI corpus) + SF-6 (FP suite) + Arabic recall regression. Governance (flags, atomic commits, sign-off register, safety-surface CI gate) matches "auditability over elegance." Product-vision: detection sensitivity untouched, response graded, T2 floor absolute — honors the "reflective wellness companion that still routes crisis into a pre-approved protocol" scope.
