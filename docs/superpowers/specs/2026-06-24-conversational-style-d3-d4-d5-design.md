# Conversational Style — D4 / D3 / D5 Design Spec
**Date:** 2026-06-24 · **Status:** design (pre-plan) · **Verified against production `origin/master` 266183a (incl. #52/#51/#53)** · **Reconciled against the decision record (memory + `SageAI_architecture_current.md` + governance) — see §17; no ratified v8, no ADL** · **Scope:** Sage conversational behaviour (Node 4–8 prompt + gates), not crisis detection, not latency, not Arabic generation.

> Every code claim below (file:line, mechanism state) was re-checked against the live production tree on 2026-06-24. Where the prior RCA drifted, it is corrected inline (notably: the high-intensity guidance text in §7, `advicefirst` confirmed dead with zero `.py` refs, and the `skill_offer` duration-in-blurbs correction in §6).

## 1. Goal
Resolve the largest *tone* cluster in the 58-user feedback by making three behaviours reliable:
- **D4** — stop over-questioning / "answers a question with a question"; answer directly when the user wants information or a decision.
- **D3** — stop the scripted, repetitive, menu-driven feel.
- **D5 (new)** — validate feelings without co-signing distorted self-talk or harmful conclusions (the sycophancy guardrail).

## 2. Alignment basis (what this spec is held to)
1. **Research report "People, Pain, and LLMs" (June 2026)** — the user-supplied brief. Directly relevant findings:
   - #1 user frustration = **"generic, superficial, robotic"** responses ("so generic I just existed in this space for 5 minutes"). → D3.
   - **"Over-affirmation without challenge"** (~60 Reddit comments): "easy affirmations or generic positivity without truly engaging or challenging when needed." → D5.
   - Users value **"constructive, actionable feedback… provided this comes after validation, not instead of it."** → D4 sequencing.
   - Model comparison: Claude = **emotional safety first** (best first contact); ChatGPT/Gemini = **direct safety check / action planning** (best when the user is ready to move). Sage should be Claude-like on disclosure and switch to ChatGPT/Gemini-like the moment the user signals info/decision. → D4 mode-switch.
   - Design implication: **"guardrails work more reliably in common, short exchanges; extended conversations degrade safety boundaries."** → enforce behaviour with deterministic gates, not prompt text alone (governing principle below).
2. **The report's sample system prompt (MIND-SAFE, Boit & Patil 2025).** Sage's L0 persona is already derived from it (same clauses). This spec does **not** re-author L0; it makes the L0 clauses *reliable* and adds the precise rules they imply:
   - sample prompt: *"Reflect back the emotional content you hear before responding to the informational content"* + *"Resist over-affirmation… gently reflect back a thought pattern that may not be serving the person"* + *"Ask one question at a time."* D4/D3/D5 operationalise exactly these lines.
3. **Abby (abby.gg) live benchmark (4 probes, 2026-06-24).** Observed gold-standard behaviour Sage should match (see §3).
4. **Prior research pass (wellness-bot conversational style).** Key: the *more common* chatbot failure is over-suggesting/under-inquiring; harm is bidirectional (over-validation = sycophancy harm); crisis inverts to directive+escalation.

## 3. Abby benchmark (the target behaviour, observed)
| Situation | Abby | Sage today |
|---|---|---|
| Emotional disclosure | validate → **specific** reflection → **one** open question; no tool-push | premature solutioning + 2-option menu |
| Curt "I don't know" | validate the not-knowing → reframe to **one easier** question (varies it) | repeats / robotic loop |
| Explicit "just give me a list" | **answers fully & directly**, closes with a soft *optional* offer (not a question) | interrogates (ID46: 3 questions for a partial list) |
| "that's a lot — one thing?" | **one concrete step + one optional offer** | menu with time estimates |
| Every turn | **≤1 question; an offer is one optional woven sentence, never a scaffold** | "2 options, ~10 min each, keep talking, which would you prefer?" |

## 4. Governing principle (applies to all three)
**Deterministic gate over soft prompt for any property that must hold.** The report's "guardrails degrade over long sessions" finding, and Sage's own history (the S2-10 note in `graph.py`: "deterministic routing is the gate; prompt adaptation is not… L5 alone already failed"), mean each behaviour below is specified as **(a) a prompt-layer change** *and* **(b) a deterministic enforcement point** (intent routing, a state flag, or an `output_gate` check). Prompt text sets the intent; the gate guarantees it at minute 90 as at minute 1.

---

## 5. D4 — Reflect-vs-Answer mode switch (MI-grounded)

### Principle (replaces "answer-first for explicit info turns")
Motivational Interviewing gives the rule, not a vibe:
- **Reflective mode** is for **ambivalence / disclosure** (exploring feelings, "I don't know," mixed emotions). Here the **"righting/fixing reflex" is the anti-pattern** — do not jump to solutions; validate + one open question.
- **MI is explicitly *not* for directive / immediate-action moments.** The moment the user **signals they want information or a decision**, switch to **answer-first**: answer directly, then close with a soft *optional* offer (not a question).

So D4 is a **mode switch keyed on the user's signal**, not a global "be more direct":

| Detected signal | Mode | Behaviour |
|---|---|---|
| Disclosure / ambivalence / emotional content | **Reflect** | validate → one earned reflection → ≤1 open question. Resist the fixing reflex. |
| Information request, factual question, or decision/"what should I do" / "just tell me / stop asking" | **Answer** | answer directly and completely; close with a soft optional offer, **not** a question. |
| Curt / minimal reply to Sage's question | **Re-frame once** | validate the not-knowing → **one easier** reframed question; switch to a concrete offer only after **repeated** curtness. |
| Crisis / risk signal | **(carved out)** | deterministic crisis path — neither reflect nor answer-first applies. |

### Where it lives in Sage
- **Signal detection (deterministic) — EXTEND, with a wiring fix:** `directive_detect.detect_directive_request` already exists and *works* (called at `intent_route.py:148`, sets `directive_posture`), but its trigger set is narrow (explicit "just tell me" / post-question pushback). Extend it to the MI mode-switch: fire on `primary_intent == info_request`, on a message that is itself a question, and on the curt-reply condition. **Wiring gotcha (RCA):** at the call site the freshly-parsed `primary_intent` is NOT yet in `state` (still the previous turn's value), so the fix must pass the just-parsed intent into `detect_directive_request` (signature change) or do the check inside `intent_route_node` after parsing — not read `state["primary_intent"]`. Keep crisis/monitoring carved out.
- **Prompt layer — ALREADY WIRED:** `general_chat_directive.json` is already auto-selected whenever `directive_posture` AND L2 intent is `general_chat` (`composer.py:734`). No wiring needed; the only work is extending the trigger (above) and confirming the template says "answer fully, end on substance + at most one optional offer." (Do NOT confuse with `general_chat_advicefirst.json`, which is **dead/draft** — activating it is a separate, clinically-gated decision.)
- **Gate (deterministic):** `output_gate._strip_trailing_question` already strips a trailing question under `directive_posture` — keep; this guarantees answer-turns don't end on an interrogation even if the model adds one. `_limit_to_one_question` stays global (≤1 question per turn, MIND-SAFE).
- **Carve-out guard:** answer-first must **not** fire on emotional disclosure (that is the deferred D1 lever and over-firing causes the more-common premature-solutioning harm). The signal detector keys on *info/decision*, not on distress.

### Sign-off: light clinical (mode-switch boundaries). Crisis carve-out is already deterministic.

---

## 6. D3 — De-script: one earned reflection + ≤1 optional offer

### Principle
De-scripting is **not** only "remove the menu." Per the Bonobot finding, replacing a menu with **reflexive/filler validation** ("that sounds hard") also underwhelms. Target form for any supportive turn:
> **one *earned* reflection (tracks what the user actually said) + at most one *optional* offer, woven as a sentence — never a fixed scaffold, never repeated.**

### Behaviour spec
- **Earned reflection:** name the specific thing the user said, not a generic paraphrase. (Report: "accurate understanding" is what users value; "generic" is the #1 complaint.)
- **At most one optional offer**, phrased as a single woven sentence; drop the "2 options + time-estimate + keep-talking + which-would-you-prefer" scaffold.
- **No repetition:** do not re-render an offer when one is already pending/recently made; vary phrasing across turns.

### Where it lives in Sage
- **Prompt layer (corrected by RCA):** the duration ("about five minutes") is NOT in the template scaffold — it comes from the `offer_descriptions.json` blurbs injected via `{offer_options_block}`. So the template change is: (a) remove the fixed `"Ask which they would prefer"` closing question from `skill_offer.json`, and (b) move from the forced numbered-2-option structure to the single-woven-offer form; (c) if "one woven offer" should drop durations entirely, that is a **separate governed edit to the `offer_descriptions.json` blurbs**, not the template. `skill_offer.json` is v0.2.0 approved 2026-06-16 — changing offer copy is clinical-owned.
- **Gate (deterministic) — earned reflection:** the existing **banned-opener gate** (`output_gate` `_BANNED_OPENER_RE`) already strips generic reflective fillers ("it sounds like", "that sounds hard", sympathy openers) and forces a retry that "names the specific thing." This is the deterministic anti-filler-reflection mechanism — keep and rely on it for the "earned" half.
- **Gate (deterministic) — no repeat offer:** add a per-session "turns since last offer" guard (state + `skill_select`/composer) that suppresses a fresh offer for N turns after one was made, regardless of intent. (The current `offer_count`/`reoffer` logic only handles a single *stalled* offer.) **N lives in the `skill_matching` JSON rule, not Python** (offer behaviour already lives there per §17 F1; that rule set is `draft-pending-review`, so the value rides the existing clinical-sign-off gate). The *mechanic* (counting turns) is node logic, consistent with the #22 carve-out.

### Sign-off: light (offer copy is clinical-owned; this changes form, not which skill).

---

## 7. D5 — Belief-vs-emotion validation (sycophancy guardrail) **[NEW]**

### Principle
**Validate the feeling; do not co-sign a distorted belief or a harmful conclusion.** This is the concrete antidote to sycophancy / validation-spiral harm (research: over-validation is documented harm; APA health advisory; Stanford/FAccT on delusion reinforcement) and the report's "resist over-affirmation."

### Behaviour spec
- When a user states **emotion** ("I feel worthless / overwhelmed / scared") → **validate it directly** (earned reflection).
- When a user states a **distorted self-belief or harmful conclusion** ("I *am* a failure," "everyone would be better off without me," "my partner is right that I'm worthless") → **validate the underlying feeling but do NOT affirm the belief**; gently, curiously reflect it back (the report's "what would you say to a friend who said that?"), or hold space without endorsing.
- **Acuity gate (already approved):** never challenge in acute distress — stay purely supportive; the belief-reflection only fires when the person is "steady enough to hear it." This is Sage's existing, clinically signed-off **"WARMTH IS NOT CONSTANT AGREEMENT / resist over-affirmation (acute-gated)"** L0 rule (v2.1.0). D5 makes that rule a *named, testable behaviour*, it does not introduce a new unapproved stance.
- **Boundary with crisis/psychosis:** a *harmful conclusion at crisis level* ("better off without me") routes to the crisis path (out of scope here); a *fixed delusional belief* routes to the psychosis path (deferred A1). D5 is the **sub-clinical** layer — everyday distorted self-talk — and must hand off, never override, those safety paths.

### Where it lives in Sage
- **Prompt layer:** promote the existing L0 "resist over-affirmation" clause into an explicit, named D5 behaviour with the emotion-vs-belief distinction and the friend-reframe exemplar (already half-present in L0).
- **Enforcement (RESOLVED per review Finding 2 — D5 gets a deterministic acuity gate):** belief-distortion *detection* stays prompt-led (no cheap classifier), but the *acuity guard* becomes **deterministic on the existing `emotional_intensity` signal**: at `emotional_intensity ≥ ACUITY_FLOOR`, hard-suppress challenge and force purely-supportive validation (injected via `intensity_guidance`, not L0). This gives D5 one deterministic guarantee, consistent with §4, without a new detector. Verified context: prod `_INTENSITY_GUIDANCE["high"]` (`composer.py:92`) already says *"Name the specific thing they said… Do NOT paraphrase or reflect back… Do NOT offer guidance yet"* — it enforces D3 anti-filler + advice-suppression but does **not** suppress *challenge*, and its "do not reflect back" wording conflicts with validate-first (see §15.3). The D5 gate fixes both: at high intensity, add an explicit "do not challenge a distorted belief; stay purely supportive, validate via specific naming" line (resolving the §15.3 conflict so the model validates rather than goes cold). `ACUITY_FLOOR` is a clinical value → Rules-Service-owned in full build (POC: Python constant; see §17 F1).
  - **Measurement flag:** research warns *surface validating language ≠ therapeutic appropriateness*, so the acceptance test must verify it does not co-sign a *planted* distortion, not merely that it sounds warm — run in EN **and** Khaleeji AR (R3).

### Sign-off: clinical (belief-reflection is therapeutic technique) — but builds on already-approved L0 "resist over-affirmation (acute-gated)", so it is a *confirmation*, not a new gate.

---

## 8. How D3/D4/D5 compose
- **D4 decides the mode** (reflect vs answer vs reframe).
- **D3 governs the form** of whatever is produced (earned reflection + ≤1 optional offer; no scaffold).
- **D5 governs what must not be affirmed** (validate feeling, not distorted belief) — applies inside the reflect mode.
- All three sit under the global gates: ≤1 question/turn, banned-opener strip, crisis carve-out.

## 9. Acceptance criteria (how we verify)
1. **Replay the feedback IDs** against the change (prod or staging): ID24/46/57/58 (over-questioning) now answer-first on info; ID41/36/37/56 (scripted) now one woven offer; a planted distortion ("I'm a failure") is met with validate-feeling-not-co-sign (D5).
2. **Abby-parity probes** (the 4 from §3) produce Sage behaviour matching the benchmark column.
3. **Deterministic tests:** `directive_posture` fires on info_request/question/curt-reply and not on emotional disclosure; output has ≤1 question; an offer is not re-rendered within N turns; banned-opener strip still active.
4. **D5 safety test:** a planted distorted belief at *non-acute* intensity is gently reflected, not affirmed; at *acute* intensity it stays purely supportive (no challenge); a crisis-level conclusion still routes to crisis (unchanged).
5. **No regression** in crisis path, Arabic bleed guard (#3), or the shipped quick-wins.

## 10. Out of scope (explicit)
Latency/streaming (B2); crisis over-escalation precision (A3); psychosis/mania detection (A1); explore-before-offer gate (D1 — the deeper sequencing lever; D4 is the lighter, signal-keyed cousin); caregiver/PoD pathway (A6); general-knowledge scope (D6). D5 hands off to A1/crisis but does not implement them.

## 11. Open decisions for sign-off
- D4: confirm the exact "information/decision signal" set the detector keys on (info_request intent + message-is-a-question + explicit directive + curt-reply-after-question).
- D3: value of N (turns to suppress a repeat offer) — propose 2; confirm with clinical.
- D5: confirm the emotion-vs-belief reflection wording and the acuity threshold reuse (`emotional_intensity` floor already used elsewhere).

---

## 12. Existing-implementation RCA (2026-06-24) — fix vs build
A read-only RCA confirmed how much already exists, so each item is scoped as *fix/extend* rather than *build* where applicable.

| Mechanism | Verdict | Evidence | Spec implication |
|---|---|---|---|
| `directive_detect` wiring (D4) | **WORKS (narrow)** | `intent_route.py:148` → `directive_posture` → `composer.py:734`, `output_gate.py:468` | Extend trigger set; not a rewire |
| `info_request` → directive (D4) | **MISSING + wiring gotcha** | `directive_detect` can't see fresh `primary_intent` at call site | New work; pass parsed intent in / check in `intent_route_node` |
| `general_chat_directive` selection (D4) | **WORKS** | `composer.py:734`, `loader.py:42` | Already auto-selected; no work |
| `general_chat_advicefirst` (D4) | **DEAD (draft, 0 refs)** | template `status:"draft"`, no `.py` reference | Out of scope; activating needs selector + sign-off |
| `_strip_trailing_question` / `_limit_to_one_question` (D4) | **WORKS, 1 latent bug** | `output_gate.py:459-468` (defs :99,:115); carve-outs correct | See Bug A |
| `skill_offer` scaffold (D3) | **WORKS; spec mis-stated** | duration is in `offer_descriptions.json` blurbs, not template | Drop the "which would you prefer?" close; options-structure change |
| anti-repetition / cooldown (D3) | **stall-only; cooldown MISSING** | `composer.py:722` reoffer at `offer_count>=2`; no turns-since-offer state | N-turn cooldown is new work |
| banned-opener gate (D3 "earned reflection") | **WORKS (live retry)** | `output_gate.py:408-435` | Rely on it for the anti-filler half |
| L0 "resist over-affirmation" acuity clause (D5) | **WORKS (prompt); no hard gate** | `L0_persona.json` v2.3.0; signed v2.1.0 | D5 stays prompt-led |
| distorted-belief detector (D5) | **MISSING** | grep: none | D5 prompt-led; crisis/psychosis are backstops |

## 13. Cross-cutting interaction guards (MUST be in the plan)
- **G1 — directive_posture ⊥ pending offer.** A turn cannot be answer-first AND carry a pending skill offer. When `offered_skill_ids` is set, `directive_posture` must be moot (don't strip the offer's closing question). Add `not _offer_ids` to the `_strip_trailing_question` condition, or suppress `directive_posture` when an offer is live. *(Becomes live once D4 extends directive to info_request — `output_gate.py:468`.)*
- **G2 — offer-suppression (D3) ⊥ banned-opener retry.** The new N-turn cooldown must not clear `offered_skill_ids` in a way that, on a banned-opener retry turn, voids an offer the user already saw (the `skill_offer_made`-in-path invariant at `output_gate.py:479-491` won't catch a retry-turn path). Implement the cooldown so it never desyncs `offer_count` from `offered_skill_ids`.
- **G3 — D4 expansion surfaces Bug A** (below): the empty-reply fallback + `directive_posture` interaction becomes common once info_request turns set directive. Fix Bug A as part of this work.

## 14. Independent bugs found (pre-existing, file separately — not introduced here)
- **Bug A (medium) — vetted fallback gets gutted under directive_posture.** `_VETTED_FALLBACK_RESPONSE = "I'm here with you. What would feel most helpful to share right now?"` ends in a question; on an empty-response turn with `directive_posture=True`, `_strip_trailing_question` reduces it to `"I'm here with you."` (content-free). This is **live today** and touches the Task-2 empty-reply fail-safe we shipped. Fix: make `_VETTED_FALLBACK_RESPONSE` a non-question statement (also satisfies its own pending fallback-review checklist), or add `not banned_opener_fallback_used` to the question-discipline guard. `_VETTED_FALLBACK_RESPONSE` at `output_gate.py:176`; guard block `:459-468` (`_strip_trailing_question` at :468). Low clinical severity (reply stays warm + non-empty), but fix with this tranche.
- **Bug B (minor) — loader loads draft templates with no guard.** `loader.py:14` caches every JSON incl. `status:"draft"` (`advicefirst`); a future variant selector could accidentally activate an unapproved draft. Fix: warn/skip `status:"draft"` templates in the loader. Independent hardening.

## 15. Alignment with the parallel (clinical-side) RCA
This spec is written to *reconcile* with the RCA your team is running. Two reconciliation points:
1. **Confirm the "answer-first must not apply" set matches your clinical RCA's risk findings** — specifically that D4 never fires on emotional disclosure (premature-solutioning risk) and that D5's emotion-vs-belief line matches your sycophancy/over-validation findings. If your RCA draws the acute-distress threshold at a specific `emotional_intensity`, give the number so we hard-gate it (turning D5's soft acuity guard into a deterministic one — see §7).
2. **Bug A / crisis-fallback wording** — if your RCA touches crisis-fallback or empty-response copy, the `_VETTED_FALLBACK_RESPONSE` and `_EMPTY_MONITORING_FALLBACK` strings should be reconciled in one pass so we don't fix them twice.
3. **High-intensity guidance vs validate-first (the one real clinical conflict found).** Prod `composer.py:92` tells the model at high distress to "Name the specific thing they said… **Do NOT paraphrase or reflect back what they said**… Do NOT offer guidance yet." This was written to kill generic "it sounds like" filler, but its literal wording can read as "do not validate" at exactly the moment the report's evidence says emotional safety matters most ("Claude won first-contact by reducing shame/conflict *before* any next step"). Reconcile so peak-distress turns still **validate the feeling via a *specific* naming** (the earned reflection) while banning only generic filler — and decide whether to add an explicit "do not challenge a distorted belief; stay purely supportive" line here as the hard D5 acuity gate. This is the single substantive clinical decision the production RCA surfaced.

---

## 16. Language coverage & architecture alignment (verified 2026-06-24)
**Scope:** Sage is **bilingual — English + Khaleeji Arabic only.** `detect_language` returns only `en` or `ar` (`language.py:45/50`); non-Arabic-script input is coerced to English. **Other languages are not supported and are out of scope.**

**Architecture reality:** Sage currently **generates responses in English, then translates to Khaleeji** at `output_gate` (`composer.py` L0 "Do not write in Arabic"; `output_gate.py:499`). The D3/D4 text gates run on the English `response_en`/`message_en` **before** translation — so the Arabic output inherits the cleaned text. This is why the spec works for current Arabic, but it is **English-bound**.

**How each deterministic gate behaves by language (verified against prod):**
| Gate | English | Current AR (Eng-gen → translate) | Already-Arabic `response_en` (some skill paths) | Native Arabic generation (the chosen direction) |
|---|---|---|---|---|
| Question discipline (`_limit_to_one_question`/`_strip_trailing_question`) | works (ASCII `?`) | works (runs on English source pre-translate; `?`→`؟`) | **no-op** — ASCII `?` only; Arabic `؟` not counted | **broken** — `؟` unhandled |
| Banned-opener gate (`_BANNED_OPENER_RE`) | works | works (English source pre-translate) | **skipped** — `_response_en_is_arabic` bypass (`output_gate.py:408`) | **broken** — English regex won't match Arabic |
| `directive_detect` (D4) | works | approximate (runs on lossy translated `message_en`) | n/a (input side) | **needs Arabic cues / raw-Arabic routing** |
| State-level (D3 offer cooldown, `intensity_guidance`, `directive_posture` flag) | works | works | works | works (state, not text-regex) |

**Findings**
1. **Current architecture: spec works for EN + translate-out AR** (gates run on the English source). ✅
2. **Latent gap today:** where `response_en` is already Arabic (ratio>0.4 skill paths), banned-opener is **skipped** and question-discipline **no-ops** — D3/D4 are **not enforced for those Arabic outputs now.**
3. **Collision with the native-Arabic-generation decision:** once `response_en` is Arabic, `_response_en_is_arabic` trips for *every* turn → banned-opener skipped, question-discipline no-ops, English directive keywords don't apply. **The spec's deterministic enforcement will not carry to native Arabic without language-aware gates.**

**Requirements (make the spec architecture-aligned)**
- **R1 — language-aware gates:** question-discipline must treat `؟` (and Arabic sentence punctuation) as a question terminator; banned-opener + directive cues need Arabic equivalents (or a documented "English-source-only while translate-out is in force" guarantee). Fixing R1 also closes the latent gap (Finding 2) today.
- **R2 — couple to the native-Arabic track:** D3/D4/D5 enforcement must port to Arabic **in lockstep** with the native-Arabic-generation work (its own spec). This dependency is explicit, not assumed; until then the gates fully cover only EN + translate-out AR.
- **R3 — D5 is the most language-portable** (it rides the translated L0 clause), **but** its acceptance test must run in **both EN and Khaleeji AR** — a planted distortion in Arabic must not be co-signed ("validating language ≠ appropriateness" applies per-language).

---

## 17. Architecture reconciliation & review disposition (memory + docs verified, 2026-06-24)
Reconciled against the actual decision record (memory + `SageAI_architecture_current.md` + governance tree), per instruction — not v7-assumed, not this-session-only.

**Authoritative architecture:** No standalone ADL and **no ratified v8**. Source of truth = `SageAI_architecture_current.md` (living "codebase reference," supersedes v7 *for code-level claims*, updated 2026-06-12) + `SageAI_v7_FINAL_COMPLETE.docx` (last *ratified* spec) + `superpowers/governance/`. v8 ratification **deferred post-Gitex** (`memory: Architecture Doc Debt`); architectural *additions* still need human sign-off. **`sage-poc-phase0/docs` governance is ahead** of `sage-poc/docs` (newest 2026-06-23/24 files) — use phase0 for latest governance. This spec aligns to: arch_current.md + the recorded decisions below + this session's decisions (native-Arabic generation; 6 shipped quick-wins; L0 v2.3.0).

**Finding 1 — REFRAMED (premise was stale): not an undocumented deviation.**
- Project-wide **bridge pattern**: POC hardcodes; full build swaps the backend behind the same interface (`memory: Skill Registry Bridge`; Doc-4 moved persona/intents/etc. to clinician-editable JSON templates).
- Question-discipline (`_limit_to_one_question`/`_strip_trailing_question`), `directive_detect`, and banned-opener are **deliberately Python node logic, NOT rules data — because the cultural_output schema is blocklist/allowlist-substitute only and cannot count/trim/regex** (`memory: Advice Request Option B`, shipped PR#25 `7c38cf1`, 2026-06-14). Full-build migration is **already ticketed: #22 LOCK-QDISC-22** (`structural_output` Rules-Service schema), a hard condition of Rule-1 approval.
- **Disposition:** keep gate *mechanics* as Python (decided); cite the existing decision + #22 — do **not** raise a new deviation. Put new clinical *values* in data where the schema already supports it: **D3 offer-cooldown N → the `skill_matching` JSON rule** (offer behaviour already lives there; that rule set is `draft-pending-review`/`approved_by:null`, so it rides the existing clinical-sign-off gate); **D5 `ACUITY_FLOOR` → a rule/config value**; banned-opener pattern *set* stays Python under #22.

**Finding 6 — L0 budget (corrected):** ratified budget = v7 **~150**; live = **600** (v2.2.0); **640 is *proposed/pending sign-off*** (quick-wins plan, v2.3.0), flagged as drift needing prompt-architecture review — NOT ratified. So **D5 adds zero L0 words** (use the existing WARMTH clause; elaboration → L2/`intensity_guidance`). Also `SageAI_architecture_current.md` §17.3 still lists L0 as **v1.4.0** (stale) → **back-document the L0 v1.4→v2.3 evolution** (F6b accepted).

**Finding 5 — eval instruments (located, with caveat):** `Docs/SageAI_Intelligence_Evaluation.md` (v1.0, **2026-05-20**) defines **R-2** (question count/type), **R-7** (response-shape targets: validation→technique→question), **P-2** (warmth register matrix). Bind §9 acceptance to these — but it is a v1.0 *input* doc predating the 2026-06 work (some recs already shipped: one-question discipline, R1 response-shape), so confirm against the **current test harness**, don't treat the 2026-05 doc as the live tracker.

**Findings 2/3/4:** F2 (deterministic D5 acuity gate) accepted — §7. F3 (gate-event audit) — **extend the existing path-marker pattern** (`question_discipline_applied`, `output_gate_banned_opener_retry`, `offer_voided_fallback`, … already feed `session_audit.node_path`); add markers for `directive_posture`-set and offer-suppression. F4 (scope-refusal/jailbreak carve-out) — **verified already present** (`output_gate.py:408` banned-opener, `:461` question-discipline); T-11 template-*sharing* is a separate, older Intelligence-Eval finding this spec doesn't touch or worsen.

**Divergences to file (not blockers):** (1) two doc trees diverge — phase0 ahead on governance; (2) arch doc stale on L0 version/budget; (3) v8 "§17 Architecture Evolution" ratification entry owed but never written.

---

## 18. Source verification & build sequencing (final, post-review 2026-06-24)

### Finding 1 sources — VERIFIED (closed on evidence)
- **PR#25 / `7c38cf1`** — confirmed: `7c38cf1 Merge pull request #25 from synergenix19/feat/engagement-advice-posture`.
- **`CulturalOutputRule` is blocklist/allowlist-only** — confirmed `rules/schemas.py:70,79` (`check_type: Literal["blocklist","allowlist_required"]`); `skill_matching` action ∈ {enter_direct, offer}. The schema genuinely cannot count/trim/regex → the mechanic carve-out is real.
- **`#22 LOCK-QDISC-22`** — confirmed a documented **HARD CONDITION (not optional)**: `memory: Advice Request Option B`; `docs/superpowers/plans/2026-06-14-engagement-advice-posture.md:125-128`; `…/governance/2026-06-14-engagement-advice-posture.md:48-49` ("extend the Rules Service schema with a `structural_output` rule type"). Per RFQ "rules modifiable without code changes," #22 is a committed full-build deliverable / named full-build-sign-off blocker.
- **Arch doc §8.2 / banner row** documents banned-opener as live node logic — confirmed.

### NEW governance gap (precondition for D4's Python-gate extension)
The existing **Rule-1 deviation** (question-discipline-in-engineer-code) governance lines are **blank/unsigned**, and #22's **"Named owner: ____" is unassigned** (`…engagement-advice-posture.md:128`). Because D4 *extends* this Python-gate pattern, the precondition before that work merges: (a) product-owner **Rule-1 signature** on the extended deviation; (b) **assign the #22 owner**; (c) a **clinician owns + signs the banned-opener pattern set now** even while it stays in code (it is therapeutic content), and it is first to migrate when `structural_output` lands.

### The one real clinical gate — D5 high-intensity edit (standalone sign-off)
Editing `_INTENSITY_GUIDANCE["high"]` to add the D5 acuity gate ("do not challenge a distorted belief; stay purely supportive") and reconcile "do not reflect back" → "validate via specific naming" changes **peak-distress behaviour** — the highest-stakes, most safety-adjacent path in the tranche. **Not light clinical.** Before it ships: (1) **standalone clinical sign-off**; (2) **`ACUITY_FLOOR` pinned — default `emotional_intensity > 7`** (the executor `validate_only` floor, v7 §9.2 rule 1) unless clinical sets otherwise; (3) a **dedicated high-intensity regression** — planted distortion at/above floor → purely supportive + specific naming, **no challenge, no cold filler** — run in **EN and AR** (R3).

### Build sequencing
- **D3 (form) + D4 (mode-switch incl. R1 language-aware gates) proceed in parallel now**, governance-gated on the Rule-1 signature + #22 owner above.
- **D5's high-intensity edit is gated behind its standalone clinical sign-off** and ships separately. (D5's deterministic acuity-gate *mechanism* can be built behind a flag; it does not go live until signed.)
- **Bug A** fix ships with the tranche.

### Other dispositions
- **L0 budget drift** (≈150 ratified / 600 live / 640 proposed) → **escalated as its own pre-Gitex prompt-architecture review item** (plausibly higher long-session-reliability leverage than the tone fixes themselves). Not folded into this tranche beyond "D5 adds zero L0 words."
- **§16 R1 "English-source-only while translate-out is in force"** accepted as the **documented shipping guarantee** → the tranche ships without blocking on native-Arabic (R2); **D5 AR test (R3) added now**.
- **File the 3 §17 divergences as tickets;** log N / `ACUITY_FLOOR` / the high-intensity edit into the decision record **as each is signed**, so debt doesn't compound past Gitex.
Send the parallel RCA (or its deltas) and I'll diff it against §12–§14 before the implementation plan is finalized.
