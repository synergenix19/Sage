# info_request Turn-Aware — Full-Graph Eval Results — 2026-07-07

**Method (the standing gate, satisfied):** compose_prompt (branch v2.1.0 templates) → **live generation** (prod responder `openai/gpt-4o` via OpenRouter, key injected by `railway run`) → the **real** output_gate question-discipline helpers (`_limit_to_one_question`, `_strip_trailing_question`, `_strip_output_format`). This deliberately runs generation *through* output_gate — the seam a PromptFoo LLM-only eval cannot see, and the exact blindness that let v2.0.0's bridge score 4/5 in isolation while prod amputated it. Harness: `docs/superpowers/drafts/2026-07-07-info_request-fullgraph-eval.py`. Not gamed to green.

**Result: 3 / 3.** Assertions applied to the POST-GATE text (these are the rewritten Gap-2 rubrics):

| Scenario | prev_intent | Post-gate | Verdict |
|---|---|---|---|
| first_turn ("what is anxiety") | none | 1 question, survives gate, no dash | **PASS** |
| first_after_detour | general_chat (reset) | 1 question, survives gate, no dash | **PASS** |
| repeat_lookup ("symptoms of anxiety") | info_request | 0 questions (statement), no dash | **PASS** |

Representative closes (verbatim, post-gate):
- first_after_detour → *"Are you asking about anxiety for yourself or just wanting to understand more about it generally?"* (the Abby triage question, surviving the gate — the whole point).
- repeat_lookup → *"If you want to know more or explore how this fits into your experience, I'm here for you."* (statement, no question).

**What this proves and does not.** Proves end-to-end that (a) the D4 amendment lets the clarifying question survive output_gate on first turns, and (b) the repeat variant renders a statement with zero questions — the two behaviors the ruling requires, through the real gate. It does **not** prove Falcon-34B behavior: this ran on GPT-4o (prod responder today), and per the standing **GPT-4o → Falcon-34B transfer caveat**, generation-shape adherence is model-specific; the Falcon re-run must cover these three scenarios specifically. Deterministic evidence (243 unit tests: detector amendment, variant selection, strip-scope pin EN+؟) remains the guard against silent regression.

**Gap-2 note.** The PromptFoo LLM-only harness/yaml from the earlier batch is **superseded** for this change: its provider cannot reach output_gate, so its assertions could not test survival. The rewritten rubrics live here, applied post-gate. If a PromptFoo run is still wanted for CI parity, it must use a custom provider that wraps compose→LLM→output_gate (tracked, not blocking).
