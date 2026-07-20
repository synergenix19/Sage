# D1 enforce-flip attempt — CAUGHT BROKEN, rolled back (#338)

**Status: FLIP ATTEMPTED 2026-07-20, caught broken by the first-screened-turn probe, HALTED via the
pre-authorized lever. Prod restored to the proven-safe shadow state (enforce=False, converged 8/8). ZERO real
users affected.** The flip is NOT verified; it does not stand.

## What happened
On Vee's (c) ruling, the frozen flip checklist ran: migration 015 applied + verified, lock claimed, flag set,
redeploy, `/health` readback converged 8/8 to enforce=True. Then the **first-screened-turn probe caught a
real bug**: an acute-overwhelm turn served a generic freeflow offer, NOT the screen question — while the audit
row recorded `screen_asked=True`. So the mechanism DECIDED to screen but the graph did not SERVE the screen.

## Root cause — the SG-2 seam class, live only in the full graph
`screen_question_text` is **NOT a declared SageState channel**. `apply_screen_at_route` (inside skill_select)
sets it on an ask_screen decision; LangGraph **drops undeclared channels between nodes**, so by the time
`_route_after_skill_select` reads `state.get("screen_question_text")` it is gone → the router falls through to
freeflow → a generic response is served instead of the screen. A second, related seam: the answer-turn
classification only runs if the answer reaches `apply_screen_at_route`'s call site in skill_select, which a
non-skill-matching answer ("no, same as always") does not — so the answer turn recorded no branch.

## Why every upstream check missed it (the honest part)
- **check_state_channels passed** — it detects channels written in NODE modules, but `screen_question_text`
  is written by a dict-return in a HELPER module (`medical_screen.py`). Static-gate blind spot.
- **Unit tests passed** — they set `screen_question_text` directly in the input dict, bypassing the
  channel-drop entirely.
- **The router test passed** — `test_router_sends_served_question_to_screen_terminal` passes the key inline,
  again bypassing the drop.
- **The one graph test that exists** drove crisis-mid-hold (a deterministic bypass) — never the serve→answer
  path through the compiled graph with the checkpointer, which is the only place the drop manifests.
- **The behavioral probe caught it** — exactly the "verify behavior, the SHA/audit/green-suite can lie"
  discipline. The audit said `asked=True`; the served bytes said otherwise. Behavior won.

## Rollback (pre-authorized halt lever, fired immediately)
`SAGE_D1_SCREEN=false` → redeploy → **enforce=False converged 8/8**. Shadow route-identity restored;
acute-overwhelm now serves TIPP with its SG-2 delivery-side caveat (status quo ante), no D1 screen served.
No code rollback needed — the enforce path is unreachable with the flag off, as designed.

## Impact
**ZERO real (non-test) users hit the enforce path** during its ~15-min live window (query: 0 non-synthetic
sessions with screen_asked=true) — consistent with the measured 0-TIPP-in-3-days base rate. And the bug's
failure mode was *toward not serving TIPP* (generic freeflow), so even the synthetic hits had no
contraindicated exposure. Fail-safe held even in the break.

## Fix (next increment, TDD — before any re-flip)
1. **Declare `screen_question_text`** as a SageState channel (per-turn). The immediate root cause of the
   serve-drop.
2. **Fix the answer-turn seam:** guarantee `apply_screen_at_route` classifies an answering_screen turn even
   when the answer matches no skill (resolve in skill_select unconditionally on `answering_screen`, or a
   dedicated resolve step) — so clear_no resumes, disclosure/evaded route to grounding, on the real graph.
3. **Add the MISSING test:** a real end-to-end compiled-graph test (checkpointer) driving serve→answer for
   each branch — the test whose absence let this ship. Deterministic terminals where possible; the branches
   that need the LLM are asserted via the audit row, not response prose.
4. **Harden `check_state_channels`** to detect channels written via helper-module dict-returns (close the
   static-gate blind spot so this class fails CI next time, not prod).

## Re-flip gate (unchanged authorities, one added precondition)
Vee's (c) ruling STILL HOLDS (mechanism-proven-live + zero-breach) — but "mechanism proven live" now
explicitly requires the serve→answer path driven end-to-end on the real graph, which this incident proved was
never actually established. Re-flip only after the fix lands + a fresh first-screened-turn probe passes ALL
branches live. No new clinical ruling needed; the evidence bar Vee already set simply wasn't met yet.
