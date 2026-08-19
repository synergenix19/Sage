# Ticket: staging cannot rehearse anything — its database does not exist, and it sits outside flag-register discipline

**Filed:** 2026-08-19 · **Status:** open, BLOCKS the staging rehearsal of cdai PR #512
**Source:** attempting the owner-directed staging-first rehearsal of the ivfflat drop + threshold move
**Type:** environment-parity defect (two layers)

## Layer 1 — staging's database is gone

`DATABASE_URL` and `SUPABASE_URL` for the Railway `staging` environment both point at Supabase
project `jrfrficjdwguqbvumdyo`. Connecting fails, twice, deterministically:

```
asyncpg.exceptions.InternalServerError:
  (ENOTFOUND) tenant/user postgres.jrfrficjdwguqbvumdyo not found
```

Prod (`tcekehffneiqcdyhzobi`) connects fine from the same host and pooler seconds either side,
so this is not a credential or network problem.

### Forensics — the project existed, and we can date its disappearance

Staging genuinely had a database: migrations 004/005/006 were applied to `jrfrficjdwguqbvumdyo`
on 2026-07-03 and recorded at the time. It is gone now, and the evidence dates the loss to on or
before **2026-07-30**:

- **Both hostnames are NXDOMAIN** — `jrfrficjdwguqbvumdyo.supabase.co` and
  `db.jrfrficjdwguqbvumdyo.supabase.co` do not resolve at all, and the REST endpoint is
  unreachable (curl exit 6, could not resolve host). This distinguishes removal from a *pause*:
  a paused Supabase project keeps its DNS records and answers on the API hostname.
- **The staging container was already failing to resolve it on 2026-07-30**, from inside
  Railway, with the same class of error:
  ```
  audit pre-check could not verify user kwdbg-probe-user-2026-07-30: [Errno -2] Name or service not known
  session_audit write failed: [Errno -2] Name or service not known
  ```
  Eight such lines in that day's logs, which are the **last logs the environment has**.
- The same run shows `AttributeError: 'NoneType' object has no attribute 'aget'` on
  `graph.checkpointer` — the checkpointer never initialised, consistent with the DB being
  unreachable at startup.
- No alternative staging project ref exists anywhere in the repo, and there is no
  `.env.staging`, so this is not a case of the variables merely being stale relative to a
  newer project.

### The reason nobody noticed: staging reports healthy without a database

`GET /health/ready` on staging returns **200** right now, with no database behind it. On
2026-07-30 the service answered `POST /chat` with **200 OK** while every `session_audit` write
failed and no checkpointer existed. So staging has been serving chat traffic that persisted
nothing, behind a green readiness probe.

That is a defect in its own right: **readiness does not assert database connectivity**, so the
one signal an operator would check reports fine in exactly the situation that matters. Combined
with layer 2 below (the abstain gate running fail-open there), any eval or bench run pointed at
staging since 2026-07-30 produced results with no persistence and no abstain gate — while
looking healthy.

`/health/version` returns **404** on staging, so the deployment also predates the readback
widening: staging has not been redeployed in weeks, which is why the fail-closed boot change
has not surfaced there yet.

**Consequence:** staging cannot serve retrieval, cannot receive migration 018, and cannot run
the 24-query probe set. **Any plan that treats staging as a pre-prod rehearsal is currently
unfounded.** Note this also resolves a stale belief in the project record that staging *shares*
the prod Supabase — it does not; it points at a separate project, which happens to be dead.

## Layer 2 — staging is outside flag-register discipline

`config/prod_flags.yaml` is scoped `environment: production`. Nothing asserts staging's flag
set at all, and the drift is real today:

| flag | production | staging |
|---|---|---|
| `SAGE_COSINE_ABSTAIN_THRESHOLD` | `0.42` | **absent** |
| SAGE_* vars present | (full register) | 13 |

Because the threshold is absent, staging has been running the **KB abstain gate fail-open** —
retrieval never abstains. So even with a working database, staging would have diverged from
prod on a safety gate, and any retrieval behaviour observed there would not have been evidence
about prod.

As of PR #522 this also becomes a **boot failure**: an unset threshold now raises, so the next
staging deploy will not start until the variable is set.

## Why this is more than an inconvenience

Safety-flag parity between environments currently depends on someone noticing. That is the same
shape as the two defects filed alongside this one — the corpus tear and the fail-open threshold
default — where the guard existed but nothing asserted it mechanically. A staging environment
that silently disagrees with prod on a safety gate is worse than no staging environment,
because it produces evidence that reads as reassuring.

## Fix candidates

1. **Decide staging's status deliberately.** Either restore a staging Supabase project and
   re-point `DATABASE_URL`/`SUPABASE_URL`, or retire the environment explicitly. The current
   middle state — configured, referenced in plans, non-functional — is the worst of the three.
2. **Extend the register to cover every environment.** Give `prod_flags.yaml` a per-environment
   section (or a sibling `staging_flags.yaml`) and have `apply_prod_flags.py` / the parity guard
   assert **safety-class flags in every environment**, not just production. A safety flag
   missing from an environment should fail CI the way an unregistered flag already does.
3. **Minimum immediate step**, if staging is to be kept: set `SAGE_COSINE_ABSTAIN_THRESHOLD` in
   staging to match the value prod is serving, before the next staging deploy — otherwise that
   deploy fails at boot.
4. **Make readiness tell the truth.** `/health/ready` should not return 200 when the database is
   unreachable. Had it failed closed, this would have been visible on 2026-07-30 instead of
   being discovered three weeks later while trying to rehearse a deploy on it. This is the same
   pattern as the other two findings filed today — the failure was detectable and nothing
   asserted it — and it is the cheapest of the three to fix.

## Related

- cdai PR #512 (ivfflat drop) — its staging rehearsal is blocked by layer 1
- PR #522 (fail-closed threshold) — makes layer 2 a boot error rather than silent fail-open
- `docs/superpowers/tickets/2026-08-19-abstain-threshold-fail-open-default.md`
