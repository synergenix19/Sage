# archive/scripts/ — F5 disposition record (primary record)

This file is the **primary record** of the scripts-triage audit's F5 (stale-script)
table. The audit itself was an in-conversation report and was never persisted as a
repo artifact before this sweep — the disposition it drove (which files move, which
are deleted, which stay) previously existed nowhere durable. **This file is now that
record.** Cross-referenced from `scripts/README.md`'s "archive/scripts/" section,
which carries the same 18-row table; this file adds the deletions and keeps and
states the recovery path.

The audit's F5 table covered roughly 25 files across three dispositions, all
executed under the K3.3 keystones-plan archive sweep:

1. **18 files ARCHIVED here, 2026-08-19** (this sweep, `git mv` — see table below).
2. **5 `lookup_*` prod-data scripts DELETED, not archived**, earlier in **PR #485**
   (P0 batch), for PDPL reasons — they queried/echoed prod personal data in ways
   that made even a repo-history-only retention inappropriate. Deletion, not
   archival, was the correct disposition for that group; they are out of scope for
   this file's table (their record is PR #485 itself).
3. **2 files KEPT IN PLACE at `scripts/`, with 3-line status headers** added by this
   same sweep (F9 ruling — campaign closed, re-run justified on a defined
   trigger): `verify_tiering_recall.py`, `gen_deterministic_surface.py`. Not
   archived; see `scripts/README.md` for their status-header text.

## Recovery path

Every row below is a `git mv`, not a delete — full history (blame, prior commits,
content) is intact under the new path. To recover or inspect a file as it stood
before archival:

- **From the file itself**: it is sitting at the path in the table below, unchanged
  in content (only its directory moved).
- **From git history**: `git log --follow -- archive/scripts/<name>.py` walks back
  through the move to every commit that touched the file at its original
  `scripts/<name>.py` path. `git mv` preserves this automatically (no `--follow`
  gymnastics needed for a straight rename with no intervening content edit at
  archival time).

## The 18 archived files (2026-08-19)

| file | group (F5 table) |
|---|---|
| `benchmark_latency.py` | superseded latency (×2) |
| `benchmark_poc_scenarios.py` | superseded latency (×2) |
| `baseline_format_check.py` | deprecated-direct-invoke closed-campaign (×4) |
| `bot_behaviour_recall_baseline.py` | deprecated-direct-invoke closed-campaign (×4) |
| `probe_freeflow_openers.py` | deprecated-direct-invoke closed-campaign (×4) |
| `rescore_openers.py` | deprecated-direct-invoke closed-campaign (×4) |
| `smoke_cultural_overrides.py` | smoke_cultural_overrides (standalone) |
| `pool_characterize_entry_screen.py` | entry-screen pair (×2) |
| `entry_screen_integration_run.py` | entry-screen pair (×2) |
| `demo_script_gitex.py` | demo/C-sprint (×2) |
| `functional_test_c1_c2_c3.py` | demo/C-sprint (×2) |
| `staging_live_replay.py` | staging replay pair (×2) |
| `staging_tiering_replay.py` | staging replay pair (×2) |
| `a4_dialect_eval.py` | misc closed probes (×3) |
| `eval_counsel_chat_routing.py` | misc closed probes (×3) |
| `d5_intensity_confusion_probe.py` | misc closed probes (×3) |
| `verify_tiering_behavioral.py` | closed campaign, via F9 ruling |
| `bot_behaviour_audit/measure_layer1.py` | superseded, via F10 ruling (superseded by `scripts/bot_behaviour_audit/measure_layer1_prod_http.py`) |

All 18 were grep-verified against `.github/workflows/`, `tests/`, and doc mentions
before archival — every hit found was either the file itself or a historical
audit/plan-doc mention, never a live CI/test reference. No file was left in place
due to a live reference.

## Not part of this sweep

- The 5 `lookup_*` prod-data scripts: **deleted** (not archived) in PR #485, for
  PDPL reasons. See that PR for their record.
- `verify_tiering_recall.py`, `gen_deterministic_surface.py`: **kept in place** at
  `scripts/`, per the F9 ruling, with status headers. See `scripts/README.md`.
