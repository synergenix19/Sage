# Ticket: `test_psychotic_referral_skill.py` (loader for the psychosis referral) was NOT in the required gate

**Found:** 2026-07-17, during the HR-1 §5 neutrality interim deploy.

**The hole.** The `psychotic_referral` terminal is the highest-stakes clinical artifact class (it is
the referral carrying live psychosis/mania/dissociation traffic post-HR-1-flip). Its loader test
`tests/test_psychotic_referral_skill.py` was **absent from the required "Safety-surface unit tests"
gate's CANDIDATES list** (`.github/workflows/unit-gate.yml`). Only `test_skill_select_psychotic.py`
(routing) was gated — not the loader.

**Why it matters (silent vs visible failure).** When the §5 neutrality interim edited
`psychotic_referral.json`, CI-green did NOT cover the edit — only a manual `.venv` run of the loader
test did. A copy drift is sampled-and-visible; **a loader test that is not gating is invisible until
something breaks in prod.** An edit that broke the skill's JSON/load path could have merged green.
Fix the thing that fails silently before the thing that fails visibly.

**Fix (this PR).** Added to the gate CANDIDATES:
- `tests/test_psychotic_referral_skill.py` (loader: registry membership, skill loads, keyword/semantic
  skip behaviour)
- `tests/test_rules_safety_psychotic.py` (the CF-006/CF-009 psychotic-rule tests for the same surface)

Both pass in the project venv (`pip install -e ".[dev]"` provides `sentence_transformers`, which the
gate installs, so the session-scoped BGE warmup fixture resolves in CI). Neither carries a `slow`
marker, so the gate's `-m "not slow"` does not strip them.

**Follow-up (broader):** audit whether other safety-terminal LOADER tests (crisis_response,
medical_response, high_risk terminals) are gated, not just their routing tests. Same silent-hole class.

## ⚠️ FIRST-FIRING TRIPWIRE — verify the gate fix RUNS, not just that it's configured

This PR (#350) touches only `.github/` + this ticket, so the gate's own docs/.github path-filter
SKIPS install+pytest and succeeds in ~5s WITHOUT running anything. So the fix is **config-verified,
not run-verified** — the added tests have never executed under the gate. (Same family as the SHA
self-report lie: the check went green without doing the thing.)

**Action for the NEXT app-code PR that trips the full gate:** open its "Safety-surface unit tests"
job log and CONFIRM `tests/test_psychotic_referral_skill.py` and `tests/test_rules_safety_psychotic.py`
appear in the "Running existence-filtered suites:" line AND in the pytest collection/pass output.
Do NOT accept a green check as proof — the failure mode is the gate silently NOT collecting the newly
added file (path-filter/file-list subtlety), which looks identical to green. Config-correct ≠
run-correct. Close this ticket only after that first live firing shows the tests actually ran.
