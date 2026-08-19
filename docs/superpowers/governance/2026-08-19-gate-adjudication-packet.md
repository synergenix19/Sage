# K1.5 — Gate Adjudication Packet (DRAFT — PRE-STAGING)

**Status:** DRAFT for owner ruling. This document makes recommendations only; the IN/OUT
decision on each suite is the owner's per the plan's K1.5 boundary ("The K1.5 in/out
adjudication of ungated suites is an OWNER decision — the plan produces the recommendation
packet, not the decision").

**Instrument:** detached worktree of `origin/master` @ `49f29d90` (head at census time; ancestor
of `55d92fba` "ci(gate): register safety_gate marker"). `PYTHONPATH=src`,
`.venv/bin/python -m pytest`, env `OPENROUTER_API_KEY=dummy-ci HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1`. Pass-state runs used `-m "not slow"` to match `unit-gate.yml`'s own
selection discipline (the gate never runs `@slow` tests); collected counts shown are the
gate-selected (not-slow) count per file unless noted.

**Baseline drift note:** the current `CANDIDATES` block in `.github/workflows/unit-gate.yml`
holds **83** files (not the 82 the K1.2 brief's task description used before the
testpaths-scoping-trap disclosure) — confirmed against `origin/ci/tag-safety-gate-suites`
(PR #515, head `64c4f854`, 83 files tagged, empty collected-ID diff vs the path-list). PR #515
is **open, not yet merged** — `master` still selects by path list, not by marker. `2274` is
K1.2's proven marker-selected collected count for the current 83-file CANDIDATES set.

---

## 1. Census: ungated safety-relevant suites

Pattern: filename matches
`safety|crisis|hr_|hr-|veto|redflag|tiering|screen|override|medical|harm|si_|passive|means|cardiac|psychotic|derealization`,
AND not in the 83-file CANDIDATES list. **27 files matched** (up from the ~21 of the prior
audit — the drift is real new suite creation: `test_grief_override.py`,
`test_selfworth_override.py`, `test_means_access_surface.py`, `test_veto_input_normalization.py`,
`test_derealization_flag.py`, `test_cultural_overrides_cross_concern.py`,
`test_modality_screen_foundation.py`, and `test_panic_override.py` all postdate the prior count;
`test_rules_safety.py` and `test_cardiac_escalation.py`, which the prior audit still listed as
gaps, are now IN CANDIDATES and correctly excluded here).

## 2. Per-file table

| # | File | Tests (not-slow) | Deterministic? | Pass state | Recommendation |
|---|------|------------------:|-----------------|------------|-----------------|
| 1 | `tests/test_crisis_affordance_decision.py` | 9 | Yes — pure decision fn extracted from `/chat` emit boundary, no LLM/network | 9 passed | **IN** — #205 crisis-card path-consistency backstop; no gated twin |
| 2 | `tests/test_crisis_boot_guard.py` | 5 | Yes — fail-closed boot-time placeholder resolution, no LLM | 5 passed | **IN** — guards the crash-on-unresolved-`{{crisis_*}}` invariant |
| 3 | `tests/test_crisis_config.py` | 2 | Yes — static code-site grep for hardcoded helpline digits | 2 passed | **IN** — cheap, high-value single-source guard |
| 4 | `tests/test_crisis_locale_parity.py` | 6 | Yes — boot-time EN/AR twin-existence check, no LLM | 6 passed | **IN** — closes the #329/#330 AR-bypass class at boot |
| 5 | `tests/test_crisis_resources_selection.py` | 6 | Yes — pure lead-logic over injected doc-like data | 6 passed | **IN** — H4 directory selection logic, no twin |
| 6 | `tests/test_crisis_smoke.py` | 1 (1 more `@slow`, deselected — real BGE-M3 S3 check) | Yes for the not-slow test (S1 keyword tier); the S3 test is real-model and excluded like every other `@slow` in the gate | 1 passed, 1 deselected | **IN** — thin but real regression smoke for the two pre-invite phrases; the deselected half is out of scope by the gate's own `-m not slow` discipline, same as every currently-gated suite with a slow tail |
| 7 | `tests/test_crisis_templating_byte_identical.py` | 16 | Yes (no LLM) | **3 FAILED, 13 passed** | **OUT (for now)** — currently RED: the byte-identical snapshot for `skills/psychotic_referral.json`, `skills/psychoed_depression.json`, `skills/post_crisis_check_in.json` no longer matches origin/master's pinned original (templating now emits `[STORED_ONLY ...]` prefixes on L2-L4 audit strings the snapshot doesn't have). Gating a suite that is red today would either red the gate on merge or force an unreviewed snapshot re-pin under this packet's authority, which is out of scope. Fix/re-pin first, then reconsider IN. |
| 8 | `tests/test_crisis_tiering.py` | 32 | Yes — resolver unit tests over `tier_routing.json`, no model | 32 passed | **IN** — W1-core v7.1 §5.1 OR-fusion tiering, no twin |
| 9 | `tests/test_cultural_overrides_cross_concern.py` | 4 | Yes — `AsyncMock`/`patch`-mocked composer calls | 4 passed | **IN** — Phase C cross-concern injection/non-injection guard |
| 10 | `tests/test_dbt_tipp_safety_caveat.py` | 3 | Yes | 3 passed | **IN** — signed cardiac/pregnancy contraindication caveat on the most-used acute skill; highest clinical-severity item in this census |
| 11 | `tests/test_derealization_flag.py` | 18 | Yes | 18 passed | **IN** — §1c CF-010 both-direction fixtures (fires/doesn't-fire), Vee 1a-1d signed 2026-07-21 |
| 12 | `tests/test_entry_screen_behavioral.py` | 28 | Yes — behavioral acceptance criteria, LLM path exercised via mocked error injection | 28 passed | **IN** — entry-screen contraindication-hold acceptance criteria; complements `test_medical_screen*` (gated) which covers a different surface |
| 13 | `tests/test_entry_screen_integration.py` | 0 selected (18 deselected — entire file is `pytestmark = pytest.mark.slow`) | **No** — docstring: "against the real LLM (OpenRouter) with NO mocking" | n/a under gate filter (0 collected not-slow) | **OUT** — live-LLM adversarial suite by design; architecturally excluded from any deterministic gate the same way every other `@slow` file is |
| 14 | `tests/test_grief_override.py` | 9 | Yes | 9 passed | **OUT (pending)** — docstring: "S2a ... BUILT INERT (2026-08-04); boundary sheet pending Vee." Flag default OFF. Green and deterministic, but encodes an unratified clinical boundary; gate it once Vee signs (mirrors `test_panic_override.py`'s already-signed twin) |
| 15 | `tests/test_harm_intrusive_veto.py` | 23 | Yes | 23 passed | **IN** — Stage 1 Clinical Containment Pathway, arm-independent veto, approved precedent (mirrors the already-gated OCD veto) |
| 16 | `tests/test_means_access_surface.py` | 10 | Yes | 10 passed | **OUT (pending)** — docstring: "DRAFT, gated on Vee signature (packet item 1, due 2026-08-25)." This is the MSK-02 live-prod-miss fix (Safety Detection Baseline memory item); green and deterministic but explicitly awaiting the same Vee ruling this packet is staged ahead of |
| 17 | `tests/test_modality_screen_foundation.py` | 12 | Yes | 12 passed | **IN** — EMR Phase 2 screening state machine, includes signed-copy pin test; no twin |
| 18 | `tests/test_ocd_compulsion_veto.py` | 27 | Yes | 27 passed | **IN** — approved expedited hotfix (2026-07-07 escalation), arm-independent; AR twin `test_ocd_compulsion_ar_330.py` already gated, this is the EN base and is not redundant with it |
| 19 | `tests/test_panic_override.py` | 12 | Yes | 12 passed | **IN** — §1c panic-grounding override, **Vee-signed 2026-07-28** (already ratified, unlike its grief/self-worth siblings below) |
| 20 | `tests/test_post_crisis_classifier.py` | 8 | Yes — `resilient_invoke` fully `patch`-mocked on every path, including the LLM-fallback path | 8 passed | **IN** — S7 post-crisis classifier tier; no twin |
| 21 | `tests/test_psychotic_referral_skill.py` | 3 | Yes — static skill-registry/content checks | 3 passed | **IN** — pins the helpline number verbatim in the psychotic-referral skill content; distinct surface from `test_skill_select_psychotic.py` (already gated, routing not content) |
| 22 | `tests/test_rules_safety_psychotic.py` | 20 | Yes — calls `_eval_safety()` directly | 20 passed | **IN** — CF-006 psychotic_disclosure detection; confirmed no overlap with gated `test_rules_safety.py` (that file has zero CF-006/psychotic coverage) |
| 23 | `tests/test_safety_detection.py` | 78 (70 passed + 8 xfailed by design — known FN gaps, not failures) | Yes — Arabic translation mocked to a benign phrase, no live LLM | 70 passed, 8 xfailed, 0 failed | **IN — highest-value single item in this census.** Unified SF-1 (passive SI/veiled ideation) + SF-6 (false positive) hard-gate through the full `safety_check_node` pipeline; nothing else in CANDIDATES exercises this pipeline end-to-end at this density |
| 24 | `tests/test_safety_node_integration.py` | 20 (1 more `@slow` — real S3/BGE-M3 — deselected) | Yes for the 20 — docstring: "Arabic translation is mocked throughout so no live LLM calls are made" | 20 passed, 1 deselected | **IN** — node-level integration (language detection → rules → flags → state), explicitly contrasted in its own docstring with gated `test_rules_safety.py` (engine-only) and gated `test_nodes.py` (smoke only); this is the missing middle layer |
| 25 | `tests/test_safety_precedence.py` | 9 | Yes | 9 passed | **IN** — B0 deterministic Node-1 safety-route precedence resolver (crisis/medical/HR/IPV ordering); foundational, no twin |
| 26 | `tests/test_selfworth_override.py` | 19 | Yes — `resilient_invoke` monkeypatched on every exercised path | 19 passed | **OUT (pending)** — docstring: "S4b ... DRAFT, gated on Vee signature (packet item 3, due 2026-08-25); flag default OFF." Same pending-signature status as items 14 and 16 |
| 27 | `tests/test_veto_input_normalization.py` | 11 | Yes | 11 passed | **IN** — F2 fix (code_review.md 2026-08-17): closes the U+2019/ZWSP silent-veto-disarm class across OCD/IPV/harm-intrusive lexicons |

**Failed-when-run:** only `tests/test_crisis_templating_byte_identical.py` (3 of 16 tests
failed; itemized above). Every other file in the census is currently green under the gate's own
`-m "not slow"` discipline.

## 3. Special item: `test_crisis_config_cross_stack.py`

This file **is already in CANDIDATES** (line 174 of `unit-gate.yml`) — it is not part of the
27-file census above — but its own in-repo comment records that it **skips, not blocks**, in CI:
it only runs its assertions when a `../cdai` checkout is present next to this repo, which CI does
not currently provide. Today it is a no-op skip that reads as coverage but provides none — a gate
entry that is green by construction, never by verification.

Three options (owner picks):

- **(a) Vendor the cdai constant.** Copy the frontend's `CRISIS_RESOURCES` array (or a generated
  snapshot of it) into `sage-poc` with a sync-check script that fails when the vendored copy drifts
  from the upstream `cdai` source. Cost: a new sync-check surface to maintain across two repos;
  the check can itself go stale if the vendoring script is never re-run.
- **(b) Add a cdai checkout step to the CI job.** `actions/checkout` a second repo into `../cdai`
  before the gate runs. Cost: couples this repo's CI to another repo's default branch and access
  (cross-repo checkout auth, a second repo's flakiness becomes this gate's flakiness); makes the
  "MERGE-BLOCKING" claim in the file's own docstring actually true for the first time.
- **(c) Explicit OUT with a recorded reason.** Remove it from CANDIDATES (or leave it but document
  the skip as accepted debt) rather than let a skip masquerade as coverage. Cost: the cross-stack
  crisis-number divergence this test exists to catch (H4) goes back to being caught only by manual
  review or a live-probe readback, not CI.

**Owner's stated preliminary lean:** "a gate entry which skips in CI is worse than an honest
exclusion" — this favors (c) unless (b) is cheap enough to wire before the next crisis-copy change,
or (a) is preferred to avoid the cross-repo CI coupling. Not adjudicated here.

## 4. Totals

- **IN-recommended: 22 of 27** (5 OUT: 1 currently red — `test_crisis_templating_byte_identical.py`;
  1 architecturally live-LLM — `test_entry_screen_integration.py`; 3 pending Vee clinical
  sign-off due 2026-08-25 — `test_grief_override.py`, `test_means_access_surface.py`,
  `test_selfworth_override.py`).
- **Tests added if all 22 INs are adopted: 337** (gate-selected, `-m "not slow"` count per file,
  summed: 9+5+2+6+6+1+32+4+3+18+28+23+12+27+12+8+3+20+78+20+9+11 = 337).
- **Projected gate size:** 2274 (current K1.2-proven marker-selected count) + 337 = **2611**.
- **Resulting `.github/gate_floor.txt` value:** **2611** — i.e., once K1.3 flips selection to the
  `safety_gate` marker and these 22 files are tagged and added, K1.4's floor-recording step
  (`Record the current marker-selected collected count ... into gate_floor.txt as a single
  integer`) would record 2611, not 2274. If the owner accepts fewer than all 22, the floor is
  2274 + (sum of tests in the accepted subset) — recompute from the per-file counts in §2 rather
  than re-deriving 2611.

Three of the five OUTs (`test_grief_override.py`, `test_means_access_surface.py`,
`test_selfworth_override.py`) are green and deterministic today and would each raise the floor
further the moment Vee signs (2026-08-25 window) — 9 + 10 + 19 = 38 additional tests, projecting
to 2649 if all three land after this packet's 22.


## Exhibit A (owner directive 2026-08-19): the ungated-red-pin case for a generous IN ruling

`test_crisis_templating_byte_identical.py` sat silently RED on master since ~2026-07-14: commit 179016d7 (owner-authored, documented, legitimate) added [STORED_ONLY] annotations to three skill files, and the byte-identity snapshot was never re-pinned — because the test was UNGATED, nobody saw it break for five weeks. Provenance traced 2026-08-19: the change was authorized; the pin was stale (repin PR with provenance in flight). The systemic point stands regardless: an ungated safety pin silently red on master is the exact failure K1.4's fatal-miss design exists to prevent. Every OUT ruling below leaves a suite in this blind spot.

---

## Owner rulings 2026-08-19

This section is the durable record of the decisions the packet above staged. It is the primary
source both `.github/workflows/unit-gate.yml`'s marker-selection rationale comment and
`tests/test_crisis_config_cross_stack.py`'s honest-OUT comment cite. Executed IN batch:
**PR #532** (`ci(gate): tag adjudicated-IN ungated safety suites with safety_gate`). Executed
cross_stack OUT: **this PR** (`ci/gate-marker-selection`, K1.3).

- **A1 — §4 totals, approved WITH EDIT.** The packet's 22-of-27 IN recommendation is approved,
  **plus** `test_crisis_templating_byte_identical.py` (item 7, packet-time OUT for being red) —
  by the time of this ruling it had been provenance-traced and re-pinned green (16/16, see
  Exhibit A and PR #527). Ruling: leaving the exhibit itself ungated would be absurd — the whole
  point of Exhibit A is that an ungated byte-identical pin is precisely the blind spot K1.4
  exists to close; shipping K1's fatal-floor gate while its own motivating example stays outside
  it is incoherent. **Final: 23 IN / 4 OUT** (not the packet's 22/5). Floors are RECOMPUTED at
  tagging time from actual collected counts, never copied from this packet's projected 2611/2649
  — those were staged before real drift (new tests added to master between packet-authoring and
  execution moved the true baseline).
- **A2 — §3 special item, cross_stack, option (c) approved.** "An entry that skips in CI is a
  gate lying about its own coverage" — the no-op skip is removed from marker selection with a
  recorded reason in the test file, rather than kept as false-positive coverage. Revisit as
  vendor-the-constant (option a) only on an actual cross-stack drift incident — not preemptively,
  and not via option (b)'s cross-repo CI coupling.
- **The 3 pending-Vee OUTs** (`test_grief_override.py`, `test_means_access_surface.py`,
  `test_selfworth_override.py`, due 2026-08-25) are not decided here — they stay OUT under this
  ruling. Disposition on signature: each **auto-flips IN via a one-line floor PR** (add the
  `safety_gate` mark to the one file, raise `.github/gate_floor.txt` by that file's collected
  count) — no re-adjudication needed, since the packet's per-file analysis already stands; only
  the Vee signature was pending.
- **Live-LLM OUT is permanent.** `test_entry_screen_integration.py` (item 13) stays
  architecturally OUT — it is `@pytest.mark.slow` by design (real OpenRouter, no mocking), the
  same class every other `@slow` file is excluded from this deterministic gate for. Not a
  pending decision; there is no future ruling that flips this one.
