# DPO Notification — Personal Data Incident: E2E Test Identity Access

**To:** DPO  
**From:** Rohan Sarda (synergenix.global@gmail.com)  
**Date:** 2026-05-30  
**Subject:** PDPL Incident Notification — E2E Test Identity with Unauthorized Clinical Data Access Capability  
**Reference:** DPIA-FINDING-E2E-PROD-ACCESS (docs/compliance/DPIA-FINDING-E2E-PROD-ACCESS.md)

---

## What I am notifying you of

On 2026-05-30 during a security review, I identified that the automated E2E test
identity (`sage-e2e@test.internal`) has held `is_admin = true` in the production
Supabase project since its creation on **2026-05-21**. This flag gated three legacy
RLS policies on clinical monitoring tables, granting SELECT access to sensitive
health data belonging to all users:

| Table | Data accessible |
|---|---|
| `session_audit` | `crisis_state`, `clinical_flags`, `emotional_intensity`, `node_path` for all users |
| `clinician_review_queue` | All clinical flag reviews across all users |
| `message_feedback` | All user feedback across all users |

The legal basis for an automated test identity to access production clinical data
was never established. This was not an authorised processing activity.

---

## What has been done

**As of 2026-05-30 (today):**

1. The E2E seed has been corrected — `sage-e2e@test.internal` now seeds with
   `is_admin: false`. No future test run will grant this identity admin privileges.

2. Migration 013 has been applied and adversarially verified: the three
   `is_admin`-gated RLS policies have been dropped and replaced with
   `user_roles`-based policies. A member identity with any `is_admin` value now
   receives zero rows from all three tables. Verified by `supabase/verify-rls-013.ts`
   (5/5 assertions passed).

3. An auth log export for the E2E identity has been preserved to
   `docs/compliance/e2e-audit-log-export-<timestamp>.json`. The E2E user
   UUID is `706b613e-4012-4f13-a9fa-ab97f3f8a65b`.

The capability gap is **closed**. The open question is whether the capability was
ever exercised.

---

## POC context

**This project is in Proof of Concept phase as of 2026-05-30.** No real clinical users
have been onboarded. The data subjects who could have been affected by this finding are
limited to internal developers and testers who interacted during the POC window.

This materially affects the breach assessment: PDPL notification obligations and the
72-hour PDPC clock apply to breaches affecting real data subjects. The DPO should
characterise the actual subject population and assess notification thresholds accordingly.
This finding still requires DPO sign-off before any real-user onboarding — the value
of closing it now is that it cannot become a live-user incident.

## What I need you to determine

**The key question for PDPL Art. 23–25:**

Was the `sage-e2e@test.internal` identity ever used to SELECT from these three tables?

To answer this, you need to:

1. **Pull the Supabase API request logs** for user ID
   `706b613e-4012-4f13-a9fa-ab97f3f8a65b`:
   - Supabase dashboard → Logs → API Logs → filter by `user_id`
   - Look for any GET requests to `/rest/v1/session_audit`,
     `/rest/v1/clinician_review_queue`, or `/rest/v1/message_feedback`
   - Also review **all** API paths touched by this identity during its sessions —
     the complete picture matters, not just the three tables
   - **Urgency:** Supabase API log retention is finite (1 day on Free, 7 days on Pro).
     The exposure window started 2026-05-21. If the retention window has passed,
     those logs are gone and the finding becomes indeterminate.

2. **Pull the Supabase Auth logs** for the same user ID:
   - Supabase dashboard → Logs → Auth Logs → filter by `user_id`
   - These show when sessions were active and therefore when queries *could* have
     been issued, even if API logs are no longer available.

3. **Check whether Postgres statement logging was enabled** on this project
   (Supabase dashboard → Logs → Postgres Logs). If `log_statement = all` or `mod`
   was active, query logs may exist there. If it was not enabled, document this gap
   explicitly — absence of logs under incomplete logging is not exculpatory.

4. **Make the breach vs. capability-gap determination:**
   - If no SELECT calls are found **and** logging was complete: capability-only
     finding. Assess whether unauthorized-access capability (without exercise)
     requires PDPC notification under the DESC/NCA control set.
   - If SELECT calls exist: document scope (rows, dates, run IDs) and assess
     against the PDPL notification threshold.
   - If logging was incomplete: treat as worst-case for the assessment.

---

## Exposure window

| Event | Timestamp |
|---|---|
| E2E identity created (`is_admin: true` seeded) | 2026-05-21T21:26:26Z |
| Last sign-in (seed fix run, `is_admin` corrected) | 2026-05-30T11:24:41Z |
| Migration 013 applied + verified | 2026-05-30 |
| Log export preserved | 2026-05-30T13:03:31Z |

Exposure duration: **approximately 9 days**.

---

## Reference documents

- `docs/compliance/DPIA-FINDING-E2E-PROD-ACCESS.md` — full finding, root cause,
  data scope, actions taken, breach assessment framework
- `docs/compliance/e2e-audit-log-export-*.json` — durable auth record for the
  E2E identity; commit to repo
- `supabase/verify-rls-013.ts` — adversarial verification script (run record: 2026-05-30)
- `supabase/migrations/013_rls_rbac_migration.sql` — structural fix

---

## Your action items

| Item | Urgency |
|---|---|
| Pull Supabase API logs for the E2E user ID before retention window expires | **Immediate** |
| Pull Supabase Auth logs for the same user | Today |
| Check Postgres statement logging status | Today |
| Determine: breach vs. capability-gap | Before any production user-facing deployment |
| Sign off on §5 of the DPIA | Before Gitex demo (condition 3 of Gitex carve-out) |

The Gitex demo carve-out in the DPIA (§6) permits the demo to proceed once:
1. Migration 013 is applied and verified — **DONE**
2. Demo environment tables contain zero real clinical rows — **your check before demo**
3. This notification is on file — **this document satisfies condition 3**

The §5 breach assessment remains yours to close. The 72-hour PDPC clock, if applicable,
runs from the date you determine a notifiable breach has occurred — not from this
notification to you.

Please acknowledge receipt.

Rohan
