# Clinical Containment Pathway — Implementation Plan (rev 2)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use `- [ ]`.
>
> **TWO STAGES.** Stage 1 (this week) stops the live iatrogenic leak with the OCD-veto precedent — no schema change, no architecture approval. Stage 2 is the approval-gated containment destination class; when it lands, harm-intrusive's destination upgrades abstain→contain as one migration row.

**Goal:** stop postpartum harm-intrusive disclosures routing to self-help skills (Stage 1), then add a first-class *containment* outcome for clinically-significant non-crisis disclosures (Stage 2).

**Clinical authority = the BOT BEHAVIOUR spec (clinician-owned), NOT Abby.** Abby is a *warmth/style* reference; the spec is what the content conforms to and what the clinician signs against. The spec ALREADY prescribes this territory:
- **OCD-type / intrusive-thought / compulsive content → route to PROFESSIONAL REFERRAL, not self-guided skills** (spec §Worry-track guards, lines ~229/271: "Worry Tree/Worry Time… can reinforce compulsive patterns"). This is an intermediate disposition, **separate from the crisis guard** (line ~81).
- **Universal crisis override supersedes everything** (line ~83 and ~9 repeats): SI/self-harm/harm-to-others → exit immediately to crisis protocol.
- **"Safety woven in naturally rather than led with"** (lines ~482/541/591) is the mandated risk-check style — do not lead with the risk question.

So the postpartum→worry_time routing the finding caught is a **documented spec deviation** (the exact "can reinforce compulsive patterns" failure), which raises Stage 1's urgency. **Reference exemplar:** Abby's postpartum reply (validate → psychoeducate → differentiate "does not mean you want to act on them" → name "postpartum OCD" → risk-check → engage) supplies the warmth; the spec adds the **professional-referral signpost** Abby omits.

## Global Constraints
- **Safety over capability:** the open leak does not wait for the destination class. Stage 1 ships behind clinician *pattern* sign-off only.
- **Deterministic trigger only** (patterns, never the phrasing-sensitive reranker). **The deterministic keyword veto is a PERMANENT Tier-1 guardrail** (like the OCD veto / crisis keywords) — it stays. A semantic S2-MARBERT classifier (Gap #65) is ADDED later as a second layer for generalization (defense in depth), NOT a replacement — the deterministic floor is never removed. Every phase is production; no interim/throwaway work.
- **Tools never replace guardrails:** on a containment/veto turn, `suggest_skill` is unbound (or family-vetoed) — a guardrail must not be optional through a tool.
- **Prompt-layer discipline:** retrieved KB → existing **L4** (~300w, via Node 6); containment few-shot/tone/step → **L3** skill-context slot (template-owned). NO new layer. Per-layer word budget asserted in tests; total ≤ ~1,100w.
- **Bilingual/cultural is mandatory content:** every containment family needs AR+EN few-shot ≥3, `cultural_overrides`, Node-8 cultural rules; **per-language KB fail-safe** — AR falls back if the AR article/naming isn't clinician-ruled yet.
- **KB-content gating, fail-safe per language:** no ready article → bare abstain, never an empty turn.
- **Escalation is human-in-loop:** probe autonomous; risk-positive → L3 safety protocol (`crisis_response`); no autonomous "no-risk" clearance ([[project_cssrs_active_screening]]).
- **Crisis supremacy:** containment is evaluated AFTER Node 1's crisis short-circuit; it never competes with it.
- **No em dashes in rule/skill content** ([[feedback_em_dash_rule_content]]). Clinical content needs qualified-human sign-off, never eng self-assessment.

---

# STAGE 1 — URGENT harm-intrusive veto (ships this week, OCD-veto precedent)

No state/schema/graph-vocabulary change. Destination = today's bare abstain (Node 3). Approval = clinician pattern sign-off only.

## Task S1.0: Harm-gate corpus expansion FIRST (measurement discipline)
- [ ] Add the failing worry-framed phrasing ("can't make them stop, scares me so much") + clinician paraphrases + the "can't shake" control to the **committed** `tests/fixtures/routing_eval/` harm set. Commit fixtures (cite SHA).
- [ ] Re-measure BOTH arms on the expanded corpus; **annotate the verdict artifact** (`2026-07-08-v2-reverdict-FLIP.md`) — the harm-domain number moves; record honestly. This is the gate for S1.1.

## Task S1.1: Deterministic harm-intrusive veto (mirror `ocd_compulsion`)
- [ ] **Test first (both directions):** natural + terse postpartum harm-intrusive phrasings → vetoed/abstain (0 skill routes on the expanded corpus); ordinary parenting worry → NOT vetoed (false-positive veto that drops a real worry skill is a defined failure).
- [ ] Create `rules/data/safety/harm_intrusive_patterns.json` (clinician-owned) + `nodes/harm_intrusive.py` `is_harm_intrusive(message_en)`, wired into `skill_select_node` before both tiers, arm-independent (exactly like `is_ocd_compulsion`). Returns bare abstain → Node 3 today.
- [ ] Byte-identical guard: no change to any non-matching path. Ship to staging → prod behind the standing deploy gates (ancestry, health, probe).

---

# STAGE 2 — Containment destination class (APPROVAL-GATED)

## Task 0 (BLOCKING): Absolute-Rule-1 deviation spec + 3 sign-offs
**Create** `docs/superpowers/specs/2026-07-08-clinical-containment-pathway-design.md`; propose (unsigned) a section in `docs/SageAI_architecture_current.md`.
- [ ] Spec the design (state / `contain` action / one edge / L3+L4 mapping / template / audit + review-queue), and state explicitly: **crisis supremacy** (containment after Node 1, never competing); **escalation mapped to the v7 tier vocabulary** — risk-positive → **L3 safety protocol** (`crisis_response`), continued containment → **L2 flag** — so the clinician signs in their own taxonomy.
- [ ] Record three sign-offs: **arch-doc owner** (edge/state/vocabulary), **clinical lead** (containment *as a destination class*; harm-intrusive differentiation questions + escalation branches + KB article + **Khaleeji rendering of "postpartum OCD"**), **PO** (Rule 1). Each later family = a CMS decision, not a re-approval.
- [ ] **STOP** until all three are recorded.

## Task 1: State — `containment_directive`
- [ ] Test: `_build_state` returns `containment_directive: None` each turn (per-turn reset, like `path`/`skill_select_abstained`).
- [ ] Declare `containment_directive: Optional[dict]` (`{family, flag_level, kb_topics, containment_skill_id?, rule_id}`) in `SageState`; reset in `_build_state`.

## Task 2: Rules Service — `contain` action + queue side-effect
- [ ] Test: a `contain` rule match populates `containment_directive` (with `rule_id`); non-match → None. **`flag_level` writes the clinical flag into the 24h clinician review queue** (assert the queue row exists, not just the audit row).
- [ ] Add `contain` to the action schema/loader; CMS validation gates on KB-topic existence + first-person/char-cap rules. Document precedence: `contain` **supersedes** bare `abstain` for families that have it; others unchanged.

## Task 3: Graph — one conditional edge (no new node) + tool suppression
- [ ] Test: directive present → `knowledge_retrieve` (seeded `kb_topics`) → `freeflow_respond` (or `skill_executor` if `containment_skill_id`); directive absent → routing byte-identical; **`suggest_skill` is UNBOUND on the containment turn** (assert the tool cannot re-introduce a skill offer).
- [ ] Add the branch (priority beside crisis/veto safety routes, before generic abstain/freeflow). `knowledge_retrieve` accepts directive `kb_topics`.

## Task 4: Prompt layers — L4 (KB) + L3 (template), NO new layer
- [ ] Test: containment turn composes retrieved article into **existing L4** (~300w) + containment few-shot/tone/step into **L3** (from the template); assert per-layer budgets and total ≤ ~1,100w; absent directive → composition byte-identical.
- [ ] Populate L3 from the containment template; do NOT invent an L4_containment layer.

## Task 5: Harm-intrusive containment content (bilingual, cultural)
- [ ] Author the KB article (`data/knowledge_corpus/postpartum_intrusive_thoughts.md`) modeled on Abby; deploy-time auto-sync + recalibrate if corpus crosses the gate.
- [ ] **Checklist (clinician-ruled, not memo):** AR+EN few-shot **≥3 each**; `cultural_overrides`; the **Khaleeji rendering of "postpartum OCD"**; **Arabic KB counterpart**. Until the AR set is ruled, the per-language fail-safe treats AR as content-not-ready → AR falls back to bare abstain.

## Task 6: Containment skill template (validate → psychoeducate → differentiate → risk-check → REFER → engage)
Template steps must match the BOT BEHAVIOUR spec, not just Abby. The **professional-referral signpost is required** (spec's OCD/intrusive prescription) — Abby omits it. Risk-check is **woven in naturally, not led with** (spec lines ~482/541/591). Differentiation+branches are authored in the spec's **"guard"** vocabulary (the clinician already owns it).
- [ ] Test: the differentiation risk-positive branch → `crisis_response`; risk-negative → continued containment carrying the professional-referral signpost + L2 flag; NO autonomous "no-risk" clearance path; the referral step is present on every containment turn.
- [ ] **EGO-SYNTONIC / PSYCHOSIS deterministic branch (clinician-added, safety-critical):** absence of distress about the harm thought, ego-syntonic framing, or command-hallucination language → **crisis-path**, NOT containment continuation (maternal psychosis is a medical emergency; ego-dystonic distress e.g. "it scares me" is the REASSURING marker). Test both: ego-dystonic-with-distress → containment; ego-syntonic/no-distress/command-language → crisis. Sage screens+escalates, never adjudicates.
- [ ] **Family split:** first-person ego-dystonic intrusion → containment/referral (harm-intrusive family); third-party or behavioural-indication report → **safeguarding family** (#1 priority, TARGET 2026-07-31; posture = referral-with-urgency + mandatory L2 clinician review, distinct from the suicide-crisis protocol; tier L3-adjacent, clinician-ruled).
- [ ] Build the skeleton once (Falcon-interpretation + rule-based escalation lands here, inherited by every family); harm-intrusive supplies its differentiation question + branches + the referral copy (clinician-owned, no em dashes).

## Task 7: Audit + output_gate
- [ ] Test: Node-8 audit row logs directive `family`, `rule_id`, KB retrieval ids, `flag_level`; audit writes alert-or-fail (#160), never silent.

## Task 8 (Migration): upgrade existing bare-abstain destinations → `contain`
- [ ] Test: harm-intrusive (Stage 1 veto) and OCD-compulsion, post-upgrade, produce the enriched containment turn (not bare Node-3) and still never route to a skill.
- [ ] Change both vetoes' action bare-abstain → `contain(family, kb_topics, skill_id)`. Harm-intrusive is one row; OCD is the second. Clinical-flag families follow one at a time as CMS work on the clinical clock.

## Migration order
Stage 1 harm-intrusive veto (this week) → Stage 2 approval → containment pathway → upgrade harm-intrusive + OCD abstain→contain → clinical-flag families (CMS, clinical clock).

## Relationship to the BOT BEHAVIOUR audit (run in PARALLEL — the audit is the discovery engine)
The postpartum finding was one hand-found instance of a **spec deviation**; the bot-behaviour audit is the systematic version, and it now runs on the **live V2 matcher**. Its "route to professional referral / escalate / guard" prescriptions (OCD/intrusive §229; depressive rumination §228; anger-harm §750; boundary-unsafe-reaction §911/988; "know what to do but can't" §398/401; existential+low-mood §423) are **the family backlog for the containment pathway** — each is a place the current system may route to self-help against the spec. So:
- **Parallel, with a feed:** the audit does NOT block Stage 1 (harm-intrusive ships now). The audit *discovers* the deviation set; the containment pathway is the *general remedy*; each discovered family becomes a CMS `contain` row on the clinical clock.
- The audit ALSO surfaces non-containment conformance gaps (tone/register, safety-woven-in, presentation-one-step-at-a-time §201, cultural-never-assume §1438) — separate work, separately owned.
- **Sequencing:** don't wait for the audit to finish before Stage 1 (the leak is live). Do let the audit's family list define Stage 2's backlog rather than guessing families.

## Self-review
- Urgent leak decoupled to Stage 1 (safety over capability). ✓
- Single psychoeducation source: KB→L4, few-shot→L3, no 7th layer, budget asserted. ✓
- `suggest_skill` suppressed on containment turns (tools ≠ guardrails). ✓
- Bilingual/cultural mandatory + per-language fail-safe. ✓
- Measurement: expanded harm fixtures + re-measure before S1; review-queue write asserted. ✓
- Crisis supremacy + v7 tier vocabulary in Task 0 spec. ✓
