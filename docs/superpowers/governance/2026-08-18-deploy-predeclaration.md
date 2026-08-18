# Deploy predeclaration — F1+F2 (+F3+F4 riding) window, declared before the deploy

**Date:** 2026-08-18 (written and committed BEFORE the deploy window opens — the
prediction-first discipline applied to production; owner deploy authorization same date).
**Scope:** merge train #451→#456 on master; deploy = next window via the deploy runbook.

## Predeclared metric directions (the fix working, not a regression)

1. **Crisis-route rate WILL INCREASE (F1).** Compound disclosures (first-person SI
   co-occurring with a third-party mention) were previously wiped to `is_safe=true`; they
   now fire the crisis route. An on-call read of "crisis rate jumped after deploy" is the
   expected effect of the fix — not grounds for rollback. Pure third-party behavior is
   byte-stable (pinned by test).
2. **Veto-fire rate WILL INCREASE for mobile-keyboard users (F2).** Smart-apostrophe
   (U+2019) and invisible-char input now matches the OCD / harm-intrusive / IPV veto
   lexicons that bare `.lower()` silently missed. More vetoes from iOS/Android users is
   the intended widening (NFKC folding included, stated in the F2 commit).
3. **F3 diagnostic expectation:** p50 latency trend should improve on `info_request`-bearing
   traffic (event loop no longer blocked by knowledge-path BGE-M3 encodes). If no movement
   is visible, that is diagnostic input for the latency workstream — capture it, it is not
   a rollback trigger.
4. **F4 + instruments:** no served-behavior change expected (state-channel declaration,
   CI gates, instrument provenance). Any served delta traced to these is a finding.

## Post-deploy verification (three checks, in order)

- (a) **Boot logs:** zero `UNAPPROVED ACTIVE SAFETY RULE` warnings **except** the known
  SK-EN-HTO-001 pre-existing warn — which is now the standing canary that the
  loader-manifest convergence follow-up is still open. Any other rule warning = stop.
- (b) **Register parity, stamped:** run
  `uv run python scripts/characterize_1a_gap.py --parity-only` against the deployed flag
  set and keep the stamped verdict with the deploy record.
- (c) **F1 observable in the runtime record:** behavioral probe of the served build — a
  compound message (first-person SI + third-party mention) must produce the crisis
  response with `third_party_crisis` recorded true alongside non-empty `crisis_flags` in
  the audit row (a state that was impossible pre-F1); a pure third-party probe must stay
  non-crisis with resources. Probe scripts export prod-parity flags per the standing rule.

## Rollback unit

**The finding, not the window.** One commit per finding was held on every clinical
surface; if anything misbehaves, revert that finding's commit (register/branch revert per
runbook), never a blanket window rollback that would drag F1 back out of prod.
