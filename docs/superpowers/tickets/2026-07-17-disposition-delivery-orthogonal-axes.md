# TICKET / architecture note 2026-07-17 — disposition and delivery are orthogonal axes (into P0b's spec + §2.1.1-style record)

**Owner:** whoever writes P0b (`delivery_format`). **Status:** durable architecture principle; today's psychoed Mechanism-A incident is the cited rationale.

## The principle
A skill's per-presentation prescription has two orthogonal axes. They must be **separate fields with separate consumers, and neither may appear in the other's decision:**
- **Disposition** — *what response does this presentation get?* (a specific skill / presence / referral / KB). Field: `target_presentations`. Consumer: the **router / node-4 skill-matching** (Rules-Service territory). Answers "does the doc prescribe a skill for this presentation?"
- **Delivery** — *how is that skill rendered?* (video / guided-conversation / instructional / single_message / info_resource). Field: `delivery_format` (P0b). Consumer: the **executor / node-5**. Answers "how do we present the skill we already chose?"

## The incident that proves it (rationale)
Psychoed Mechanism-A first scoped an info_request skill-consult by `delivery_format == "instructional"`. That derivation returned **exactly one skill** (`sleep_hygiene`) and recovered **none** of the psychoed cluster — because the cluster's prescribed skills (`psychoed_anxiety`, `psychoed_depression`, etc.) are guided-conversation *delivery*, but are the correct *disposition* for those presentations. Scoping a routing decision by a delivery-format value was an architectural misplacement (delivery leaking into the router), which v7 nowhere licenses. The fix re-scoped to the disposition set (`target_presentations`-derived); `delivery_format`/`instructional_set.py` stays where it belongs (the executor).

## What P0b must do with this
1. Introduce `delivery_format` as an **executor-only** field. Document explicitly that it is NOT a routing/matching input.
2. Document `target_presentations` as the **disposition** field, the router/matching input, orthogonal to `delivery_format`.
3. Add one sentence to the §2.1.1-style architecture record: *"Disposition (`target_presentations`, node-4) and delivery (`delivery_format`, node-5) are orthogonal; neither field appears in the other's decision."* with this incident as the cited example.
4. When `delivery_format` lands, the `instructional_set.py` convergence test (currently xfail) flips to enforce `INSTRUCTIONAL_SKILLS == {s | s.delivery_format == "instructional"}`.
