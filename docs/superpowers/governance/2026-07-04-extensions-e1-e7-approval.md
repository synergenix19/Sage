# BOT BEHAVIOUR — Architectural Extensions · Approval Record (E1–E4, E7)

**Status:** DRAFT FOR SIGN-OFF (definitions + overview complete; extension entries drafted one at a time).
**Governance basis:** Absolute Rule 1 (deviations from v7 are flagged and approved, never silent; spec and code merge together).
**Consumes:** the BOT BEHAVIOUR clinician spec (§1–§7 + §C + §HR). **Companion:** `2026-07-04-crisis-hr-protocol-conversion.md`.
**Set size:** the §4–7 delta reduced the mechanism set from seven candidates to **five** — E1, E2, E3, E4, E7. The two dropped candidates (offload mode, diagnosis-refusal) were assessed and resolved as content/config; see **Appendix A**. Labels are kept stable (E7 stays E7) for citation continuity.

---

## 0. Purpose & how to use this document

This is the **citation anchor** for every architectural change required to ingest BOT BEHAVIOUR. Once signed, each implementation PR references the extension entry it advances ("implements E1 per approval record §E1"). **Unsigned entry = not approved = no build.** Entries may be signed independently.

**Scope — what counts as an "extension":** an *architectural delta beyond v7* — a new SageState channel, graph node, `step_policy`/executor action type, safety route, or Skill-schema field. **Out of scope:** new skill JSONs, trigger/lexicon tables, and copy — those are **Cardinal Rule 4 clinician content**, signed separately (conversion doc + CMS). This split keeps mechanism approval (here) distinct from content approval (clinical). The demotion of the two former candidates in Appendix A is this test applied honestly.

---

## 1. E7 — definition (stated first; the signer meets it here, not as a line item)

**E7 — Coercive-control / relationship-safety routing pre-emption.** *Surfaced by:* §6a (Saying No / People-Pleasing), §6b (Boundary Setting), §6c (Rehearse/Draft a Message), §6d (Understanding Assertiveness) — categories that coach a user to assert, set boundaries, or confront another person.

**This is NOT a new recognition layer.** v7 already detects `domestic_situation` at Node 1 (`clinical_flag_patterns.json`: abuse/assault/violence/"hits me"/"abusive relationship"/"controlling relationship"/"controls everything"/"physically abused"/"being beaten"), carries a coercive-control framework (`sensitive_topic_suppression_lexicon.json`: HITS/WAST, phone/finances/isolation/movement control), a safety-first response adaptation, and referral resources (Dubai Foundation for Women & Children, Ewaa Shelters) in `clinical_flag_adaptations.json`. E7 is therefore **(a)** expand the `domestic_situation` phrase table (coercive control, surveillance/monitoring, financial control, fear-of-a-partner's-reaction) and **(b)** upgrade its *consequence* from passive L2 response-framing + clinician-review to **active routing pre-emption**: when the flag fires, block the §6 assertiveness skills *before they activate* and route to a relationship-safety referral protocol.

*Why it is a mechanism extension despite the detector existing:* the passive-flag → routing-override upgrade is a new precedence-gated route out of Node 1 (executor/routing change), not content. *Why E1–E4/§C don't cover it:* E3 screens medical emergencies, E4 psychosis/mania/dissociation, §C self-harm/suicide — **none screen danger originating from another person**, and coaching boundary-setting to someone with a controlling partner can escalate real-world danger.

---

## 2. Overview — the extension set at a glance

| # | Name | Type | New safety route? | Status |
|---|---|---|---|---|
| E1 | Cross-skill severity-tier supervisor (+ `care_pathway` state) | State channel + executor action (`switch_skill`) | No | ☐ pending |
| E2 | Category / skill-group abstraction | Skill-schema field + routing | No | ☐ pending |
| E3 | Medical red-flag guard (cardiac/stroke) | Safety route | **Yes — recall gate (§f)** | ☐ pending |
| E4 | Deterministic high-risk route (psychosis/mania/dissociation) | Safety route (extends existing) | Extends E-existing | ☐ pending |
| E7 | Coercive-control / relationship-safety pre-emption | Safety route (elevates `domestic_situation` flag) | **Yes — recall gate (§f)** | ☐ pending |

Precedence across these routes is a binding convention, not an extension — see **§4.5**. Two candidates resolved as content/config — see **Appendix A**.

---

## 3. Entry schema — every extension section carries exactly these fields

- **(a) v7 delta + Cardinal Rule(s) touched** — what changes vs v7, and the rule engaged (Rule 3 LLM-renders-only; Rule 4 deterministic safety detection + ≥95% recall; Rule 5 rules-first; Absolute Rule 1 governs approval).
- **(b) Options considered + recommendation** — alternatives stated honestly (each option's one real advantage named), with the recommendation and why.
- **(c) Dependencies** — on other extensions / shared substrate (e.g. tier transitions depend on E1's `care_pathway` counters for carry-forward of cleared screens).
- **(d) Test obligations** — tests that must exist before merge.
- **(e) Rollback posture** — kill-switch + prod-safe default.
- **(f) [E3 and E7 only] Deterministic recall gate** — numeric target **≥95%** + named fixture source, defined *before* implementation. Per Cardinal Rule 4, a new safety route without a measured recall bar is a deviation in spirit even when deterministic.

---

## 4. Cross-cutting conventions (bind all entries)

1. **Safety routes inherit the ≥95% deterministic recall bar** (E3, E7).
2. **Kill-switch default = prod-safe.** Every extension ships behind a flag defaulting OFF / byte-identical, mirroring `SAGE_CRISIS_TIERING`'s strict fail-safe parse.
3. **Dependency ordering is safety-first:** §C/§HR + E4 → E3, E7 → E1 → E2; E5/E6-class content is independent.
4. **Mechanism ≠ content.** Approving an extension does not approve the clinician content that rides it.
5. **Deterministic Node-1 route precedence (BINDING; ratify at sign-off).** With crisis (§C), medical (E3), high-risk (E4), and IPV (E7) all producing deterministic routes out of Node 1 — and tier/category classification beneath them — one message can fire multiple tables ("my chest is crushing and I don't want to be here anymore"). Evaluation order is fixed: **crisis > medical > HR > IPV > tier/category.** On multi-hit, the highest-precedence route wins the turn; **all fired flags are still written to SageState and the audit trail — never dropped.** This generalises v7's existing structural precedence (`safety_check → crisis_response` runs before `intent_route`) and the rules engine's first-match-by-ascending-priority. The *ordering itself* is a clinical decision to ratify here. Resource co-surfacing (e.g. 999 serves both crisis-immediate-danger and a cardiac emergency) is a content concern, not a routing one.

---

## 5. Dependency graph

```
§C/§HR conversion ──┐
E4 (HR route) ──────┼──> E3 (medical guard) ──┐
                    │                          ├──> E1 (supervisor + care_pathway state) ──> E2 (category grouping)
                    └──> E7 (IPV pre-emption) ─┘
Node-1 route precedence (§4.5, binding):  crisis > medical > HR > IPV > tier/category
```
E1's `care_pathway` state (tier, cleared-screens, tried-tools counters) is the shared substrate E2 builds on and the home of the former check-in-signal counters (Appendix A).

---

## 6. Sign-off

Complete when all five entries are signed.

| Role | Name | Date |
|---|---|---|
| Product owner (mechanism + §4.5 precedence order) | ______________ | ______ |
| Clinical lead (safety routes E3/E4/E7 recall gates + precedence order) | ______________ | ______ |

---

## Appendix A — Assessed, resolved as content/config (NOT mechanism extensions)

Held to §0's scope test, two former candidates are v7-covered and demoted:

- **Offload / supportive-listening mode (§3d "just needs to offload").** Already in v7: `skill_select` no-match → freeflow path + `L2_intents/new_skill_unmatched.json` + `general_chat_advicefirst.json` (acute-distress "Do NOT offer guidance yet", one-question gate) + composer `intensity_guidance` already deliver validation-first, no-tool responses. Needs at most an intent-taxonomy label + a skill-suggestion-suppression rule — **Rules Service / content**, not mechanism.
- **Diagnosis-refusal + check-in signal.** Diagnosis-refusal covered twice: L0 persona HARD LIMITS ("do not diagnose or prescribe") + `scope_refusal` intent (`intent_route.py:34`). The check-in-signal half (1–10 / three-button) now lives inside **E1's `care_pathway`** counters. Nothing mechanism-level remains.

---

## Extension entries

*Drafted one per review turn, Phase-2 discipline.*

### E1 — Cross-skill severity-tier supervisor + `care_pathway` state

**(a) v7 delta + Cardinal Rule(s) touched.**
v7 advances/holds/completes/exits *within a single skill only* — `skill_executor.py:733` sets `active_skill_id` to the same skill or `None`; the only cross-skill jump is `exit_to_crisis_protocol`. There is no mechanism to move a mid-conversation user from one skill to a *different* skill (e.g. Mild→Box Breathing stepping up to High→TIPP) while carrying context. E1 adds two mechanism pieces: (1) a checkpoint-persisted `care_pathway` SageState channel (schema below); (2) a `switch_skill` executor action that atomically sets `active_skill_id` to a different skill, resets `active_step_id` to that skill's entry step, and preserves `care_pathway` (cleared screens not re-run). A deterministic supervisor evaluates tier transitions on check-in results and emits `switch_skill`.

- **Cardinal Rule 2** (clinical logic stays clinician-editable, never a code constant — cf. S15 Tier-1 priority): **the supervisor decides *which skill*, never *which step*.** Step sequencing stays in `step_policy` JSON; tier-transition thresholds (step-up at 2 no-improvement, tier→skill mapping) live in clinician-editable Rules Service / JSON, **not Python.** Stated explicitly to preempt the most likely drift — tier logic absorbing step logic into engineering-owned code.
- **Cardinal Rule 5** (rules-first): tier classification and transition triggers are deterministic (self-report / `emotional_intensity` / `keyword_matcher`), never LLM-decided.
- **Cardinal Rule 3** (LLM renders language only): the LLM renders the transition copy; it never decides the transition.
- **Absolute Rule 1**: v7 deviation → this sign-off.

**`care_pathway` state schema** (checkpoint-persisted):
| field | type | role |
|---|---|---|
| `category` | str | active BOT BEHAVIOUR category (e.g. `"anxiety"`) |
| `tier` | `mild`\|`moderate`\|`high`\|`null` | current severity tier |
| `cleared_screens` | list[str] | e.g. `["medical_red_flag"]`; **carried forward, never re-run on step-up** |
| `tried_skills` | list[str] | skills already offered/run in this pathway (no re-offer). **Scope: per pathway-episode (this activation), NOT per session/user** — a user who benefited from Box Breathing this morning must not find it suppressed tonight; the longer horizon is the therapeutic profile's `effective_techniques`. |
| `consecutive_no_improvement` | int | increments on a check-in showing no improvement at the current tier; **step-up trigger at 2** (spec §C). **Resets to 0 on (a) any improvement check-in and (b) any tier transition** — a stale Mild count must never fire a step-up at Moderate. |
| `ceiling_reached` | bool | set when the highest tier's skill completed AND a check-in still shows no-improvement/worsening → offer human/professional support; do NOT cycle lower tiers or repeat (spec §E) |

(This channel is also the home of the check-in-signal counters demoted from former E6 — Appendix A.)

**(b) Options considered + recommendation.**
- **Option A — `switch_skill` supervisor over discrete skills (RECOMMENDED).** Each tier's tool stays an independent, separately-authorable/testable skill JSON; the supervisor emits `switch_skill` on transition. Reuses consent-offer + `step_policy` unchanged; mirrors the live `crisis_tier` precedent; clean implementation seam at `skill_executor.py:733`.
- **Option B — mega-skill with internal tier-branches in `step_policy`.** *One real advantage: no new executor action type* — transitions expressed as `next_step_id` within one skill. Costs: bloats `step_policy` past the ~50–100-rule comfort zone; collapses discrete tools into one giant JSON; error-prone CMS editing; and directly entangles tier logic with step logic, breaching the Cardinal Rule 2 boundary above.
- **Recommendation: Option A.** `switch_skill` is a small, auditable executor addition; the tier-branch alternative saves exactly one action type at the cost of the clinical-editability and modularity the architecture depends on.

**(c) Dependencies.**
- Sequenced AFTER §C/§HR conversion + E4 + E3/E7 — the safety routes must exist first, so anxiety §F ("silently divert to crisis protocol") and the medical/IPV pre-emptions are testable before tiering rides on top.
- Feeds E2 (category grouping builds on `care_pathway`) and the tier carry-forward of cleared screens.
- Bound by §4.5 precedence: `switch_skill` NEVER overrides a higher-precedence route — crisis/medical/HR/IPV win over any tier transition.

**(d) Test obligations.**
1. **Step-up is automatic + skips re-screening** — on a worsening / no-improvement check-in (or "isn't working"), the supervisor emits `switch_skill` to the next tier's offer-first skill WITHOUT re-running that tier's preliminary questions; a `cleared_screens` entry (e.g. medical red-flag already cleared) is not repeated.
2. **Step-down is OFFERED and requires user assent — never automatic.** On improvement the supervisor offers the lower-tier tool as an option and does not switch until the user assents. **This asymmetry test is as important as the step-up test** (spec §D: recovering users must not feel pushed into more tasks).
3. **`consecutive_no_improvement == 2` fires a step-up** (spec §C).
4. **Ceiling** — highest-tier skill completed + no improvement → `ceiling_reached=True` → human-support offer; supervisor does NOT cycle to lower tiers or repeat the top skill (spec §E). Distinct from the crisis guard.
5. **Precedence preemption** — at every tier/step, a fired crisis/medical/HR/IPV flag routes out per §4.5; `switch_skill` never suppresses it (spec §F universal override).
6. **`switch_skill` invariant** — sets `active_skill_id` to the target skill (not `None`, not same), resets `active_step_id` to the target's entry, preserves `care_pathway` across the checkpoint; regression-guards `skill_executor.py:733`.
7. **`care_pathway` persists** across turns via the LangGraph checkpoint.

**(e) Rollback posture.**
Kill-switch `SAGE_TIER_SUPERVISOR` (strict fail-safe parse like `SAGE_CRISIS_TIERING`: only a literal `false`/`true` toggles; garbage → signed default). **Default OFF → byte-identical v7**: no `switch_skill`, no `care_pathway` transitions, skills behave as single units. Instant revert, no redeploy.

**Sign-off (E1).**
| Role | Name | Date |
|---|---|---|
| Product owner (mechanism: `switch_skill` action + `care_pathway` channel) | ______ | ______ |
| Clinical lead (tier-transition thresholds, step-up/down asymmetry, ceiling→human-support) | ______ | ______ |

---

- E2 — pending
- E3 — pending
- E4 — pending
- E7 — pending
