#!/usr/bin/env bash
# #258 — BUILD-SIDE deploy-lock enforcement (the "prevent" to the tripwire's "detect").
#
# The tripwire (scripts/deploy_tripwire.sh) fires AFTER an unlocked deploy is already live. This runs
# INSIDE the image build: it fails the build when the SHA being built never claimed the deploy lock
# (i.e. its short SHA is absent from LOCKED_DEPLOY_LOG, which scripts/deploy_prod.sh populates BEFORE
# `railway up`). A direct `railway up` that bypasses deploy_prod.sh never adds its SHA to the log, so
# its build fails here — the bypass is prevented, not merely reported.
#
# DEFAULT-OFF by design: ENFORCE_DEPLOY_LOCK != "1" -> warn-and-pass (no behavior change). This ships
# dormant; the flip to enforce is gated on a STAGING build test that confirms Railway actually passes
# LOCKED_DEPLOY_LOG into the Dockerfile build ARG (unverified from a dev box — see prod-deploy-control).
#
# Usage (in Dockerfile RUN): verify_build_lock.sh "$RAILWAY_GIT_COMMIT_SHA" "$LOCKED_DEPLOY_LOG" "$ENFORCE_DEPLOY_LOCK"
#   --self-test : run the offline logic tests and exit.
set -euo pipefail

_check() {  # sha, log, enforce -> exit 0 (pass) / 1 (blocked)
  local sha="${1:-}" log="${2:-}" enforce="${3:-0}"
  local short="${sha:0:12}"
  if [ "$enforce" != "1" ]; then
    echo "🔓 build-lock check DORMANT (ENFORCE_DEPLOY_LOCK != 1) — not gating this build." >&2
    return 0
  fi
  if [ -z "$sha" ] || [ "$sha" = "unknown" ]; then
    echo "🚨 build-lock: no deploy SHA (RAILWAY_GIT_COMMIT_SHA unset) — cannot verify lock. BLOCKING." >&2
    return 1
  fi
  if echo ",$log," | grep -q ",${short},"; then
    echo "✅ build-lock: ${short} claimed the deploy lock (in LOCKED_DEPLOY_LOG)." >&2
    return 0
  fi
  echo "🚨 build-lock: ${short} is NOT in LOCKED_DEPLOY_LOG — this build bypassed deploy_prod.sh. BLOCKING." >&2
  echo "   Legit deploy? run via scripts/deploy_prod.sh (claims the lock). Emergency? break-glass runbook" >&2
  echo "   in 2026-07-08-prod-deploy-control.md (ENFORCE_DEPLOY_LOCK=0 for the one build, justified + logged)." >&2
  return 1
}

if [ "${1:-}" = "--self-test" ]; then
  fail=0
  # dormant: enforce=0 always passes regardless of log
  _check "abc123def456" "" "0" || { echo "SELFTEST FAIL: dormant should pass"; fail=1; }
  # enforce + SHA in log -> pass
  _check "abc123def456" "999,abc123def456,777" "1" || { echo "SELFTEST FAIL: in-log should pass"; fail=1; }
  # enforce + SHA NOT in log -> block
  if _check "abc123def456" "999,777" "1"; then echo "SELFTEST FAIL: missing SHA should BLOCK"; fail=1; fi
  # enforce + empty/unknown SHA -> block
  if _check "unknown" "999" "1"; then echo "SELFTEST FAIL: unknown SHA should BLOCK"; fail=1; fi
  # enforce + short-SHA prefix match works (12-char)
  _check "abc123def456789" "abc123def456,x" "1" || { echo "SELFTEST FAIL: 12-char prefix should match"; fail=1; }
  [ "$fail" = "0" ] && echo "✅ verify_build_lock self-test PASSED" || { echo "❌ self-test FAILED"; exit 1; }
  exit 0
fi

_check "${1:-}" "${2:-}" "${3:-0}"
