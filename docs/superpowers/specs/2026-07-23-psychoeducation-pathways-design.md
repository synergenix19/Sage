# Psychoeducation Pathways — Design (Approach B: deterministic serve + LLM continuation)

**Date:** 2026-07-23 · **Status:** DESIGN APPROVED section-by-section in brainstorm session; awaiting written-spec review
**Source of truth:** BOT BEHAVIOUR clinician doc — all table-derived content cites `bot_behaviour_full.md` (NOT the stripped `.txt`; 2026-07-17 source-integrity rule)
**Companions:** `../governance/2026-07-04-bot-behaviour-content-inventory.md` · `../plans/2026-07-04-bot-behaviour-ingestion-plan.md` · `../governance/2026-07-23-psychoed-consult-golive-verification.md` (Mechanism-A record, PR#362)

---

## 0. Baseline at time of writing, and relationship to Mechanism-A

On 2026-07-23 (same day as this design), `SAGE_INFO_REQUEST_CONSULT=true` went live (Vee B1, PR#362): psychoed-shaped info requests route to four existing skills ({psychoed_anxiety, psychoed_depression, assertive_communication, grief_loss}) via `skill_match_method=info_request_skill_consult`. Matrix moved 8→11/36 (§1f/S2c/§6d 5/5, §3c 4/5, §4a/§7c OUT-by-design).

**Mechanism-A is routing-level conformance. This design is the doc-complete capability.** None of the doc's psychoed substance exists in prod: no ratified block library (40 blocks), no menu-first/answer-first delivery shapes, no personally-framed safety weave, no PSY-WEAVE-1, no verbatim serving, no diagnosis-guard split. Matrix-green ≠ doc-complete (green proves it flows, not that it is correct/complete).

**Migration rule (binding):** the Node-4 psychoed resolver (this design) supersedes Mechanism-A consult routing **per category, at each category's flag flip** — the two mechanisms must never both claim the same utterance class. Until a category flips, Mechanism-A behavior stands for it. On flip, the consult-set entry for that category is retired in the same change (the consult set lives in `info_request_consult_set.py`, per the go-live record — that file is where retirement happens). §4a remains Mechanism-B territory (out of this design's scope); §7c moves from "matching gap" to this design's answer-first KB category (ruled amendment, §9).

**Live-exposure note (filed with the P0, §9):** S2c conforming-live means grief traffic is actively invited today, while the reunification-ideation phenotype has ZERO Node-1 coverage (verified 2026-07-23: `crisis_keywords.json`, `passive_si_patterns.json`, `crisis_phrases.json` — EN and AR) and Mechanism-A carries no safety weave. Node 1 screens every turn as normal, but the compounded exposure raises the P0's urgency.

---

## 1. Scope and shape of the capability

One clinical capability, one content library, two delivery surfaces:

- **Surface 1 — Understanding-X pathways** (§1f, §3c, §4b, §6d, §7c, S2c): served from the KB corpus through the existing `info_request → skill_select early-return → knowledge_retrieve → freeflow_respond → output_gate` path. No new graph node, no new edge.
- **Surface 2 — in-flow step-3 psychoed** (1a–1e, 2a, 2b, 3a, …): stays inside `skill_executor` steps. Each skill's 1–3 sentence script is distinct signed copy (skills-framing text, clinician-authored separately from the topic explainers — verified against the doc: not abridgements) carrying a `kb_ref` to its Understanding-X article family. Tier modulation (full/short/one-line-folded) and skip-on-repeat parameterize the existing `skip_psychoeducation` step-policy action.

The doc's cross-wiring makes the two surfaces one capability: in-flow tiers terminate into the dedicated pathways ("Psychoeducation | Info | Give options from 1f"), the pathways bridge back into skills, and the guards are shared. The cross-surface relationship is a **pointer (`kb_ref`), never a copy**.

The one-line per-skill psychoed strings in the doc's Skills tables (e.g. Box Breathing's "simple 4-count breathing pattern…") are Surface-2 skill-presentation copy, **out of this capability's scope** — fixtures must not read them as missing blocks.

---

## 2. Architecture placement & data flow

### 2.1 The psychoed category resolver — Node 4 (`skill_select`)

The resolver lives in Node 4, the node v7 designates for deterministic phrase matching (Rules Service: "keyword patterns mapping phrases to pathways", rules-first). It runs the §0 trigger match **on the raw turn, regardless of `primary_intent`** — deterministic recognition is never conditional on the probabilistic router (placing it downstream of intent_route would make the trigger tables' reachability conditional on an LLM classification: the §5-drift class one node upstream).

Order of evaluation inside Node 4:

1. **PSY-WEAVE-1 precedence** — on weave-pending turns, PSY-WEAVE-1 (§6.1) evaluates BEFORE any resolver matching. A reply of "actually, what is anxiety?" to the safety question is a deflection, not a serve.
2. **Active-skill suppression stands.** Mid-skill "go deeper" questions do NOT route through the resolver; in-skill psychoed access is the step's `kb_ref` offer plus the bound `knowledge_lookup` tool. Fixtures treat this as correct behavior, not a miss.
3. **§0 trigger match** against the ingested trigger tables (normalized phrase match, Tier-1 matcher pattern; Arabic orthographic normalization via `rewriter.py` when AR tables land). Longest-match selects the more specific row WITHIN a category (specificity proxy only, never a safety arbiter); cross-category ties are collisions (§5.2).
4. **On category hit → Classifier A, the acute-distress precedence rule** (§5.3): crisis/HR/medical remain upstream and untouched by topology; if deterministic acute-distress signals are present, psychoeducation is the wrong tool — route to the coping category with the psychoed offer deferred to check-in. Otherwise **the trigger hit wins even when `primary_intent` read emotional_support** — the `psychoed_serve` payload (category, delivery shape, block ID(s), template version) is resolved here and routed to `knowledge_retrieve`.
5. No hit → existing behavior unchanged (info_request early-return, post-crisis auto-select, two-tier matching).

`knowledge_retrieve` fetches blocks by ID; `freeflow_respond` composes the deterministic turn-1 emission (no LLM call); `output_gate` audits (§6.2). Same node count, same edges — the v7 §4.3-sanctioned class ("a query routing decision inside the node, not a graph structure change").

### 2.2 Outcome 2 — semantic backstop (category-scoped)

When the trigger tables miss but RAG retrieves a psychoed-flagged article above the abstain threshold, the fallback **resolves the category from the block's article-family metadata — never serves a bare block** — and runs the identical Classifier A + Classifier B checks as outcome 1, with the **fail-to-personal default**. This is where classification certainty is lowest; no emission path skips the classifiers. Legacy articles are quarantined from this path (§3.4).

### 2.3 Precedence (unchanged, fixture-asserted)

Universal overrides sit upstream and are untouched. Psychoed is the lowest-precedence pathway in the graph — nothing in the serve branch can pre-empt a safety route, by topology rather than by rule.

---

## 3. Content model & ingestion

### 3.1 Content unit: one KB article per block, atomic

Each block is stored whole, `atomic: true` — never chunked (v7 §5.3 "crisis content NEVER chunked" precedent) — and served whole by ID. Embeddings exist only for the outcome-2 backstop; deterministic serving never touches similarity scoring.

Block metadata: `block_id`, `psychoed_category` (1f|3c|4b|6d|7c|s2c), `article_family`, `delivery_shape` (menu_first|answer_first), `verbatim: true`, `language`, `menu_label`, optional `block_guard` (per-block conditional guard annotation — e.g. S2c "how long does grief last" → prolonged-grief support note, no diagnosis naming).

### 3.2 Pathway manifests (clinician-editable data; phrases in data, runner in code)

Per category: framing statement, menu-offer script, check-in/close script, ordered block list, `delivery_shape`, `safety_weave` (per-category weave-scope field — §3c and S2c set at minimum; clinician owns it), guard references, and the **bridge map** (doc's block→skill offers: §1f maintenance-cycle→worry_tree, fight/flight→box_breathing; §4b responding-vs-reacting→route-to-1a; §7c specific-person→hand-off-to-6c). Bridges are optional-not-automatic (fixture F5).

### 3.3 Trigger tables

Versioned data files, same governance class as the lexicons; they feed the Node-4 resolver AND the fixtures from one source (measurement-parity). **Source: `bot_behaviour_full.md`** — every §0 trigger table is a Word table stripped from the `.txt` extraction; each ingested artifact's manifest entry carries its source citation. Row schema carries the doc-native `type` column → drives Classifier B (`framing: personal|abstract`) and the diagnosis-guard row split (`direct_diagnostic` vs `formal_diagnosis`, §5.4).

### 3.4 Ingestion map (by name — full-coverage rule)

| Section | Shape | Blocks |
|---|---|---|
| §1f Understanding Anxiety | menu-first | 5 — what is anxiety; fight/flight/freeze; why physical symptoms; maintenance cycle; what is worry |
| §3c Understanding Depression | answer-first + weave | 7 — bio-psycho-social; snap-out-of-it; motivation/energy; numb/empty (anhedonia); sadness vs. depression; no-reason; seeking help |
| §4b Understanding Emotions | answer-first | 7 — why emotions; what emotions signal; intensity differences; getting triggered; body-before-thought; responding vs. reacting; shutting down |
| §6d Understanding Assertiveness | answer-first | 6 — what is assertiveness; four styles; why patterns develop; building the skill; boundaries; culture |
| §7c How Do I Connect | answer-first (how-to) | 7 — starting conversations; friends as adult; deepening; maintaining; awkwardness; belonging; family |
| S2c Understanding Grief | answer-first | 8 — what is grief; waves; stages; right way; physical/cognitive symptoms; guilt; anger; how long |

Total **40 blocks + 6 framing + 6 menu-offer + 6 check-in scripts**, plus Surface-2 step-3 scripts (signed clinical fields, gaining `kb_ref`).

**Legacy quarantine:** `anxiety-001/002/003`, `depression-001/002/003`, `grief-001` are NOT reused as psychoed blocks — marked non-psychoed, general RAG corpus only, so the serve path only ever emits doc-ratified copy (fixtured: F9). Overlap reconciliation is content cleanup, not a blocker.

### 3.5 Shared single-sourced scripts (#321 class)

Diagnosis-guard script (defined §1f, reused verbatim §3c), personally-framed safety weave, human-referral close: **one constants module** (the `CRISIS_RESOURCES` pattern), referenced by templates, plus a CI single-source check that these strings appear nowhere else in served copy.

### 3.6 Copy transformation, then ratify the artifact

Em-dash→comma conversion at ingestion (served copy mirrors into output; standing rule). The scrubbed copy **becomes the signable artifact**: the packet carries the doc→artifact diff; the verbatim pin (character-for-character, source-drift-guard CI) anchors on the signed artifact, not the raw docx. The §6d culture block informs cultural_overrides/TD6 alignment but shares no strings (different surface).

### 3.7 Arabic

One AR pair per block (40) + scripts (18), each gated on faithfulness grading before serve (cbt-001-ar lesson: nothing ships ungraded). AR trigger tables, AR weave data: Lane-3. **Hard dependency, named:** the entire AR measurement track is blocked on clinical naming a native-Khaleeji clinically-credentialed validator — no named validator, no AR corpus, no AR psychoed artifacts, and the AR fixture families queue behind the same unnamed validator. **Validator naming is the first domino; the AR flag's clock does not start until it falls.** (Also listed in the packet's asks, §9.)

---

## 4. Delivery orchestration & the declared state channel

### 4.1 Turn-1 composition (deterministic, no LLM call)

- **Menu-first (§1f):** framing + menu-offer script.
- **Answer-first, abstract framing:** framing + matched block + menu-offer script.
- **Answer-first, personal framing with `safety_weave`:** framing + matched block + **weave question — full stop. The menu offer is deferred to the following turn, contingent on a clear-negative response** (doc §3c order: framing → answer → safety check → menu; "meet the actual question first"). The weave fires on the same turn as the FIRST personally-framed block, never deferred behind the menu loop — no multi-topic tour with a perpetually pending check.
- **Guard-script path (formal diagnosis-seeking):** the two-stage diagnosis script; weave-checked identically — no emission path skips Classifier B.

Every composition is a versioned serve template; `template_version` goes to audit.

### 4.2 The declared psychoed state channel (#319: declared in state schema, `check_state_channels.py` CI, graph test)

- **Per-turn (reset every turn):** `psychoed_serve` payload.
- **Pathway-scoped (persist while active):** `psychoed_active_category`, `psychoed_delivery_shape`, `psychoed_blocks_served`, `psychoed_menu_offered`, `psychoed_weave_fired`, `psychoed_weave_pending`, `psychoed_matched_row_id`, `psychoed_collision_path`, `psychoed_framing`.

Pathway-scoped keys clear on exit (new skill activation, safety-route firing, explicit close) — audit-feeding facts persist to `session_audit` BEFORE clearing. Never-disarm: nothing in this channel is readable by upstream safety nodes; one-way dependency by construction.

**Recorded decision — weave-pending session expiry:** pending state does not survive session exit. Rationale: Node 1 screens every turn universally; a stale pending flag crisis-routing a next-day "good morning" is the worse failure. (Deviations register, §10.)

### 4.3 Turns 2+

- **Menu selection:** resolver fires every turn with **context-scoped matching first** (active category's `menu_label` set before global tables). A menu pick is an outcome-1 hit: same serve path, same audit.
- **Loop-back:** re-offers composed from `psychoed_blocks_served` — served topics marked, never re-assumed.
- **Check-in glue:** the only LLM-mediated turns (`L2_psychoed_continuation` template), reads blocks-served + bridge map; bridge offers optional-not-automatic.
- **"Something going on right now" branch:** not special-cased — next turn re-enters Node 4; Classifier A and normal precedence apply.
- **Exits:** safety route (universal override, pathway abandoned), user requests/matches a skill, or explicit close.

### 4.4 Cross-surface carry-forward ("do not re-run psychoeducation from scratch")

At serve time, increment per-article-family `prior_exposure` in the therapeutic profile; the existing step-policy rule 6 (`prior_exposure ≥ threshold → skip_psychoeducation`) performs the skip — no new condition type, no read-before-clear ordering dependency (the channel-clearing timing bug the naive design had). `psychoed_blocks_served` stays for loop-back and audit only.

**Dependency, declared not wired:** within-session increment + rule-6 skip works today and alone eliminates the ordering bug. The cross-session behavior the doc implies ("recognized pattern → skip straight to skill offering on future occurrences") is a declared dependency on the profile-persistence repair (layer VERIFIED non-functional end-to-end 2026-07-10; DEFECT/SCOPE/GUARDRAIL, PRs #290/#291, do-NOT-wire guardrail respected).

---

## 5. Routing detail & the deterministic classifiers

### 5.1 Resolver matching mechanics

Normalized phrase match (case/punctuation/whitespace; AR orthographic normalization) over the §0 tables. Longest-match within category only. Row `type` column → framing classification and guard-row routing.

### 5.2 Collision policy — deterministic, declared, CI-enforced

At ingestion, CI computes the full cross-category collision set (exact + subsumption); any collision without a declared resolution entry fails CI. Resolutions live in a clinician-visible collision table (data), using ONLY: (a) **declared session context** (deterministic state signals — grief disclosure in active issues, recent S2-family pathway → S2c); (b) **a scripted clarifying question** (ratified copy) when no context signal exists and guard postures differ. **Never embedding-similarity tie-break.** Known instance: "Why do I feel numb?" (§3c vs S2c) → §3c absent grief context.

**Kept verbatim in the record:** the collision is safe before it is disambiguated — both phrasings are personally framed, both categories carry the weave, and the fail-to-personal default means the safety check fires on either branch. This is the property that makes the collision mechanism acceptable at this risk tier.

### 5.3 Classifier A — acute-distress precedence

Deterministic inputs only, all data-declared: existing safety-route state (post-crisis/HR/medical flags — upstream, already decided) + a distress-marker lexicon (present-tense physiological/panic phrasings) + **structural signals** (message fragmentation thresholds, numeric self-report intensity e.g. "9/10" — the doc's Routing §A tier-recognition signals; S2c's "in the middle of something right now" is often carried structurally, not by panic vocabulary). Fail direction: **on ambiguity, treat as acute** (doc: "when signals conflict, default to the higher tier"). Outcome when acute: coping category, psychoed offer deferred to check-in.

### 5.4 Classifier B — personal-vs-abstract framing (safety-rule governance)

Outcome-1: free and deterministic — matched row's `type` maps to `framing: personal|abstract`. Outcome-2: **fail-to-personal, always.** Weave scope: per-category manifest `safety_weave` field. Weave script: #321 constant.

**Governance (binding):** Classifier B is CALLED at Node 4 (skill-matching call site) but GOVERNED as a safety rule — its output decides whether a safety check fires. Its data (row framing mappings, fail-to-personal default, weave-scope field) takes safety-rule review rigor: clinical sign-off on changes, not the lighter skill-matching edit path. A trigger-table edit must not be able to silently reclassify a personal row as abstract under content-edit governance.

### 5.5 Diagnosis-guard row split (the doc routes these two ways)

- `direct_diagnostic` rows ("I think I might be depressed", "Is this depression or just stress?") → **normal answer-first flow** with the disclaimer-carrying framing (§3c builds the can't-diagnose disclosure into its framing statement).
- `formal_diagnosis` rows ("do I have GAD/depression/panic disorder") → **two-stage guard script** (initial + push-further), category-agnostic, single-sourced.
- Guard-script yes-branch ("Want me to walk through that?" → consent): serve the relevant concept block through the same audited path.
- Personally-framed diagnosis-seeking is high-risk phrasing: weave ordering applies to guard-script emissions exactly as to block emissions.

### 5.6 Classifier outcomes recorded in state

Matched row ID, resolved category, collision path, framing result, weave fired/pending — all in the declared channel, feeding the Node-8 audit row and the fixtures.

### 5.7 Node-1 dependency (verified 2026-07-23, not assumed)

The reunification-ideation phenotype ("want to be with him/her/the person who died", "join them") is ABSENT from all Node-1 surfaces, EN and AR: `crisis_keywords.json` (nearest: "better off dead"), `passive_si_patterns.json` (wish-dead/relieved-dead/burdensomeness/purposelessness phenotypes present; no reunification), S3 `crisis_phrases.json`. **Filed as a standalone P0 Node-1 safety item on the safety queue's own clock** (VG-class lexicon addition, C-SSRS/INQ anchoring, FP verification, Lane-3 sign-off) — this design doc is NOT the item's home. Secondary consequence here: **S2c serve stays flag-gated OFF until it lands** (and see §0: S2c is Mechanism-A-live today, which raises the P0's urgency, not this design's).

---

## 6. Safety integration & Node-8 transit

### 6.1 PSY-WEAVE-1 — the weave-response rule (highest-stakes rule in this design)

Deterministic, evaluated at Node 4 AFTER Node 1 runs normally on the reply, and BEFORE any resolver matching (§2.1 step 1).

**Definition:** `psychoed_weave_pending` set + reply not a clear negative → crisis protocol.

**Matching semantics (false-crisis cost addressed, fail-closed preserved):**
- Replies pass through the resolver's normalization before evaluation.
- The allowlist holds **normalized negative patterns**, not exact strings — "no, nothing like that", "no, alhamdulillah", "no I haven't, why?" are clear negatives and must pass.
- **Hard contradiction guard:** if the reply contains ANY affirmative or ambiguity marker (signed marker list), it fails closed regardless of a leading negative — "no, but sometimes…" can never pass.
- Everything else — "kind of", "sometimes", "not really but…", deflection/topic-change — fails closed to crisis, implementing the doc's "any indication of yes" as a stricter-than-lexicon standard.

`psychoed_weave_pending` is one-shot (cleared on evaluation; distinct from `psychoed_weave_fired`); a later personally-framed category with `safety_weave` re-arms it. Never-disarm preserved: Node 1 never reads psychoed state — a downstream node routing TOWARD safety on a fail-closed default is the permitted direction.

**Governance:** allowlist patterns, contradiction markers, weave-scope field, framing mappings — all safety-rule review rigor. **Deflection→crisis is a design-added extension** (the doc's branch is binary yes/no); it is presented BY NAME in the sign-off packet for explicit clinical ratification, never carried silently in data (Absolute Rule 1). Softening the deflection branch is a clinician edit to signed data, not an engineering call.

### 6.2 What output_gate asserts on psychoed turns (Rider 1 realized)

- **Audit persistence:** one migration adds psychoed columns to `session_audit` (block IDs, matched row ID, collision path, framing, weave fired/pending-evaluated, template version) — one-row-per-turn model unchanged.
- **Verbatim integrity, behavior-anchored:** hash-compare of the emitted block segment against the pinned signed artifact for the claimed `block_id` (assertion on behavior, not prose markers). By-construction serving is the belt; the emit-time hash is the suspenders.
- **Defined failure action:** on hash mismatch, output_gate BLOCKS the emission and re-serves directly from the pinned signed artifact (pinned copy = ground truth by definition); logs an integrity incident with both hashes; flags for engineering review. If artifact fetch fails: neutral referral template. **Never emit unverified copy on this path.** (Mirrors the crisis-emission shape.)
- **Single-source (#321):** no `mandatory_caveat` duplication; the diagnosis disclaimer exists only in the framing/guard-script fields the gate reads.
- **No new gate authority:** existing crisis-precedence and safety checks run unchanged; no bypass.

### 6.3 Universal override mid-pathway

Crisis/HR/medical firing at any point — mid-menu, weave-pending, anywhere — abandons the pathway by topology (upstream nodes never see psychoed state). Sequence: audit-feeding facts persist, then pathway-scoped keys clear. Fixtures assert override + non-leak (no psychoed copy fragments in the crisis emission; #359 pattern).

### 6.4 CI surface (existing check classes, extended)

Trigger-table collision audit · single-source check on shared scripts · source-drift guard vs. signed artifacts (sourced from `bot_behaviour_full.md`) · `check_state_channels.py` for the new channel · signed-fields pinning over manifests, blocks, collision table, and PSY-WEAVE-1 data.

---

## 7. Measurement & rollout

### 7.1 Fixture inventory (stable IDs; flip preconditions reference these)

| ID | Family | Gate |
|---|---|---|
| **F1** | Recognition — TWO sets per the fixture-independence rule (now BINDING on every detection route: `docs/ARCHITECTURE_BOUNDARIES.md`, "detection recall … independent of the detector's pattern source", PR#361): wiring fixtures from the trigger tables (verify data read; NEVER quoted as recall) + **independently-authored naturalistic paraphrases** (the only set recall claims may cite). Precision negatives from neighboring categories (§3c vs 3a, §7c vs 7a/7b, §1f vs 1a–1e). | tracked baseline, clinician-set bar |
| **F2** | Collision — every declared resolution path (grief-context→S2c, absent→§3c, scripted-clarify). | green required |
| **F3** | Classifiers — A: lexicon + structural signals, ambiguity→acute, **including mixed-pull turns** ("what is anxiety? I can't breathe right now" — recognition and precedence pulling opposite directions); B: row-type mapping, outcome-2 fail-to-personal. | green required |
| **F4** | PSY-WEAVE-1 — clear-no incl. natural phrasings, clear-yes, ambiguous, deflection, contradiction-guard ("no, but…"), weave-pending precedence (trigger-phrase reply → crisis, not serve). Authored per language: the EN set gates EN flips; the AR set gates the AR flag. | **100% hard gate** |
| **F5** | Multi-turn flow — menu loop-back with served-topic marking, both check-in branches, bridges present-but-not-auto-launched, weave turn-boundary (menu deferred), within-session carry-forward skip, **per-block guard contrast** (S2c how-long block carries the prolonged-grief note; sibling blocks do not). | green required (Rider 3 flip precondition) |
| **F6** | Safety precedence — crisis/HR override mid-menu + non-leak; mid-skill suppression asserted as correct. | **100% hard gate** |
| **F7** | Integrity — hash-compare pass + BOTH failure branches (re-serve; fetch-fail → neutral referral). | green required |
| **F8** | Both-direction regression — **bare-emotional-words property re-pinned against the resolver directly** ("I'm stressed"/"I feel depressed" must not trigger-match; the 2026-05-27 verification does not transfer to the new surface unmeasured); existing matrix rows asserted unmoved. | **100% hard gate** |
| **F9** | Semantic backstop — category-from-metadata (never bare block) + correct weave; **legacy-quarantine negative** (query landing nearest anxiety-001/depression-001 → normal RAG, never psychoed serve). | green required |
| **F10** | Diagnosis-guard split — direct_diagnostic→answer-first w/ disclaimer framing; formal_diagnosis→two-stage script incl. push-further; consented yes-branch→audited block serve. | green required |

**Cross-cutting:** the runner asserts the **expected `session_audit` row per fixture** (block IDs, row ID, collision path, framing, weave state, template version) — Rider 1 as a measured property, not a schema check.

**Gate rationale:** psychoed is the lowest-precedence pathway; a recognition miss degrades to today's RAG/freeflow behavior, not harm — importing the 95% safety bar into F1 would be false rigor. F4/F6/F8 are safety properties: 100%.

### 7.2 Harness

The one fixture-driven runner (GL-0/E3/E4/E7 machinery) extended with F1–F10 — full-graph execution, flag-parity enforced mechanically (runner derives flags from config, reads `/health/version` serving readback, refuses on mismatch/deploy-window — PR#360 discipline).

### 7.3 Flags & flip order

`SAGE_PSYCHOED_PATHWAYS` master (default-OFF) + per-category enablement:

- Per-category flip preconditions: signed artifacts (blocks, manifests, collision table, weave data) · F2–F10 green full-graph at prod parity, F1 wiring set green + naturalistic baseline meeting the clinician-set bar (EN sets for EN flips; AR sets gate the AR flag) · audit columns live · state-channel CI green · clinician packet signed · **Mechanism-A consult-set entry retired in the same change (§0 migration rule)**.
- **S2c:** additionally gated on the reunification-ideation lexicon landing (its own P0 clock).
- **AR:** separate flag. Preconditions: **all fixture families F1–F10 green in AR** (not graded-artifacts-plus-EN-measurement), faithfulness grading of all 58 AR artifacts, AR trigger tables, AR weave data — and upstream of all of it, **the named-validator dependency (§3.7): the AR clock does not start until clinical names the validator.** Never quote EN-only results as system conformance.

### 7.4 Rollback & latency

Flag-off reverts every turn to current behavior; no data unwinding; audit columns and profile increments inert when OFF. Turn-1 psychoed is a no-LLM deterministic serve — near-instant on a path with p50 ~17s; measure at flip, not a design goal.

---

## 8. Work breakdown

- **Phase 1 — Content & data (no code, starts immediately):** extraction from `bot_behaviour_full.md` → blocks, manifests, trigger tables; collision audit; scrub; packet assembly → **Lane-3 clinician clock starts here** (packet is schedule-critical).
- **Phase 2 — Mechanism (flag-OFF, parallel with sign-off loop):** Node-4 resolver + classifiers; state channel + CI; serve composition; Node-8 audit migration + hash gate w/ failure path; PSY-WEAVE-1; step-policy carry-forward parameter. TDD.
- **Phase 3 — Measurement:** F1–F10 (naturalistic sets authored independently of tables), harness extension with audit-row assertions, full-graph runs at prod parity.
- **Phase 4 — Staged flip:** EN categories minus S2c → staging soak → per-category prod flip on packet signature (retiring Mechanism-A consult entries per category); S2c on P0 lexicon landing; AR on all-families-AR-green.

Lane mapping: reunification P0 = Lane 1 (safety queue, own clock). Psychoed build = BOT BEHAVIOUR ingestion stream. Lane-3 items: packet, collision-table ratification, PSY-WEAVE-1 data, AR validator naming → AR grading → AR tables.

---

## 9. Governance records

**Ruled amendment — §7c:** moves from skill_select target to answer-first KB category (inventory correction, consistent with the doc's "same shape as the other psychoeducation categories"). Supersedes the sibling-pathways provisional match (interpersonal_effectiveness, flagged least-bad) — **routed past clinical for ratification, not silently dissolved**. Bridge target (specific person/message → 6c) is in the bridge map. Aligns with the Mechanism-A record's "§7c=matching-gap→clinician-packet" disposition. **§4a stays open on the clinical queue untouched** (space-holding category; Mechanism-B territory; not psychoed).

**Standalone P0 filing — reunification-ideation phenotype:** filed to the safety queue with the 2026-07-23 verification evidence (§5.7) **plus the live-exposure note (§0): S2c is Mechanism-A-live today with no weave, actively inviting grief traffic against zero Node-1 reunification coverage.** VG-class path, C-SSRS/INQ anchoring, FP verification, EN+AR, Lane-3 sign-off.

**Sign-off packet (one packet, everything by name):** 40 blocks + 18 scripts enumerated against the doc section list · doc→artifact diffs (em-dash scrub) · pathway manifests (delivery shapes, weave scopes, bridge maps, per-block guards) · trigger tables + collision table with declared resolutions · PSY-WEAVE-1 data with **deflection→crisis presented explicitly as design-added** · diagnosis-guard row-split mapping · framing-row mappings (safety-rule governance) · Classifier A structural-signal thresholds · §7c amendment · Surface-2 `kb_ref` additions · **AR validator-naming ask (first domino for the entire AR chain)** · **F1 naturalistic-recall acceptance bar (clinical sets it, per category or global — their call; without this ask the §7.3 flip precondition dangles on a number nobody was asked to set)**. All pinned via signed-fields on landing.

---

## 10. Deviations register & schema extensions (Absolute Rule 1)

**Deviations/extensions vs. the doc:**
1. Deflection→crisis in PSY-WEAVE-1 (doc's branch is binary yes/no) — design-added, fail-closed; named in packet for ratification.
2. Weave-pending session expiry (pending state does not survive session exit; rationale §4.2) — recorded decision, safety-adjacent.
3. §7c reclassification (ruled amendment, §9).
4. Em-dash copy transformation (ratified via doc→artifact diff).
5. Per-category flag structure (doc is silent on rollout).

**Named schema extensions (not doc deviations):**
6. `delivery_shape` as a per-category attribute (block metadata + manifests) — the schema extension flagged in the original scope ruling, realized here; this closes that ruling's loop.
7. Per-article-family `prior_exposure` granularity — v7 §9.1 defines `prior_exposure` per-skill (0–5+); the carry-forward increments it per article family: a mild granularity extension of the profile schema.

---

## 11. Not in scope

Structured-UI menus (post-POC; degrade-to-text stands) · cross-session carry-forward (declared dependency on profile repair; not wired) · E2 adoption (seam only, pending signature) · legacy-article overlap reconciliation (quarantine holds meanwhile) · §4a (clinical queue; Mechanism-B) · Mechanism-A itself (live interim; retired per category at flip, §0).
