import { chromium } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

// Load .env.local so this script works without pre-exported env vars
function loadEnv() {
  const envPath = path.resolve(__dirname, '../.env.local')
  if (!fs.existsSync(envPath)) return
  const raw = fs.readFileSync(envPath, 'utf-8')
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx === -1) continue
    const key = trimmed.slice(0, eqIdx).trim()
    const val = trimmed.slice(eqIdx + 1).trim()
    if (!process.env[key]) process.env[key] = val
  }
}

const TEST_EMAIL    = 'sage-e2e@test.internal'
const TEST_PASSWORD = 'SageE2E-2026!'
const AUTH_STATE    = path.resolve(__dirname, '.auth-state.json')
const SEED_FILE     = path.resolve(__dirname, '.seed-state.json')

export default async function globalSetup() {
  loadEnv()

  const supabaseUrl    = process.env.NEXT_PUBLIC_SUPABASE_URL!
  const anonKey        = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY!

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local')
  }

  // Admin client — creates users and seeds test data
  const admin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  // 1. Ensure test user exists
  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const existing = users.find((u) => u.email === TEST_EMAIL)

  let userId: string
  if (existing) {
    userId = existing.id
  } else {
    const { data, error } = await admin.auth.admin.createUser({
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
      email_confirm: true,
    })
    if (error) throw new Error(`Failed to create test user: ${error.message}`)
    userId = data.user.id
  }

  // 2. Ensure user_profiles row exists (page.tsx reads name from here)
  // is_admin: false — the E2E identity must not hold admin privileges.
  // is_admin = true would grant read access to session_audit, clinician_review_queue,
  // and message_feedback for ALL users via the is_admin-gated RLS policies in
  // 003_complete_trace_fields.sql, 006_clinician_review_queue.sql, and 009_session_audit.sql.
  // Admin-route access (STATE-1) is correctly gated by user_roles, not this field.
  await admin.from('user_profiles').upsert(
    { id: userId, name: 'E2E Test', locale: 'en', onboarding_complete: true, is_admin: false },
    { onConflict: 'id' }
  )

  // 3. Seed a "session A" with one message so test 3 can verify history.
  // Delete any stale E2E sessions from prior runs so the selector stays unique.
  await admin
    .from('chat_sessions')
    .delete()
    .eq('user_id', userId)
    .eq('name', 'E2E Session A')

  const { data: sessionA } = await admin
    .from('chat_sessions')
    .insert({ user_id: userId, name: 'E2E Session A' })
    .select()
    .single()
  if (!sessionA) throw new Error('Failed to seed session A')

  await admin.from('messages').insert({
    session_id: sessionA.id,
    role: 'user',
    content: 'Hello from session A',
    intent: 'emotional',
  })

  fs.writeFileSync(SEED_FILE, JSON.stringify({ sessionAId: sessionA.id }))

  // 4. Sign in via the web UI and capture cookies into storageState
  const browser = await chromium.launch()
  const page    = await browser.newPage()

  await page.goto('http://localhost:3000/sign-in')
  await page.getByPlaceholder('Email').fill(TEST_EMAIL)
  await page.getByPlaceholder('Password').fill(TEST_PASSWORD)
  await page.getByRole('button', { name: /sign in/i }).click()

  // Wait until we land on /chat (auth redirect)
  await page.waitForURL('**/chat**', { timeout: 15_000 })

  await page.context().storageState({ path: AUTH_STATE })
  await browser.close()
}
