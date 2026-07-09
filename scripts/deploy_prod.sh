#!/usr/bin/env bash
# Prod/staging deploy wrapper — enforces prod-deploy-control.md MECHANICALLY (the deploy lock #225).
# A control that exists beats a norm everyone must remember. Usage: deploy_prod.sh <staging|production> <full-sha>
set -euo pipefail
ENV="${1:?usage: deploy_prod.sh <staging|production> <full-40char-sha>}"; SHA="${2:?full deploy SHA required}"
PROJECT=4f1811e7-cab2-4002-9107-a9f782f2f274; SERVICE=160e9f65-e3c8-409a-b647-fbe2339a265d
HOLDER="${USER:-unknown}@$(hostname -s 2>/dev/null||echo host)-$$"; TTL=1200
# railway CLI (this version) does NOT accept --project/--environment/--service on `variables` —
# set context ONCE via link, then call flag-free. (Fix: dogfood caught the inline-flag bug 2026-07-09.)
RAILWAY_CALLER="skill:use-railway@1.2.0" RAILWAY_AGENT_SESSION="deploy-lock-$$" \
  railway link --project "$PROJECT" --environment "$ENV" --service "$SERVICE" >/dev/null 2>&1 \
  || { echo "❌ railway link failed (auth/context)" >&2; exit 4; }
rw(){ RAILWAY_CALLER="skill:use-railway@1.2.0" RAILWAY_AGENT_SESSION="deploy-lock-$$" railway "$@"; }
now(){ date +%s; }
# 1. CHECK LOCK (shared Railway var DEPLOY_LOCK = holder|env|sha|epoch)
LOCK=$(rw variables --json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('DEPLOY_LOCK',''))" || echo "")
if [ -n "$LOCK" ]; then
  TS=$(echo "$LOCK"|awk -F'|' '{print $4}'); N=$(now)
  if [ -n "$TS" ] && [ $((N-TS)) -lt $TTL ]; then
    echo "❌ ABORT: deploy in progress — [$LOCK] held $((N-TS))s ago (< ${TTL}s). Serialize (prod-deploy-control.md §1)." >&2; exit 2
  fi
  echo "⚠️  stale lock [$LOCK] (> ${TTL}s) — reclaiming."
fi
# 2. CLAIM
rw variables --set "DEPLOY_LOCK=${HOLDER}|${ENV}|${SHA:0:12}|$(now)" >/dev/null
echo "🔒 lock claimed: $HOLDER on $ENV @ ${SHA:0:12} (TTL ${TTL}s)"
# tripwire feed: record this locked deploy in LOCKED_DEPLOY_LOG (last 10 short-SHAs, comma-sep) so
# scripts/deploy_tripwire.sh can detect a prod SHA that never claimed the lock (an unlocked deploy).
_LOG=$(rw variables --json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('LOCKED_DEPLOY_LOG',''))" || echo "")
_NEW=$(printf "%s,%s" "${SHA:0:12}" "$_LOG" | tr ',' '\n' | awk 'NF' | head -10 | paste -sd, -)
rw variables --set "LOCKED_DEPLOY_LOG=$_NEW" >/dev/null 2>&1 || true
# 3. ANCESTRY GATE (load-bearing safety commits must be ancestors of the deploy tree)
FAIL=0; for c in bc3cb4b 5852ea1 944939b 27bfd3b 8079caa 7a57107; do
  git merge-base --is-ancestor $c "$SHA" 2>/dev/null || { echo "❌ ancestry: $c NOT ancestor of $SHA"; FAIL=1; }; done
[ $FAIL -eq 1 ] && { echo "ABORT: ancestry gate failed."; rw variables delete DEPLOY_LOCK >/dev/null 2>&1||true; exit 3; }
echo "✅ ancestry gate passed"
# 4. cache-bust hygiene (full-SHA ARG; delete the lying SAGE_BUILD_SHA override)
rw variables delete SAGE_BUILD_SHA >/dev/null 2>&1 || true
rw variables --set "RAILWAY_GIT_COMMIT_SHA=$SHA" >/dev/null
echo "✅ cache-bust set: RAILWAY_GIT_COMMIT_SHA=$SHA · SAGE_BUILD_SHA deleted (derives from ARG)"
echo ""
echo "NEXT (still yours to run, the lock is held ${TTL}s): from a worktree detached at origin/master ($SHA):"
echo "  railway up --detach -c -m '<msg>'"
echo "Then MANDATORY behavioral probe (health SHA is necessary-not-sufficient) + verify crisis_copy_templated."
echo "Release when verified:  railway variables --set DEPLOY_LOCK='' ... (or let the ${TTL}s TTL expire)."
