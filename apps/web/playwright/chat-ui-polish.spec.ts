import { test, expect } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

// Functional + visual test for the chat-UI-polish quick wins (#1 long-form prose,
// #2 neutral assistant bubble, #5 softened sidebar buttons). The Sage ML backend
// (SAGE_API_URL=:8000) is NOT required: the chat page renders message history
// server-side from the `messages` table, so we seed a session and assert how it
// renders. Auth is the shared storageState created by global-setup.

function loadEnv() {
  const envPath = path.resolve(__dirname, '../.env.local')
  if (!fs.existsSync(envPath)) return
  for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    const i = t.indexOf('=')
    if (i === -1) continue
    const k = t.slice(0, i).trim()
    if (!process.env[k]) process.env[k] = t.slice(i + 1).trim()
  }
}

const TEST_EMAIL = 'sage-e2e@test.internal'

const LONG_MARKER = 'POLISH-LONG: deep breathing techniques'
const LONG_CONTENT =
  `${LONG_MARKER}\n` +
  '1. Slow, extended-exhalation breathing raises heart-rate variability.\n' +
  '2. Box breathing lowers physiological arousal and helps manage stress.\n' +
  '3. Diaphragmatic breathing triggers the parasympathetic rest-and-digest response.'
const SHORT_AI_MARKER = 'POLISH-SHORT: sure, I can help with that.'
const USER_MARKER = 'POLISH-USER: does deep breathing help anxiety?'

let admin: ReturnType<typeof createClient>
let sessionId: string

test.beforeAll(async () => {
  loadEnv()
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!
  admin = createClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const user = users.find((u) => u.email === TEST_EMAIL)
  if (!user) throw new Error(`Test user ${TEST_EMAIL} not found — run global-setup`)

  const { data: session } = await admin
    .from('chat_sessions')
    .insert({ user_id: user.id, name: 'UI Polish Visual Check' })
    .select()
    .single()
  if (!session) throw new Error('Failed to seed polish session')
  sessionId = session.id as string

  await admin.from('messages').insert([
    { session_id: sessionId, role: 'user', content: USER_MARKER, turn_number: 1 },
    { session_id: sessionId, role: 'ai', content: LONG_CONTENT, turn_number: 2 },
    { session_id: sessionId, role: 'user', content: 'POLISH-USER2: thanks', turn_number: 3 },
    { session_id: sessionId, role: 'ai', content: SHORT_AI_MARKER, turn_number: 4 },
  ])
})

test.afterAll(async () => {
  if (!sessionId) return
  await admin.from('messages').delete().eq('session_id', sessionId)
  await admin.from('chat_sessions').delete().eq('id', sessionId)
})

test('#1 long-form AI answer renders as prose (no bubble), structure preserved', async ({ page }) => {
  await page.goto(`/chat?session=${sessionId}`)
  await page.waitForLoadState('networkidle')

  const longEl = page.getByText(/POLISH-LONG/)
  await expect(longEl).toBeVisible()

  const cls = (await longEl.getAttribute('class')) ?? ''
  expect(cls).not.toContain('rounded-2xl')        // no bubble shape
  expect(cls).not.toContain('color-surface')      // no fill
  expect(cls).toContain('whitespace-pre-wrap')    // list line-structure preserved

  // newlines survive into the DOM (numbered list, not run-on)
  const text = (await longEl.textContent()) ?? ''
  expect(text).toContain('1. Slow')
  expect(text).toContain('3. Diaphragmatic')
})

test('#2 short AI turn uses the neutral bubble; user turn stays green', async ({ page }) => {
  await page.goto(`/chat?session=${sessionId}`)
  await page.waitForLoadState('networkidle')

  const shortEl = page.getByText(/POLISH-SHORT/)
  await expect(shortEl).toBeVisible()
  const shortCls = (await shortEl.getAttribute('class')) ?? ''
  expect(shortCls).toContain('bg-[var(--color-surface-muted)]')
  expect(shortCls).not.toContain('surface-tinted')
  expect(shortCls).toContain('rounded-2xl')

  const userEl = page.getByText(/POLISH-USER: does deep breathing/)
  const userCls = (await userEl.getAttribute('class')) ?? ''
  expect(userCls).toContain('bg-[var(--color-primary-dark)]')
})

test('#5 sidebar New conversation button is tinted, not solid green', async ({ page }) => {
  await page.goto(`/chat?session=${sessionId}`)
  await page.waitForLoadState('networkidle')

  const btn = page.locator('aside').getByRole('button', { name: /new conversation/i })
  await expect(btn).toBeVisible()
  const cls = (await btn.getAttribute('class')) ?? ''
  expect(cls).toContain('bg-[var(--color-surface-tinted)]')
  expect(cls).not.toMatch(/(^|\s)bg-\[var\(--color-primary\)\]/) // base not solid primary
})

test('visual: capture chat with long + short answers and sidebar', async ({ page }) => {
  await page.goto(`/chat?session=${sessionId}`)
  await page.waitForLoadState('networkidle')
  await expect(page.getByText(/POLISH-LONG/)).toBeVisible()
  await page.screenshot({ path: 'test-results/polish-chat-full.png', fullPage: true })
})
