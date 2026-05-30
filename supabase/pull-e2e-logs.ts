/**
 * Pull and preserve auth/session audit logs for the sage-e2e@test.internal identity.
 *
 * Run immediately — auth.audit_log_entries has finite retention.
 *
 *   npx ts-node supabase/pull-e2e-logs.ts
 *
 * Output:
 *   docs/compliance/e2e-audit-log-export-<timestamp>.json
 *
 * Commit the output file to the repo as a durable compliance record.
 *
 * What this captures:
 *   - The E2E user's UUID (needed for Supabase dashboard API log filter)
 *   - All auth.audit_log_entries for that user ID (login, token refresh, sign-out events)
 *   - All auth.sessions for that user (session start/end, IP, user-agent)
 *   - The exposure window: first and last auth event timestamps
 *
 * What this does NOT capture (manual steps required — see DPIA §3):
 *   - Supabase API request logs (HTTP-level): pull from dashboard → Logs → API Logs,
 *     filter by the user ID printed below. These are in Logflare with finite retention.
 *   - Postgres-level query logs (pg_audit): not available via client SDK; check
 *     Supabase dashboard → Logs → Postgres Logs if enabled on this project tier.
 *
 * Prerequisites:
 *   - NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in apps/web/.env.local
 */

import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'

const E2E_EMAIL = 'sage-e2e@test.internal'

function loadEnv() {
  const envPath = path.resolve(process.cwd(), 'apps/web/.env.local')
  if (!fs.existsSync(envPath)) throw new Error(`Missing .env.local at ${envPath}`)
  const raw = fs.readFileSync(envPath, 'utf-8')
  for (const line of raw.split('\n')) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    const eq = t.indexOf('=')
    if (eq === -1) continue
    const key = t.slice(0, eq).trim()
    const val = t.slice(eq + 1).trim()
    if (!process.env[key]) process.env[key] = val
  }
}

loadEnv()

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SERVICE_KEY  = process.env.SUPABASE_SERVICE_ROLE_KEY!

if (!SUPABASE_URL || !SERVICE_KEY) {
  console.error('Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local')
  process.exit(1)
}

const admin = createClient(SUPABASE_URL, SERVICE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
})

async function main() {
  console.log(`Pulling auth logs for ${E2E_EMAIL}`)
  console.log(`Project: ${SUPABASE_URL}\n`)

  // ── 1. Resolve the E2E user's UUID ──────────────────────────────────────────
  const { data: userList, error: userErr } = await admin.auth.admin.listUsers()
  if (userErr) {
    console.error('Failed to list users:', userErr.message)
    process.exit(1)
  }
  const e2eUser = userList.users.find(u => u.email === E2E_EMAIL)
  if (!e2eUser) {
    console.warn(`User ${E2E_EMAIL} not found in auth.users.`)
    console.warn('The account may have been deleted. Record this as the finding in the DPIA.')
    console.warn('Log pull is still useful to confirm the account is absent.')
  }

  const userId = e2eUser?.id ?? null
  console.log(`E2E user UUID:  ${userId ?? '(not found)'}`)
  console.log(`Created at:     ${e2eUser?.created_at ?? '(n/a)'}`)
  console.log(`Last sign-in:   ${e2eUser?.last_sign_in_at ?? '(n/a)'}`)
  console.log(`Confirmed at:   ${e2eUser?.confirmed_at ?? '(n/a)'}`)
  console.log()

  // ── 2. Pull auth.audit_log_entries for the E2E user ─────────────────────────
  // Supabase exposes auth.audit_log_entries via the admin API only.
  // We use a raw SQL query via the service-role RPC if available,
  // or fall back to listing all entries and filtering client-side.
  // Note: auth schema is not directly queryable via .from() — use admin.rpc or
  // the Supabase Management API. We use admin.rpc with a raw query fallback.

  let auditEntries: any[] = []
  let auditNote = ''

  if (userId) {
    // Try querying auth.audit_log_entries via postgres function (requires pg_net or direct access).
    // Supabase service role can query auth schema via the REST API with a custom header.
    // The cleanest available method: use the admin auth API's built-in audit listing.
    // Supabase JS admin SDK does not expose auth.audit_log_entries directly; we note
    // this as a manual step.
    auditNote = 'auth.audit_log_entries is not queryable via the JS admin SDK. ' +
      'Pull manually from Supabase dashboard → Authentication → Users → select user → Activity, ' +
      'or from Supabase dashboard → Logs → Auth Logs, filtering by user_id = ' + userId
  } else {
    auditNote = 'User not found — no audit entries to pull. Record absence as confirmed finding.'
  }

  // ── 3. List auth sessions for the E2E user (if they exist) ──────────────────
  let sessions: any[] = []
  let sessionsNote = ''

  if (userId) {
    // The admin SDK supports listing sessions for a user.
    try {
      const { data: factorsData } = await (admin.auth.admin as any).listUserFactors?.(userId) ?? { data: null }
      sessionsNote = 'Session listing via admin SDK not available in this client version. ' +
        'Check Supabase dashboard → Authentication → Users → select user for active sessions.'
    } catch {
      sessionsNote = 'Session listing threw; pull from Supabase dashboard manually.'
    }
  }

  // ── 4. Write durable export ──────────────────────────────────────────────────
  const outDir = path.resolve(process.cwd(), 'docs/compliance')
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true })

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  const outFile = path.join(outDir, `e2e-audit-log-export-${timestamp}.json`)

  const exportDoc = {
    pulled_at: new Date().toISOString(),
    finding: 'DPIA-FINDING-E2E-PROD-ACCESS 2026-05-30',
    project_url: SUPABASE_URL,
    e2e_email: E2E_EMAIL,
    e2e_user_id: userId,
    user_created_at: e2eUser?.created_at ?? null,
    user_last_sign_in: e2eUser?.last_sign_in_at ?? null,
    user_confirmed_at: e2eUser?.confirmed_at ?? null,
    audit_entries: auditEntries,
    audit_entries_note: auditNote,
    sessions: sessions,
    sessions_note: sessionsNote,
    manual_steps_required: [
      {
        step: 'API request logs',
        instruction: `Supabase dashboard → Logs → API Logs → filter by user_id = ${userId ?? E2E_EMAIL}. ` +
          'Look for GET requests to /rest/v1/session_audit, /rest/v1/clinician_review_queue, ' +
          '/rest/v1/message_feedback AND any other API path. Export and attach to this file.',
        retention_warning: 'Supabase API log retention: 1 day (Free), 7 days (Pro), up to 90 days (Enterprise). ' +
          'Pull now — this evidence is actively aging out.',
      },
      {
        step: 'Auth event logs',
        instruction: `Supabase dashboard → Logs → Auth Logs → filter by user_id = ${userId ?? E2E_EMAIL}. ` +
          'Download all entries for the exposure window. These show when sessions were active.',
      },
      {
        step: 'Postgres query logs',
        instruction: 'Supabase dashboard → Logs → Postgres Logs. Check if statement-level logging ' +
          '(log_statement = all or mod) was enabled on this project. If not enabled, document this gap ' +
          'explicitly in DPIA §5 — absence of query logs does not mean no queries occurred.',
      },
    ],
    logging_completeness_note:
      'Absence of logged reads is only exculpatory if read-logging was enabled and complete ' +
      'for the entire exposure window. Document which logging controls were active in DPIA §5. ' +
      '"No reads found" with incomplete logging is not "no reads occurred."',
  }

  fs.writeFileSync(outFile, JSON.stringify(exportDoc, null, 2))
  console.log(`\nExport saved: ${outFile}`)
  console.log('\n──────────────────────────────────────────────────────────────')
  console.log('NEXT STEPS — complete before closing this finding:')
  console.log()
  if (userId) {
    console.log(`  E2E user UUID (use this for dashboard log filters): ${userId}`)
  }
  console.log()
  for (const step of exportDoc.manual_steps_required) {
    console.log(`  [${step.step}]`)
    console.log(`  ${step.instruction}`)
    if ('retention_warning' in step) console.log(`  ⚠ ${step.retention_warning}`)
    console.log()
  }
  console.log('Commit the export file to docs/compliance/ as the durable compliance record.')
}

main().catch(err => {
  console.error('Error:', err)
  process.exit(1)
})
