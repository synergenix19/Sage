# FINAL REVIEW — fix/psychoed-resolver-reachability (3 commits off master 9c762759)

- **Reviewer:** whole-branch adversarial review, 2026-08-15
- **Verdict: FINDINGS-FIRST.** One HIGH finding (F-1) that the branch's own 66 pins cannot see
  because the test harness's intent_route mock is unfaithful to the real node's contract. The
  routing delta itself is sound; the crisis surface is provably untouched; the do-not-widen
  verdict holds. F-1 must be fixed (and re-pinned with a faithful mock) before merge.

## Method

Full diff read (`git diff 9c762759..HEAD`, +597/-0, 5 files). Master comparator snapshotted
from `git show 9c762759:src/sage_poc/graph.py` and diffed mechanically. All claims below marked
VERIFIED were re-derived or re-run in this worktree (`.venv/bin/python`,
`OPENROUTER_API_KEY=dummy-ci HF_HUB_OFFLINE=1`, no live LLM calls). The decisive F-1 evidence
is a pytest probe run under the branch's own conftest, with the intent_route mock made faithful
(stamping `gate_path` exactly as the real node does); probe deleted after the run.

---

## FINDINGS

### F-1 — HIGH — scope_refusal HIT path is broken in the real graph; the branch's pins pass only because the mock omits intent_route's gate_path stamp

**The mechanism.** The real `intent_route_node` stamps `gate_path = "scope_refusal"`
unconditionally on every scope_refusal-classified turn
(`src/sage_poc/nodes/intent_route.py:359-360`). Nothing on the new serve path clears it:
`skill_select_node`'s resolver-hit delta (`src/sage_poc/nodes/skill_select.py:824-833`) does
not touch `gate_path`, nor do `knowledge_retrieve` or `freeflow_respond`. At the gate,
`output_gate_node` replaces the composed response with the clinician-authored refusal copy
whenever `gate_path == "scope_refusal"` (`src/sage_poc/nodes/output_gate.py:663-664`).

**Observed behavior (reproduced experimentally, full graph, faithful mock):**

1. **Menu-first hit (`block_id is None`) — the serve is silently destroyed.** The refusal copy
   ships to the user, while final state records `psychoed_active_category`,
   `psychoed_matched_row_id`, `psychoed_menu_offered=True` — a serve recorded that never
   happened. The Node-8 verbatim hash gate cannot rescue it because it is keyed on a block_id
   (`src/sage_poc/nodes/output_gate.py:951-952`). The next turn's reply will be interpreted by
   the resolver's `active_category` menu-pick branch against a menu the user never saw.
   **2 of the branch's own 3 scope_refusal evidence rows are menu-first**: F1-1f-t3-01
   ("do I have GAD") and F1-1f-t3-02 ("do I have panic disorder") both resolve with
   `block_id=None`. The fix's own evidence base fails live for these rows.
2. **Answer-first hit (the 3rd row, F1-3c-t5-01; also the suite's TRIGGER_3C) — the serve
   survives only by accident, through an alarm channel.** output_gate first substitutes the
   refusal copy, then the psychoed verbatim hash gate detects the ratified block is missing
   from the final response and re-serves the pinned recomposition via its MISMATCH branch
   (`src/sage_poc/nodes/output_gate.py:986-996`) — logging
   `psychoed_integrity_incident kind=mismatch` at ERROR **on every such serve**. That channel
   exists to detect ratified-copy corruption; a routine intent label now fires it (false-alarm
   load on a safety observability channel, and `psychoed_gate_action="reserved"` skews the
   drift-rate metric). The audit row carries `gate_path="scope_refusal"` on a psychoed-served
   turn — an incoherent record.

**Why 66/66 pins pass anyway.** `_run_turn`'s `_mock_intent_route`
(`tests/test_psychoed_reachability.py:362-370`, and the carry variant) returns
primary_intent/confidence/etc. but **omits the `gate_path` stamp the real node always writes
for scope_refusal/jailbreak**. Under the mock, `gate_path` stays None and output_gate treats
the turn as standard. Probe result side-by-side (same phrase, same graph, only the stamp
differs): unstamped = serve, clean; stamped = the two behaviors above. This is exactly the
mock-fidelity failure class the CI-tier/flip-tier divergence that opened Ticket A came from.

**Consequences for the pins as evidence:** the reachability pins (suite section 1), the
51-row taxonomy sweep (section 6), and the scope_refusal no-hit byte-identity pin all run
under the unfaithful mock. (The no-hit byte-identity comparison additionally compares
empty-fallback-vs-empty-fallback for scope_refusal — with gate_path None and no response, the
RC-6 fail-safe fires on both sides — rather than refusal-copy-vs-refusal-copy. The null-case
property itself is still real; see "Verified" below.)

**Scope note (fairness):** the same clobber class pre-exists on master via the weave-pending
path — a `psychoed_menu_after_weave` continuation on a scope_refusal-labeled reply would also
be clobbered at the gate (no block_id, no rescue). The branch did not create the class; it
widened the exposed surface from that corner case to every scope_refusal trigger hit, and its
DoD claims the widened path works. The branch's weave pin escapes it only because the
escalation outcome overwrites `gate_path="crisis"`.

**Required before merge:** (a) decide and implement where the resolver-claimed turn sheds the
scope_refusal gate stamp — clearing/overriding `gate_path` in the resolver-hit delta, or
making output_gate's scope_refusal substitution yield to a psychoed serve (a Node-8
precedence decision; arguably needs the same human ruling discipline as the rest of this
ticket); (b) make the test mock stamp `gate_path` exactly as `intent_route.py:359-360` does,
so the pins run against the real contract; (c) re-check the answer-first path no longer logs
integrity incidents, and the menu-first path serves the menu.

### F-2 — MEDIUM — residual reachability gap: general_chat below the confidence gate still never reaches the resolver, and the record cannot size it

`_route_after_intent_base` returns `"low_confidence"` for general_chat with
`intent_confidence < 0.6` (`src/sage_poc/graph.py:480-481`), which is not in
`_PSYCHOED_TRANSIT_ORIGINS`, so such turns still bypass Node 4. `intent_confidence` is the
probabilistic router's own output — the ticket's principle ("deterministic recognition is
never conditional on the probabilistic router") remains violated for this slice. The
committed console log has **no per-row confidence**, so the size of this residue inside the
48 general_chat evidence rows is unmeasurable from the record; the CI sweep pins
`confidence=0.9` (`tests/test_psychoed_reachability.py:71`, default in `_run_turn`), so CI is
structurally blind to it. scope_refusal is unaffected (its branch precedes the confidence
gate). Not necessarily in the 2026-08-11 ruling's scope — but it is currently **undocumented**
in the branch's comments, assessment, and report, which present general_chat+scope_refusal as
"100% of the observed unreachable set." At minimum: document the boundary, and let the DoD
live re-run quantify it (per-row confidence should be added to the runner's output if cheap).

### F-3 — LOW/MEDIUM — unpriced flag interaction: VENTING_SUPPRESSION × transit

A venting-detected general_chat turn's base destination is freeflow via F6's suppression
branch (`src/sage_poc/graph.py:436-440`), so it is transit-eligible. With both
`SAGE_VENTING_SUPPRESSION` and psychoed on, a trigger phrase inside a "just listen" turn now
serves a psychoeducation block — overriding a branch whose entire purpose is routing
authority for "don't fix, listen." This is the same decision class the assessment doc itself
treats as needing its own ruling for exit_skill ("a block served in response to asking to
stop"). No live exposure today (flag default false, `src/sage_poc/config.py:395`), and
deterministic-recognition-wins is a defensible reading of §2.1 — but the interaction is
nowhere assessed or priced. Should be named in the assessment doc (or the ticket) with a
one-line ruling, not discovered later in prod.

### F-4 — LOW — mock-fidelity generalization

Both `_run_turn` variants share the unfaithful intent_route mock (F-1's carrier). When fixing
F-1(b), sweep the whole file: any pin whose label is scope_refusal or jailbreak must run with
the stamp. Consider asserting mock fidelity structurally (e.g., derive the mock's return from
the real node's post-classification stamping logic) so the next intent_route contract change
cannot silently de-fang these pins again.

---

## VERIFIED CLEAN (each item independently re-derived, not taken from the report)

1. **Crisis routing is provably untouched.**
   - `_route_after_intent_base` is **byte-identical** to master's `_route_after_intent`
     (mechanical body diff against `git show 9c762759:src/sage_poc/graph.py`).
   - The widening (`src/sage_poc/graph.py:322-328`) can only redirect a turn whose base
     destination is `freeflow`/`gate` (`psychoed_transit_destination`,
     graph.py:297-319): `intent=="crisis"` returns `"crisis"` from the base router and is not
     in `_PSYCHOED_TRANSIT_INTENTS`; the panic/grief overrides return `"skill_select"`
     (not a transit origin → routing unchanged); Node-1's short-circuit never reaches
     `intent_route`. No branch of `_route_after_safety` was touched. Pinned by
     `test_crisis_intent_never_transits` and
     `test_node1_crisis_short_circuit_still_precedes_everything` — both re-run, pass.
2. **No behavior change for turns already reaching skill_select.** Any turn whose base
   destination is `skill_select` (answering_screen, weave-pending, modality-pending,
   monitoring, HR referral, offer-accept, acute intensity, prepass hint, EMR redirect,
   new_skill/info_request) yields `psychoed_transit_destination == None` in **both** readers
   (dest not in `{freeflow, gate}`), so router and node body behave exactly as master.
   Ladder-order analysis confirms the transit fall-through in `_route_after_skill_select`
   (graph.py:534-536) sits below every psychoed-outcome branch and above the
   screen/abstain/info_request/active-skill ladder — the mid-skill general_chat case
   correctly falls to freeflow, not skill_executor (pinned, passes).
3. **The no-hit null case is genuinely byte-identical** (state-level): the psychoed block is
   at the literal top of `skill_select_node`; a transit no-hit turn executes only
   resolver/gates (all pure — Classifier A is deterministic JSON+regex,
   `src/sage_poc/psychoed/classifiers.py`, no LLM, no in-place state mutation) and returns
   `{}` with no path append (`skill_select.py:858-860`). `path` is reset per turn
   (`src/sage_poc/server_helpers.py:168`), the base router is pure, and both readers
   re-derive from the identical state — the two calls cannot disagree. The caveat is F-1's
   note about what the scope_refusal byte-identity pin exercised.
4. **EMR rehand guard correct in both directions.** The only executor→skill_select edge is
   `exit_with_rehand` (`graph.py:597-598`), whose delta stamps `"skill_executor"` into path
   (`src/sage_poc/nodes/skill_executor.py:607`); path is per-turn, so a transit turn can
   never carry the stamp, and a rehand turn always does →
   `psychoed_transit_destination` returns None for rehand (graph.py:316-317), full node
   body + normal ladder run. Pinned; passes.
5. **scope_refusal semantics (the ruled intent):** deterministic recognition winning over the
   probabilistic scope_refusal label is what the 2026-08-11 ruling and spec §2.1 say; the
   serve path's gating inside Node 4 (active-skill suppression, EN-only entry, Classifier A
   acute veto) is intent-agnostic and fully in force on the widened path (code-traced), and
   weave scheduling is set in the same hit delta. The failure is downstream at the gate (F-1),
   not in the resolver's gating.
6. **Do-not-widen verdict (jailbreak/exit_skill) — evidence sound.** Independently re-parsed
   the committed console log
   (`docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log`): 133 F1 rows,
   real_label distribution info_request 56 / general_chat 53 / scope_refusal 3 /
   new_skill 21 — **zero** jailbreak, **zero** exit_skill; misses = 48 general_chat +
   3 scope_refusal (+1 collision row F1-s2c-t5-01, disposition OK with audit/state MISS —
   Ticket B, correctly excluded). The cost-side claims verified by code reading: widening
   jailbreak would pre-empt the persona-reassertion terminal, exit_skill would serve a block
   into a disengagement turn. Boundary pin
   (`test_labels_outside_the_ruled_scope_are_not_widened`) is a real graph-constant pin with
   a documented re-open criterion that the existing runner already measures.
7. **Gate-exact no-regression re-run (this review's own run):** CANDIDATES extracted from
   `.github/workflows/unit-gate.yml` (79 files, all present), passed via python subprocess
   argv, `-m "not slow"`, dummy-ci/offline env → **2025 passed, 5 skipped, 73 xfailed,
   0 failed, 0 xpassed, exit 0**. Strict xfails individually confirmed still-xfailing:
   F4-002 (all 9 swept labels), F1-1f-t2-02-all-armed, F1-s2c-t5-01-all-armed, F10-004.
   New suite (66 tests) green. `scripts/check_state_channels.py`: OK, 116 declared keys —
   **no new state channel** (transit is a pure re-derivation, confirmed).
8. **#359 discipline:** assertions are on markers, state keys, path membership, and
   store-sourced content (`store.manifest(...)["framing_statement"]`), never copied strings.
   Volatile audit fields excluded by name, not wildcard. The 51-row sweep is count-guarded
   (48+3) against silent narrowing. The weave-pending scope_refusal pin is genuine (asserts
   escalation markers, correctly avoids the reset `psychoed_weave_escalation` channel) —
   subject to the F-4 mock caveat.
9. **Never-disarm / YAGNI / clarity:** no existing gate weakened; unit-gate CANDIDATES
   strengthened (new suite added); no flag defaults changed; the delta is scoped to the
   ruling (modulo F-3's unpriced interaction); comments are accurate against the code with
   one exception — the claim that general_chat+scope_refusal "account for 100% of the
   observed unreachable set" is true of the *observed* set but silently excludes the
   low-confidence slice CI pins away (F-2).

## COULD NOT VERIFY

- **The assessment doc's §3 widened-set experiment** (session-scoped pytest plugin,
  deliberately uncommitted): numbers accepted on plausibility; the cost-side conclusions were
  instead verified by direct code reading.
- **Live behavior under the real intent classifier** — the DoD flip-tier re-run. No LLM calls
  permitted in this review; F-1 was demonstrated with a faithful mock, not live. The live
  re-run remains the acceptance test and would surface F-1's menu-first breakage on
  F1-1f-t3-01/02.
- **Per-row intent confidence for the 2026-08-05 run** — absent from the committed log, so
  F-2's residue size on the 48-row evidence set is unquantifiable from the record.
- **The implementer's whole-tree vs base-worktree failure-set diff** and the
  `test_server_offer_voiding.py` pre-existing-failure characterization (report §Verification)
  — not re-run; the gate-exact set and the new suite were re-run instead.

## Verdict

**FINDINGS-FIRST.** Fix F-1 (gate_path shedding on a resolver-claimed turn + faithful mocks +
re-pin), document F-2's boundary, and name F-3 in the assessment doc. The routing topology
work itself — the widening, the null case, the rehand guard, the crisis proof, the boundary
pins — is correct and well-evidenced; nothing here re-opens the do-not-widen verdict.
