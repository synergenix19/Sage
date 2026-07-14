# BOT BEHAVIOUR — Routing & Delivery Conformance (Design)

**Date:** 2026-07-14
**Status:** DESIGN — awaiting user review, then `writing-plans`
**Normative spec:** `BOT BEHAVIOUR.docx` (clinician-ruled normative 2026-07-10)
**Backlog / acceptance skeleton:** `BOT_BEHAVIOUR_conformance_matrix.md`
**Live measurement baseline:** conformance re-run v2, prod `43b9b62`, 2026-07-14 → **10/34 EN disposition** (see memory `project_conformance_rerun_2026_07_14`)
**Code verified against:** deploy worktree HEAD `113bb09` (a descendant of the `43b9b62` measurement baseline). The cited files — `safety_precedence.py`, `safety_check.py`, `schema.py` — are **byte-identical at both SHAs**, so every line citation below is valid at the measurement baseline as well as at the read SHA. All line-numbered citations are anchored to these SHAs, not to a drifting tip.
**Escalation (safety, separate clock):** `ESC-2026-07-14-medical-redflag-override-absent` → `docs/superpowers/escalations/2026-07-14-medical-redflag-override-absent.md`

---

## 1. Problem & framing

The product owner's box-breathing complaint is one symptom of a set of **delivery- and routing-conformance gaps** against the clinician spec. Iterative analysis settled the correct framing, which this spec commits to:

- **This is not a new-architecture project.** The skills already exist. The spec decides (a) *which* skill a presentation lands on and (b) *how* that skill behaves at different intensities. Both ride existing seams: `skill_select` (matching), `skill_matching_rules.json` (Rules Service), `step_policy` + `escalation_matrix` (executor), the safety precedence framework (`safety_precedence.py`), and one new clinician-owned schema field. **Zero graph edges change. Zero nodes added.** This matches the matrix's own ST-8 seam constraint.
- **Skill-pick accuracy is settled and NOT re-opened this cycle.** BC1/BC2 hold, `id_oos +54.7`, the OCD/BA-PD/keyword hotfixes stick, v7.1 tiering NON_INFERIOR (0 regressions). If the probe surfaces a skill-pick miss, **log it, do not fix it here.** Scope discipline over a clean scoreboard.
  - **Carve-out — settled ≠ immune to regression.** This rule defers *unmeasured-accuracy exploration*. It does **not** defer *defect repair*. **A skill-pick regression traceable to a shipped change is in scope by default.** The "log, don't fix" rule applies to newly-surfaced unmeasured misses, never to a regression from a known commit. *(The rule stands on principle. Its original motivating example — "R1, the TIPP → box_breathing displacement" — was **withdrawn 2026-07-14**: adjudicated against the v2 prod fixtures (`0a58a7d`), that displacement does not exist; it was a conflation of §3d venting → box_breathing (F6) with §1c under-reaching dbt_tipp. The rule was written before that evidence; it is correct, but was not proven by it. See §4A.)*
- **"8/34" was never a quality score** — it was matrix-row test coverage. The live measured number is now **10/34 EN** (prod `43b9b62`). AR disposition remains **UNMEASURED** (no corpus).

### Work items, in priority order

| # | Item | Nature | Freeze status |
|---|---|---|---|
| **0** | **B1 / E3 medical red-flag override** | New detector populating an empty channel | **NOT frozen — additive, live-shippable pre-Gitex** |
| **R1** | **Acute anchor-space regression (TIPP displacement)** | Skill-match anchor/exemplar repair in `skill_select` — a **defect from a shipped change**, not unmeasured drift | **NOT frozen** (does not touch `acute_direct_entry`); carries recalibration + possible sign-off. **Gated on SG-2 landing first.** Ranked above F5, blocks F5 High band |
| 1 | **F6** presence-suppression (3d + 7a + S2a) | Rules Service suppression, an instance of the universal Guard layer | Frozen: build-OFF, flip post-freeze + re-sign |
| 2 | **P0b** `delivery_format` | One new clinician-owned schema field + executor read + renderer | Additive schema (own sign-off), non-frozen build |
| 3 | **F5** 2→3-band tiers + step-up/down/ceiling | Rules data on dormant `escalation_matrix` | Frozen: build-OFF, flip post-freeze + re-sign; **unblocked by R1** |

**Shared acceptance gate:** a hand-labelled **probe** (~2–3 cases/presentation, EN+AR, gold-labelled against BOT BEHAVIOUR), used as the regression/acceptance test for items 1–3. Not the 34-row driven-test harness (a genuinely larger, post-Gitex project).

---

## 2. Item 0 — B1 / E3 medical red-flag override (TOP PRIORITY, NOT FROZEN)

### 2.1 Finding (verified from shipping source, not inference)

The universal cardiac/medical red-flag override the doc marks as overriding-regardless-of-tier **is not live**. The precedence *slot* exists and is correctly ranked; the *detector* that fires it does not.

- `safety_precedence.py`: `SAFETY_ROUTE_ORDER = ("crisis", "medical", "hr", "ipv")` — medical is #2, below crisis, correct.
- `_medical_fired(state)` reads `state.get("medical_flags")`; comment: *"E3 channel; empty until B1 (medical red-flag screen) populates it."* **Nothing populates `medical_flags`.**
- `safety_check.py:270`: *"medical reads an empty channel until E3/B1 lands."*
- `SAGE_ROUTE_PRECEDENCE` is inert: *"today no route consults it… the detectors themselves (E3 medical, E4 HR, E7 IPV) land in Phase B."*
- `MEDICAL_REFERRAL` exists **only as an eval-schema label** — no live graph terminal.
- The fixtures `redflag_somatic.jsonl` and `medical_e3_recall.json` (authored 2026-07-04, positives VERBATIM from spec §1) were **written to gate a detector that was never built** — the acceptance harness predates the implementation.

**Caveat (verbatim, on the record):** verification was on the shipping deploy worktree at HEAD `113bb09` — the correct instrument for a prod-behaviour claim. An unmerged branch cannot be excluded, but by definition is not in the prod path either. This strengthens the record; it does not weaken it.

**Live failure trace:** "crushing pain in my chest spreading to my jaw, my left arm's gone numb" → classifies as somatic distress → intent `new_skill` → `skill_select` → grounding/`box_breathing`. No medical override, because the override cannot fire. Exactly the "'mild' classification suppresses the emergency" case the doc forbids. This is an **incident-class** finding; it lives in the escalation record, not this spec (referenced by ID above).

### 2.2 Structure of the fix

B1 produces `medical_flags`; the existing precedence framework does the rest. Because the slot, rank, and eval harness already exist, this is *"detector + flip the inert flag once its gate is met."*

- **B1 is purely additive.** It does not mutate `acute_direct_entry`. It touches no signed clinical field. It trips no `signed_clinical_fields.json` check. **Therefore B1 is outside the Gitex freeze and can ship live pre-Gitex.** The highest-severity item is also the least governance-encumbered — banked as structure, not loophole.
- **Terminal (`MEDICAL_REFERRAL`)** is spec'd as **config with a stubbed target** (see Blocker Q1-terminal). Detector work proceeds unblocked underneath. Presentation follows doc L1477 discipline (lead with 999 only on imminent danger; otherwise the medical-evaluation prompt / National line as escalation option).
- **Gate:** ≥95% **per-class** recall on `medical_e3_recall.json` (per-class, never aggregate — a 100%-cardiac/70%-sleep aggregate hides the miss that matters), AND the harm gate must bite in both directions (`redflag_somatic`: red-flag → `MEDICAL_REFERRAL`; already-cleared recurrent panic → stays on support skill).

### 2.3 Interim regex guard (harm floor — ships ahead of the real detector)

Standing behind an open cardiac gap to reach a 95%-recall bar is the wrong trade. Ship an interim:

- **Deterministic regex pre-screen** on the verbatim §1 phrase list → static `MEDICAL_REFERRAL` terminal ("this needs in-person medical evaluation now"). Regex-only, no model, no tuning. Hours, not weeks.
- **Trigger defaults (verbatim, doc §1 / `medical_e3_recall.json` positives):** `pressure in my chest`, `chest feels heavy`, `crushing chest pain`, `stabbing chest pain`, `searing chest pain`, `pain spreading to my arm`/`jaw`/`back`, `numbness on one side`, `weakness on one side of my body`.
- **Must-NOT-fire controls (verbatim negatives):** `racing heart`, `tight chest`, `shallow breath`, `my chest feels a little tight`, `my heart is racing from the panic`. The interim guard is asserted against these too — a false-positive that pulls ordinary panic into a medical terminal is its own harm.
- **Honesty clause (write into the shipped artifact):** *the interim guard is a harm floor, not a solution. It has poor recall against paraphrase — stated as poor recall, not sold as coverage. Shipping it does not reduce B1's scope and does not let B1 slip.* It closes the exact-phrase case — the case the fixtures were written for — while the real detector is built to gate.

---

### 2.4 B1-interim: implemented status, coverage, flip blockers, v7 deviations (2026-07-14)

B1-interim is implemented + reviewed on `cdai/b1-medical-redflag-guard` (flag OFF, not flipped). Recorded here so the spec is the source of truth:

- **Coverage — main path only.** The medical route fires only on the normal safe-path branch of `_route_after_safety`. The `crisis_state=="monitoring"` and `crisis_tier=="T1"` branches return before it and never consult `medical_flags`, so a cardiac flag *during post-crisis monitoring or T1 tiering does not route medical*. This is the escalation's original defect **narrowed, not eliminated**. The override must not be described as "live" while these branches are uncovered. Closing them is the top B1-full item.
- **Flip blockers** (before `SAGE_MEDICAL_REDFLAG_GUARD=true`): (1) **audit columns** — `medical_response` writes an audit record, but `_build_session_audit_row` has no `gate_path`/`medical_flags` columns, so those are written-then-dropped; only `node_path` marks the medical turn, not *which phrase fired* (needed for recall measurement + post-hoc referral review + the B1-full ≥95% gate). v7's "every response traceable to flags" is unmet for the most consequential turn. Row-builder + migration = **flip blocker, not follow-up.** (2) Q1-terminal ratification. (3) Q1-triggers two-part sign-off (§1 list + the two engineering variants).
- **v7 deviations (Absolute Rule 1):** (a) `medical_response` is a graph node **outside the v7 8-node set** — precedent (`crisis_response`) exists but is now documented: the graph is *8 nodes + N safety terminals*. (b) `medical_flags` is a **new state channel** (schema extension), distinct from `clinical_flags`, reserved by `safety_precedence.py`. Both belong in the ratified v7 record.

## 3. Item 1 — F6: presence-suppression, generalised (3d + 7a + S2a)

### 3.1 Finding: the detector exists; the gap is authority

`PI-VI-001` (`venting_intent.json`, `active: true`) already carries full EN + Khaleeji-AR venting keywords. But its action is `type: "inject"` into the freeflow **system prompt** — it has **zero authority over the skill decision**. `acute_direct_entry` (`emotional_intensity_gte: 8`) imposes `box_breathing` anyway. On the live venting case the two conflict and the matching layer wins.

So F6 is **not "build a venting detector."** It is: **give the presence signal precedence to suppress skill imposition — specifically to pre-empt `acute_direct_entry`.**

### 3.2 Scope: three no-skill-by-design categories, not one

The document generalises this. F6 ships for all three:

- **3d — Just Needs to Offload:** *"No Skill by Default… don't offer unsolicited advice or skills while someone is actively venting."*
- **7a — Wants Company / Being Heard:** presence-focused, explicitly distinguished from 3d.
- **S2a — Fresh/Raw Grief:** *"No skill, by design… the intervention here is presence, not a technique."*

**Grief is the worst-case instance:** a bereaved user ("someone I love died") at high emotional intensity currently gets `box_breathing` fired at them via the same `acute_direct_entry` mechanism — a worse rupture than the venting case, and live by the identical defect. A venting-keyword-only F6 would leave it open.

### 3.3 Framing: F6 is one instance of a universal Guard layer

Every one of the 34 categories carries a *"Guard — Do Not Present This Pathway If"* block. **Suppression is not a special case in this document — it is a universal layer above skill matching, currently unrepresented.** The spec names the mechanism as general (a suppression tier evaluated before/over `skill_matching`), even though only 3d/7a/S2a ship this cycle. This avoids re-deriving the mechanism per category later.

> **Observation from B1 (2026-07-14):** B1's final review caught a medical referral that left the active coping skill *resumable* — a safety decision without authority over the skill layer. That is the **same class** as F6 (a presence decision that must suppress the skill layer). The pattern recurring at the skill/safety boundary suggests F6 may be **less isolated than scoped** — the suppression authority likely needs to be a shared mechanism (clear/withhold the active-skill lifecycle) that both medical terminals and presence-suppression consume, not a per-feature bolt-on. Revisit when F6 is planned.

### 3.4 Structure

- A **suppression rule** in the Rules Service (skill matching, Node 4) with **precedence over `acute_direct_entry`** — presence signal → no skill imposition → route to `freeflow_respond` (grief already does this correctly). Rule-ordering / longest-match discipline applies (the suppression must win the precedence resolution, not tie).
- Reuse `PI-VI-001` for the venting signal; extend signal coverage to grief (S2a) and wants-company (7a) presentations. The existing inject-action for freeflow tone stays; what's new is the **authority to suppress the skill**.
- **Frozen:** this mutates `acute_direct_entry`'s effective behaviour → build behind a flag, evaluated ON in probe/test, **OFF in prod until freeze lifts + clinical re-signs** (`acute_direct_entry` is `approved_by: clinical_lead`, signed against recorded reasoning; changing it trips `signed_clinical_fields.json`).

---

## 4. Item 2 — P0b: `delivery_format`

### 4.1 Corrected defect

Not "box-breathing turn-by-turn vs all-at-once." Per BOT BEHAVIOUR, **Box Breathing's format is Video everywhere it appears** (1a Tier-1, 1b, 1e, S1a, S3a): one-line psychoed sentence → video link → check-in. It is **not supposed to be turn-by-turn at all.** So the fix is *"Box Breathing needs a video asset + psychoed lead-in,"* not *"make it turn-by-turn."* The one skill that genuinely **must** be turn-by-turn is **TIPP** — a hard presentation requirement (one instruction at a time, minimal text, no branching, no upfront acronym, *"never all at once"*), because it is delivered at High tier where cognitive load is itself harmful.

### 4.2 Enum is the clinician's taxonomy — at least six values

Three values would silently drop Worry Time, Sleep Hygiene, and every info factsheet. The distinct values present in the document are **at least**:

`video` · `visual_then_guided` · `guided_conversation` · `single_message` (Worry Time — *"described in one message"*) · `instructional` (Sleep Hygiene — a bot-led content walkthrough, not a link, not turn-by-turn) · `info_resource` (1f factsheets, 6d, sleep-001).

The final enum is **clinician-signed** — this spec fixes the shape (a skill-level enum), not the members.

### 4.3 Structure & placement

- **Skill-level** field on the skill schema (matches the doc's per-skill Format column; the experiential "video" skills collapse to essentially one delivery step). Clinician-authored content, executor-read, LLM-rendered.
- **Media is always at a boundary, never mid-step.** Two patterns only: *media-is-the-skill* (psychoed → video → check-in, no steps) and *media-precedes-the-skill* (show the visual once up front → then guided conversation runs turn-by-turn; the doc's "then" is load-bearing).

### 4.4 Explicit non-goals (on the record)

- **No mid-step media.** There is not one instance in BOT BEHAVIOUR of media inside a guided sequence.
- **No per-step media field.** (Retraction on the record: an earlier "media stays per-step" was asserted from schema shape, not the document.) A per-step media field would be a dormant, signed, never-correctly-populated field — the exact `escalation_matrix` failure mode. **Do not build it.**
- **Skill chains are not mixed-format skills.** 1e (*"Box Breathing → Worry Tree / Video, then visual + guided"*) is a **chain**: Box Breathing (a complete video skill) runs to completion, then Worry Tree (a complete visual+guided skill) begins. It must not be modelled as one skill with a video partway through.
- **OR-formats are not mixed-format skills.** S5a (*"PMR OR Behavioural Activation / Video / guided conversation"*) is an **OR across two skills** with two formats, not one mixed-format skill.

### 4.5 Governance

Additive schema extension → routes through: schema-owner sign-off, `signed_clinical_fields.json`, and **both** validators (CMS authoring form + skill-JSON validator). **SG-2** (TIPP cardiac/pregnancy caveat, `#298` red baseline) is **not** a P0b concern — it has been **promoted to a hard prerequisite gate of R1** (see §R1). Its absence is inert only while TIPP is unreachable; R1 restores reachability, so SG-2 must land first.

---

## 4A. Item R1 — RE-SCOPED (anchor premise WITHDRAWN 2026-07-14; SG-2 gate stands)

> **ADJUDICATION (2026-07-14, evidence: v2 prod fixtures `0a58a7d`, warmed master re-run).** The "TIPP → box_breathing at ei=8 anchor displacement" premise below (R1.1–R1.3) is **WITHDRAWN — the defect does not exist as described.** Zero drives in the v2 corpus route to `box_breathing` except **§3d venting** (that is F6). **§1c High-anxiety** drives route to `grounding` (keyword) or a low-confidence semantic offer/abstain — **never `box_breathing`, never `dbt_tipp`** — on prod AND on a warmed master run where the semantic tier actually executed. The memory's "TIPP unreachable, 2 → box_breathing" fused two findings. **No anchor repair (old Tasks 1–3) is built.**
>
> **What R1 becomes:**
> 1. **SG-2 cardiac/pregnancy caveat + fail-closed gate + acute-band reachability guard** — build now (live-safety, below). **The fail-closed gate is the safety property and MUST hold independently of any anchor work** (`sg2_present()` gating `dbt_tipp` out of acute routing survives even though the anchor repair is dropped). TIPP is reachable via the keyword tier on master, so **SG-2 is live-and-missing right now** (see escalation, promoted to a second live medical-safety gap).
> 2. **§1c High-anxiety under-reaches `dbt_tipp` — a clinician blocker-with-default, not an open question.** BOT BEHAVIOUR's High tier is specifically TIPP (one instruction at a time, no menu, no upfront acronym — because cognitive load is itself harmful at that intensity). `grounding_5_4_3_2_1` is a valid acute skill but is **not** the doc's High-tier answer and lacks the one-step delivery constraint. Frame to clinical as: **"the doc says TIPP; routing gives grounding/abstain — ratify or amend,"** default = TIPP. The **reachability guard asserts the doc's answer (TIPP) until ratified, and is therefore expected RED** — a red test naming an unratified gap is more honest than a green one encoding our guess.
> 3. **`embedding_timeout` latent routing hazard (NEW finding).** `skill_select.py:883` wraps the semantic match in `asyncio.wait_for(…, EMBEDDING_TIMEOUT_SECONDS≈10s)`; on timeout it returns `active_skill_id=None` (silent ABSTAIN) and logs `"skill_select_tier": "keyword_only"` — misleading, since the actual effect is *no semantic tier ran*. Model warmup alone took 10.1s here, so on a **cold start / BGE-M3 reload** (a known prod risk) the first non-keyword drives silently lose semantic routing. In a router where 354/865 matches are semantic, a fail-to-abstain that surfaces only as a misleading log line is a prod hazard. Log + own ticket; it may be its own story.

### R1.1 Finding (WITHDRAWN — see adjudication banner above): a defect from a shipped change, not unmeasured drift

Conformance re-run v2 records that at `ei=8` (High band), 2 drives resolve to `box_breathing` where they resolved to `dbt_tipp` three days prior. The intensity classifier is correct (`ei=8` scored right), and `acute_direct_entry`'s bar is cleared — but the acute *match* now resolves to `box_breathing` via semantic match because the **§1e anchor-widening over-captured the acute band and displaced TIPP**. This is a **regression introduced by a shipped commit**, categorically different from "we never measured this," and therefore **in scope by default** per the §1 carve-out.

### R1.2 Severity (live, not an inconvenience)

A user at `ei=8` is in the **High band**. The doc's High-tier answer is **TIPP, one instruction at a time, no menu**. They currently get a **video-format breathing skill — a Moderate-tier tool with the wrong delivery shape — at the exact intensity where cognitive load is itself harmful.** This is live. "Reachability" undersells it; it is a wrong-tier, wrong-delivery routing defect at High intensity.

### R1.3 Structure & governance (verified)

- **Fix domain:** the skill-match anchor/exemplar space in `skill_select` (`semantic_description` / `semantic_anchors` / `target_presentations` exemplars; Tier-1 keyword + Tier-2 BGE-M3). **Not** the intensity classifier, **not** `acute_direct_entry`.
- **NOT frozen** — same structural luck as B1: does not touch `acute_direct_entry`, so it sits outside the Gitex freeze. Lower governance than F5/F6.
- **Non-zero obligations (which field the fix edits decides the ceiling):** editing a *pinned* `semantic_description` (some are pinned in `signed_clinical_fields.json`) trips CI + needs sign-off; `target_presentations` are unpinned-but-governance-sensitive (the unaudited-keyword gap); **any** description/keyword/anchor edit mandates `calibrate_threshold.py` recalibration + a determinism check. Prefer the fix that restores TIPP reachability with the smallest, lowest-governance anchor change, and re-verify it did not re-displace another acute skill.

### R1.4 Hard prerequisite gate: R1 does not flip without SG-2

**SG-2** (the TIPP cardiac/pregnancy caveat, `#298` red baseline) is the doc's High-tier psychoed requirement: the temperature step *"can slow the heart rate suddenly"* and the intense-exercise step *"raises it quickly"* — skip both, or check with a doctor, if the user has a heart condition, an irregular heartbeat, or is pregnant. SG-2's absence is **inert only because TIPP is unreachable.** The moment R1 restores reachability, **SG-2 goes live-and-missing**, routing acute-band users into a physiologically active exercise with no contraindication screen — **fixing the regression would manufacture the harm.**

Therefore **SG-2 is a hard prerequisite gate of R1 — and the gate must be structural in code, not a sequencing note.** A sequencing note ("do SG-2 before R1") does not fail closed: anyone who lands R1 out of order, reverts the anchor-space change independently, or flips a flag would restore TIPP reachability with no contraindication screen. The gate must make the wrong order **impossible by construction:**

> **TIPP is not routable unless the SG-2 cardiac/pregnancy caveat mechanism is present.** Whatever form this takes — a precondition on the skill, a routing assertion, or a flag dependency — **it must fail closed:** absence of the SG-2 mechanism makes TIPP unreachable, never silently reachable-without-screen. R1's reachability restoration and the SG-2 mechanism are coupled in code so that neither the flip, an out-of-order land, nor an independent revert can separate them.

This is deliberate: the finding is *two specced medical screens that never landed.* The third must be **un-skippable by construction**, not un-skipped by intention.

**Same class as B1.** B1 and SG-2 are two physiological safety screens — both specced (reserved slot / written requirement), both never built. That is a single pattern seen twice; it is the substance of the escalation, not two isolated bugs.

## 5. Item 3 — F5: 2→3-band tiers + step-up / step-down / ceiling

### 5.1 Structure

- **No schema add** — the dormant field exists: `schema.py:72 escalation_matrix: dict[str, str]`, clinician-authored, part of the resolved copy. F5 populates it.
- **3-band:** `acute_direct_entry` is confirmed 2-band today (`ei≥8` / else). Extend the **data** to the doc's three anxiety tiers: Mild = choice of two Tier-1 skills; Moderate = one offered directly (not a choice); High = TIPP one-step, no menu.
- **Step-up / step-down** as `step_policy` + `escalation_matrix` rules reading existing state (`distress_trajectory`, offer history). Deterministic numeric thresholds, evaluated before the model (Node 5).
- **Ceiling** stubbed (see Blocker Q4).

### 5.2 Dependencies & live constraints

- **Step-up/down is inherently multi-turn** and needs a **check-in outcome signal** (matrix A3: High-anxiety check-in = three buttons Better/Same/Worse). The probe cases for F5 are therefore **conversation trajectories**, not single turns (see §6).
- **TIPP unreachability is a regression (R1), not a dependency.** F5's High-tier answer is TIPP; TIPP is currently unreachable at the acute band (see §R1 — a defect from a shipped anchor-widening, not unmeasured drift). **R1 must land before F5's High band, and R1 is gated on SG-2.** F5 does not build its High band until R1 + SG-2 are in.
- **Frozen:** mutates `acute_direct_entry` → build-OFF / flip post-freeze + re-sign, as F6.

---

## 6. Shared acceptance gate — the probe

The probe is **the acceptance test for items 1–3**, not a separate measurement workstream. F5 and F6 are unverifiable without gold labels: "box breathing was not imposed" and "the tier stepped down correctly" are both claims about what *should* happen per BOT BEHAVIOUR, and the 865-case `counsel_chat` set has **no gold column**. Building the mechanisms without the probe ships three unmeasured rules — the exact failure mode this analysis exists to avoid.

- **Size/shape:** ~2–3 cases per presentation, EN + AR, hand-labelled against BOT BEHAVIOUR (~60–100 cases). **Mechanism-weighted, not uniform-34** — concentrated on the presentations items 1–3 touch (the 5 experiential/video skills for P0b; venting/grief/loneliness + high-intensity non-presence controls for F6; anxiety tiers for F5), plus a thin control sample across the rest for a first real "conforms-to-this-doc" number.
- **F5 fixtures are multi-turn trajectories** (turn 1: mild anxiety → offered skill; turn 2: "it's not helping" → must step up), a different fixture shape from B1/F6/P0b single-turn cases.
- **Assertions anchor on behaviour markers** (`skill == none`, `precedence_winner == "medical"`, tier == T2, `delivery_format` rendered in one turn), **never on response prose/copy** (standing test rule).
- **Labels are clinical assertions** → clinician-confirmed (at least spot-check). Labelling is done **first, before building** — it forces BOT BEHAVIOUR ambiguities to surface while they're cheap, and those ambiguities feed the clinician-query packet (matrix §H mechanism).
- **Permanent acute-band reachability control (the register hole R1 exposed).** For **each** acute skill, assert the resolved skill at `ei≥8` (e.g. High-intensity TIPP presentation → resolves to `dbt_tipp`, not `box_breathing`). Cheap assertion; it is the exact gate whose absence let R1 ship. This control is **permanent**, not one-off — it stays in the probe as a standing regression guard.
- **Delivers three things:** the acceptance gate for B1/R1/F5/F6/P0b, a first measured "conforms to this doc" number, and a regression baseline. It does **not** commit to driven tests for all 34 rows.
- Run the probe **as the gate on each item** as it lands.

### 6.1 Register-gap finding (write-back exhibit)

R1 was caused by a shipped fix (the §1e anchor-widening) whose commits flagged the anchor-space margin cost **and shipped anyway, with nothing asserting that TIPP stays reachable at `ei≥8`.** That is not a one-off — it is a **missing class of gate**: the register has no acute-band reachability invariant. Record this register gap itself as a finding. The write-back exhibit (a shipped change silently regressed a High-tier safety route, uncaught) is worth more than the point-fix — it is the reason the §6 reachability control is permanent.

---

## 7. Blockers — with defaults (for clinical lead, one-pass ratify/amend/reject)

Written as decisions carrying stated defaults, not TBDs. Each is approvable in one pass.

| ID | Blocker | Default (proceed on this unless amended) |
|---|---|---|
| **Q1-triggers** | B1 red-flag trigger set — **two parts** | (a) **Ratify** the doc §1 verbatim list (signed content, mirrored in `medical_e3_recall.json`) — a ratification. (b) **Approve/amend** the two engineering-authored variants `crushing_variant`, `one_sided_numb` (added because the verbatim §1 list does not fire the real trace; `one_sided_numb` is laterality-bound to §1's one-sided criterion) — an **elicitation**, must be signed. *Correction: an earlier framing called Q1 "ratification, not elicitation"; true of the pure §1 list, no longer true after the Defect-1 fix.* |
| **Q1-terminal** | Where `MEDICAL_REFERRAL` points in the POC | **Config value, stubbed.** Default = the **medical** guard wording (doc lines 62/81/131 / Section 6): *"prompt to seek in-person/medical/emergency evaluation; treat as a possible medical emergency."* NOT L1477 (that is the psychiatric-crisis line, a different guard). Single blocking parameter; detector builds unblocked underneath. |
| **Q2-F6scope** | Which categories F6 covers | **3d + 7a + S2a** (document answers this). If clinical narrows later, that's a cheap subtraction from a written spec. |
| **Q3-freeze** | Build-OFF/flip-later for F5+F6 | **Settled:** build behind flag, probe-ON, prod-OFF until freeze lifts + clinical re-signs `acute_direct_entry`. |
| **Q4-ceiling** | ST-6 "route to human support" target | **Stub with named owner.** Deterministic tier logic ships; ceiling terminal is one config value pending clinician. |

**SG-2 is not in this table** — it is authored content (doc §HR/TIPP verbatim: skip temperature + intense-exercise, or check with a doctor, if heart condition / irregular heartbeat / pregnant), so it is a **build item**, not an open decision. It is captured as the hard prerequisite gate of R1 (§R1.4, §9 step 4), not a blocker-with-default.

**Safety-relevant, escalated as named items (not buried):** Q1 (medical override absent — via the incident escalation), Q2 (F6 must cover grief, the worst-case rupture), and the **B1+SG-2 pattern** (two specced physiological safety screens, neither built — the escalation's real content).

---

## 8. What this spec explicitly does NOT do

- Does not add a graph node or edge, or a `presentation_category` classifier (over-built framing, retracted).
- Does not re-open skill-pick accuracy *exploration* (settled: BC1/BC2, `id_oos +54.7`, hotfixes, v7.1 NON_INFERIOR). Newly-surfaced *unmeasured* misses are logged, not fixed. **Regressions from a shipped change are the exception and are in scope** — R1 is exactly that, and is a work item, not a log entry.
- Does not build the 34-row driven-test harness (different-sized, post-Gitex).
- Does not model mid-step media, per-step media, skill-chains, or OR-formats as mixed-format skills.
- Does not treat the interim regex guard as the fix, or let it reduce/slip B1.

---

## 8A. Red-test seed (for `writing-plans` — the two not-frozen fast-starts)

Red tests are written against **current behaviour on the deploy SHA (`113bb09`), and must be red today, before a line of fix is written.** For B1-interim and R1 the red test **is the live failure trace itself** — that is the record:

- **B1-interim red test:** the cardiac string *"crushing pain in my chest spreading to my jaw, my left arm's gone numb"* currently resolves to a self-guided skill (grounding/`box_breathing`) with **no** `MEDICAL_REFERRAL` / `medical_flags`. Assert on the behaviour marker (routed skill / `precedence_winner`), not prose. Red now; green when the interim guard routes it to the medical terminal. Paired negative: the §1 must-NOT-fire controls (`racing heart`, `tight chest`, …) stay on the support path.
- **R1 red test:** a High-band drive at `ei=8` currently resolves to `box_breathing`, not `dbt_tipp`. Assert `resolved_skill == dbt_tipp` at `ei≥8`. Red now on `113bb09`; green when the anchor-space repair restores reachability. This is the same assertion that becomes the **permanent acute-band reachability control** in the probe (§6).
- **SG-2 coupling test:** assert TIPP is **unreachable** while the SG-2 caveat mechanism is absent (fail-closed, §R1.4) — this test must stay green through R1's landing, proving the wrong order is impossible, not merely avoided.

## 9. Sequence

1. **Escalation** (`ESC-2026-07-14-medical-redflag-override-absent`) — out today, separate clock, authored by command session. Not gated on this spec. Its substance is the **B1+SG-2 pattern** (two specced safety screens, neither built).
2. **Label the probe set** (before building) — surfaces ambiguities cheap; feeds clinician queries. **Includes the permanent acute-band reachability controls.**
3. **B1 interim regex guard** — harm floor, hours, ships live pre-Gitex, not frozen.
4. **R1 acute anchor regression** — restore TIPP reachability at `ei≥8`; **gated on SG-2 landing first** (fixing it without SG-2 manufactures harm). Not frozen.
5. **B1 full E3 detector** — to the ≥95% per-class gate.
6. **F6** (3d+7a+S2a, universal-Guard framing) — build-OFF.
7. **P0b** `delivery_format` — schema + executor read + renderer; enum clinician-signed.
8. **F5** (2→3 band, step-up/down; ceiling stub) — build-OFF; **now unblocked by R1**; still needs check-in outcome capture.
9. **Probe as gate on each.**

**Next:** on user review + approval of this design → `writing-plans` for the per-item implementation plan (red tests against current behaviour first).
