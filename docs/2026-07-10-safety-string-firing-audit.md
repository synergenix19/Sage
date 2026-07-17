# Safety-String Delivery-Path Audit (Contraindication-Firing class)

**Date:** 2026-07-10 · **Trigger:** SG-2 driven-transcript finding — a cardiac caveat present in JSON never reached the user (LLM-discretionary). This inventories every safety-critical string and classifies its delivery path, so we fix the *class*, not one string at a time.

> **Checkout note:** the audit agent read the stale main checkout (`098469c`), so it reported "dbt_tipp not fixed / mechanism absent." That is a checkout artifact — the SG-2 fix (`mandatory_caveat` + `_pin_contraindication_caveat`) is on **PR #298**, not yet merged. **dbt_tipp is fixed; every OTHER row below is genuinely un-fixed** (the fix touched only dbt_tipp).

> **Root cause (architectural):** `L3_skill_wrapper.json` frames all skill copy — including `contraindications` — as *"Example phrases that convey this well (use as inspiration, not scripts)"* + *"Do NOT read these instructions aloud."* So by design, every skill safety caveat is LLM-discretionary. The gate-injection (`_pin_contraindication_caveat`) is the deterministic escape hatch.

## Firing-gap candidates (LLM-DISCRETIONARY safety copy) — priority order

| # | safety string | file:line | why it's a gap | note |
|---|---|---|---|---|
| 1 | **Post-SI "Are you safe right now?" safety question** | psychoed_depression.json:50 | the ONLY safety-screen question in the repo, buried in `contraindications` prose → L3 "inspiration" aside | **HIGHEST STAKES** — post-SI screening is LLM-discretionary; output_gate only *protects* an emitted question from collapse, never *injects* one |
| 2 | dbt_tipp entry_screen cardiac/pacemaker/ED caveat | dbt_tipp.json | LLM-discretionary L3 block | **FIXED on PR #298** (reference implementation) |
| 3 | PMR entry_screen injury/DVT/surgery caveat | progressive_muscle_relaxation.json | LLM-discretionary L3 block | entry_screen hold exists; caveat wording does not fire |
| 4 | body_scan entry_screen dissociation caveat | mindfulness_body_scan.json | LLM-discretionary L3 block | " |
| 5 | mindfulness_meditation entry_screen dissociation/panic/flashback + **referral** caveat | mindfulness_meditation.json | LLM-discretionary L3 block | carries a *referral escalation* discretionarily |
| 6 | safe_place_visualization entry_screen dissociation caveat | safe_place_visualization.json | LLM-discretionary L3 block | " |
| 7 | act_psychological_flexibility entry_screen passive-SI caveat | act_psychological_flexibility.json | LLM-discretionary L3 block | passive-SI screen — high stakes |
| 8 | box_breathing hyperventilation/asthma/cardiac caveat | box_breathing.json | LLM-discretionary **+ NO entry_screen gate** | no deterministic hold backstop either |
| 9 | grounding_5_4_3_2_1 sensory/visual-impairment caveats | grounding_5_4_3_2_1.json | LLM-discretionary **+ no gate** | " |
| 10 | stop_technique high-intensity→crisis redirect | stop_technique.json | LLM-discretionary **+ no gate** | " |
| 11 | escalation_matrix **L2/L3/L4** strings (all skills) | e.g. dbt_tipp.json:193-195 | **read by NO runtime code** — inert | **DEAD/MISLEADING:** "exit to crisis" / "human handoff" as written never fire; real enforcement is separate (crisis detection, review queue). Wire or annotate-as-docs — verify first |
| 12 | escalation_matrix **L1** exit + step_policy `validate_only` / `exit_warm_closing` wording | skill_executor.py:529 / :485 | the hold/exit *decision* is deterministic; the *words the user sees* are LLM-composed | lower stakes (wording only) |
| 13 | psychotic_referral wording | psychotic_referral.json:17 | routing pinned (graph forces skill_select); referral *text* LLM-rendered | wording only |

## Deterministic (sound — no gap)
Acute crisis response CC-EN-001/AR (rules-engine verbatim, crisis→END bypasses LLM); extended crisis resources CC-EN-002; crisis-node hard fallback (graph.py); `SCOPE_REFUSAL_RESPONSE` (PS-2); `JAILBREAK_RESPONSE`; `_pin_mood_anchor`; `_pin_ocd_referral`; `_EMPTY_MONITORING_FALLBACK`; `_VETTED_FALLBACK_RESPONSE`; step_policy hold/precedence *decision* (fail-closed). These substitute verbatim + bypass composition.

## Class-fix plan
- **Mechanism = DONE** (PR #298): `mandatory_caveat` + gate injection, generalizes to any step.
- **Per-skill caveat TEXT = clinical** (rows 1, 3-10): each verbatim caveat is doc-sourced (where the doc has it) or clinician-authored — goes to the clinician batch, like SG-2's L188. Priority: **row 1 (post-SI safety question)** and **rows 8-10 (no gate backstop)**.
- **Row 11 (dead escalation strings):** separate decision — wire L2/L3/L4 to real behavior or annotate them as documentation-only. Verify the "no runtime reader" claim first.
- **DoD upgrade (matrix legend):** every safety-copy row = content present + **behavioral firing test** + driven transcript.

## Standing rule (now in the matrix legend)
JSON-presence / content-contract tests are necessary but NEVER sufficient for safety copy; a green content-contract test is explicitly NOT evidence of firing. Third *per-layer-green-masks-end-to-end-miss* incident class after #191 (render seam) and #205 (affordance seam).
