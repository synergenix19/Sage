# Node 2 Structured-Context Experiment — Scope (NOT STARTED)

Date: 2026-07-28. Status: SCOPED ONLY, per queue item 5. Depends on: determinism
pins (seed + provider pin) landing first, for arm (c). Blocked from starting until
explicitly approved.

## Hypothesis

The dominant cause of Node-2 bistability is that the classifier prompt embeds raw
conversation history containing temperature-0.7 responder turns. Replacing raw
history with a DETERMINISTIC structured context block (derived solely from state:
last primary/secondary intent, active_skill_id + step, offer state, declined list,
`recent_presentation`, crisis/monitoring state) removes the stochastic input
component, and per-boundary flip-rate drops to the provider-variance floor.

## Design

- **Fixtures:** the turn-2 boundary family ("can you tell me how to manage my
  anxiety" and 6-10 paraphrase variants known or suspected bistable), plus 5 stable
  controls (clear general_chat, clear new_skill, clear info_request).
- **Arms:** (a) current raw-history prompt (baseline); (b) structured-context
  prompt, no pins; (c) structured-context + seed + provider pin.
- **N=50 per fixture per arm** (LLM-cost estimate ~2.3k classifier calls at
  gpt-4o-mini prices — cheap; wall-clock dominated by rate limits).
- **Metrics:** per-fixture flip rate (label entropy); confidence distribution vs
  flip rate (calibration curve — the RT-1-linked deliverable); Node-3 reachability
  (fraction of samples with confidence < 0.6 on boundary fixtures); intent accuracy
  vs a small labeled set (guards against the structured block LOSING signal — the
  known risk: summaries can drop nuance raw history carries).
- **Instrument:** the parity-rule helper in N-sample mode; artifacts carry flags,
  SHA, seed, provider, per-arm prompt template hash.

## Success / decision criteria

- Arm (b) flip-rate ≤ arm (c) flip-rate within noise AND both ≪ arm (a): context
  stochasticity confirmed dominant → structured context becomes a Node-2 design
  proposal (its own plan, clinician-visible since it changes what the classifier
  sees).
- Arm (b) ≈ arm (a): provider variance dominant → pins + seed are the remediation,
  structured context not pursued for determinism (may still be pursued for
  calibration).
- Accuracy drop on the labeled set > agreed floor in arm (b): hypothesis rejected
  on cost grounds regardless of flip-rate.

## Out of scope

Any change to what Node 3 does; any responder-side determinism; production
classifier migration (see the divergence-register entry: results transfer as
design, numbers do not).
