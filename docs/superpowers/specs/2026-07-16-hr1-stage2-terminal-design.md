# HR-1 Stage 2 — Doc-faithful High-Risk Terminal — Design Spec

**Status:** approved to build (user directive 2026-07-16). **Shape: two-turn stateful, doc-faithful now (NOT a single-turn interim).** Branch `cdai/hr1-stage2-terminal` off master@130134f (Stage 1 merged, inert).

**Normative source:** BOT BEHAVIOUR §HR (bot_behaviour.txt L1506–1548): detect → **ask distress (one question)** → standardized message → refer, with §3 branching on the answer.

## Why the B1-interim shape is the WRONG precedent here (the load-bearing reasoning)
B1's harm floor worked because a degraded medical response is still safe: "call 998 now" without nuance is correct for every true positive; the interim's weakness was bounded recall. **HR does not degrade that way.** Its distress score is not decoration — **it is the branch condition** deciding "see a doctor promptly" vs "999/ER now." A single-turn compression has exactly two forms, both violating the doc:
1. **Skip the question** (message + referral in one turn): the branch condition was never collected, so a manic user mid-spending-spree with risk behavior underway gets the see-someone-soon framing — the doc's §3 explicitly separates those outcomes; collapsing them picks the wrong one for the highest-severity cases, deterministically.
2. **Ask but ignore the answer** (fixed follow-up regardless): worse — performs the protocol's shape while discarding its function, and asks a distressed user a question that visibly doesn't matter (the doc's rationale for the one question is that it "informs whether emergency services are needed immediately").

So a single-turn "interim" is **not a harm floor here — it is a different protocol that resembles the doc.** That is artifact-shaped-like-reality (the thread's founding defect), built knowingly. Rejected.

## The state-machine cost is real but already paid for
The codebase already holds this shape: skills are multi-turn stateful flows (`active_skill_id`/`active_step_id`, completion evaluated on the user's reply). **The HR terminal is structurally a two-step skill with DETERMINISTIC steps:** step 0 = fixed-copy distress question; step 1 = branch on the answer → fixed-copy message + referral variant. It **rides the executor's existing step machinery (or a minimal mirror)**, not a new state channel.

## Four requirements (all doc-derived) — binding
1. **The branch is DETERMINISTIC, not LLM-evaluated.** Numeric parse of the reply (0–10 + the obvious verbal forms: "an 8", "like 7", "really bad"→high). §3's "signs of agitation, danger, or risky behavior already underway" is the one clause needing more than a number → implement as **risk-language in the reply → crisis-framing branch**, same phrase-class discipline as everything else. **NO `evaluate_completion_criteria` / LLM call on this path** — this terminal exists precisely because the LLM must not exercise judgment here.
2. **The non-answer case is specified, not improvised.** The user often replies with content instead of a number ("they're outside right now"). The doc forbids probing content or repeating diagnostics → **ask once more gently, then DEFAULT to the higher-severity branch (999/ER framing). Fail toward 999, never toward see-someone-soon.** This default is a blocker-with-default in the clinician packet (obvious safe answer).
3. **Mid-protocol interrupts keep global precedence.** If the reply contains SI/crisis content → **crisis wins mid-protocol** (routes immediately; the doc says both protocols can apply). If it contains new HR content → **stay in-protocol** (don't restart). The HR state must NOT become a bubble `safety_check` can't pierce — **safety_check runs on every turn regardless**, same as during skills.
4. **Skill-flow exit + audit on entry.** `active_skill_id` cleared on entry (the `medical_response` lesson — third appearance; **make it structural this time**, not convention). Own audit row carrying the **distress answer AND the branch taken**. Fixed copy from the doc's §2/§3 **verbatim as templates**, `crisis_copy_templated`-style (single-sourced, never LLM-rendered).

## Scope guard (binding)
**Two turns maximum, then terminal.** One question, no follow-up loop, no "how are you feeling now." The doc's protocol is deliberately minimal ("minimal engagement with the content itself is the point"). The state machine must be **incapable of exceeding two turns by construction, not by convention.**

## Fixed copy (verbatim from §HR — single-sourced)
- **Step 0 — the one question (§1):** "On a scale of 0 to 10, how distressing is this for you right now?"
- **Step 1 supportive message (§2):** "Thank you for telling me what's going on for you. What you're describing sounds really difficult, and I want to make sure you get support from someone who can help properly with this."
- **Step 1 redirect (§3), two branches:**
  - **higher-severity** (score high / agitation / risk-underway / non-answer default): crisis-framing via the **existing crisis pathway** — encourage 999 / nearest ER now, same UAE resources as crisis.
  - **lower-severity** (score low, no risk language): "This is something a doctor or mental health professional should look at with you soon..." + see-a-doctor-promptly, same UAE resources.

## What replaces / relates to Stage 1
Stage 1 routes all HR classes to the existing LLM-rendered `psychotic_referral`. Stage 2 replaces that terminal delivery with this deterministic two-step flow (generalize the name psychotic_referral → high_risk, or a new terminal — decide in the plan against the executor machinery). The Stage-1 detection (CF-006/007/008/009 + `hr_disclosure_present` routing) is unchanged; Stage 2 is the delivery upgrade behind the same gate.

## Open (into the plan, grounded by exploration)
- Ride skill_executor's step machinery vs a minimal dedicated 2-step flow — decide against the actual executor code (how a skill persists across turns, how completion is evaluated, where to force determinism).
- Where the distress-answer parse + risk-language phrase-class live.
- Audit column for the distress answer + branch (migration).
- Flag gate: same `HIGH_RISK_DETECTION_ENABLED`, or a distinct Stage-2 flag so the terminal upgrade can flip independently of detection.

---

## RESOLVED (2026-07-16, PO) — final shape, supersedes the "Open" section above

### Dedicated node, not a skill — and WHY it's architecturally right (not just mechanically forced)
The skill schema's inability to branch on parsed reply content is a **feature, not a limitation**. Skills are clinician-authored therapeutic content whose progression rides bounded numeric signals (intensity/engagement/resistance) precisely so clinicians author them safely without engineering. The HR protocol branches on a **parsed user value with an emergency-services consequence** — that is a **safety-control decision, and safety-control decisions live in nodes** (Cardinal Rule 1: nodes are control decisions; the arch doc's §2.2 "criteria_eval is not a node" states the same principle). The doc said it first: "fundamentally different shape from every other category, including crisis" → different shape, different layer. A skill that could branch on arbitrary reply content would be a hole in the schema's safety story.

### Architecture: no deviation, reuse maximised
- Dedicated 2-step node `high_risk_response` at `_route_after_safety`, **modeled on `medical_response`** (entry-clear of any in-progress skill, own audit row, deterministic copy, → END bypassing output_gate).
- Reuses: `select_crisis_resources()`/`CRISIS_CONFIG` (higher-severity branch), the LangGraph checkpointer (two-turn persistence via `active_step_id`), the audit conditional-column pattern, `safety_check`-runs-every-turn (Requirement 3 free — crisis returned first in `_route_after_safety`, so SI on turn 2 wins by graph shape: invariant by construction).
- **HR becomes the 4th safety terminal** (crisis, medical, HR, + low_confidence path). Node-catalogue entry in `docs/SageAI_architecture_current.md` rides the Stage 2 merge as a proposed addition (living-ref, human sign-off) — and closes the currently-missing `medical_response` entry in the same edit.
- Migration of HR out of the skill layer (Stage 1's `psychotic_referral`) is the doc's own "no skill here" claim made structural. Gated `SAGE_HIGH_RISK_TERMINAL` (strict-parse idiom, distinct from `SAGE_HIGH_RISK_DETECTION`); OFF = Stage-1 behavior.

### The two-turn flow (deterministic, exact)
- **T1:** fixed-copy §1 distress question. Set `active_step_id="hr_await_distress"` (checkpoint-persisted); entry-clear any in-progress skill.
- **T2 reply:** `safety_check` runs first (crisis pierces → crisis_response if SI). Then, in the HR node:
  1. **Risk/agitation language screens FIRST** (phrase-class, deterministic) → higher-severity branch immediately. Never re-ask someone who already gave §3 evidence in words ("they're outside right now").
  2. Else parse for 0–10 (numeric + verbal forms). Clean → branch on score (high → higher-severity; low → see-a-doctor).
  3. Neither → **one** fixed-copy gentle re-ask; set `active_step_id="hr_reask"`.
- **T3 reply:** parse again. Clean → branch. Otherwise → **default to higher-severity**. Terminal. **No third ask under any input.**

### Scope guard (reworded to what it always meant)
**"One question, asked at most twice; two branch evaluations, ever."** Enforced by the step counter — a third question is **unrepresentable** (the node has exactly steps {await_distress, reask}; after reask, any input terminates), not merely prohibited.

### Non-answer default (into the packet, done)
Risk-language → higher-severity immediately (bypasses re-ask); else one re-ask, then fail to higher-severity. Blocker-with-default in the clinician packet.
