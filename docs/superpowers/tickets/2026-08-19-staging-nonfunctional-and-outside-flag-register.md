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

The project is deleted or otherwise unreachable. Prod (`tcekehffneiqcdyhzobi`) connects fine
from the same host and pooler, so this is not a credential or network problem.

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

## Related

- cdai PR #512 (ivfflat drop) — its staging rehearsal is blocked by layer 1
- PR #522 (fail-closed threshold) — makes layer 2 a boot error rather than silent fail-open
- `docs/superpowers/tickets/2026-08-19-abstain-threshold-fail-open-default.md`
