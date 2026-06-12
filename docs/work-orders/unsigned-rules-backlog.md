# Work Order — Unsigned Active Rules Backlog

**Date opened:** 2026-06-13
**Source:** PR #4 engagement audit, Phase F (finding S2-8 sub-item); reviewer instruction "the backlog-clearing itself should be a ticket with an owner"
**Owner:** Clinical lead (sign-offs) + Rule 1 approver (engineering-control rules)
**Blocking:** wiring the governance suite (`pytest -m governance`) as a REQUIRED CI status check on master

## The finding

`tests/test_clinical_governance.py -m governance` fails on **46 active rules with `approved_by: null`** across the Rules Service categories, plus **14 live templates** (now 16 with the PR #4 canary additions of `L2_skill_offer` and `L2_general_chat`). These are production-active clinical-behavior artifacts running without recorded sign-off. The governance suite was built as the enforcement instrument (approved-by-ci-guard plan, 2026-06-04) but is wired to no CI, so the debt accumulates silently.

## Why this blocks the technical merge gate

The PR #4 audit found master had no branch protection; protection is now enabled (1 required review). The reviewer-approved end state adds the governance suite as a required check — but requiring it TODAY would deadlock the repository on this backlog. Interim design (approved): a **changed-files-scoped guard** (fail only on new/modified unsigned artifacts in the PR's diff) enforces the envelope on everything new immediately, while this backlog clears on its own schedule.

## Work items

1. Inventory: generate the current unsigned list (`uv run pytest -m governance -q` output → per-rule table with category, rule_id, authored_by, effective_date). Attach to the clinical review session bundle.
2. Clinical lead + Rule 1 approver: batch-review and set `approved_by` per rule/template, or deactivate rules that should not be live. Highest priority per the severity-over-tractability convention: safety category rules, then skill_matching, then cultural/prompt_injection, then templates.
3. Engineering: changed-files-scoped governance check as a CI workflow + required status check on master (separate small PR; unblocks immediately, independent of item 2).
4. When the backlog reaches zero: flip the required check from changed-files-scoped to the full suite.

## Status

OPEN. No items started.
