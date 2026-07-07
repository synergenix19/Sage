# L2 Engagement PromptFoo Results — 2026-07-07

**Run:** `npx promptfoo eval` against the DRAFT templates (via `l2_promptfoo_prompt.py` shim), provider `openrouter:openai/gpt-4o` (temp 0.7 = prod responder), `--no-cache`. Key injected via `railway run` (prod OPENROUTER_API_KEY). Raw output: `docs/superpowers/drafts/2026-07-07-l2-eval-results.json` (eval id `eval-WAJ-2026-07-07T09:41:21`).

**Result: 4 / 5 passed (80%).** 12,183 tokens, 14s. Not gamed to green — the one failure is reported as-is because it is real, minor, and informative.

**RATIFIED 2026-07-07 (clinical lead): ACCEPT.** The list-compat case is rewritten to encode the accepted behaviour (a symptom list may open without a one-sentence prose lead-in; the bridge and affect-neutrality are still asserted). This is **not "issue closed":** the lead-with-prose concern (an L4 `light_structure_directive` matter) is **DEFERRED to the Falcon-34B re-run** as a named case, because list-formatting adherence is highly model-specific and the eval ran on GPT-4o while production renders on Falcon-34B+LoRA. If Falcon also skips the prose lead-in, reinforce `light_structure_directive` then — with evidence from the actual production model, its own L4 version bump, and the manifest guard. Reinforce-in-L4 is Option 2 deferred to the moment it is meaningful, not rejected.

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

The lead-with-prose instruction is **L4 content** — it lives in `light_structure_directive`, which fires only when knowledge passages are present. Per v7 §5.6.2 an instruction has a single owning layer; duplicating it into L2 is prohibited ("repeating instructions wastes tokens without improving compliance") and blurs the single-ownership that made this whole bug traceable. A future editor tuning list behaviour must have exactly one place to look. So the resolution is between exactly two options:

1. **Accept** — a symptom list may arrive without a one-sentence prose lead-in. Lowest cost. The clinically load-bearing invariants (bridge present, zero assumed affect, ABSTAIN recovery, no fabrication) ALL passed on this same case; this is a formatting preference, not an engagement or safety failure.
2. **Reinforce in L4** — strengthen the wording of `light_structure_directive` itself. This is a separate one-line change to the **L4 template**, with its own version bump and manifest-adjacent traceability, landing in this same batch. The `info_request` v2.0.0 **L2 draft stays untouched.**

**Not an option: reinforce in L2.** Duplicating the L4 directive into the info_request template violates §5.6.2 single-ownership.

### Two notes for the session
- **Model-transfer caveat (applies with force here).** List-formatting adherence is among the most model-specific behaviours there are, so tuning L4 wording to GPT-4o's adherence profile has limited transfer to Falcon-34B. If option 2 is chosen, the Falcon re-run follow-up must cover THIS list-compat case specifically.
- **Do not move this to the output gate.** The gate enforces safety and cultural rules; loading it with a cosmetic lead-with-prose check dilutes its audit purpose. A formatting preference stays in the L4 prompt directive, never the gate.

### Test disposition by decision (the suite must neither lie nor lose coverage)

The session's choice maps to a defined disposition for the list-compat case — it is not left red or silently deleted:

- **If reinforce-in-L4 (option 2):** apply the one-line `light_structure_directive` change, then **re-run the eval to confirm the case reaches 5/5.** (And, per the model-transfer note, the Falcon-34B re-run must cover this list-compat case specifically.)
- **If accept (option 1):** **rewrite the list-compat case** to encode the accepted behaviour — a symptom list without a prose lead-in is a PASS, while still asserting the bridge is present and affect-neutral. Not left failing (the suite would lie), not deleted (list-compat coverage would be lost). The case keeps testing the load-bearing invariants; only the lead-with-prose sub-assertion is dropped to match the ratified behaviour.
