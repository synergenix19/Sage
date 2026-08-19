# Ticket (SAFETY/COMPLIANCE): `/health/ready` returns 200 without a database — on PROD, not just staging

**Filed:** 2026-08-19 · **Status:** open
**Source:** staging forensics (ticket `2026-08-19-staging-nonfunctional-and-outside-flag-register.md`)
found the gap; this ticket records that **prod runs the same code path**
**Type:** health-signal defect on the live clinical surface, with an audit-trail consequence

## The defect

`server.py::health_ready` gates its 200 on exactly one condition:

```python
if not _bge_ready:
    raise HTTPException(status_code=503, ...)
return {"status": "ready", "routing_mode": ..., "reranker_head_control": ...}
```

There is **no database assertion**. Readiness reports the BGE warmup and the reranker head
control — both genuinely useful — and says nothing about whether the process can reach
Postgres. This is prod's code, not a staging variant.

Railway's healthcheck targets `/health/ready`, so a container that cannot reach the database is
marked healthy and is sent live traffic.

## This is not hypothetical — it already happened, in the environment we could observe

Staging ran in exactly this state on 2026-07-30 (its last logs):

- `POST /chat` answered **200 OK**
- every `session_audit` write failed: `[Errno -2] Name or service not known`
- `graph.checkpointer` was `None` (`AttributeError: 'NoneType' object has no attribute 'aget'`)
- and `/health/ready` returned **200 the whole time** — it still does today, with no database
  in existence behind it

So the failure mode is demonstrated, not theorised: **serve normally, persist nothing, report
healthy.** The only reason it was staging rather than prod is which tenant disappeared.

## Why this is a compliance problem, not only an ops one

`session_audit` is the PDPL audit trail — one row per turn is the design commitment. A silent
persistence failure on prod means clinical turns are served with **no audit record**, while every
health signal reads green. The gap would be invisible until someone queried for rows that were
never written, and would be unbounded in duration because nothing degrades or alarms.

Related: `write_session_audit` already fails soft by design (serving must not break because the
audit row failed). That is the right call for a single turn. It is the wrong outcome when the
database is gone entirely and *every* row fails, which is precisely the case readiness should
catch and does not.

## The meta-finding: this was recorded and then sat

The 2026-07-30 remediation record already carried it as deploy-ops finding 3:

> "Staging `DATABASE_URL` points at a dead Supabase tenant (ENOTFOUND) — staging audit
> persistence is broken; behavioral reads unaffected. **Owner: infra.**"

Correctly observed, correctly assigned, and untouched for three weeks — found again only because
a deploy rehearsal needed the environment. Same shape as CLAUDE.md PR #505 sitting open through
the incident it would have prevented: **a follow-up that is recorded but unowned does not
execute.** The phrase "behavioral reads unaffected" is also the exact reasoning that let staging
keep being used while its persistence was dead — true for routing checks, and quietly false for
anything asserting an audit row.

## Fix candidates

1. **Assert database reachability in readiness.** A `SELECT 1` against the existing pool, so a
   process with no database cannot report ready and cannot be handed traffic.
2. **Do not let it flap.** A transient blip should not cycle the service out of the load
   balancer: cache the probe result for a few seconds, or require N consecutive failures before
   withholding readiness. The goal is catching "the database is gone", not "one query was slow".
3. **Consider a distinct signal for audit-write health**, since audit failure is the consequence
   that matters most and can occur even when the pool is up (permissions, RLS, table drift).
4. Keep the existing BGE/reranker conditions exactly as they are — they are load-bearing for the
   deploy gate and this ticket does not touch them.
5. **Readback tooling must resolve the live host from Railway's own record, never from memory or
   a scratch note.** Scoped in here because it is the same surface: any script or runbook step
   that curls a health endpoint should read `RAILWAY_PUBLIC_DOMAIN` (or `railway domain`) at
   call time rather than carrying a hardcoded hostname.

   Near-miss, 2026-08-19 post-deploy verification: the readback was aimed at
   `sage-api-production-03c1.up.railway.app`, a stale domain carried in notes. The live host is
   `sage-api-production-3328.up.railway.app`. The stale host returned **404**, which parsed as a
   response body with no `cosine_abstain_threshold_raw_env` field — indistinguishable, at a
   glance, from *"the serving process has no abstain threshold set"*, i.e. the KB gate running
   fail-open in production. That reading would have triggered rollback motion on a safety gate
   that was in fact correctly configured. Caught only by checking whether the key was **absent**
   versus **present-and-null** before believing it.

   This is the recall-vs-readback rule striking a hostname rather than a value: a stale target
   makes a correct readback mechanism produce a false negative, and a 404 is not a measurement.

## Related

- `docs/superpowers/tickets/2026-08-19-staging-nonfunctional-and-outside-flag-register.md`
- `docs/superpowers/governance/2026-07-30-inc2-panic-override-remediation-record.md` (finding 3)
- Sibling class filed the same day: corpus sync fail-open silent chunk loss; abstain gate
  fail-open default. All three are "the failure was detectable and nothing asserted it".
