# DPIA Finding: E2E Test Identity — Cross-User Clinical Data Access

**Finding date:** 2026-05-30  
**Severity:** High — past access event; assess for PDPL notifiability  
**Status:** Structurally mitigated — seed fix applied 2026-05-30; migration 013 applied and adversarially verified 2026-05-30  
**Owner:** Rohan Sarda  
**DPO action required:** Yes — breach assessment in §5 is open; DPO notified 2026-05-30

---

## §1 What Happened

This is a record of a processing activity that **already occurred**, not a hypothetical
future risk. The E2E test suite has been running with `is_admin: true` in the
`user_profiles` seed since the automated tests were introduced. Every run of
`global-setup.ts` against the production Supabase project set this flag for the
`sage-e2e@test.internal` identity.

Three RLS policies gate access to clinical monitoring tables on `user_profiles.is_admin`
rather than on the canonical `user_roles` table introduced in migration 011:

| Table | Policy | What was accessible |
|---|---|---|
| `session_audit` | "admin_read" | All rows: turn-by-turn `crisis_state`, `clinical_flags`, `emotional_intensity`, `node_path`, `user_id`, `session_id` for every clinical user |
| `clinician_review_queue` | "admin read review queue" | All clinical flag reviews across all users |
| `message_feedback` | "admin read feedback" | All user feedback across all users |

The `sync_is_admin` trigger fires on `INSERT/DELETE` to `user_roles`, not on
`user_profiles` upserts. The seed bypassed the canonical path and left
`is_admin = true` without a corresponding privileged `user_roles` entry.
The middleware's 403 check uses `v_user_roles_for_tenant`; the RLS layer used the
legacy `is_admin` field. Two systems disagreed; the permissive one determined access.

---

## §2 Data Scope

| Attribute | Value |
|---|---|
| Processing activity | Automated E2E test execution against production Supabase project |
| Data subjects | All clinical users whose `session_audit`, `clinician_review_queue`, or `message_feedback` rows existed during any E2E test run |
| Personal data categories | Pseudonymised `user_id`; mental health indicators (`crisis_state`, `clinical_flags`, `emotional_intensity`); behavioural data (`node_path`, `primary_intent`); clinical review records; user feedback |
| Legal basis | None established for synthetic test access to real clinical data |
| Data residency | Supabase project — AWS ap-south-1 (UAE region) |
| Period of exposure | From first E2E test run with `is_admin: true` to 2026-05-30 (seed fixed) |
| Access mechanism | SELECT via Supabase anon client with JWT for `sage-e2e@test.internal`; same API path as application code |
| Sovereignty constraint | DESC/NCA controls require logged, authorised access to UAE-resident clinical data. This access had no DPO authorisation and may not have been logged at the Supabase level |

---

## §3 Was the Data Actually Accessed?

**The DPO must determine this, not assume it.**

"Readable" and "read" are different findings. The `is_admin = true` flag granted the
*capability* to read cross-user clinical data. Whether the E2E identity ever exercised
that capability depends on whether any test called Supabase API endpoints that query
these three tables.

**Important:** The canonical record of "what did this identity touch" may live in
connection/query logs rather than per-table access logs. The log pull below must cover
the E2E user's **full auth and session activity** over the entire exposure window,
not just queries against the three monitored tables.

**Critical limitation on evidence:** Absence of a logged read is only exculpatory if
read-logging was actually enabled and complete for the entire exposure period.
"No reads found" with incomplete or disabled logging is not "no reads occurred."
The DPO must explicitly confirm which DESC/NCA logging controls were in force (Postgres
statement logging, Supabase API request logging, Logflare retention) and document that
finding in §5. Asserting "no reads occurred" on the basis of incomplete logs is not
defensible under PDPL audit.

Action required before DPO sign-off:

1. **Run `supabase/pull-e2e-logs.ts`** to export and preserve the E2E user's auth
   event history from `auth.audit_log_entries`. This establishes the session timeline:
   when the identity was active and therefore *could* have issued queries. Output is
   saved to `docs/compliance/e2e-audit-log-export-<timestamp>.json` — commit to repo
   for durable record. Run the script immediately; auth log retention is finite.

   ```
   npx ts-node supabase/pull-e2e-logs.ts
   ```

2. **Check Supabase API request logs** (Supabase dashboard → Logs → API Logs) for any
   requests originating from the `sage-e2e@test.internal` JWT. Filter by user ID
   (obtain from the script output). Look for any `GET /rest/v1/session_audit`,
   `GET /rest/v1/clinician_review_queue`, or `GET /rest/v1/message_feedback` calls,
   AND for any other API path the E2E identity called during its sessions. These HTTP
   logs are the most direct evidence of what API surface was touched.

3. **Note Supabase API log retention:** Supabase API logs have a retention window
   (1 day on Free, 7 days on Pro, up to 90 days on Enterprise). If the retention window
   has passed, state this explicitly in §5 and treat the "no reads found" finding as
   indeterminate, not exculpatory.

4. **Review the E2E spec files** for any test that calls Supabase directly (not just
   the UI). The current suite tests UI flows only; the service-role admin client in
   `global-setup.ts` is used for seeding only (INSERT/UPSERT), not SELECT on
   clinical tables. This is corroborating evidence but does not substitute for the log check.

5. **If no SELECT logs exist and logging was complete:** the access was readable but not
   read. This affects the breach assessment level (§5).

6. **If SELECT logs exist or logging cannot be confirmed complete:** document which
   rows, on which dates, under which run. This is the scope for any notification
   obligation. Treat incomplete-logging-period as worst-case for assessment purposes.

---

## §4 Actions Taken

### Immediate (2026-05-30 — applied)
- `global-setup.ts` seed changed to `is_admin: false`. The E2E identity no longer
  holds admin privileges in `user_profiles`. This closes the capability gap
  immediately for any future test run.
- Confirmed no E2E assertion depends on `is_admin` for the 403 test (STATE-1 uses
  `v_user_roles_for_tenant`); no E2E test functionality broken.

### Before Gitex demo (COMPLETE — applied and verified 2026-05-30)
- `013_rls_rbac_migration.sql` applied: the three `is_admin`-gated RLS policies
  (`admin_read`, `admin read review queue`, `admin read feedback`) are confirmed absent.
  Three new `user_roles`-gated policies (`staff_read`, `staff_read_review_queue`,
  `staff_read_feedback`) are confirmed present. Verified via `supabase db query --linked`
  against `pg_policies`. Migration history record repaired: 013 marked applied.
- `supabase/verify-rls-013.ts` run 2026-05-30: **5/5 assertions passed.**
  Member identity (no `user_roles` entry, `is_admin = false`) got zero rows from
  all three tables. Clinical reviewer got non-zero rows from `session_audit` and
  `clinician_review_queue`. RLS posture is adversarially verified.

### Post-Gitex (deferred)
- Stand up separate Supabase branch/project for E2E. Synthetic identities must not
  transit production `auth.users`. This is tolerable for Gitex POC if migration 013
  is verified; it is not a permanent state.
- Drop `is_admin` column and `sync_is_admin` trigger (migration 014) once all
  remaining references confirmed dead. The is_admin reference sweep (2026-05-30)
  found zero application code or Python backend references. Only schema/trigger
  remains after 013 applies.
- Scope `sage-e2e@test.internal` to `member` role in `user_roles` explicitly.
- Seal `sage@cdai.ae` as real break-glass: disable direct login, wire Supabase auth
  hook on login event, document unsealing procedure in-repo.
- Migrate master admin from `rohansarda@gmail.com` to managed `@cdai.ae` identity
  with enforced MFA and a second named human admin; retire the personal Gmail.

---

## §5 Breach Assessment — DPO Action Required

Under PDPL Art. 23–25 and the v7 compliance baseline (DESC/NCA controls), the DPO
must assess whether this constitutes a notifiable personal data breach.

**The relevant question is not "could data be accessed" but "was it accessed."**
The answer depends on the Supabase access log review in §3. The DPO should assess:

1. Was the `sage-e2e@test.internal` identity ever used to SELECT from `session_audit`,
   `clinician_review_queue`, or `message_feedback`? (Check Supabase API logs — see §3.)

2. If yes: what is the scope (rows, user IDs, dates)? Does it meet the PDPL threshold
   for notification to the PDPC within 72 hours?

3. If no SELECT occurred: the finding is an unauthorized access *capability* that
   existed during the exposure window, now closed. Assess whether capability-only
   findings require reporting under the applicable DESC/NCA control set.

4. Regardless of notification outcome: document this as a processing activity that
   occurred without a DPIA entry and without DPO authorisation. Future E2E runs
   against any production-adjacent environment require a documented legal basis and
   DPO sign-off on the RLS posture.

**This section must be completed and signed off by the DPO before any user-facing
production deployment. The Gitex demo carve-out below does not substitute for this.**

---

## §6 Gitex Demo Carve-Out

The Gitex demo may proceed under the following conditions. All three must be true:

1. Migration 013 is applied and `supabase/verify-rls-013.ts` passes with zero failures.

2. The demo environment's `session_audit`, `clinician_review_queue`, and
   `message_feedback` tables contain **zero real clinical user rows** at demo time.
   "Confirmed-non-clinical seed" is not sufficient — if the demo runs against the
   shared production project, real rows from previous interactions are present in
   those tables regardless of what the demo seed inserts. The clean version: demo
   against an isolated environment (Supabase branch or separate project) with no
   real user data in those three tables, OR confirm via a COUNT query immediately
   before the demo that those tables are empty of non-synthetic rows.

3. This document is on file and the DPO has been notified of the finding (even if
   the breach assessment in §5 is still in progress).

**This carve-out gates the demo only. It does not substitute for the §5 DPO
assessment or the full production deployment sign-off.**

---

## §7 Reference

- `supabase/migrations/013_rls_rbac_migration.sql` — structural fix (applied + verified 2026-05-30)
- `supabase/verify-rls-013.ts` — adversarial RLS verification script (5/5 passed 2026-05-30)
- `supabase/pull-e2e-logs.ts` — log-pull script; run to export E2E user auth events
- `docs/compliance/e2e-audit-log-export-*.json` — durable auth record (committed 2026-05-30)
- `docs/compliance/DPO-NOTIFICATION-2026-05-30.md` — DPO notification letter
- `cdai/apps/web/playwright/global-setup.ts` — seed fix applied 2026-05-30
- is_admin reference sweep: 39 references found, all in migrations + seed; zero in
  application code or Python backend (confirmed 2026-05-30)
- E2E user UUID: `706b613e-4012-4f13-a9fa-ab97f3f8a65b`; created 2026-05-21, last sign-in 2026-05-30
