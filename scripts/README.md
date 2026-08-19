# scripts/ classification

One table of every file under `scripts/`, generated from each script's first
docstring line (K3.3 archive sweep, 2026-08-19). Columns:

- **class** — `gate` (CI-enforced or merge/deploy-blocking check), `instrument-of-record`
  (the one authoritative measurement/deploy tool for its surface), `diagnostic`
  (indicative probe/analysis, not authoritative), `calibration` (threshold-tuning
  one-off), or `archived` (moved to `archive/scripts/`, kept for history only).
- **supersedes / superseded-by** — only populated where the source states or implies
  a supersession relationship; blank otherwise.
- **invocation** — the script's own `Run:`/`Usage:` line where documented, else the
  standard `python scripts/<path>` form.

This table cross-references `tests/test_instrument_helper_only.py`'s `_SANCTIONED`
and `_LEGACY` sets (graph-invocation allowlists) — see the **helper-allowlist**
column notes inline below the table. Allowlist and README must not silently
disagree: if you edit one, check the other.

## scripts/ (root)

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `__init__.py` | — (package marker) | | n/a |
| `apply_prod_flags.py` | instrument-of-record | | `python scripts/apply_prod_flags.py` |
| `audit_corpus.py` | diagnostic | | `uv run python scripts/audit_corpus.py` |
| `calibrate_knowledge_threshold.py` | calibration | | `DBURL=... uv run python scripts/calibrate_knowledge_threshold.py` |
| `calibrate_retrieval_threshold.py` | calibration | | `uv run python scripts/calibrate_retrieval_threshold.py` |
| `calibrate_s3_threshold.py` | calibration | | see in-file `Usage:` block |
| `calibrate_threshold.py` | calibration | | `uv run python scripts/calibrate_threshold.py` |
| `characterize_1a_gap.py` | diagnostic (Phase 0 characterization, BOT BEHAVIOUR §1a presence_only gap) — allowlisted with deprecation marker in `_SANCTIONED` when present (see `tests/test_instrument_helper_only.py`) | superseded-by `instrument/graph_evidence.py` for this script's register-file read (per its own docstring) | `python scripts/characterize_1a_gap.py` |
| `check_anchor_si_boundary.py` | gate (pre-submission) | | see in-file `Usage:` block |
| `check_disposition_ownership.py` | gate (CI, unit-gate.yml) | | `python scripts/check_disposition_ownership.py` |
| `check_env_flag_enumeration.py` | gate (CI, unit-gate.yml) | | `python scripts/check_env_flag_enumeration.py` |
| `check_env_register_coverage.py` | gate | | `python scripts/check_env_register_coverage.py` |
| `check_eval_distinctness.py` | gate (A2.3, pre-submission) | | `PYTHONPATH=src python scripts/check_eval_distinctness.py [path.jsonl] [max_jaccard]` |
| `check_pilot_gate.py` | gate (pilot deploy) | | `.venv/bin/python scripts/check_pilot_gate.py` |
| `check_safety_language_parity.py` | gate (CI, unit-gate.yml) | | `python scripts/check_safety_language_parity.py` |
| `check_safety_reads_raw.py` | gate (CI, unit-gate.yml) | | `python scripts/check_safety_reads_raw.py` |
| `check_signed_fields.py` | gate | | see in-file `Usage:` block |
| `check_state_channels.py` | gate (CI, unit-gate.yml) | | `python scripts/check_state_channels.py` |
| `coverage_matrix.py` | diagnostic | | `python scripts/coverage_matrix.py` |
| `d1_monitored_enforce.py` | instrument-of-record (D1 honesty-clause window read, #338) | | `DATABASE_URL=... python scripts/d1_monitored_enforce.py` |
| `embedding_timeout_watch.py` | diagnostic (monitor) | | `python3 scripts/embedding_timeout_watch.py [--days 7]` |
| `fetch_cradle_bench.py` | diagnostic (data fetch utility) | | `python scripts/fetch_cradle_bench.py` |
| `flag_watchdog.py` | diagnostic (alert-first watchdog) | | see in-file `Usage:` block |
| `functional_multiturn_prod.py` | diagnostic (live prod probe) | | `python scripts/functional_multiturn_prod.py` |
| `functional_test_production.py` | diagnostic (live prod probe) | | see in-file `Usage:` block |
| `gen_deterministic_surface.py` | instrument-of-record — **KEPT with status header (F9 ruling); campaign closed, re-run on any flag-gated routing/gate_path/crisis-copy change** | | `.venv/bin/python scripts/gen_deterministic_surface.py > surface.json` |
| `ingest_knowledge.py` | instrument-of-record (prod knowledge-corpus load/refresh) | | see in-file `Usage:` block |
| `knowledge_ar_recall_probe.py` | diagnostic | | `python scripts/knowledge_ar_recall_probe.py` |
| `latency_baseline.py` | diagnostic | supersedes `archive/scripts/benchmark_latency.py`, `archive/scripts/benchmark_poc_scenarios.py` | see in-file `Usage:` block |
| `monitor_abstain_band.py` | diagnostic (monitor) | | `python scripts/monitor_abstain_band.py` |
| `negatives_smoke.py` | diagnostic | | `python scripts/negatives_smoke.py` |
| `passive_si_s3_precision.py` | diagnostic (#18 / LOCK-SF1-02 measurement) | | `uv run python scripts/passive_si_s3_precision.py` |
| `per_skill_routing_test.py` | diagnostic (live prod probe) | | see in-file `Usage:` block |
| `prod_write_guard.py` | gate (mechanical source-ref assertion, mandatory in any prod-write script) | | imported by `repair_corpus_articles.py` and similar; not run standalone |
| `repair_corpus_articles.py` | instrument-of-record (targeted prod corpus repair) | | `python scripts/repair_corpus_articles.py` (guarded by `prod_write_guard.py`) |
| `s3_threshold_sweep.py` | calibration | | see in-file `Usage:` block |
| `safety_confusion_matrix.py` | diagnostic | | `python scripts/safety_confusion_matrix.py` |
| `semantic_probe_set.py` | diagnostic | | `uv run python scripts/semantic_probe_set.py` |
| `validate_grief_sf1_boundary.py` | diagnostic | | `uv run python scripts/validate_grief_sf1_boundary.py` |
| `verify_arabic_safety.py` | diagnostic | | `cd sage-poc && uv run python scripts/verify_arabic_safety.py` |
| `verify_tiering_recall.py` | instrument-of-record — **KEPT with status header (F9 ruling); campaign closed, re-run on any crisis-tier/S1/S3 detector change.** In `_LEGACY` graph-invocation allowlist (carries `DEPRECATED-DIRECT-INVOKE` marker; migrate to `instrument/graph_evidence.py` when re-run is needed). | | `cd sage-poc && .venv/bin/python scripts/verify_tiering_recall.py` |

## scripts/bot_behaviour_audit/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `build_conformance_matrix.py` | instrument-of-record (Layer-1 conformance matrix builder) | | `python scripts/bot_behaviour_audit/build_conformance_matrix.py` |
| `build_oracle_map.py` | instrument-of-record (Layer-1 oracle map + trigger corpus) | | `python scripts/bot_behaviour_audit/build_oracle_map.py` |
| `measure_f1_baseline_ci_tier.py` | instrument-of-record (F1-naturalistic recall-by-category, CI tier) | | `python scripts/bot_behaviour_audit/measure_f1_baseline_ci_tier.py` |
| `measure_layer1_fullgraph.py` | diagnostic — explicitly "DIAGNOSTIC, NOT the method of record"; in `_SANCTIONED` graph-invocation allowlist (parity runner the helper is extracted from) | superseded-by `measure_layer1_prod_http.py` (absolute values; deltas stay indicative) | `python scripts/bot_behaviour_audit/measure_layer1_fullgraph.py --diagnostic-only` |
| `measure_layer1_prod_http.py` | instrument-of-record — explicitly "THE METHOD OF RECORD" for BOT BEHAVIOUR Layer-1 conformance (EN) | supersedes `measure_layer1_fullgraph.py`; also supersedes `archive/scripts/bot_behaviour_audit/measure_layer1.py` (F9: worktree-path bug fixed in #465, isolation method not-of-record) | see in-file `Usage:` block |
| `measure_psychoed_families.py` | instrument-of-record (Psychoeducation Phase 3 Task 9 flip-tier conformance runner) | | `python scripts/bot_behaviour_audit/measure_psychoed_families.py` |

## scripts/instrument/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `__init__.py` | — (package marker) | | n/a |
| `graph_evidence.py` | gate / instrument-of-record — the ONLY unconditionally sanctioned direct graph-invocation helper (signed instrument-parity rule, 2026-07-28); anchors `_HELPER` in `tests/test_instrument_helper_only.py` | | see in-file `Usage:` block |
| `r4_transcript_preview.py` | diagnostic — explicitly "PREVIEW, NOT EVIDENCE" | | `uv run python scripts/instrument/r4_transcript_preview.py [--json out.json]` |
| `run_emr_baseline.py` | instrument-of-record (EMR Phase-0 distributional baseline) | | see in-file `Usage:` block |

## scripts/lib/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `__init__.py` | — (package marker) | | n/a |
| `prod_probe.py` | instrument-of-record (shared prod-probe harness backing the five prod-HTTP driver scripts: `prod_smoke/hr1_stage1_verify.py`, `prod_smoke/hr1_stage1_conformance.py`, `prod_smoke/verification_session.py`, `safety/sf1_phase0_prod_http.py`, `bot_behaviour_audit/measure_layer1_prod_http.py`) | supersedes the five duplicated per-script harness copies (K3.1/K3.2) | imported, not run standalone |

## scripts/prod_smoke/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `cases.py` | gate (Tier A safety-invariant case data) | | imported by `tier_a_safety.py` |
| `hr1_stage1_conformance.py` | instrument-of-record (HR-1 Stage 1 §HR TERMINAL CONFORMANCE pass) | | `python scripts/prod_smoke/hr1_stage1_conformance.py [--runs 2]` |
| `hr1_stage1_verify.py` | instrument-of-record (HR-1 Stage 1 flip prod behavioral verification) | | `python scripts/prod_smoke/hr1_stage1_verify.py --flag {off,on}` |
| `result.py` | — (shared result type) | | imported, not run standalone |
| `run.py` | gate (post-deploy health gate) | | see in-file `Usage:` block |
| `tier_a_safety.py` | gate (must-pass safety invariants unless XFAIL) | | invoked by `run.py` |
| `tier_b_features.py` | diagnostic (Playwright feature-card checks, report-only in v1) | | invoked by `run.py` |
| `tier_c_regression.py` | gate (deployed-flag readback + response-header regression) | | invoked by `run.py` |
| `verification_session.py` | instrument-of-record (standing prod safety-verification session, #328 cadence) | | `cd sage-poc && python scripts/prod_smoke/verification_session.py [--run NNN]` |

### scripts/prod_smoke/tests/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `test_prod_probe_lib.py` | gate (CI, unit-gate.yml credential-guard family; pure-function tests only) | | `pytest scripts/prod_smoke/tests/test_prod_probe_lib.py` |
| `test_runner_exit.py` | gate | | `pytest scripts/prod_smoke/tests/test_runner_exit.py` |
| `test_tier_a_shape.py` | gate | | `pytest scripts/prod_smoke/tests/test_tier_a_shape.py` |
| `test_tier_b_credential_guard.py` | gate (CI, unit-gate.yml — explicitly reachable outside `testpaths`) | | `pytest scripts/prod_smoke/tests/test_tier_b_credential_guard.py` |
| `test_tier_c_shape.py` | gate | | `pytest scripts/prod_smoke/tests/test_tier_c_shape.py` |

## scripts/psychoed_ingest/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `__init__.py` | — (package marker) | | n/a |
| `audit_collisions.py` | gate (spec §5.2 cross-category trigger collision audit; CI fails on undeclared collisions) | | `python scripts/psychoed_ingest/audit_collisions.py` |
| `schemas.py` | gate (content-as-code validators, spec §3) | | imported, not run standalone |

## scripts/register_eval/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `rating_harness.py` | instrument-of-record (offline blinded dual-arm register rating harness, Task 9) | | `python scripts/register_eval/rating_harness.py` |
| `replay_gates.py` | diagnostic (offline estimate of which EN deterministic gates fire on native Khaleeji) | | `python scripts/register_eval/replay_gates.py` |

## scripts/routing_eval/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `reverdict_cells.py` | diagnostic (routing gate-metrics cells: recall/abstain/misroute by stratum) | | `python scripts/routing_eval/reverdict_cells.py` |
| `reverdict_harm.py` | diagnostic (harm/redflag-strata gate probe, fast-first output) | | `python scripts/routing_eval/reverdict_harm.py` |

## scripts/safety/

| script | class | supersedes / superseded-by | invocation |
|---|---|---|---|
| `sf1_phase0_prod_http.py` | instrument-of-record (SF-1 Phase 0 veiled/passive-SI recall + FP baseline, prod-HTTP) | | see in-file `Usage:` block |

## archive/scripts/ (K3.3 archive sweep, 2026-08-19)

Moved outside `scripts/` — and outside `tests/test_instrument_helper_only.py`'s walk —
because each is a closed-campaign or superseded probe with no live CI/test/doc
reference at time of archival. Kept for history only; do not import or run from CI.

| script (former path) | closed campaign / superseded by |
|---|---|
| `benchmark_latency.py` | superseded latency group; superseded by `scripts/latency_baseline.py` |
| `benchmark_poc_scenarios.py` | superseded latency group; superseded by `scripts/latency_baseline.py` |
| `baseline_format_check.py` | deprecated-direct-invoke closed-campaign group (was in `_LEGACY`, now archived) |
| `bot_behaviour_recall_baseline.py` | deprecated-direct-invoke closed-campaign group (was in `_LEGACY`, now archived) |
| `probe_freeflow_openers.py` | deprecated-direct-invoke closed-campaign group (was in `_LEGACY`, now archived) |
| `rescore_openers.py` | deprecated-direct-invoke closed-campaign group (paired with `probe_freeflow_openers.py`) |
| `smoke_cultural_overrides.py` | closed campaign |
| `pool_characterize_entry_screen.py` | entry-screen pair, closed campaign |
| `entry_screen_integration_run.py` | entry-screen pair, closed campaign |
| `demo_script_gitex.py` | demo/C-sprint, closed campaign |
| `functional_test_c1_c2_c3.py` | demo/C-sprint, closed campaign |
| `staging_live_replay.py` | staging replay pair, closed campaign |
| `staging_tiering_replay.py` | staging replay pair, closed campaign |
| `a4_dialect_eval.py` | misc closed probe |
| `eval_counsel_chat_routing.py` | misc closed probe |
| `d5_intensity_confusion_probe.py` | misc closed probe (D5 parked, see memory `project_d5_parked_low_priority`) |
| `verify_tiering_behavioral.py` | closed campaign |
| `bot_behaviour_audit/measure_layer1.py` | superseded by `scripts/bot_behaviour_audit/measure_layer1_prod_http.py` (worktree-path bug fixed in #465; isolation method not-of-record) |

`lookup_*` scripts referenced in earlier audit drafts were already deleted in P0 (#485)
and are not part of this sweep.

## Graph-invocation allowlists (tests/test_instrument_helper_only.py)

- **`_SANCTIONED`** (unconditional): `bot_behaviour_audit/measure_layer1_fullgraph.py`,
  `characterize_1a_gap.py` (when present), plus the `prod_smoke/` and `instrument/`
  directories in full.
- **`_LEGACY`** (frozen, deprecation-marker required): `verify_tiering_recall.py` only,
  as of the K3.3 archive sweep — shrunk from six entries when the five archived
  `_LEGACY` scripts (`baseline_format_check.py`, `benchmark_poc_scenarios.py`,
  `bot_behaviour_recall_baseline.py`, `probe_freeflow_openers.py`,
  `benchmark_latency.py`) moved to `archive/scripts/`, outside the walk. Shrinking this
  set is the sanctioned direction; do not add new entries — new scripts go through
  `scripts/instrument/graph_evidence.py`.
