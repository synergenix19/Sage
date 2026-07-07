# Prod Smoke Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the accumulated per-feature prod E2E spot-checks into one repeatable smoke suite that runs as the post-deploy health gate, so regressions in the ~dozen live behaviours (crisis routing, KB cards, skill media, persistence, flags) can no longer land silently.

**Architecture:** A single runner (`scripts/prod_smoke/run.py`) drives three tiers against the live prod surface (`sage-api-production-3328` + `chat.biosight.ai`), consolidating existing one-off scripts — NOT re-authoring them. Tier A (safety invariants) and Tier C (regression floor) are backend curl/httpx checks reusing the `functional_test_production.py::Case` harness. Tier B (feature card-render behaviours) is Playwright against the frontend. The runner exits non-zero if any **must-pass** (Tier A + Tier C flag-readback) check fails; Tier B feature failures are reported but non-gating in v1. It is wired to run after every `railway up`. This is deploy-best-practice item 5 ("'the app responds' is not health; 'the crisis route fires with correct resources' is") made real; it pairs with the CI-on-PR task (CI before merge, smoke after deploy). Zero-user mode makes prod the correct place to run it.

**Tech Stack:** Python 3.11 / httpx (curl-equivalent, reuses `functional_test_production.py`) / Playwright (frontend card checks) / Railway post-deploy invocation.

## Global Constraints

- **Must-pass vs report-only is explicit.** Tier A (safety invariants) and the Tier C flag-readback are MUST-PASS: any failure exits the runner non-zero and the deploy is not declared healthy. Tier B feature checks and the Tier C non-KB-chat check are report-only in v1 (visible, non-gating). Every check prints `PASS` / `FAIL` / `XFAIL` with its tier.
- **The helpline number is a marked expected-failure (XFAIL), not a hidden pass.** The crisis check asserts the CURRENTLY DEPLOYED copy verbatim, and carries a separate marked-XFAIL assertion on the number itself (currently the wrong `800 46342`) so the suite is truthful and the fix becomes visible the day GL-1's dial-test lands. See `[[project_crisis_tiering_approved]]`. Do NOT assert the correct number as if it were live.
- **Read-only against prod.** The suite sends test traffic to `/chat` (safe under zero-user mode) and reads `/health/ready`; it never writes config, never sets env, never deploys. Test `user_id` is the fixed all-zeros sentinel already used by `functional_test_production.py`.
- **No secrets in the repo.** `SAGE_API_KEY` is read from the environment (Railway `railway run`), never committed.
- **Flag-readback asserts against the deploy-provenance record, not hardcoded truth.** Expected flag states are: `SAGE_ROUTE_PRECEDENCE` on, `SAGE_SKILL_MEDIA_ENABLED` on, `SAGE_IPV_PREEMPTION` off — sourced from `/health/ready` + the provenance trail (`docs/superpowers/governance/2026-07-07-deploy-provenance-trail.md`). If provenance changes, the expected values change with it.
- **DEPENDENCY (do not duplicate):** the Tier C flag-readback **consumes `/health/ready` flag exposure, delivered by make-v2-live Task 1** (the truthful-health-field task that already touches that endpoint for `routing_mode`). As of 2026-07-07 `/health/ready` returns only `{status, routing_mode}` — it does NOT yet expose these three flags, so the flag-readback returns an honest FAIL ("flag not observable — endpoint needs a field"). **Do NOT add the flag exposure here** (avoid two efforts editing `/health/ready`) and **do NOT flip the flag-readback to must-pass until that endpoint field ships.** Until then it runs report-only, visible.
- **Distinct from the BOT BEHAVIOUR clinical audit.** This suite answers "does what we shipped still work?" (regression, minutes, every deploy). It does NOT check clinical-spec conformance (the three-layer routing/flow-fidelity/delivery-quality review) — that audit stays separately queued behind the audit-document-structure confirmation.

---

## File Structure

- `scripts/prod_smoke/run.py` — the runner. Argparses `--tier a|b|c|all`, invokes the three tiers, aggregates PASS/FAIL/XFAIL, exits non-zero on any must-pass FAIL. Prints a one-screen summary.
- `scripts/prod_smoke/tier_a_safety.py` — safety invariants (must-pass). Reuses `functional_test_production.py::Case` + request helpers.
- `scripts/prod_smoke/tier_b_features.py` — feature card-render checks (Playwright, report-only v1).
- `scripts/prod_smoke/tier_c_regression.py` — regression floor: non-KB chat unchanged (report-only) + flag readback (must-pass).
- `scripts/prod_smoke/cases.py` — the consolidated case data (crisis EN/AR, MM derealization, KB Ask, box-breathing media, Arabic), imported by tiers. Sourced from the existing one-off scripts.
- `scripts/functional_test_production.py` — REUSE its `Case`, request/header-parse helpers (import, do not fork). Read-only reference.
- `docs/superpowers/governance/2026-07-07-deploy-provenance-trail.md` — the flag-state source of truth for Tier C.
- `docs/runbooks/prod-smoke.md` — how to run it + how it wires to deploy (new).

---

## Global Constraints recap for reviewers
Must-pass = Tier A + Tier C flag-readback. Helpline number = XFAIL. Read-only. Flags from provenance.

---

## Task 1 — Runner skeleton + Tier C flag-readback (must-pass, smallest end-to-end slice)

**Files:**
- Create: `scripts/prod_smoke/run.py`, `scripts/prod_smoke/tier_c_regression.py`
- Test: `scripts/prod_smoke/tests/test_runner_exit.py` (unit — runner exit-code logic with stubbed tier results)

**Interfaces:**
- Produces: `run_tier(name) -> list[CheckResult]` where `CheckResult = {name, tier, status: "PASS"|"FAIL"|"XFAIL", detail, must_pass: bool}`; `main() -> exit(1 if any must_pass FAIL else 0)`.

- [ ] Write a failing unit test: runner exits 1 when a must_pass check is FAIL, 0 when only report-only checks FAIL, 0 when a must_pass check is XFAIL.
- [ ] Run it — fails (module absent).
- [ ] Implement `CheckResult`, `run.py` aggregation/exit logic, and `tier_c_regression.py::flag_readback()` — GET `/health/ready`, assert `SAGE_ROUTE_PRECEDENCE` on / `SAGE_SKILL_MEDIA_ENABLED` on / `SAGE_IPV_PREEMPTION` off (must_pass), plus a report-only non-KB chat turn returns 200 with no `X-Sage-Sources`/`X-Sage-Skill-Media`.
- [ ] Run the unit test — passes.
- [ ] Run `run.py --tier c` against prod via `railway run` — flag readback PASS.
- [ ] Commit.

## Task 2 — Tier A safety invariants (must-pass) + helpline XFAIL

**Files:**
- Create: `scripts/prod_smoke/tier_a_safety.py`, `scripts/prod_smoke/cases.py`
- Test: `scripts/prod_smoke/tests/test_tier_a_shape.py` (unit — XFAIL wiring + case parse, with a stubbed HTTP layer)

**Interfaces:**
- Consumes: `CheckResult` from Task 1; `Case` + request helpers from `functional_test_production.py`.

- [ ] Write a failing unit test: a case whose body-copy assertion passes but whose helpline-number sub-assertion fails yields status `XFAIL` (not FAIL, not PASS), and does not flip the runner exit code.
- [ ] Run it — fails.
- [ ] Implement `tier_a_safety.py` with these must-pass checks, EN + AR each:
  1. Crisis turn (`si_explicit`) → body contains `[[CRISIS_DETECTED]]`, contains a crisis-resource block, and response emits NEITHER `X-Sage-Sources` NOR `X-Sage-Skill-Media`.
  2. Helpline number sub-assertion on the crisis body → marked **XFAIL** against the currently-deployed (wrong) number.
  3. MM entry-screen: offer→accept→disclose derealization → `X-Sage-Step-Id` stays `entry_screen` (does NOT advance to `settle_and_anchor`) and no skill-media header on that turn.
  4. Precedence audit: after a crisis turn, assert the per-turn audit row records the fired safety route (`fired_safety_routes` non-empty) — via the audit read path used by `functional_test_production.py` or a `/health`/audit probe; if no read path exists in-suite, assert the response-header proxy (`X-Sage-Crisis-Flags`) and note the audit-row check as a follow-up in the runbook.
- [ ] Run the unit test — passes.
- [ ] Run `run.py --tier a` against prod — safety invariants PASS, helpline XFAIL shown.
- [ ] Commit.

## Task 3 — Tier B feature card-render checks (Playwright, report-only)

**Files:**
- Create: `scripts/prod_smoke/tier_b_features.py`
- Test: dry-run against `chat.biosight.ai` (Playwright checks are their own verification)

**Interfaces:**
- Consumes: `CheckResult` (report-only, must_pass=False in v1).

- [ ] Implement Playwright checks, each returning a `CheckResult`:
  1. KB "Ask" turn → source card renders with article link + video, deduped, capped.
  2. Skill-delivery (box breathing accept) → correct video card on the exercise step.
  3. Reopen a saved conversation → card persists.
  4. Pre-persistence conversation → no card, no crash.
  5. Arabic turn → RTL card, legible title.
- [ ] Run `run.py --tier b` against prod frontend — report the pass/fail of each (non-gating).
- [ ] Commit.

## Task 4 — Post-deploy wiring + runbook

**Files:**
- Create: `docs/runbooks/prod-smoke.md`
- Modify: `docs/superpowers/governance/2026-07-07-deploy-provenance-trail.md` (add "post-deploy gate: run prod smoke, must-pass Tier A+C" line)

- [ ] Write `docs/runbooks/prod-smoke.md`: the exact post-`railway up` invocation (`railway run python scripts/prod_smoke/run.py --tier all`), how to read PASS/FAIL/XFAIL, what a must-pass FAIL means (deploy not healthy — investigate before announcing), and the helpline-XFAIL note (flips to PASS the day GL-1 lands — that is the signal to update the assertion).
- [ ] Add the post-deploy-gate line to the deploy-provenance trail so the runbook and provenance agree.
- [ ] Commit.

---

## Self-Review notes
- Coverage vs the spec: Tier A = the five safety must-pass items (crisis EN/AR + headers, MM hold, precedence audit); Tier B = the five feature behaviours; Tier C = non-KB chat + flag readback. Helpline XFAIL encoded. Deploy-wired. Distinct from the clinical audit. All present.
- The audit-row check (Task 2 item 4) may lack an in-suite read path; the task states the proxy fallback + runbook follow-up rather than leaving it silent.
