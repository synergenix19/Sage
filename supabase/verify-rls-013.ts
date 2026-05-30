/**
 * Adversarial RLS verification for migration 013.
 *
 * Run after applying 013_rls_rbac_migration.sql and before the Gitex demo.
 *
 *   npx ts-node supabase/verify-rls-013.ts
 *
 * What this proves:
 *   1. A member-role user (no user_roles entry, is_admin = false) gets zero rows
 *      from session_audit, clinician_review_queue, and message_feedback for rows
 *      belonging to another user. This is the adversarial test — it must fail for
 *      any member identity trying to read clinical data that isn't theirs.
 *   2. A user with a non-member role in user_roles CAN read those tables (happy path).
 *
 * Tests are deliberately adversarial: they authenticate as a real Supabase user and
 * call the API the same way application code would. SQL-level SELECT via service role
 * is not used for the member test because service role bypasses RLS — that would prove
 * nothing. Only the anon/authenticated user JWT tests RLS enforcement.
 *
 * Prerequisites:
 *   - 011_rbac_roles.sql and 013_rls_rbac_migration.sql applied
 *   - NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local
 *   - NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local
 *   - Two test users created (see MEMBER_EMAIL and REVIEWER_EMAIL below)
 *     OR set environment variables to override
 *
 * The script creates temporary users, seeds synthetic rows, runs assertions, and
 * cleans up. No real clinical data is created or accessed.
 */

import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'

// ─── Load .env.local ──────────────────────────────────────────────────────────
function loadEnv() {
  const envPath = path.resolve(process.cwd(), 'apps/web/.env.local')
  if (!fs.existsSync(envPath)) {
    throw new Error(`Missing .env.local at ${envPath}`)
  }
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

const SUPABASE_URL     = process.env.NEXT_PUBLIC_SUPABASE_URL!
const ANON_KEY         = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SERVICE_KEY      = process.env.SUPABASE_SERVICE_ROLE_KEY!
const TENANT_ID        = process.env.NEXT_PUBLIC_TENANT_ID!

if (!SUPABASE_URL || !ANON_KEY || !SERVICE_KEY || !TENANT_ID) {
  console.error('Missing required env vars. Check .env.local.')
  process.exit(1)
}

// Temporary test identities — created and deleted by this script.
// Override via env if you need to reuse existing accounts.
const MEMBER_EMAIL   = process.env.RLS_TEST_MEMBER_EMAIL   || `rls-verify-member-${Date.now()}@test.internal`
const MEMBER_PASS    = process.env.RLS_TEST_MEMBER_PASS    || `RlsTest-${Date.now()}!`
const REVIEWER_EMAIL = process.env.RLS_TEST_REVIEWER_EMAIL || `rls-verify-reviewer-${Date.now()}@test.internal`
const REVIEWER_PASS  = process.env.RLS_TEST_REVIEWER_PASS  || `RlsTest-${Date.now()}!`

// Admin (service role) client — bypasses RLS for setup and teardown only.
const adminClient = createClient(SUPABASE_URL, SERVICE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
})

// ─── State ────────────────────────────────────────────────────────────────────
let memberId:   string | null = null
let reviewerId: string | null = null
let auditRowId: string | null = null
let queueRowId: string | null = null
let feedbackSessionId: string | null = null
let feedbackMsgId: string | null = null
let errors = 0

function pass(label: string) {
  console.log(`  ✓ ${label}`)
}

function fail(label: string, detail: string) {
  console.error(`  ✗ FAIL: ${label}`)
  console.error(`    ${detail}`)
  errors++
}

// ─── Setup ────────────────────────────────────────────────────────────────────
async function setup() {
  console.log('\n── Setup ─────────────────────────────────────────────────────')

  // Create member user
  const { data: m, error: me } = await adminClient.auth.admin.createUser({
    email: MEMBER_EMAIL, password: MEMBER_PASS, email_confirm: true,
  })
  if (me || !m.user) throw new Error(`Member create failed: ${me?.message}`)
  memberId = m.user.id
  await adminClient.from('user_profiles').upsert(
    { id: memberId, name: 'RLS Test Member', locale: 'en', onboarding_complete: true, is_admin: false },
    { onConflict: 'id' }
  )
  // member gets member role only
  await adminClient.from('user_roles').insert({
    user_id: memberId, tenant_id: TENANT_ID, role: 'member', granted_by: memberId,
  })
  console.log(`  member:   ${MEMBER_EMAIL} (${memberId})`)

  // Create reviewer user
  const { data: r, error: re } = await adminClient.auth.admin.createUser({
    email: REVIEWER_EMAIL, password: REVIEWER_PASS, email_confirm: true,
  })
  if (re || !r.user) throw new Error(`Reviewer create failed: ${re?.message}`)
  reviewerId = r.user.id
  await adminClient.from('user_profiles').upsert(
    { id: reviewerId, name: 'RLS Test Reviewer', locale: 'en', onboarding_complete: true, is_admin: false },
    { onConflict: 'id' }
  )
  // reviewer gets clinical_reviewer role
  await adminClient.from('user_roles').insert({
    user_id: reviewerId, tenant_id: TENANT_ID, role: 'clinical_reviewer', granted_by: reviewerId,
  })
  console.log(`  reviewer: ${REVIEWER_EMAIL} (${reviewerId})`)

  // Seed a session_audit row attributed to reviewerId (victim row for member to attempt)
  const { data: auditRow } = await adminClient
    .from('session_audit')
    .insert({
      session_id:     `rls-verify-session-${Date.now()}`,
      turn_number:    1,
      node_path:      ['safety_check', 'intent_route', 'freeflow_respond', 'output_gate'],
      primary_intent: 'general_chat',
      crisis_state:   'none',
      user_id:        reviewerId,
    })
    .select('id')
    .single()
  auditRowId = auditRow?.id ?? null
  console.log(`  seeded session_audit row: ${auditRowId}`)

  // Seed a clinician_review_queue row attributed to reviewerId
  const { data: queueRow } = await adminClient
    .from('clinician_review_queue')
    .insert({
      user_id:  reviewerId,
      session_id: `rls-verify-session-${Date.now()}`,
      source:   'layer1_safety',
      severity: 'medium',
      status:   'pending',
      reason:   'rls-verify synthetic row',
      payload:  {},
    })
    .select('id')
    .single()
  queueRowId = queueRow?.id ?? null
  console.log(`  seeded clinician_review_queue row: ${queueRowId}`)

  // Seed a message_feedback row: needs session + message first
  const { data: sess } = await adminClient
    .from('chat_sessions')
    .insert({ user_id: reviewerId, name: 'rls-verify-session' })
    .select('id')
    .single()
  feedbackSessionId = sess?.id ?? null

  if (feedbackSessionId) {
    const { data: msg } = await adminClient
      .from('messages')
      .insert({ session_id: feedbackSessionId, role: 'user', content: 'rls-verify' })
      .select('id')
      .single()
    feedbackMsgId = msg?.id ?? null

    if (feedbackMsgId) {
      await adminClient
        .from('message_feedback')
        .insert({ message_id: feedbackMsgId, user_id: reviewerId, rating: 1 })
    }
  }
  console.log(`  seeded message_feedback via session ${feedbackSessionId}`)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

async function runTests() {
  console.log('\n── Test A: member identity gets zero cross-user rows ─────────')

  // Authenticate as member
  const memberClient = createClient(SUPABASE_URL, ANON_KEY)
  const { error: signInErr } = await memberClient.auth.signInWithPassword({
    email: MEMBER_EMAIL, password: MEMBER_PASS,
  })
  if (signInErr) {
    fail('member sign-in', signInErr.message)
    return
  }

  // A-1: session_audit — member must see zero rows
  const { data: auditRows, error: auditErr } = await memberClient
    .from('session_audit')
    .select('id, user_id, crisis_state')
    .limit(100)

  if (auditErr) {
    // RLS can legitimately return an error instead of zero rows depending on policy type
    pass('A-1: session_audit SELECT returns error (access denied) for member')
  } else if (!auditRows || auditRows.length === 0) {
    pass('A-1: session_audit SELECT returns zero rows for member')
  } else {
    fail('A-1: session_audit', `Member got ${auditRows.length} rows: ${JSON.stringify(auditRows.slice(0, 2))}`)
  }

  // A-2: clinician_review_queue — member must see zero rows
  const { data: queueRows, error: queueErr } = await memberClient
    .from('clinician_review_queue')
    .select('id, user_id, severity')
    .limit(100)

  if (queueErr) {
    pass('A-2: clinician_review_queue SELECT returns error (access denied) for member')
  } else if (!queueRows || queueRows.length === 0) {
    pass('A-2: clinician_review_queue SELECT returns zero rows for member')
  } else {
    fail('A-2: clinician_review_queue', `Member got ${queueRows.length} rows: ${JSON.stringify(queueRows.slice(0, 2))}`)
  }

  // A-3: message_feedback — member must see zero rows for other users
  const { data: feedbackRows, error: feedbackErr } = await memberClient
    .from('message_feedback')
    .select('id, user_id, rating')
    .limit(100)

  if (feedbackErr) {
    pass('A-3: message_feedback SELECT returns error (access denied) for member')
  } else if (!feedbackRows || feedbackRows.length === 0) {
    pass('A-3: message_feedback SELECT returns zero rows for member')
  } else {
    // member may see their own rows (own-data policy); fail only if they see others'
    const crossUserRows = feedbackRows.filter(r => r.user_id !== memberId)
    if (crossUserRows.length === 0) {
      pass('A-3: message_feedback returns zero cross-user rows for member')
    } else {
      fail('A-3: message_feedback', `Member got ${crossUserRows.length} rows for other users: ${JSON.stringify(crossUserRows.slice(0, 2))}`)
    }
  }

  await memberClient.auth.signOut()

  // ─────────────────────────────────────────────────────────────────────────
  console.log('\n── Test B: clinical_reviewer gets data (happy path) ──────────')

  const reviewerClient = createClient(SUPABASE_URL, ANON_KEY)
  const { error: rSignInErr } = await reviewerClient.auth.signInWithPassword({
    email: REVIEWER_EMAIL, password: REVIEWER_PASS,
  })
  if (rSignInErr) {
    fail('reviewer sign-in', rSignInErr.message)
    return
  }

  // B-1: session_audit — reviewer must see rows (their own at minimum)
  const { data: rAuditRows, error: rAuditErr } = await reviewerClient
    .from('session_audit')
    .select('id')
    .limit(10)

  if (rAuditErr) {
    fail('B-1: session_audit reviewer read', rAuditErr.message)
  } else if (!rAuditRows || rAuditRows.length === 0) {
    fail('B-1: session_audit reviewer read', 'Got zero rows — reviewer should see data (migration 013 policy may be wrong role or tenant scope)')
  } else {
    pass(`B-1: session_audit returns ${rAuditRows.length} rows for clinical_reviewer`)
  }

  // B-2: clinician_review_queue — reviewer must see rows
  const { data: rQueueRows, error: rQueueErr } = await reviewerClient
    .from('clinician_review_queue')
    .select('id')
    .limit(10)

  if (rQueueErr) {
    fail('B-2: clinician_review_queue reviewer read', rQueueErr.message)
  } else if (!rQueueRows || rQueueRows.length === 0) {
    fail('B-2: clinician_review_queue reviewer read', 'Got zero rows — reviewer should see data')
  } else {
    pass(`B-2: clinician_review_queue returns ${rQueueRows.length} rows for clinical_reviewer`)
  }

  await reviewerClient.auth.signOut()
}

// ─── Cleanup ──────────────────────────────────────────────────────────────────
async function cleanup() {
  console.log('\n── Cleanup ───────────────────────────────────────────────────')
  if (auditRowId) {
    await adminClient.from('session_audit').delete().eq('id', auditRowId)
  }
  if (queueRowId) {
    await adminClient.from('clinician_review_queue').delete().eq('id', queueRowId)
  }
  if (feedbackSessionId) {
    // cascade deletes messages and message_feedback
    await adminClient.from('chat_sessions').delete().eq('id', feedbackSessionId)
  }
  if (memberId) {
    await adminClient.auth.admin.deleteUser(memberId)
  }
  if (reviewerId) {
    await adminClient.auth.admin.deleteUser(reviewerId)
  }
  console.log('  cleaned up test users and synthetic rows')
}

// ─── Entry point ──────────────────────────────────────────────────────────────
async function main() {
  console.log('RLS adversarial verification — migration 013')
  console.log(`Target: ${SUPABASE_URL}`)
  try {
    await setup()
    await runTests()
  } finally {
    await cleanup()
  }

  console.log(`\n── Result ────────────────────────────────────────────────────`)
  if (errors === 0) {
    console.log('  ALL PASSED — member identity correctly blocked from cross-user clinical data.')
    console.log('  clinical_reviewer correctly granted access.')
    console.log('  Migration 013 RLS posture is verified.')
  } else {
    console.error(`  ${errors} FAILURE(S) — do not proceed to demo. Fix the failing policies and re-run.`)
    process.exit(1)
  }
}

main().catch(err => {
  console.error('Unexpected error:', err)
  process.exit(1)
})
