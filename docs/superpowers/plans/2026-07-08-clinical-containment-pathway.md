# Clinical Containment Pathway — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement task-by-task. Steps use `- [ ]` checkboxes.
>
> **⚠️ APPROVAL-GATED (Absolute Rule 1).** Task 0 is a BLOCKING architecture-deviation approval. No task ≥1 starts until Task 0's sign-offs are recorded. This plan is the artifact for that approval.

**Goal:** Add a first-class response outcome — *containment* — for clinically-significant, non-crisis disclosures that must NOT get a self-help skill and deserve better than bare clarification (postpartum harm-intrusive as the reference; substance/trauma/eating/domestic/medication as CMS follow-ons).

**Architecture:** One new deterministic state field (`containment_directive`), one new Rules Service action (`contain`), one new conditional graph edge (no new nodes), one new prompt layer (L4 psychoeducation) inside the existing `freeflow_respond` composition, and one reusable containment skill template. Per-family behavior is authored in the CMS (pattern + `contain` action + KB topics), never engineered.

**Tech Stack:** Python/LangGraph graph (`graph.py`), `SageState` TypedDict (`state.py`), Rules Service JSON (`rules/data/`), `freeflow_respond` 6-layer composer, `knowledge_retrieve` pgvector RAG, KB corpus (content-as-code), Supabase audit.

**Reference exemplar:** Abby's postpartum reply (2026-07-08, provided by PO) — validate → normalize/psychoeducate → **differentiate** ("does not mean you want to act on them") → name ("postpartum OCD") → **risk-check** ("noticed these influencing your behavior?") → engage. This is the target quality + the harm-intrusive family's KB/few-shot content.

## Global Constraints (apply to every task)
- **Absolute Rule 1:** this deviates the v7 graph edges + state schema + Rules Service vocabulary. Task 0 sign-off (arch-doc owner + clinical lead + PO) precedes all implementation. Never quiet reinterpretation.
- **Containment destination is `freeflow_respond`, NOT `low_confidence_respond`.** Node 3 is deliberately bare (no L-layer composition, no clinical context). Abby-class output requires the 6-layer composer + L4. The Task-6 bare abstain→Node-3 stays for *generic* low-confidence; containment is a distinct, richer destination.
- **Deterministic trigger only.** The `contain` directive is set by deterministic rules (Node-1 flag patterns / Node-4 vetoes), never by the reranker — the postpartum finding proved the reranker is phrasing-sensitive. Harm-intrusive needs a robust pattern set (like the OCD veto), not a semantic score.
- **KB-content gating (fail-safe).** A family with a `contain` rule but no ready KB article/few-shot MUST fall back to the existing bare abstain (Node 3), never a broken/empty psychoeducation turn. Per-family activation gates on KB readiness.
- **Escalation is human-in-loop.** The differentiation/risk-check probe is autonomous; a positive risk signal routes to `crisis_response` (deterministic); an autonomous "you're fine / no risk" clearance is NOT permitted (constraint from [[project_cssrs_active_screening]]).
- **No em dashes in any rule/skill *content* string** (mirrors into LLM output) — commas ([[feedback_em_dash_rule_content]]).
- **Clinical faithfulness ≠ green pipeline** — every content/differentiation string needs qualified-human sign-off, never eng self-assessment.
- **Reset-per-turn + fully audited** (mirror the `skill_select_abstained` per-turn reset in `_build_state`).

## File Structure
- **Create:** `docs/superpowers/specs/2026-07-08-clinical-containment-pathway-design.md` (Task 0 deviation spec)
- **Modify:** `src/sage_poc/state.py` (state field), `src/sage_poc/server_helpers.py` (`_build_state` reset)
- **Create:** `src/sage_poc/rules/data/safety/harm_intrusive_patterns.json` (deterministic trigger)
- **Modify:** Rules Service schema/loader (add `contain` action), CMS validation
- **Modify:** `src/sage_poc/graph.py` (conditional edge, no new node)
- **Create:** `src/sage_poc/prompts/templates/L4_containment/harm_intrusive.json` (psychoeducation layer + few-shot)
- **Modify:** `freeflow_respond` composer (inject L4 when directive present)
- **Create:** `data/knowledge_corpus/postpartum_intrusive_thoughts.md` (KB article) + a containment-skill template (validate→psychoeducate→differentiate→check)
- **Modify:** `src/sage_poc/audit.py` + `output_gate` (log directive family/rule_id/kb_ids/flag_level)
- **Modify:** `src/sage_poc/nodes/skill_select.py` (OCD veto: `abstain` → `contain`, migration step 2)
- **Test:** graph-routing, rules-parse, composer-L4, audit, containment-skill behavior tests

---

## Task 0 (BLOCKING): Absolute-Rule-1 deviation spec + approval gate
**Files:** Create `docs/superpowers/specs/2026-07-08-clinical-containment-pathway-design.md`; add a section to `docs/SageAI_architecture_current.md` (proposed, unsigned).

- [ ] Write the deviation spec: the 6-point design (state / `contain` action / edge / L4 prompting / escalation template / audit), the destination-≠-Node-3 clarification, the KB-gating fail-safe, the escalation human-in-loop constraint, and the migration order. Attach Abby's exemplar as the harm-intrusive content target.
- [ ] Record the three required sign-offs in the spec: (1) **arch-doc owner** — the graph/state/vocabulary amendment; (2) **clinical lead** — approve *containment as a destination class* (the pattern), plus the harm-intrusive differentiation questions + escalation branches + KB article; (3) **PO** — Absolute Rule 1 acceptance. Each subsequent family is a CMS clinical decision, not a re-approval of the pattern.
- [ ] **STOP.** Do not proceed to Task 1 until all three sign-offs are in the spec. Green tests prove flow, not clinical correctness.

---

## Task 1: State — `containment_directive`
**Interfaces — Produces:** `containment_directive: Optional[dict]` = `{family, flag_level, kb_topics, containment_skill_id?, rule_id}`. Set only by deterministic rules; reset `None` each turn by `_build_state`; carried to `output_gate` for audit.

- [ ] **Test first:** `_build_state` returns `containment_directive: None` every turn (per-turn reset, like `path`/`skill_select_abstained`).
- [ ] Declare `containment_directive` in `SageState` (beside the clinical-flags component, as its response-side counterpart).
- [ ] Add `"containment_directive": None` to `_build_state`. Run; confirm reset + no cross-turn leak.

## Task 2: Rules Service — the `contain` action
**Interfaces — Produces:** rule action `contain(family, flag_level, kb_topics, skill_id?)` → sets `containment_directive`. Fourth action alongside route/veto/abstain/flag; authorable in the CMS via the same draft→review→approve→publish flow.

- [ ] **Test first:** a fixture rule with a `contain` action, when its pattern matches, yields `containment_directive` populated + `rule_id` set; a non-matching turn leaves it `None`.
- [ ] Add `contain` to the action schema + loader; CMS validation rejects a `contain` rule whose `kb_topics` reference no existing KB article (KB-gating at authoring time) and enforces the first-person-pronoun / char-cap rules ([[project_cms_semantic_description_validation]]).
- [ ] Reconcile with existing `clinical_flag` + `skill_select_disposition:"abstain"`: `contain` **supersedes** bare `abstain` for families that have a directive; families without a `contain` rule keep today's behavior. Document the precedence.

## Task 3: Harm-intrusive deterministic trigger (reference family)
**Files:** `rules/data/safety/harm_intrusive_patterns.json` (+ a Node-1 flag rule or a Node-4 veto-style hook, mirroring `ocd_compulsion`).

- [ ] **Test first (behavioural, both directions):** natural postpartum harm-intrusive phrasings (incl. the "can't make them stop, scares me" phrasing that routed iatrogenically, AND the "can't shake" phrasing) → directive set, family=`harm_intrusive`; ordinary parenting worry → NOT triggered (a false-positive containment that suppresses a real worry skill is a defined failure).
- [ ] Author the pattern set (clinician-owned content) robust to phrasing (deterministic, not reranker). Wire it to set `containment_directive` with `kb_topics=[postpartum_intrusive_thoughts]`, `containment_skill_id` once Task 7 exists.

## Task 4: Graph — one conditional edge (no new node)
**Interfaces:** wherever a rule sets `containment_directive`, routing goes → `knowledge_retrieve` (seeded with `kb_topics`) → `freeflow_respond` (L4-enriched) if no containment skill, else → `skill_executor` (guided containment skill). Trigger = "directive present", generalized (not "postpartum matched").

- [ ] **Test first:** a state with `containment_directive` set routes to `knowledge_retrieve` (then `freeflow_respond`), NOT `skill_select`/`freeflow` bare/`low_confidence`; directive absent → unchanged routing (byte-identical). Directive + `containment_skill_id` present → `skill_executor`.
- [ ] Add the conditional-edge branch (checked with the same priority as crisis/veto safety routes, before the generic abstain/freeflow fallbacks). `knowledge_retrieve` accepts `kb_topics` from the directive (not only `info_request`).

## Task 5: L4 containment prompt layer (composer enrichment)
**Files:** `freeflow_respond` composer; `prompts/templates/L4_containment/harm_intrusive.json`.

- [ ] **Test first:** when `containment_directive` is present, `compose_prompt` includes the L4 layer (family psychoeducation + the containment few-shot) on top of L0–L2; absent → composition byte-identical to today.
- [ ] Add the L4 layer to the 6-layer composition (freeflow_respond only; Node 3 untouched). Few-shot exemplar = Abby-structured (validate/normalize/differentiate/name/risk-check/engage), authored per family.

## Task 6: Harm-intrusive KB content + few-shot (the quality ceiling)
**Files:** `data/knowledge_corpus/postpartum_intrusive_thoughts.md`; the L4 few-shot from Task 5.

- [ ] Author the KB article (clinician-owned) modeled on Abby's reply: normality of intrusive thoughts in new parents, the ego-dystonic differentiation, "postpartum OCD" naming, when-to-seek-help. Deploy-time auto-sync per [[project_kb_corpus_autosync]]; recalibrate abstain/threshold if the corpus crosses the gate.
- [ ] Verify KB-gating fail-safe: with the article present → containment fires; simulate article-missing → directive falls back to bare Node-3 abstain (no empty turn).

## Task 7: Containment skill template (validate → psychoeducate → differentiate → check)
**Files:** a reusable skill skeleton; harm-intrusive instance (differentiation question + escalation branches = per-family clinical content).

- [ ] **Test first:** the differentiation step's risk-positive branch (e.g. disclosed intent/behavioral influence) routes to `crisis_response` (deterministic); the risk-negative branch continues containment; NO autonomous "no risk" clearance path exists ([[project_cssrs_active_screening]] constraint).
- [ ] Build the skeleton once; the Falcon-interpretation + rule-based escalation branch lands in the template so every future family inherits it. Harm-intrusive supplies the specific differentiation question ("have you noticed these thoughts influencing your behavior?") + branches.

## Task 8: Audit + output_gate
- [ ] **Test first:** `output_gate` (Node 8) audit row for a containment turn records `containment_directive` family, `rule_id`, KB retrieval ids, flag level — every containment turn traceable to the exact clinician-authored rule (strengthens the PDPL right-to-object story: named versioned rule, not model discretion).
- [ ] Add the fields to `_write_session_audit_row`. Alert-or-fail per the standing audit-integrity convention (issue #160) — never a silent swallow.

## Task 9 (Migration step 2): OCD-compulsion veto → `contain`
- [ ] **Test first:** an OCD compulsion, post-upgrade, produces the enriched containment turn (not bare Node-3 abstain) and still never routes to a self-help skill (the veto family already exists; only the action changes `abstain`→`contain` + an OCD KB article + differentiation).
- [ ] Change the veto's action from bare abstain to `contain(family=ocd_compulsion, kb_topics=[ocd], skill_id=containment)`. Byte-identical guard: flag-off / no-directive paths unchanged.

---

## Migration order
1. **harm-intrusive** — reference implementation (clinically urgent; Abby exemplar in hand). Ships behind the KB-gating fail-safe.
2. **OCD-compulsion veto upgrade** — family exists, action changes abstain→contain + OCD KB/differentiation.
3. **clinical-flag families** (substance, trauma, eating, domestic, medication) — evaluated one at a time by the clinical team as **CMS work** on their clock. No graph change per family, ever.

## Clinician packet (added item)
Approve **the pattern** (containment as a destination class) — not just the postpartum instance — with the note that each subsequent family is a CMS decision on the clinical clock, not an engineering project.

## Self-review
- **Spec coverage:** all 6 design points → Tasks 1–8; migration → 1/2/9. ✓
- **Destination correctness:** containment→freeflow_respond (L4), not Node 3. ✓
- **Trigger robustness:** deterministic patterns, not the phrasing-sensitive reranker. ✓
- **Fail-safe:** KB-missing → bare abstain, never empty. ✓
- **Safety:** escalation human-in-loop; no autonomous clearance. ✓
- **Type consistency:** `containment_directive` shape identical across state/rules/graph/audit. ✓
