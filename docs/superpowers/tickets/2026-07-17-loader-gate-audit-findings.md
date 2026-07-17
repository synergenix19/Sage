# Loader-gate audit — do safety-terminal loader/definition tests run in the required gate?

**Origin:** the psychosis-referral loader test (`test_psychotic_referral_skill.py`) was found ABSENT
from the required "Safety-surface unit tests" gate (fixed in PR #350). Hypothesis: the crisis/medical/
high-risk terminals — carrying 999/998 traffic — likely have the same ungated-loader hole. **Audited
2026-07-17. Hypothesis CONFIRMED, and worse than expected on the medical terminal.**

Method: enumerated safety-terminal tests, checked gate CANDIDATES membership, ran each ungated
candidate under the gate's exact env (`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OPENROUTER_API_KEY=dummy-ci`)
to confirm gate-eligibility (deterministic) vs live-dep. Verified, not inferred.

## Findings (priority order)

### 🔴 P0 — `test_medical_redflag_guard` is UNGATED **and RED on master**
The EN medical red-flag guard (998 ambulance terminal). Its Arabic sibling `test_medical_redflag_ar_329`
IS gated; the EN guard is not. Worse: `test_honesty_notes_ship_verbatim` **fails in both the stub env
and the real-model env** — it asserts the stale string `"ZERO native Arabic"`, but #329 (2026-07-16)
changed that honesty note to `"INTERIM native Arabic layer…"`. **The test drifted red because it is
ungated** — had it been in the gate, #329 would have been forced to update it or been blocked. This is
the silent-failure class exactly, on the highest-stakes terminal.
- Root cause is also an **assert-on-PROSE** test (anchored on a copy string, the drift-prone pattern
  the standing rule forbids). Fix = re-anchor `test_honesty_notes_ship_verbatim` on BEHAVIOR (the guard
  fires on cardiac + passes raw+message_en, which the file's other 20 tests already assert), or delete
  it if fully redundant — clinician/owner call on a safety test, do not silently string-swap.
- **Sequence:** re-anchor/fix the red test FIRST, then add the file to the gate. Gating it red would
  deadlock; string-swapping it green repeats the prose-assert anti-pattern.

### 🟢 P1 — three ungated deterministic safety tests, GREEN under the gate stub, safe to gate now
Verified pass under the gate's offline env:
- `test_218_ocd_erp_referral.py` — pins the **signed** ERP professional-referral copy verbatim at
  output_gate (Node 8). A signed clinical field with no gate on its test.
- `test_crisis_config.py` — guards that code-sites (graph.py, output_gate.py) reference the crisis
  number via the config constant, never re-embed digits. Crisis-number integrity, ungated.
- `test_skill_schema.py` — skill loader/schema (27 tests, `load_skill(...)`). The generic loader-class
  coverage that would have caught a broken skill JSON.

### ✅ fix-in-flight — psychosis loader (PR #350)
`test_psychotic_referral_skill.py` + `test_rules_safety_psychotic.py` added to the gate in #350
(config-verified; first-firing tripwire pending — see that ticket).

### Legitimately ungated (not gaps — recorded so they are not re-flagged)
`test_wrong_skill_routing`, `test_skill_routing_v2`, several `test_skill_*` — need live OpenRouter/DB
(the gate's stated ~53-test live-dep exclusion). `test_skill_ids` — covered by ferry-gate, not unit-gate.

## Remediation in this PR
Gate the three P1 green tests. P0 (medical) is filed for re-anchor-then-gate — NOT gated here because
it is red; gating it now would deadlock the required check. Broader principle for the backlog: a
LOADER/definition test for any safety terminal must be in the gate, and prose-anchored safety asserts
should be re-anchored on behavior (the medical red is the object lesson).
