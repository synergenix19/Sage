# Divergence Register Entry — Intent Classifier Model (POC vs Spec), Evidence-Transfer Rule

Date: 2026-07-28. Class: recorded deliberate divergence, evidence-scope rule.
Joins the recorded v7 §5.4 divergence (spec: Falcon-primary; POC prod runs
GPT-primary, gpt-4o-mini via OpenRouter — spec edit remains with the spec owner).

## The rule this entry adds

All Node-2 evidence gathered on the POC classifier transfers to any future
production classifier **as hypothesis only**, never as established fact. This
includes, as of today: the intent bistability finding and its cause analysis
(context stochasticity + provider variance), the confidence-calibration concern and
its RT-1 link, per-boundary flip rates from any distributional runs, and any
calibration thresholds derived from them (including the Node-3 confidence gate's
effective reachability).

**Production classifier migration is a MODEL CHANGE, not a config change.** It
re-opens: intent-boundary behavior (all conformance rows near boundaries),
confidence calibration (Node-3 gate), the bare-emotional-words SPOF definition,
offer-reply classification, and every distributional baseline. The model-promotion
protocol applies (never silent), plus a full distributional re-baseline under the
instrument-parity standing rule. Budgeting a "swap the model id" migration is the
failure mode this entry exists to prevent.

## Seed-honor / provider-echo visibility (recorded 2026-07-28, per Q-b review)

Verified from installed client source (langchain-openai 1.2.1): response metadata is
built from a fixed key set and does NOT propagate OpenRouter's upstream `provider`
field. Therefore, as deployed today: the `classifier_provider` audit column resolves
via the pin value (or null when unpinned), not from a response echo; and seed-honor
is observable ONLY via `system_fingerprint` when the provider returns one
(normalized to null, never fabricated, when absent). Consequence for baselines: the
determinism claim rests on the provider pin + N-sampling, with `system_fingerprint`
as corroboration where present — not on the seed request alone. The metadata path is
wired and takes precedence automatically if a future client version surfaces the
provider echo.

## Scope note

The determinism pins landing now (seed, provider pin, context-hash audit) reduce
variance for the CURRENT model; they do not make POC evidence portable across
models. The structured-context experiment (scoped separately) tests an
architecture-level mitigation whose RESULT may transfer as a design, but whose
numbers will not.
