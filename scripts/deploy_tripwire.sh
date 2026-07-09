#!/usr/bin/env bash
# Deploy tripwire (#225): FAIL LOUD if prod's live SHA never claimed the deploy lock — i.e. someone
# deployed bypassing scripts/deploy_prod.sh. A control that only binds the compliant is not a control.
# Run periodically (cron) or in CI. Exit 1 on a detected unlocked deploy. Complements the durable
# build-side check (server-side enforcement) — see the #225 build-side follow-up.
set -euo pipefail
PROJECT=4f1811e7-cab2-4002-9107-a9f782f2f274; SERVICE=160e9f65-e3c8-409a-b647-fbe2339a265d
PURL=https://sage-api-production-3328.up.railway.app
rw(){ RAILWAY_CALLER="skill:use-railway@1.2.0" RAILWAY_AGENT_SESSION="tripwire-$$" railway "$@"; }
RAILWAY_CALLER="skill:use-railway@1.2.0" RAILWAY_AGENT_SESSION="tripwire-$$" railway link --project "$PROJECT" --environment production --service "$SERVICE" >/dev/null 2>&1
KEY=$(rw variables --json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('SAGE_API_KEY',''))")
LOG=$(rw variables --json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('LOCKED_DEPLOY_LOG',''))")
PROD_SHA=$(curl -s -m 10 -H "X-Sage-Api-Key: $KEY" "$PURL/health/version" | python3 -c "import sys,json;print(json.load(sys.stdin).get('build_sha','')[:12])")
if [ -z "$PROD_SHA" ]; then echo "TRIPWIRE: could not read prod SHA" >&2; exit 3; fi
if echo ",$LOG," | grep -q ",${PROD_SHA:0:12},"; then
  echo "✅ tripwire OK: prod ${PROD_SHA} claimed the lock (in LOCKED_DEPLOY_LOG)."
else
  echo "🚨 TRIPWIRE FIRED: prod is ${PROD_SHA} but that SHA NEVER claimed the deploy lock." >&2
  echo "   -> a deploy bypassed scripts/deploy_prod.sh (the #225 serialize case). LOCKED_DEPLOY_LOG=[$LOG]" >&2
  echo "   Investigate: who deployed, why the bypass, and whether it clobbered (git merge-base --is-ancestor <safety-shas> $PROD_SHA)." >&2
  exit 1
fi
