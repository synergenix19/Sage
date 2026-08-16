# Merge policy — inert-until-signed vs live-on-merge (the two-category rule)

**Status:** standing process rule, made explicit 2026-07-17 (the psychoed-consult gate-or-live call). Cite this instead of re-litigating precedent.

## The test
The question is NOT "does everything go inert." It is: **does the change alter what a user receives on a clinically-scoped turn?**

## Category 1 — clinical routing / content behavior → **inert until clinical authority attaches**
What response *class* a presentation gets, what copy a safety turn carries, which skills are reachable from which intents, what a detector fires. These merge flag-OFF / inactive and flip only on the relevant clinician sign-off. Precedents: B1 medical guard, F6 venting, HR-1 Stages 1+2, the HR copy pools, the psychoed info_request consult.
- **Why, sharply:** our derivation of "what the doc prescribes" has been wrong after feeling certain (the instructional-vs-disposition axis conflation was *this* fix, days before). "The doc says so" is a claim the clinician **ratifies**, not one engineering **self-certifies and ships live**. Shipping a clinical-routing change live under "it's just conformance" would, if the derivation were wrong, ship the error live — and would make any accompanying clinician review **retroactive** (the #270 active-before-signed shape: a question only has integrity while the answer can still change the outcome).
- **Cost is cheap here:** these gates are status-quo-preserving (the pre-fix behavior continues a few more days), not harm-continuing. Contrast HR-1, where the gate delayed *stopping a contraindicated intervention* — a harm-continuing gate, which needs its own justification. Status-quo gates are cheap; harm-continuing gates are not.

## Category 2 — guards / instrumentation / provenance → **live on merge, no gate**
Tests that pin existing correct behavior, audit columns, flag readback, CI wiring. These don't change what a user receives; they protect it. Precedents: the urgency-marker guard, the HR-suite gate wiring, `/health/version` readback, migration columns.

## Decoupling
A gated change's flip condition is the **specific** approval it needs, not the whole packet. The psychoed consult flips on the **consult-set confirmation** alone; it must not queue behind HR ratification. The flip checklist lists per-gate conditions so one async answer can flip one gate.

## Runbook note (subagent-driven development)
Subagent reports are how an agent *closes*, but they can be lost (an agent can die before writing one). **Pinned-exact tests are the report that can't be lost** — a test asserting `recovered == 3/3` per category, not `>= 1`, reconstructs the result from git when the report is gone. Prefer exact-pinned assertions over floors for anything whose number is the deliverable. (2026-07-17: the psychoed consult's recovery was reconstructed this way after its build subagent died pre-report.)
