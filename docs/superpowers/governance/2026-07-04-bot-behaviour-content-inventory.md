# BOT BEHAVIOUR — Content-Type → Architectural-Home Map (Content Inventory)

**Status:** DRAFT (§1 filled; §2–§4 one review turn each, Phase-2 discipline).
**Companions:** `2026-07-04-extensions-e1-e7-approval.md` (mechanism — this doc is its named content destination) · `2026-07-04-crisis-hr-protocol-conversion.md` (§C/§HR content + safety lexicons).

## §0 — Purpose & scope

This inventory **proves every clinician content-*type* in the spec has a tunable, clinician-editable architectural home**, and **flags the reconcile cases** where spec copy would modify already-signed behaviour. It is deliberately **type-level with per-category coverage accounting — not a block-level transcription** of the spec's ~170 content blocks. That reframe is the point: the architecture holds the words, and content population is the ordinary iterative tune lane (the spec's own copy is "illustrative, not exhaustive — tune against real usage data"). This doc exists so nothing falls *between* documents; it does not pull content authoring onto the critical path.

Out of scope of the E1–E7 approval record (mechanism); this is the destination its §0 scope note names.

## §1 — Content-type → home map

Every content type in the spec maps one-to-one onto a v7 ownership surface. "Clinician-editable (CR2)" = tunable without an engineering change (Cardinal Rule 2), made auditable per type.

| Content type | Architectural home (v7) | Clinician-editable (CR2) | Present vs to-add | Reconcile-risk | Notes |
|---|---|---|---|---|---|
| **Validating / framing statements** | skill JSON `steps[]` — first-step `goal` / `tone` / `examples` | **Yes** | Home present + populated (existing skills open with validation); spec's **tier-specific** statements are add/reconcile | **Yes** — tier-specific vs current generic openers | "validate before inform" is also enforced globally by L0 (row 5) |
| **Preliminary / screening questions** | skill JSON `steps[]` — screening steps + `completion_criteria` | **Yes** | Home present; per-category question sets add where a new flow | Low–Med — condensed vs full sets differ per tier | one-question-per-turn is an L0 rule (row 5), not per-skill copy |
| **Psychoeducation scripts** | psychoed_* skill `steps[]` **and** `info_request` → RAG (KB corpus) | **Yes** (skill JSON + CMS-managed corpus) | psychoed_anxiety/depression/stress present; §HR / grief / emotions / assertiveness psychoed **to-add** | Low — additive | Two homes: in-flow step vs selectable menu → RAG. Pick per delivery shape (§2 records which) |
| **Check-in + guided-technique copy** | skill JSON `steps[]` + `step_policy` (check-in step + advancement rules) | **Yes** | Home present; per-tier check-in copy to-add | **Yes** — the check-in **format** change (1–10 → three-button *Better/Same/Worse*) is more than copy | The signal (`emotional_intensity`) exists; the **structured-UI affordance is a deferrable enhancement** (§4), degrades to text today |
| **Cross-cutting tone / constraint rules** | **L0 persona / output_gate rules** — NOT per-skill `steps[]` | **Yes**, but L0 is a signed artifact → edits are **re-sign-gated** | **Mixed:** "no unbidden diagnostic label," "concise / plain," "validate before advice" **present** in L0; §C "no categorical confidentiality claims" only partially present (L0 PRIVACY clause) → **to-add** in crisis copy | **High** — an L0 change is an L0 re-sign (same authority as the helpline payload) | A global rule mis-homed in per-skill tone would be re-authored ~30× and drift — these live **once** in L0/output_gate. Present-vs-add is called per rule (§2/§3) |
| **Trigger words / phrases** | Rules Service lexicons — Node-4 skill-matching (`target_presentations`, `keyword_matcher`) | **Yes** | category-matching tables add/tune per category | Low | **⚠ GOVERNANCE SPLIT:** the **safety-route** lexicons (crisis / medical / HR / IPV — `crisis_keywords`, medical red-flag, psychosis/mania/dissociation, `domestic_situation`) are governed by the **conversion doc + recall-gated fixtures** and tracked **there**, NOT here. **Only the non-safety category-matching trigger tables (Node-4 skill selection) are homed through this inventory** — so the same lexicon never appears under two authorities |

**Read of §1:** every type has a clinician-editable home on an existing v7 structure; none requires one of the five extensions to *hold* content (E1/E2 change how skills are *sequenced*, not where their copy lives). The two rows carrying real risk are **check-in format** (an enhancement, not copy) and **cross-cutting rules** (L0 re-sign-gated) — both surfaced in the reconcile register (§3).

## §2 — Per-category coverage checklist

**Legend.** Content types carried: **V** validating/framing · **P** preliminary Qs · **E** psychoeducation · **C** check-in · **T** category trigger words · **X** invokes a cross-cutting rule (§1 row 5). Disposition: **present** (populated existing home) · **add** (new content/skill) · **reconcile** (adjusts signed-off copy → §3). Destinations: `skill_id` **✓** = verified present in `src/sage_poc/skills/*.json`; `KB:<id>` = verified KB article; **NEW:** = not in inventory (→ §4); **UNVERIFIED** = claimed but not confirmable. Safety routes (crisis/medical/HR/IPV) are governed elsewhere (conversion doc + recall gates) — noted, not owned here.

| Category | Destination(s) [verified] | Types | Disposition | Note |
|---|---|---|---|---|
| §1a–1c Anxiety (mild/mod/high) | box_breathing✓, grounding_5_4_3_2_1✓, stop_technique✓, progressive_muscle_relaxation✓, mindfulness_body_scan✓, dbt_tipp✓ | V P E C | **reconcile** | tier-specific validating/flow via E1/E2; existing skill copy is generic — reconcile per tier |
| §1d Worry loops/rumination | **NEW:** Worry Tree, worry_time✓, problem_solving_therapy✓ | V P E C | add + present | Worry Tree new (§4) |
| §1e Anticipatory anxiety | box_breathing✓ → **NEW:** Worry Tree → problem_solving_therapy✓ | V P E C | add + present | composite sequence (E2) |
| §1f Understanding anxiety | **KB:anxiety-001/002/003**, psychoed_anxiety✓ | E (+menu) | present | **skill-vs-KB decision: menu → KB via knowledge_retrieve**; psychoed_anxiety for in-flow |
| §2a Practical decision | problem_solving_therapy✓ | V P E C | present | ⚠ inventory doc lists SK-028 `problem_solving` as *proposed*, but `problem_solving_therapy.json` exists — doc stale |
| §2b Values guidance | values_clarification✓ | V P E C | reconcile | spec "Life Compass" domain-menu structure vs current — reconcile |
| §3a Low mood/withdrawal | behavioral_activation✓, grief_loss✓ (grief branch) | V P E C (+safety) | reconcile | safety-question-woven + grief-softening branch |
| §3b Worthlessness/self-criticism | **NEW:** Fact vs Opinion (or cognitive_restructuring✓), self_compassion_break✓ | V P E C (+safety) | add + present | "better off without me" = mandatory crisis trigger |
| §3c Understanding depression | **KB:depression-001/002/003**, psychoed_depression✓ | E (+menu) | present | KB menu; safety-check when personally framed |
| §3d Just needs to offload | freeflow/L2 (no skill) | X | present + add | offload intent label + suppression rule = Appendix-A content |
| §4a Can't name the feeling | **NEW:** Emotions Wheel, mood_check_in✓ | V P E C | add + present | dissociation-vs-alexithymia trigger → E4 |
| §4b Understanding emotions | **NEW psychoed** (no emotions KB article exists) | E (+menu) | add | inventory has no `emotions-00x` — new KB article or psychoed skill |
| §4c Wanting to tune in/process | mindfulness_body_scan✓ (+E5 hold-space) | V P E C | present | dissociation → grounding_5_4_3_2_1✓ |
| §5a Quick lift | behavioral_activation✓ (micro variant), safe_place_visualization✓ | V P E C | reconcile | micro-action variant of BA |
| §5b Build positives | **NEW:** Wins-Log, cognitive_restructuring✓ | V P E C | add + present | between-session follow-up |
| §6a Saying no/people-pleasing | assertive_communication✓, interpersonal_effectiveness✓ | V P E C | reconcile | coercive-control pre-empt = E7 (coaching_confrontation class) |
| §6b Boundary setting | interpersonal_effectiveness✓ (DEARMAN), assertive_communication✓ | V P E C | present | reuses §6a E7 guard |
| §6c Rehearse/draft message | **NEW:** Draft/Role-Play, assertive_communication✓ | V P E C | add + present | reuses §6a guard |
| §6d Understanding assertiveness | **KB:assertiveness-001**, **NEW psychoed** | E (+menu) | present + add | KB menu present |
| §7a Wants company/being heard | freeflow/E5 (no skill) | V X | present | hold-space; loneliness-severity check |
| §7b Isolation/withdrawal | behavioral_activation✓ | V P E C | present | reroute to §3a/§6b = E1/E2 |
| §7c How do I connect | **KB:relationships-001**, **NEW psychoed** | E (+menu) | present + add | hand-off to §6c = E1 |
| S1a Mind racing at night | box_breathing✓, progressive_muscle_relaxation✓, safe_place_visualization✓, worry_time✓ | V P E C | present | near-nightly → CBT-I flag (E1) |
| S1b Sleep disruption | sleep_hygiene✓, **KB:sleep-001** | V P E C | present | sleep-disorder red-flags (snoring/gasping/choking) → E3 |
| S2a Fresh/raw grief | grief_loss✓ (presence mode) | V (no-skill) | reconcile | presence mode; traumatic/suicide-loss guard content |
| S2b Coping with loss | grief_loss✓ (continuing bonds) | V P E C | present | Islamic-practices content already in grief_loss |
| S2c Understanding grief | grief_loss✓ psychoed, **KB:grief-001** | E (+menu) | present | KB menu |
| S3a Acute money worries | box_breathing✓, financial_anxiety✓, problem_solving_therapy✓, worry_time✓ | V P E C | present | coercive-financial → E7; material-crisis guard content |
| S4a Harsh self-criticism | self_compassion_break✓, act_psychological_flexibility✓, **NEW:** Kind Self-Talk | V P E C | present + add | escalate → §3b (E1) |
| S4b Rejecting self-compassion | self_compassion_break✓, **NEW:** Myths vs Facts | V P E C | present + add | trauma/weaponized-kindness guard content |
| S4c After a setback/failure | self_compassion_break✓, cognitive_restructuring✓, **NEW:** Handling Setbacks | V P E C | present + add | hopelessness → crisis route |
| S5a Chronic stress & burnout | progressive_muscle_relaxation✓, behavioral_activation✓, problem_solving_therapy✓, assertive_communication✓/interpersonal_effectiveness✓, psychoed_stress✓, **KB:coping-002** | V P E C | present | burnout physical red-flags → E3; workplace-harassment scope-limit |
| **C — Crisis** | `crisis_response` node (not a skill), post_crisis_check_in✓, **KB:crisis-001..004** | protocol | present | **safety route — governed by conversion doc + GL-0 gate**, not here |
| **HR — High risk** | psychotic_referral✓ (+E4) | protocol | reconcile | **safety route — E4 + conversion doc**; §HR shape change |

**Cardinality both ways.** Many categories resolve to multiple items (recorded above); and several items serve multiple categories — e.g. `box_breathing` (§1a-c, §1e, S1a, S3a), `grounding_5_4_3_2_1` (§1a-c, §4c), `self_compassion_break` (§3b, S4a/b/c), `problem_solving_therapy` (§1d/e, §2a, S3a, S5a). No item is single-use; the ladder/pathway reuse (E2) is what makes that safe.

**Orphan signal (cheap reverse check, not a full audit).** Inventory skills the spec's 35 categories do **not** appear to reference: **`mi_readiness_ruler`** (SK-009, motivational-interviewing readiness) — no readiness/ambivalence category in the spec; and **`cbt_thought_record`** (SK-001) is only indirectly implicated (§3b routes to Fact-vs-Opinion / `cognitive_restructuring`, not the full thought record). Worth a clinician glance — a spec that silently drops an implemented skill is itself a finding. (Reverse KB-article orphans, e.g. `therapy-001`, `trauma-001`, `wellbeing-001`, not enumerated here.)

**Inventory-doc staleness (finding).** `docs/SageAI_Skills_Knowledge_Base.md` lists 24 skills (SK-001–024) + 4 proposed, but `skills/*.json` has **27** — it omits `psychotic_referral`, `act_psychological_flexibility`, and `problem_solving_therapy` (the last listed as *proposed* SK-028 while its JSON ships). The inventory doc needs a refresh; destinations above are verified against the JSON dir (ground truth), not the doc.

## §3 — Reconcile register

The subset from §2 where spec copy **adjusts already-signed behaviour**. Each names its **re-sign path — one of three**: **CMS** (clinical CMS content re-approval) · **L0** (L0/output_gate re-sign, same authority as the helpline payload) · **RECORD** (approval-record amendment, because it touches an extension-governed artifact). Split rows name both.

| Item | What it adjusts | Re-sign path | Note |
|---|---|---|---|
| §1a–1c tier-specific validating statements | replace the generic openers in the acute-anxiety skills | **CMS** | tiering *mechanism* is E1/E2 (already in the record); only the copy reconciles |
| §2b Life Compass domain menu | restructures `values_clarification` step content | **CMS** | domain-menu is skill-internal content |
| §3a safety-question woven into preliminary | inserts a direct safety question into `behavioral_activation` intake | **CMS** (clinical) | safety-relevant placement — clinician-owned |
| §5a micro-action BA variant | lower-bar variant of `behavioral_activation` | **CMS** | |
| §6a coercive-control pre-empt | **SPLIT:** `coaching_confrontation` class + pre-emption behaviour = **RECORD (E7)**; referral wording = **CMS** | RECORD + CMS | mechanism vs copy |
| S2a grief presence-mode | reframes `grief_loss` opening (companionship, not "fixing") | **CMS** | |
| HR §HR protocol shape | **SPLIT:** distress-rating-first step + escalate-by-distress = **RECORD (E4)**; standardized message wording = **CMS** (conversion doc) | RECORD + CMS | mechanism vs copy |
| §C behavioral guardrails (to-add) | adds "no categorical confidentiality claims" to crisis copy / persona | **L0** | cross-cutting rule (§1 row 5); not per-skill tone |
| Check-in format (1–10 → three-button) | structured-response affordance, not copy | **RECORD/deferred** (§4 enhancement) | frontend + API; degrades to text today |

## §4 — New content-skills, deferred enhancements & tracked fixes

New skills each carry an **`evidence_base`** obligation — schema-mandatory, so "new skill" can never mean "unsourced skill." The inventory may *suggest* a citation candidate; it is marked **proposed** — the clinical lead sources/confirms. **POC-priority** reads each item against the ingestion plan's phases (Phase C = anxiety family) so the backlog isn't undifferentiated.

**New skills:**
| Skill | Serves | POC-priority | evidence_base (proposed — clinician confirms) |
|---|---|---|---|
| Worry Tree | §1d, §1e | **POC** (anxiety family / Phase C) | Butler & Hope (1995); GAD worry-tree literature — *proposed* |
| Fact vs Opinion | §3b | POC-candidate (may fold into `cognitive_restructuring`✓) | Beck (1979); Burns (1980) — *proposed* |
| Emotions Wheel | §4a | post-POC | Plutchik (1980); Feldman Barrett (2017) — *proposed* |
| Wins-Log | §5b | post-POC | Fava well-being therapy; positive-psychology — *proposed* |
| Draft/Role-Play | §6c | post-POC | assertiveness rehearsal literature — *proposed* |
| Kind Self-Talk | S4a | post-POC | Neff (2011); Gilbert CFT — *proposed* |
| Myths vs Facts (self-compassion) | S4b | post-POC | Neff (2011) self-compassion myths — *proposed* |
| Handling Setbacks | S4c | post-POC | growth-mindset / CFT — *proposed* |
| Life Compass domains | §2b | post-POC (or reconcile into `values_clarification`✓ — see §3) | Hayes ACT (1999) — *proposed* |

**New psychoed content:** §4b Understanding Emotions (no `emotions-00x` KB article — new article/skill, post-POC); §6d Understanding Assertiveness (`KB:assertiveness-001` present; extend, post-POC); §7c How Do I Connect (`KB:relationships-001` present; extend, post-POC).

**Deferred UX enhancements:** structured-UI check-in (three-button *Better/Same/Worse*) and selectable topic menus — both degrade to text via the offer/intent pattern today; post-POC, frontend + API.

**Tracked governance fix (onward routing):** refresh `docs/SageAI_Skills_Knowledge_Base.md` from 24 → **27 skills** (add `psychotic_referral`, `act_psychological_flexibility`, `problem_solving_therapy`; correct SK-028 status). It is the project protocol's cited reference inventory, so its drift from `skills/*.json` is a **governance defect**, not cosmetic. Priority: **now** (cheap). *(The orphan signal — `mi_readiness_ruler` / `cbt_thought_record` unreferenced by the spec — is routed to the clinical lead via PR #114, being a deliberate-omission-vs-oversight question only they can answer.)*

---
*Inventory complete — §0–§4. Proves every content type has a tunable clinician-editable home (§1), accounts for all 35 categories against verified destinations (§2), isolates the signed-behaviour-touching subset with re-sign routes (§3), and tracks the new-content backlog against the plan with sourcing obligations (§4). Content population remains the iterative lane; this document is its map, not its transcript.*
