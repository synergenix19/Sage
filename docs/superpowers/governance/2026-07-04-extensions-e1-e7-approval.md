# BOT BEHAVIOUR — Architectural Extensions · Approval Record (E1–E4, E7)

**Status:** DRAFT FOR SIGN-OFF (definitions + overview complete; extension entries drafted one at a time).
**Governance basis:** Absolute Rule 1 (deviations from v7 are flagged and approved, never silent; spec and code merge together).
**Consumes:** the BOT BEHAVIOUR clinician spec (§1–§7 + §C + §HR). **Companion:** `2026-07-04-crisis-hr-protocol-conversion.md`.
**Set size — five extensions, verified across the FULL spec:** E1, E2, E3, E4, E7. Completeness was checked by name against every section — §1a–§7c, §4a, the S-series (S1 sleep, S2 grief ×3, S3 money, S4 self-criticism/compassion/setback ×3, S5 burnout), and §C/§HR (two bounded delta passes, 2026-07-04). Every category maps to an existing skill, a new *content* skill, or one of E1–E4 / E7 / the §4.5 precedence convention — **no category surfaced a sixth mechanism.** Two originally-considered candidates (offload mode, diagnosis-refusal) resolved as content/config (**Appendix A**). Labels kept stable (E7 stays E7) for citation continuity.

---

## 0. Purpose & how to use this document

This is the **citation anchor** for every architectural change required to ingest BOT BEHAVIOUR. Once signed, each implementation PR references the extension entry it advances ("implements E1 per approval record §E1"). **Unsigned entry = not approved = no build.** Entries may be signed independently.

**Scope — what counts as an "extension":** an *architectural delta beyond v7* — a new SageState channel, graph node, `step_policy`/executor action type, safety route, or Skill-schema field. **Out of scope:** new skill JSONs, trigger/lexicon tables, and copy — those are **Cardinal Rule 4 clinician content**, tracked in the content-type→home map `BOT_BEHAVIOUR_CONTENT_INVENTORY.md` (Phase-1 artifact four) and signed separately (conversion doc + CMS). The architecture holds the words; it does not wait for them. This split keeps mechanism approval (here) distinct from content approval (clinical). The demotion of the two former candidates in Appendix A is this test applied honestly.

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
| E4 | Deterministic high-risk route (psychosis/mania/dissociation) | Safety route (extends existing *routing*; new detection surface) | **Yes — recall gate (§f), all 3 trigger classes** | ☐ pending |
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

### E2 — Category / skill-group abstraction

**(a) v7 delta + Cardinal Rule(s) touched.**
v7: 1 skill = 1 routable unit; there is no notion of a *category* — a group of skills forming an offer-first/offer-second ladder with shared screening. The consent-offer mechanism offers ≤2 candidates but holds no persistent "we are in category X, cycle among its tools" concept. E2 adds **three metadata fields to the existing Skill schema** — `pathway_id`, `tier`, `offer_rank` — plus clinician-editable Rules Service routing rules that read them. **No new document type.**

- **Cardinal Rule 2** (clinical logic stays clinician-editable, never code): the category ladder lives in skill metadata + Rules Service rules. A separate "category JSON" is explicitly **rejected** — it would be a second CMS authoring surface and a second thing to version against the skills it references. The one thing it buys (reading a whole category's ladder in one place) is met by a **CMS *view* projecting the ladder from metadata**, not by a new storage type.
- **Cardinal Rule 4** (deterministic detection, never softened): category guards are deterministic contraindications, not LLM discretion.
- **Absolute Rule 1**: schema-field addition = v7 deviation → sign-off.

**Schema additions (existing `Skill` model; all nullable, additive):**
| field | type | role |
|---|---|---|
| `pathway_id` | str\|null | groups skills into a category (e.g. `"anxiety_acute"`); **null = standalone skill = current v7 behaviour** |
| `tier` | `mild`\|`moderate`\|`high`\|null | the tier this skill serves within its pathway (feeds E1's `care_pathway.tier`) |
| `offer_rank` | int\|null | offer-first (`1`) / offer-second (`2`) ordering within a tier; feeds the consent-offer candidate ordering |

**Where category-level guards live (spec §6 "do not present this pathway if…").**
These apply to a *whole category*, not one skill. Mechanism: expressed as skill-level `contraindications` (existing field) **inherited by every skill sharing a `pathway_id`**, evaluated at `skill_select` via Rules Service. Crucially, the **safety-route guards (crisis / medical / HR / IPV) are handled UPSTREAM by §4.5 precedence and never reach this layer** — so category guards cover only the **residual, non-safety conditions**: e.g. "anxiety is more than mild / long-standing → professional referral," "user explicitly asks for a human → don't redirect into the bot flow," "dissociation / panic-with-derealisation → escalate to referral (grounding can intensify)." This split means each guard is authored once — never duplicated across the safety-route and category layers.

**(b) Options considered + recommendation.**
- **Option A — metadata fields + Rules Service routing (RECOMMENDED).** `pathway_id`/`tier`/`offer_rank` on the existing schema; clinician-editable rules read them; the consent-offer renders the ladder. No new artifact.
- **Option B — separate "category JSON" document type.** *One real advantage: a single place to read a whole category's ladder.* Costs: a second authoring surface, a second versioned artifact, and drift risk between category-doc and the skill-docs it references. The advantage is fully served by a CMS view over metadata.
- **Recommendation: Option A.**

**(c) Dependencies.**
- **Depends on E1.** The ladder and step-up/down operate over E1's `care_pathway` (current `tier`, `tried_skills`, `cleared_screens`); without E1's `switch_skill` + state, E2 metadata has nothing to drive transitions.
- Feeds the consent-offer mechanism (candidate ordering by `offer_rank`, filtered by `care_pathway.tried_skills`).
- Bound by §4.5: category guards are strictly downstream of safety-route precedence.

**(d) Test obligations.**
1. **Offer-second only after offer-first check-in** — a tier's `offer_rank=2` skill is not surfaced until the `offer_rank=1` skill's check-in shows no-help / user wants variety.
2. **No re-offer of `tried_skills`** — a skill in `care_pathway.tried_skills` is filtered from candidates (per-pathway-episode scope, per E1).
3. **Cognitive-load cap** — never present all of a tier's tools at once; ≤2 offered (existing `max_offered`), honouring "don't present all 6 at once — cognitive load itself increases anxiety."
4. **Pathway-inherited guard** — a contraindication on the pathway suppresses the *whole category* at `skill_select`, not just one skill.
5. **Residual-only category guards** — a crisis/medical/HR/IPV hit is resolved by §4.5 upstream and never reaches (or double-fires at) the category guard.
6. **Backward-compat** — a skill with `pathway_id=null` routes exactly as v7 (standalone).

**(e) Rollback posture.**
Kill-switch `SAGE_CATEGORY_PATHWAYS` (E2 requires E1, so `SAGE_TIER_SUPERVISOR=off` also renders E2 inert). Default OFF → `pathway_id`/`tier`/`offer_rank` ignored; skills route as standalone v7 units. Fields are additive/nullable, so OFF is byte-identical.

**Sign-off (E2).**
| Role | Name | Date |
|---|---|---|
| Product owner (mechanism: 3 schema fields + Rules Service routing) | ______ | ______ |
| Clinical lead (pathway groupings, offer-rank ladders, residual category guards) | ______ | ______ |

---

### E3 — Medical red-flag guard (cardiac / stroke)

**(a) v7 delta + Cardinal Rule(s) touched.**
v7 `safety_check` detects self-harm/suicide crisis (S1/S3) only; there is no screen for acute medical-emergency descriptors. Anxiety and panic present with chest tightness, racing heart, breathlessness — v7 reads these as anxiety and routes to a breathing/grounding skill. E3 adds a **deterministic medical red-flag recognition layer** (new lexicon category in the safety rules) + a **new route to a brief medical-screen protocol**, firing at Node 1, positioned in §4.5 precedence **below crisis, above HR/IPV/tier**.

- **Cardinal Rule 4** (deterministic detection, never softened; ≥95% recall) — E3 is a safety route; detection is deterministic lexicon (**Rule 5** rules-first), bound to the recall gate (f).
- **Cardinal Rule 2** — the red-flag lexicon and screen copy are clinician-editable Rules Service content, not code constants.
- **Absolute Rule 1** — new safety route → sign-off.

**Detection & the (narrow) calibration boundary.** The clinician spec already draws most of the line:
- **Positive (must fire) — universal red-flag table, §1 "screen rather than assume anxiety":** pressure/heaviness in chest, crushing/stabbing/searing pain, pain spreading to arm/jaw/back, one-sided numbness/weakness.
- **Negative (must NOT fire) — Mild-tier benign phrases:** "my chest feels a little tight," anxious/shallow breathing, racing heart from panic.
The lexicon boundary is therefore **clinician-drawn already**. The only residual calibration decision is where *unlisted, ambiguous* phrasings fall — and the spec's own rule sets the default: **ambiguity screens up.** The clinician owns only the placement of newly-observed ambiguous phrasings, with the default already fixed to screen.

**Action — a screen, not a takeover (why recall is biased).** Unlike crisis, E3 does NOT end the conversation. It routes to a brief medical-screen protocol: acknowledge + one discriminating question ("this could be worth an in-person check — is this the same kind of feeling you've had with anxiety before, or does it feel new/different?"), then: *familiar-anxiety* → clear the screen, continue the pathway; *new / red-flag confirmed* → prompt in-person/emergency evaluation (999/ER). **False positive costs one gentle question; false negative risks a missed cardiac event.** That asymmetry is why recall binds hard while precision is a monitored tolerance (below).

**(b) Options considered + recommendation.**
- **Option A — deterministic lexicon + medical-screen route on the `f3-f4-tipp-clinical-gated` contract (RECOMMENDED).** Reuses the "deterministic contraindication detection" mechanism already in clinical sign-off for TIPP; the screen is entry-screen-style.
- **Option B — semantic/LLM medical classifier.** *One real advantage: catches novel phrasings without lexicon upkeep.* Costs: non-deterministic (breaches Rule 4/5 for a safety route); unbounded recall behaviour; and the BGE-M3 distress/SI-bleed lesson shows embeddings can't be trusted for safety-critical separation. Rejected for detection (may inform monitoring only).
- **Recommendation: Option A.**

**(c) Dependencies + E1 interaction.**
- §4.5 precedence: below crisis, above HR/IPV/tier. A co-firing crisis flag wins the route; E3's flag is still audited.
- **E1 interaction (the coherence point):** a completed screen where the user confirms familiar-anxiety writes `medical_red_flag` to `care_pathway.cleared_screens` → **not re-run within the pathway-episode** (carry-forward). **Conversely, a cleared medical screen is the precondition for offering high-tier TIPP**, whose temperature step (cold-water dive reflex → bradycardia) carries genuine cardiac contraindications. The *same* deterministic-contraindication gate serves both the inbound medical screen and TIPP entry — which is exactly why `f3-f4-tipp-clinical-gated` is the right mechanism template.
- Sequenced before E1/E2 (safety route first).

**(d) Test obligations.**
1. Positive descriptors fire the screen (crushing / spreading / one-sided numbness).
2. Benign Mild-tier chest/breathing phrases do NOT fire.
3. The screen routes to the medical-screen protocol, never a conversation-ending block.
4. Familiar-anxiety confirmation writes `cleared_screens=["medical_red_flag"]`; not re-run within the episode.
5. High-tier TIPP is not offered unless `medical_red_flag` is cleared.
6. Crisis co-fire → crisis wins (§4.5); medical flag still written to audit.
7. Kill-switch OFF → v7 behaviour (no medical screen).

**(e) Rollback posture.**
Kill-switch `SAGE_MEDICAL_REDFLAG` (strict fail-safe parse). Default OFF → byte-identical v7 (anxiety phrases route as today). Note: unlike E1/E2, OFF re-exposes the missed-cardiac risk — so the flag is a rollback lever, and **ON is the intended production state once the gate passes**, not a long-term optional.

**(f) Deterministic recall gate.**
- **Target: ≥95% recall** on the positive fixtures (crisis-recall KPI convention).
- **Positive fixtures:** spec §1 universal red-flag descriptors + the medical-emergency guard phrases recurring across categories (anxiety §6 guard, panic). **Scope broadened by the full-spec review (2026-07-04):** the medical route is a *general acute-medical* screen, not cardiac/stroke only — it also serves **sleep-disorder red-flags (S1b: snoring/gasping/choking)** and **burnout physical-health red-flags (S5a)**. All route to the same "seek in-person evaluation" screen. Fixtures span all three sources. **Per-class recall, not aggregate** (a 95% aggregate that is 100% cardiac / 70% sleep hides the miss that matters): `cardiac_stroke` and `sleep_disorder` gate at ≥95% normally; **`burnout_physical` is NOT-YET-MEASURABLE — the sub-class gate is HELD pending clinical-lead enumeration of the S5a physical symptoms** (the spec names "significant physical health symptoms" but none specifically; n=1, and a ≥95% gate over n=1 is not a measurement). This is the one E3 item that blocks a gate rather than merely informing sign-off.
- **Negative fixtures (REQUIRED):** the Mild/Moderate-tier chest and breathing phrases that must NOT fire ("chest feels a little tight," anxious shallow breathing, panic racing heart). **A recall gate without negative fixtures is trivially satisfied by over-firing** — precision is measured here against a **clinician-set tolerance**, not hard-gated.
- **Arabic fixture debt (explicit open obligation):** the POC gate runs English-first; it is NOT production-satisfied until Khaleeji / MSA / Arabizi equivalents of **both** fixture sets exist (TD3/TD4-adjacent). Recorded so it does not vanish.

**Sign-off (E3).**
| Role | Name | Date |
|---|---|---|
| Product owner (mechanism: lexicon category + medical-screen route + kill-switch) | ______ | ______ |
| Clinical lead (red-flag lexicon boundary + ambiguity-screens-up default + screen copy + ≥95% recall gate incl. Arabic fixtures + precision tolerance) | ______ | ______ |

---

### E4 — Deterministic high-risk route (psychosis / mania / dissociation)

**(a) v7 delta + Cardinal Rule(s) touched.**
The routing *mechanism* exists but is **dormant**: a `psychotic_disclosure` clinical flag → `skill_select` auto-selects `psychotic_referral` (one-step referral). Two limits make this far from complete: **(i)** detection is **keyword-only and psychosis-only** — `clinical_flag_patterns.json` states "keyword-only detection; MARBERT/semantic tier deferred"; triggers are "hearing voices" / "someone is following me"; **no mania, no dissociation**; **(ii)** the layer is **gated OFF** — CF-006 `active: false`; activation is a separate three-part motion (skill sign-off + CF-006 patterns approved + full safety suite green, *together* — per the 2026-06-04 critical-fixes plan). E4 = (1) expand triggers to mania + dissociation (new detection surface), (2) implement the §HR protocol shape, (3) establish a recall gate across all three trigger classes.

- **Cardinal Rule 4** (deterministic detection + recall) + **Rule 5** (rules-first) + **Rule 2** (lexicon + copy clinician-editable) + **Absolute Rule 1**.

**Auditable correction to "extends existing / inherits its gate":** verification found **no existing measured recall gate for psychosis detection to inherit** — `test_psychotic_referral_skill.py` asserts skill behaviour only, there is no psychosis recall fixture, and CF-006 is inactive. Therefore (f) covers **all three trigger classes**; "extends existing" describes the routing object only, never a recall obligation.

**§HR shape — mechanism vs content split (locked protocol).**
- **Mechanism (this entry / `step_policy` structure):** the step order — distress-rating step FIRST → standardized-message step → referral step; the **no-branch lock** (no follow-up that probes the content of the experience); escalate-by-distress as a `step_policy` transition keyed on the distress signal.
- **Content (conversion doc / clinician):** the standardized neutral message wording, the distress-score thresholds (which score → 999 vs "see someone soon"), and the exact trigger phrases.

**(b) Options considered + recommendation.**
- **Option A — deterministic trigger expansion + §HR step restructure (RECOMMENDED).** Expand `clinical_flag_patterns.json` (mania/dissociation); restructure `psychotic_referral` steps to the §HR shape; keyword tier now, MARBERT/semantic as the deferred recall-improvement (mirrors the crisis S1→S2 path).
- **Option B — semantic/LLM HR classifier now.** *One real advantage: catches the naturalistic disclosures keyword misses (Gap #65).* Costs: non-deterministic safety route (Rule 4/5); and because dissociation/mania language overlaps heavily with low-mood/excitement (see negatives), an unvalidated semantic tier would over-fire. Defer semantic to a gated MARBERT step with its own eval, like crisis S2.
- **Recommendation: Option A.**

**(c) Dependencies + precedence.**
- §4.5: E4 (HR) sits below crisis + medical, above IPV + tier.
- **Dissociation → §C precedence (a note, not new machinery):** dissociation phrases ("I lose chunks of time") can co-occur with crisis language; §4.5 already resolves it (crisis > HR). No new mechanism — only the test obligation below.
- **CF-006 activation dependency:** the route goes live only via the three-part gated motion. E4's mechanism can land dormant; activation is separate and gated.
- Independent of E1/E2 (safety route; sequenced before them).

**(d) Test obligations.**
1. Mania triggers fire the HR route; dissociation triggers fire the HR route (new surface).
2. §HR step shape: distress-rating step is FIRST; no content-probing branch exists; standardized message precedes referral.
3. Escalate-by-distress: high distress / danger / mania-risk → crisis framing (999); low → professional-soon.
4. **Dissociation + crisis co-fire → routes to §C (crisis); the HR flag is still written to state + audit** (precedence test).
5. Negative fixtures do NOT fire (see f).
6. CF-006 inactive → route dormant (no HR firing).
7. Kill-switch OFF → v7 behaviour.

**(e) Rollback posture.**
Kill-switch `SAGE_HR_ROUTE` plus the existing CF-006 `active` gate. Default: mechanism lands dormant (CF-006 inactive) → byte-identical v7. Activation is the separate three-part motion, not a flag flip.

**(f) Deterministic recall gate — all three trigger classes (no existing gate to inherit).**
- **Target: ≥95% recall per class** (psychosis, mania, dissociation).
- **Positive fixtures:** spec §HR trigger tables (psychosis / mania / dissociation phrase lists) + the existing psychosis keyword set (currently the only coverage).
- **Negative fixtures (unusually load-bearing — drawn from neighbouring categories, as E3 drew from Mild-tier chest phrases):**
  - *dissociation negatives* — §4a can't-name-the-feeling + §3a low-mood ("I feel numb / flat / empty / disconnected from everything") → route to §4a/§3a, NOT HR. **Available verbatim; dissociation precision gates normally.** (NB "nothing feels real" is a dissociation *positive*, not a negative.)
  - *psychosis & mania negatives* — **fixture authoring 2026-07-04 found these are NOT tabled in the spec** (no social-anxiety/hypervigilance phrasing for psychosis; no ordinary-high-energy phrasing for mania). Recall gates on the positives; **precision for psychosis + mania is not-yet-measurable, held pending clinician authoring of the confusion classes** (engineering will not invent the benign look-alikes). Discriminators recorded in the fixture (self-focused social anxiety vs other-focused paranoia; single energetic day vs sustained+sleepless+grandiose+risk).
  Over-firing HR harms in the *other* direction: routing a mildly-numb depressed user to a "see a professional soon" referral instead of the low-mood pathway is a bad miss. Precision measured against these negatives with clinician-set tolerance.
- **Psychosis baseline is currently UNMEASURED** (keyword-only, no fixture, MARBERT deferred): E4 *establishes* it — not an inherited PASS.
- **Arabic fixture debt (open obligation):** Khaleeji / MSA / Arabizi equivalents of all positive + negative sets required before production-satisfied (TD3/TD4-adjacent), as E3.

**Sign-off (E4).**
| Role | Name | Date |
|---|---|---|
| Product owner (mechanism: trigger expansion + §HR step shape + kill-switch) | ______ | ______ |
| Clinical lead (trigger tables, distress thresholds, standardized message, ≥95% recall per class incl. negatives + Arabic + psychosis baseline) | ______ | ______ |

---

### E7 — Coercive-control / relationship-safety pre-emption

**(a) v7 delta + Cardinal Rule(s) touched.**
v7 already carries: the `domestic_situation` flag (keyword, EN+AR — "hits me", "abusive relationship", "controlling relationship", "won't let me leave", + Arabic), session-immutable, with a safety-first response adaptation and a DFWAC/Ewaa referral. **And the §6 skills already declare the confrontation guard in prose** — `assertive_communication` and `interpersonal_effectiveness` contraindications say "if the other person's response to assertiveness carries a risk of escalation, threat, or control… do not proceed… assess safety," and an L2 "coercive control indicators override the assertiveness training protocol entirely." But that guard is **LLM-discretionary prose** — it relies on the model noticing mid-skill and self-halting (the Contraindication-Firing-Gap class: the RuntimeError gate does not enforce prose contraindications, and there is no behavioural firing test). **E7's mechanism delta = upgrade the consequence from passive/discretionary to a deterministic routing pre-emption:** when `domestic_situation` fires at Node 1, deterministically pre-empt the §6 skills *before* they activate + offer the referral protocol, instead of trusting the LLM to self-halt after entry.

- **Cardinal Rule 4** (deterministic detection + recall — converting discretionary prose to a deterministic route) + **Rule 2** (lexicon + copy clinician-editable) + **Rule 5** (rules-first) + **Absolute Rule 1**.

**Auditability (per E4 discipline):** `domestic_situation` detection has **no existing measured recall gate** (keyword-only, no fixture — verified). So (f) *establishes* the gate, it is not inherited. Unlike psychosis's CF-006, the flag is **live** (not `active:false`); only its consequence is passive today.

**(b) Options considered + the scoped-pre-emption design choice.**
- **Option A — SCOPED pre-emption (RECOMMENDED).** The flag fires globally at Node 1 (per §4.5), but its routing consequence is **targeted**: pre-emption applies only to skills declaring a `coaching_confrontation` contraindication class (the §6a–6d skills — the class *formalizes their existing prose contraindication*), plus the referral-protocol offer. Elsewhere the flag keeps the existing safety-first response adaptation. A user disclosing a controlling partner may still appropriately receive grounding, offloading, or sleep tools.
- **Option B — global block (suppress all skill routing on the flag).** *One real advantage: simplicity — one rule, no per-skill class.* Cost: clinically wrong suppression — it denies a distressed discloser the calming/offloading tools they may most need, **punishing the disclosure**. Rejected.
- **Recommendation: Option A (scoped).**

**(c) Dependencies + content handoff.**
- §4.5: E7 (IPV) sits below crisis/medical/HR, above tier/category.
- **Flag persistence semantics (grounded in `flag_lifecycle_config.json`):** `domestic_situation` is `flag_immutable_within_session: true` — once fired, the §6 pre-emption **persists for the session; the user cannot "un-ring" the disclosure** by changing topic and asking for boundary-scripts two turns later. Clearing is a clinician-review action; `cross_session_persistence:false` means it does not silently carry to the next session, and there is **no automatic within-session decay**.
- **Content-obligation handoff (named so it falls between neither document):** the referral-protocol copy must account for a **controlling partner reading the chat** — discretion in wording, **no persistent on-screen "we detected abuse" framing.** This is conversion-doc / clinical territory, not mechanism, but it is an E7-created obligation and is recorded here.
- Independent of E1/E2 (safety route; sequenced before them).

**(d) Test obligations.**
1. `domestic_situation` fire → §6a–6d (`coaching_confrontation`) skills pre-empted BEFORE activation; referral protocol offered.
2. Non-§6 skills (grounding, offload, sleep) **remain available** under the flag (scoped, not global).
3. Persistence: flag fired turn N → §6 pre-emption still holds at turn N+k within the session (immutable; no un-ring).
4. Negative fixtures do NOT fire (see f).
5. Precedence: crisis/medical/HR co-fire wins (§4.5); IPV flag still written to audit.
6. Kill-switch OFF → v7 behaviour (passive adaptation + LLM-discretionary §6 prose contraindication).

**(e) Rollback posture.**
Kill-switch `SAGE_IPV_PREEMPTION`. Default OFF → `domestic_situation` behaves as v7 (passive safety-first adaptation; §6 skills rely on the prose contraindication as today); no deterministic pre-emption. Note: OFF re-exposes the reliance on LLM self-halt (Contraindication-Firing-Gap), so **ON is the intended state once the gate passes.**

**(f) Deterministic recall gate.**
- **Target: ≥95% recall.**
- **Positive fixtures:** spec §6 IPV / coercive-control guard phrases + the expanded `domestic_situation` table (surveillance/monitoring, financial control, fear-of-reaction) + the existing `domestic_situation` keywords.
- **Negative fixtures (two adjacent zones; the §6 trigger tables are the richest source):**
  - (a) **ordinary relationship conflict** that must route to §6 normally — "my husband and I keep arguing," "my mother-in-law criticizes everything" (precisely the population §6 serves);
  - (b) **non-partner "controlling" language** where workplace/other assertiveness coaching is correct — "my boss is controlling," "he monitors everything I do" at work.
  **Every §6 entry phrase must NOT fire IPV** — over-firing denies §6's own population its coaching.
- **Baseline currently UNMEASURED** — E7 establishes it (not inherited), same finding as psychosis.
- **Arabic fixture debt:** existing `domestic_situation` triggers already include Arabic, but the expanded coercive-control set + negatives need Khaleeji / MSA / Arabizi coverage before production-satisfied (TD3/TD4-adjacent).

**Sign-off (E7).**
| Role | Name | Date |
|---|---|---|
| Product owner (mechanism: `coaching_confrontation` class + deterministic pre-emption + kill-switch) | ______ | ______ |
| Clinical lead (expanded lexicon + scoped-vs-global + referral-copy discretion obligation + ≥95% recall incl. negatives + Arabic) | ______ | ______ |
