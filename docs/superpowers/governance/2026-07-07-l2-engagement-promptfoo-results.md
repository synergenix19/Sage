# L2 Engagement PromptFoo Results — 2026-07-07

**Run:** `npx promptfoo eval` against the DRAFT templates (via `l2_promptfoo_prompt.py` shim), provider `openrouter:openai/gpt-4o` (temp 0.7 = prod responder), `--no-cache`. Key injected via `railway run` (prod OPENROUTER_API_KEY). Raw output: `docs/superpowers/drafts/2026-07-07-l2-eval-results.json` (eval id `eval-WAJ-2026-07-07T09:41:21`).

**Result: 4 / 5 passed (80%).** 12,183 tokens, 14s. Not gamed to green — the one failure is reported as-is because it is real, minor, and informative.

## Per-case verdicts

| # | Case | Verdict | Model output (opening) |
|---|---|---|---|
| 1 | Pure factual, grounded — bridge present, zero assumed distress | **PASS** | "Anxiety is the body's natural response to a perceived threat… 1. It is a normal part of life…" |
| 2 | Affect-laden query slipped as single-intent — conditional bridge lands, no assumed distress | **PASS** | "Anxiety can involve physical symptoms like chest tightness… Would you like…" |
| 3 | ABSTAIN — bridge as recovery, grounding intact, no fabrication | **PASS** | "I don't have specific clinical evidence on the success rate of EMDR… If you want to learn more or find spe…" |
| 4 | Negative — factual turn must not open with affect-assumptive sympathy | **PASS** | "Cognitive Behavioral Therapy, or CBT, is a structured approach that connects thoughts, feelings, and behaviors…" |
| 5 | List-directive compatibility — list may be used AND the single bridge still closes it | **FAIL** | "Anxiety can show up in several ways. Here are some common symptoms: 1. Racing thoughts… Is there something specific… you'd like to know more about?" |

## The one failure, precisely (this matters for the review)

Case 5 failed **one** sub-assertion. The rule-(a\*) core HELD: the same case passed both the "no affect assumption" rubric AND the "ends with one open invitation" rubric. It failed only this clause of the list-compat rubric:

> "The output includes a list but does not lead with a one-sentence plain answer."

So: on a pure symptom-list turn, gpt-4o went straight into the list under a meta lead-in ("Here are some common symptoms:") instead of leading with a one-sentence substantive answer first, as the L4 `light_structure_directive` requires. **This is a prompt-adherence signal about the L4 lead-with-prose instruction, not a failure of the info_request v2.0.0 bridge or its affect-neutrality.**

## Decision for the review session (not pre-patched)

Two legitimate resolutions, left to the reviewers rather than silently changed to force green:

1. **Reinforce** — add one clause to `info_request` v2.0.0: "When you use a list, lead with a one-sentence plain answer before the list." This duplicates the L4 directive at L2 for reliability. Low risk, aligns with rule (a\*).
2. **Accept** — decide a brief meta lead-in ("Here are some common symptoms:") before a symptom list is acceptable, and relax the test's lead-with-prose clause.

Either is a wording/clinical call. The eval did its job: it surfaced a real, specific adherence gap on the exact failure mode (list-compat) the cases were designed to probe. Re-run after the reviewers choose (1) or (2) to confirm 5/5.
