# Native-Arabic (Khaleeji) Shadow-Measure — Pre-Registration

- **Date:** 2026-07-07
- **Status:** DRAFT — Phase-4 gate. The flag (`SAGE_NATIVE_ARABIC_SHADOW`) does not flip on
  any live cohort until this document is merged AND every sign-off slot below is filled.
- **Governs:** the analysis plan for `shadow_register_eval` — register score, latency, and
  gate-fire-rate comparisons between the shipped (English-then-translate) Arabic path and the
  shadow (native-Khaleeji) generation described in
  `docs/superpowers/plans/2026-07-07-native-arabic-shadow-measure.md`.
- **Why pre-registered:** every rule in this document (which turns count, how latency is
  defined, how timeouts are treated, what the rubric anchors mean) is fixed here, in writing,
  **before any shadow data is collected on live traffic**. Once the flag is on, none of these
  definitions may be changed to make a result look better — a change after data exists is a
  new, separately-reviewed amendment, not an edit to this file.

---

## 1. Containment basis (serializer/checkpointer confirmation)

*(Copied forward from the Task 5 Step-2 audit — `.superpowers/sdd/task-5-report.md` — which
found this document did not yet exist and recorded the note there for this purpose.)*

The reason a shadow-measurement feature is safe to run against live traffic before Tier-1
serving is approved is that the shadow payload is **structurally incapable of reaching the
client or the durable checkpoint**, independent of code review vigilance in any one node:

- **API layer.** `server.py`'s `/chat` handler (lines ~343-516) does not serialize `SageState`
  (or the node `result` dict) wholesale to the client. The response body is an explicit
  whitelist: the streamed text is `result.get("response")` (plus the crisis-card sentinel
  token), and every other piece of turn metadata reaches the client as one of ~20
  individually-named `X-Sage-*` response headers, each an explicit `result.get("<field>")`
  call. A grep for wholesale-state-serialization patterns
  (`grep -rnE "\.dict\(\)|model_dump|jsonify\(state|return .*state\b" server.py
  src/sage_poc/**/*.py | grep -iv test`) returned no hits. There is no code path that could
  leak a shadow key even if one were accidentally added to a node's return dict, unless it
  were also added to this named whitelist.
- **Session-audit row.** `output_gate_node` does pass the full state dict into
  `write_session_audit`, but `_build_session_audit_row()` (`src/sage_poc/audit.py`, ~line 97+)
  immediately re-projects that dict into a named, explicit set of columns via individual
  `.get()` calls. It is a whitelist row-builder, not a blind `INSERT ... state`. `shadow_*`
  keys are not among the named columns it projects.
- **LangGraph checkpointer.** The `AsyncPostgresSaver` persists only `channel_values` — i.e.
  exactly the keys declared in `SageState.__annotations__`. `shadow_arabic` is not, and must
  never be, one of those declared channels (enforced by the static guard
  `test_shadow_is_not_a_sagestate_channel` in `tests/test_shadow_never_served.py`). Because
  the checkpointer only ever sees declared channels, nothing needs to "strip" shadow data from
  a checkpoint — it structurally cannot arrive there.

**Conclusion:** shadow data has exactly one sink — `shadow_register_eval`, written directly by
`write_shadow_eval_row` (`src/sage_poc/shadow_eval.py`) from inside `freeflow_respond_node`
(`src/sage_poc/nodes/freeflow_respond.py`) — and no code path today serializes state wholesale
to client, audit row, or checkpoint. This is a **confirmation**, not a patch: no exclusion code
was required. If a future change ever adds a `shadow_*` key to `SageState` or to the
`/chat` response whitelist, `tests/test_shadow_never_served.py`'s three static guards and the
Task-7 behavioral sentinel test are the tripwires that must fail first.

---

## 2. Primary comparison — zero-tool turns only

**Primary set:** turns where `tool_loop_iterations == 0` for BOTH register score and latency.

**Rationale:** the shadow arm runs a single `ainvoke` (`generate_shadow_arabic`, no tool
access). On a turn where the served (English) arm looped through one or more tool calls
(retrieved knowledge, ran a skill lookup, etc.), the shadow's native-Khaleeji reply is
generated **without** that retrieved evidence — it is answering a different, evidence-poorer
version of the same turn. Comparing register or latency on such a turn does not isolate the
"does native generation clear the register bar" question; it conflates it with "does the
absence of tool-retrieved evidence change apparent register/latency," which is a different
question this experiment is not designed to answer.

- **Register (primary):** rater scores restricted to zero-tool turn pairs.
- **Latency (primary):** `shadow_gen_latency_ms` vs. served generation+translate time (§5),
  restricted to zero-tool turn pairs — the only turns where both arms did comparable work
  (one LLM call each).

**Secondary (stratified, non-comparable):** turns with `tool_loop_iterations > 0` are reported
separately, explicitly labelled **"non-comparable — shadow generated without the served arm's
retrieved evidence."** They are not pooled into the primary means, not used for the KPI
decision, and not used for the latency delta headline number. They are retained and reported
because they are still informative for gate-fire-rate sizing (§7) and for a future Tier-1 scope
decision about whether native generation should also cover tool turns.

**Hypothesis (H1), stated in advance:**

> H1: `shadow_mean ≥ shipped_mean` **AND** `shadow_mean ≥ 4.0`, computed over the zero-tool
> primary set.

Both conjuncts must hold for the shadow arm to be reported as clearing the bar. A shadow mean
that beats shipped but sits under 4.0 (or vice versa) is reported as **not meeting H1**, not
rounded up to a pass. `register_delta()` in `scripts/register_eval/rating_harness.py` already
computes `shadow_meets_kpi = shadow_mean >= REGISTER_KPI` (`REGISTER_KPI = 4.0`); the delta
(`shadow_mean - shipped_mean`) must additionally be reported and be `>= 0` for H1 to hold — the
KPI check alone is necessary but not sufficient.

---

## 3. Register rubric (1–5)

> **CLINICAL SIGN-OFF REQUIRED** on the anchor wording below. The numbers (KPI = 4.0, scale
> 1–5) come from v7 §16.1 and are not in question; the anchor *language* — what a rater is
> actually being asked to judge at each point — has not been reviewed by a clinician and must
> not be used to rate live-collected shadow data until it is.

| Score | Anchor |
|---|---|
| 5 | Fluent Khaleeji a Gulf native would use — register, dialect, and warmth all read as native-authored, not translated or machine-generated. |
| 4 | Natural Gulf Arabic, with minor MSA leakage (a word, a construction) that a native speaker would notice but not find jarring. |
| 3 | Understandable, but MSA-flavoured or stilted — reads as competent Arabic that is not distinctly Khaleeji; a native speaker would recognize it as "translated" or "formal" rather than as something a Gulf peer would say. |
| 2 | Awkward, or partly wrong register — noticeable mis-steps in dialect, tone, or word choice that would read strangely to a native speaker, short of unintelligible. |
| 1 | Wrong dialect entirely, or broken — non-Khaleeji Arabic (e.g. Levantine/Egyptian-flavoured), or text a native speaker would not recognize as coherent Gulf Arabic at all. |

**KPI line:** shadow arm mean `≥ 4.0` on the zero-tool primary set (§2), combined with the
non-inferiority requirement against the shipped arm (H1).

`SIGN-OFF REQUIRED: ______ (clinician name / date, anchor wording as-approved-or-amended)`

---

## 4. Raters and blinding

- **Minimum 2 Gulf-native raters**, native or near-native Khaleeji speakers, independent of the
  engineering team that built the shadow generator.
- **Blinding mechanism:** `build_blinded_sheet(pairs, seed)` in
  `scripts/register_eval/rating_harness.py` performs a deterministic, seeded per-pair
  coin-flip A/B randomization. The rater-facing row exposes only `turn_id` and
  `arms: {"A": ..., "B": ...}` — no `shipped`/`shadow` key names, no arm identity, in the
  fields raters see.
- **The arm-identity mapping (`_map`) must never reach a rater.** `_map` (`{"A": "shipped" |
  "shadow", "B": ...}`) is required to unblind scores after rating, but as currently
  implemented (`build_blinded_sheet`, `scripts/register_eval/rating_harness.py:36-40`) `_map`
  is returned **in the same dict as the row itself** — it co-lives with `turn_id`/`arms` in
  every sheet row, not in a separately-withheld structure. **This is a live export-hygiene gap,
  not just a hypothetical risk**: anyone exporting `build_blinded_sheet`'s output directly to a
  rater-facing spreadsheet or form (the intended next step for the Task 12 rating pass) would
  hand the answer key to the rater in the same row.
  - **Requirement, effective before any rater-facing export:** the analysis harness MUST add
    and use a `strip_for_rater(sheet)` projection (or equivalent) that emits only
    `{"turn_id", "arms"}` per row, with `_map` retained separately (in-memory or in a
    controller-only file) for post-rating unblinding. This function does not exist yet in
    `scripts/register_eval/rating_harness.py` as of this pre-registration and must be added
    before Task 12's rating pass runs — it is a precondition on the calibration-first rule
    (§11), not merely a nice-to-have.
- **IRR (inter-rater reliability):** `compute_irr(scores_by_rater)` — simplified two-rater
  ordinal agreement, `1 - mean(|r1_i - r2_i|) / 4`. **Target: α ≥ 0.6** on the seed set (§11)
  before the flag goes live. If IRR falls below 0.6 on the seed set, raters re-adjudicate
  disagreements (joint discussion, re-score) and the harness re-runs `compute_irr` until the
  target is met, or the rubric anchors (§3) are revised (with clinical sign-off) and
  re-calibrated. A shadow rollout must not proceed on an uncalibrated or low-agreement rubric.

---

## 4b. Coverage accounting (no silent caps)

`pair_by_turn(shadow_rows, shipped_rows)` (`scripts/register_eval/rating_harness.py:81-99`)
joins shadow rows to shipped rows on `(session_id, turn_number)` and **silently drops**:
- shadow rows with no matching shipped row for that key, and
- shadow rows with an empty/missing `shadow_arabic_text`.

This is by design at the pure-function level (the docstring says "the caller is responsible
for logging/reporting the drop count") — but as of this pre-registration, **no caller does
that logging**: `fetch_pairs()` is still a `NotImplementedError` stub
(`scripts/register_eval/rating_harness.py:102-123`) with no drop-count instrumentation, because
the live DB read has not been implemented yet.

**Requirement:** when `fetch_pairs()` is implemented (a precondition of Task 12, §10), it MUST:
1. Log the count of shadow rows fetched, the count of shipped-side matches found, and the
   count/reasons for drops (no shipped match vs. empty `shadow_arabic_text`), broken out
   separately.
2. This document's results report MUST state, alongside every register/latency number, the
   coverage: `N pairs used / M shadow rows collected (K dropped: <reasons>)`. An unreported
   drop count is treated as a validity threat to the reported means — a headline number without
   a coverage line is not acceptable for the Tier-1 decision brief.

**`register_delta` empty-input guard.** As currently implemented
(`scripts/register_eval/rating_harness.py:63-78`), `register_delta([])` divides by
`n = len(unblinded) = 0` and raises `ZeroDivisionError` — there is no guard. This is a real gap
against this section's own requirement, not a hypothetical: if a stratum (e.g. `arabizi`
turns, or the zero-tool primary set itself on a small early batch) has zero completed pairs at
report time, calling `register_delta` on that slice crashes instead of reporting "no data yet."
**Requirement:** `register_delta` must be changed to return an explicit empty-input result
(e.g. `{"n": 0, "shadow_mean": None, "shipped_mean": None, "delta": None, "shadow_meets_kpi":
False}` or equivalent — exact shape left to the implementing task) rather than raising, before
this experiment's reporting code depends on per-stratum slices that could legitimately be
empty early in collection. This is a precondition on Task 12, not a re-opening of Task 9's
scope; Task 9 is otherwise unchanged.

---

## 5. Latency definition

**Shadow latency:** `shadow_gen_latency_ms`, captured inside `generate_shadow_arabic`
(`src/sage_poc/shadow_arabic.py`) as the wall-clock time of the single `ainvoke` call, stored
per-row on `shadow_register_eval`.

**Served (shipped) latency, target definition:** English `freeflow` generation time (the
served arm's `_invoke_with_tool_loop` call inside `freeflow_respond_node`) **plus**
`output_gate`'s translate-out time (`async_translate_to_arabic(response_en)`,
`src/sage_poc/nodes/output_gate.py` line ~675) — i.e. the two stages of served-path work that
correspond to what the shadow's single call replaces.

**Current instrumentation gap (must be closed before this number is reported):** as of this
pre-registration, neither of those two stages is captured as an **independent** stage timer.
The only latency figure presently written to `session_audit` is a single combined `latency_ms`
(`src/sage_poc/audit.py:142`), computed in `output_gate_node` as `turn_started_at` → the moment
`output_gate` finishes (`src/sage_poc/nodes/output_gate.py:446-449`) — this bundles routing,
the full tool loop (not just generation), gate evaluation, and translate-out into one number,
not just "freeflow gen + translate-out." Using the combined `latency_ms` as a stand-in would
overstate the served-arm comparator and bias the latency delta in the shadow's favor.
**Requirement:** before Phase-4 data collection produces the reported latency delta, either
(a) two new stage timers (freeflow generation wall-clock, output_gate translate-out wall-clock)
are added and threaded into the audit row, or (b) the report explicitly computes and states the
gap between the combined `latency_ms` and the true two-stage figure, with the direction of the
resulting bias named. Reporting the combined `latency_ms` as if it were the two-stage figure,
uncaveated, is not acceptable.

**Reporting:** p50 and p95, measured on Railway (the deployed pilot environment, not local),
for both arms, on the zero-tool primary set (§2). Tool-turn latency is reported separately
under the non-comparable secondary stratification, not blended into the primary p50/p95.

---

## 6. Timeout censoring

`shadow_timed_out = true` rows (the shadow arm exceeded `_SHADOW_TIMEOUT_S = 8.0s`,
`src/sage_poc/nodes/freeflow_respond.py`) are **right-censored observations**, not missing
data and not failures to discard.

- **Report:** the count and rate of `shadow_timed_out = true` rows, separately from the
  completed-generation count, for every reported stratum (overall, zero-tool primary, per
  `lang_profile`).
- **Treatment in the latency distribution:** censored rows are retained in the reported N and
  flagged as "≥ 8000ms, exact value unknown" — they must not be dropped from the denominator,
  and must not be imputed with a specific completed-latency value. A proper censored-data
  method (e.g. reporting the censoring rate alongside a Kaplan–Meier-style p50/p95 on the
  *completed* subset, with the censoring rate stated as a ceiling on how far the true p95 could
  sit above the completed-subset figure) is the target treatment; a naive mean/percentile over
  completed rows only, reported without the censoring rate alongside it, is not acceptable.
- **Why this matters:** dropping censored rows silently removes exactly the slowest
  observations from the shadow arm's latency distribution, which makes the shadow-vs-shipped
  latency delta look better than it is — an optimistic bias in the direction that favors
  shipping native generation. This is the same reasoning that drove the write-policy decision
  (below): a timeout writes a censored row rather than nothing, specifically so this number can
  be computed honestly.

**Why the write policy writes a censored row on timeout (not silence):** `freeflow_respond_node`
distinguishes timeout from ordinary generation failure precisely so this censoring can be
represented. On timeout (`_timed_out = True`), `write_shadow_eval_row` is called with
`shadow_timed_out=True` and a `None` payload (`shadow_arabic_text` and
`shadow_gen_latency_ms` are `NULL` in the row) — the row exists and is countable. On a
non-timeout generation failure (LLM error, empty/whitespace content), no row is written at all,
because that is not a valid measurement of *this arm's* behavior under load, it is an
unrelated generation defect, and including it would pollute the register/latency sample with
non-responses rather than censor a slow-but-real one.

---

## 7. Gate-fire rate (Tier-1 sizing)

**Source:** `scripts/register_eval/replay_gates.py` — `replay_gates_on_row` /
`gate_fire_summary`.

**What it measures:** for each `shadow_register_eval` row, the shadow Arabic text is
back-translated to English (`async_translate_to_english`) and run through the **real** live
gate logic:
- `cultural_output` evaluated via `rules_engine.evaluate("cultural_output", {...})` with the
  actual `message_en` and `clinical_flags` from that row (not empty defaults — this was
  Blocking #3 in the design review, because message-conditioned mirroring rules under-fire on
  an empty message);
- banned-opener detection via `_BANNED_OPENER_RE.match(back_en.lstrip())` — anchored-match on
  lstripped text, matching the live gate's exact call shape in `output_gate.py`;
- format-violation detection via `_strip_output_format` then `_FORMAT_VIOLATIONS.findall`,
  matching the live gate's strip-then-count order (post-strip residual, not raw density).

`gate_fire_summary` aggregates: `n`, `cultural_fires`, `banned_opener_fires`, `format_fires`,
`any_gate_fire_rate`.

**Caveat, stated precisely (do not round this off in the Tier-1 brief):** this is an
**estimate, not a measurement of what would actually fire on served native Arabic.** It runs
the live gate semantics faithfully, but against a **back-translation** of the shadow's native
Khaleeji text, not the native text itself and not what a hypothetical native-serving gate would
see. Back-translation is lossy and can introduce or remove the exact lexical triggers the
deterministic gates key on (e.g. a banned-opener phrase that exists in the back-translation's
English wording but was never really "said" in the Khaleeji original, or vice versa). Because
of this:
- The number MUST be reported with its method ("back-translation replay of live gate logic")
  every time it is cited, not as a bare percentage.
- A **rater spot-check adjudicates borderline cases** — rows where the replay disagrees with a
  native-Khaleeji reader's judgment of whether the original text would actually trip a gate —
  before the fire-rate is used to size the Tier-1 native-gate-porting backlog. The spot-check
  sample size and adjudication process are the responsibility of the rating pass in §4/§11; a
  raw `any_gate_fire_rate` without an accompanying spot-check note is a lower-confidence number
  and must be labeled as such in the decision brief.

---

## 8. Accepted served-latency impact (flag-ON)

While the flag is on, served latency for Arabic turns is **not** free — `asyncio.gather` runs
the English and shadow arms concurrently, so served latency becomes **≈ max(English arm,
shadow arm)**, bounded at **+8s worst case** (the shadow's own timeout ceiling). `create_task`
fire-and-forget was considered and rejected: request/graph teardown can cancel a detached task
mid-flight and silently drop the eval write, which would reintroduce exactly the optimistic
right-censoring bias §6 exists to prevent — a measurement instrument that drops its own
slowest observations is broken by construction. `asyncio.gather` was chosen deliberately:
reliable capture over latency, for a bounded, flag-gated window.

**Accepted, time-boxed impact:** during the pilot measurement window, Arabic-turn p95 latency
may exceed the product's `<3s` KPI. This is accepted as the deliberate cost of the measurement,
not a regression to be silently absorbed into steady-state latency budgets, and it is
time-boxed by a committed flag-off date — the flag does not stay on indefinitely "just in case
more data would help."

`FLAG-OFF DATE COMMITTED: ______`

(To be filled at Task-12 enablement time, alongside the pilot-cohort scope and target N; this
document commits that a date will exist and be enforced, not the calendar date itself, since
the enablement date is not yet known at pre-registration time.)

---

## 9. PDPL / DPO acknowledgement

`shadow_register_eval` holds `shadow_arabic_text` — native-Khaleeji clinical response text
generated from a live user's turn. This is **restricted clinical text, in the same retention
class as `identity_substitution_audit.original_response_text`** (per the migration 009 header
comment and the standing convention below) — **not** a `session_audit` column, and the ack for
this feature must name this table specifically. An ack that only references `session_audit`'s
retention posture misfiles this guarantee: the two tables are deliberately split (shadow text
was never joined into `session_audit`, by the containment design in §1), and `session_audit`'s
retention posture says nothing about this table.

**Posture, as applied (migration 010, `migrations/010_rls_shadow_register_eval.sql`):**
- `ALTER TABLE shadow_register_eval ENABLE ROW LEVEL SECURITY;` — default-deny for all
  non-bypassrls roles, including `anon`/`authenticated`, with zero policies defined.
- `ALTER TABLE shadow_register_eval FORCE ROW LEVEL SECURITY;` — the table owner is not exempt
  from RLS either, so a future ownership/grant change cannot silently re-open access.
- `REVOKE ALL ON shadow_register_eval FROM anon, authenticated;` — removes the default
  Supabase/PostgREST privilege grant outright, so even a future permissive policy added by
  mistake has no underlying grant to exercise.
- **Service-role only.** The backend writer (`write_shadow_eval_row` →
  `sage_poc.audit._supabase_insert`) uses the service role, which bypasses RLS, so legitimate
  writes are unaffected by this posture.
- **Applied to the repo-local/staging Supabase project** (`jrfrficjdwguqbvumdyo`) as of
  2026-07-07; **prod** (`tcekehffneiqcdyhzobi`) application is a separate, later controller
  action and is a named Phase-4 precondition (§10), not assumed done by this document.
- This posture is the reference implementation for a **standing convention** recorded in
  `docs/ARCHITECTURE_BOUNDARIES.md`: any table holding clinical or restricted text ships with
  RLS `ENABLE`d + `FORCE`d and default client grants revoked **in its creation migration**, not
  as a follow-up — established 2026-07-07 after two instances in one audit
  (`shadow_register_eval` and, separately, `session_audit`'s write-exposure finding, which is
  routed to the cdai ledger and is independent of this feature).

`DPO ACK REQUIRED: ______ (name/date) — acknowledging that shadow_arabic_text lives in
shadow_register_eval under the RLS posture above, is restricted-retention clinical text, and is
populated only while SAGE_NATIVE_ARABIC_SHADOW is on.`

---

## 10. Phase-4 preconditions checklist

Copied from the plan's Task 12 preconditions (`docs/superpowers/plans/2026-07-07-native-arabic-shadow-measure.md`,
"Phase 4 — Enablement (gated)"), restated here as the enablement gate this pre-registration
feeds:

- [ ] **Sentinel green on the deploy SHA** — the strengthened, compiled-graph e2e test (real
      LangGraph invocation, flag ON, sentinel asserted absent from the actual `/chat` response)
      — NOT the Task-7 hand-assembled mocked-graph test — passing on the exact commit being
      deployed. If infeasible on Railway's deployment shape, the substitute and the reason must
      be documented precisely (per Checkpoint-2 architect sign-off), not silently skipped.
- [ ] **Migrations 009 (table) and 010 (RLS) applied to the PROD database**, with RLS verified
      (`relrowsecurity=t`, `relforcerowsecurity=t`, zero `anon`/`authenticated` grants) — a hard
      precondition, checked before the flag flips, not assumed from the staging apply.
- [ ] **Exemplar `ar` fields native-authored AND clinician-reviewed** (Amendment #5), with
      `khaleeji_shadow_exemplars.json`'s `version` bumped off `-draft`.
- [ ] **This document signed** — every `SIGN-OFF REQUIRED` / `DPO ACK REQUIRED` /
      `FLAG-OFF DATE COMMITTED` slot in §11 below filled.
- [ ] **DPO ack recorded** (§9).
- [ ] **Flag-off date committed** (§8).
- [ ] **Seed set built and rubric/blinding/IRR calibrated on it first** (§11) — including the
      §4 `strip_for_rater` export function and the §4b `register_delta` empty-input guard,
      both of which are currently missing from `scripts/register_eval/rating_harness.py` as of
      this pre-registration and must land before the calibration pass, not after.

---

## 11. Calibration-first rule

Rubric anchors (§3), the blinding mechanism and its rater-facing export (§4), and IRR (§4)
must be **settled on the offline seed set before the flag is enabled on any live cohort.**

**Status of the seed set, as of this pre-registration:** the plan's Task 8
(`scripts/register_eval/seed_inputs.json`, sourced from IE findings C-1/C-3/C-4 —
dialect-realism cases spanning `khaleeji`/`code_switch`/`arabizi` `lang_profile` tags) has
**not yet been authored** — no `seed_inputs.json` exists in `scripts/register_eval/` as of this
document, and no commit on this branch creates it. This is a genuine open precondition, not a
formality: the calibration-first rule in this section cannot be executed until that file (and
its Gulf-native augmentation, per the plan's Task 8 Step 2) exists. Recording this explicitly
so the gap is visible from the pre-registration itself rather than discovered at Task 12.

**Sequence required before Phase 4:**
1. Task 8's seed set is authored (IE C-1/C-3/C-4 extraction + Gulf-native augmentation, 20–30
   inputs, tagged by `lang_profile`).
2. The rubric (§3, once clinically signed) is applied to seed-set outputs by the ≥2 raters
   under the blinding mechanism (§4), using a `strip_for_rater` export that does not leak
   `_map`.
3. `compute_irr` is run on the seed-set ratings; if `α < 0.6`, raters re-adjudicate and/or the
   rubric anchors are revised (with clinical re-sign-off) and recalibrated, repeating until the
   target is met.
4. Only once (1)-(3) are complete and this document's sign-off block (§11 below) is fully
   filled does Task 12 enable the flag on the pilot cohort.

Stratification for both the seed-set calibration and the eventual live report is by
`lang_profile` (`khaleeji` / `code_switch` / `arabizi`) and by turn type (zero-tool primary vs.
tool-turn secondary, §2) — a single pooled number across dialect profiles would hide exactly
the register-realism differences this experiment exists to detect.

---

## Sign-off block

The flag does not go live until every line below is filled in (not left as `______`):

- [ ] `SIGN-OFF REQUIRED` (§3 — register rubric anchor wording): `______`
- [ ] `DPO ACK REQUIRED` (§9 — shadow_register_eval restricted-retention posture): `______`
- [ ] `FLAG-OFF DATE COMMITTED` (§8 — time-boxed pilot window): `______`
- [ ] Seed set (§11, Task 8) authored and committed: `______`
- [ ] Rubric/blinding/IRR calibrated on the seed set, `α ≥ 0.6` achieved: `______`
- [ ] `strip_for_rater` export function added to `rating_harness.py` (§4): `______`
- [ ] `register_delta` empty-input guard added (§4b): `______`
- [ ] `fetch_pairs()` implemented with drop-count logging (§4b): `______`
- [ ] Latency stage-timer gap closed or explicitly caveated per §5: `______`
- [ ] Migrations 009 + 010 applied and RLS verified on PROD (§9, §10): `______`
- [ ] Exemplar `ar` content native-authored + clinician-reviewed, version bumped (§10): `______`
- [ ] Compiled-graph e2e sentinel green on deploy SHA (§10): `______`
