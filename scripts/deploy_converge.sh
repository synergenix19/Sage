#!/usr/bin/env bash
# Behavioral deploy convergence — NEVER build_sha (three SHA-lie instances 2026-08:
# the cache-bust variable-set restarts the OLD image with the NEW RAILWAY_GIT_COMMIT_SHA
# env, so /health/version reports the new SHA while old code serves; probes taken in
# that window recorded real-looking failures against the wrong build).
#
# Convergence = BOTH of:
#   1. Railway's latest deployment status == SUCCESS (the platform's own signal), and
#   2. a caller-supplied BEHAVIORAL probe of the change itself passing (grep pattern
#      against a curl of the serving system) — because SUCCESS says the container is up,
#      not that the router has cut traffic over.
#
# Usage: deploy_converge.sh '<probe-cmd producing output>' '<grep-pattern>' [timeout_s]
# Example:
#   deploy_converge.sh \
#     'curl -s $URL/health/version -H "X-Sage-Api-Key: $KEY"' 'modality_request_routing_enabled' 600
set -euo pipefail
PROBE_CMD="${1:?probe command required}"; PATTERN="${2:?grep pattern required}"; TIMEOUT="${3:-600}"
rw(){ RAILWAY_CALLER="skill:use-railway@1.2.0" railway "$@"; }
DEADLINE=$(( $(date +%s) + TIMEOUT ))
echo "⏳ waiting for deployment SUCCESS (platform signal)..."
while :; do
  ST=$(rw status --json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
def walk(o):
    if isinstance(o,dict):
        if o.get('latestDeployment'): yield o['latestDeployment']
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
deps=list(walk(d)); print(deps[0].get('status','?') if deps else '?')" || echo "?")
  case "$ST" in
    SUCCESS) echo "✅ deployment SUCCESS"; break;;
    FAILED|CRASHED|REMOVED) echo "❌ deployment $ST" >&2; exit 2;;
  esac
  [ "$(date +%s)" -ge "$DEADLINE" ] && { echo "❌ timeout waiting for SUCCESS" >&2; exit 3; }
  sleep 15
done
echo "⏳ waiting for BEHAVIORAL convergence (pattern: $PATTERN)..."
OK=0
while :; do
  if eval "$PROBE_CMD" 2>/dev/null | grep -qE "$PATTERN"; then
    OK=$((OK+1)); [ "$OK" -ge 2 ] && { echo "✅ behaviorally converged (2 consecutive probe passes)"; exit 0; }
  else
    OK=0
  fi
  [ "$(date +%s)" -ge "$DEADLINE" ] && { echo "❌ timeout: SUCCESS reached but probe never passed — old image may still serve; DO NOT record probe results as the new build's" >&2; exit 4; }
  sleep 15
done
