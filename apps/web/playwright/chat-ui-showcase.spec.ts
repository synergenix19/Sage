import { test, expect } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

// Showcase: render a realistic sample chat (the sleep + deep-breathing conversation
// from the product) so the polished UI can be eyeballed. No ML backend needed —
// history renders server-side from the `messages` table.

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

let admin: ReturnType<typeof createClient>
let sessionId: string
let arSessionId: string

const SAMPLE = [
  { role: 'user', content: "I've been having trouble sleeping because my mind races at night" },
  {
    role: 'ai',
    content:
      "Your mind racing at night can make sleep difficult. We can explore what's getting in the way of " +
      "your sleep and build a wind down routine that fits your life. That would take about ten minutes. " +
      "Or if you prefer, we can keep talking about what's on your mind. Which would you prefer?",
  },
  { role: 'user', content: 'Does deep breathing actually help with anxiety?' },
  {
    role: 'ai',
    content:
      'Yes, deep breathing can help reduce anxiety.\n\n' +
      '1. Slow and deep breathing, especially when the exhalation is extended, increases heart rate ' +
      'variability, which is linked to better emotional regulation and lower anxiety levels.\n\n' +
      '2. Techniques like box breathing and extended-exhalation breathing can lower physiological ' +
      'arousal, helping to manage stress.\n\n' +
      '3. Slow diaphragmatic breathing stimulates the parasympathetic nervous system, leading to a ' +
      'calming "rest-and-digest" response, reducing stress markers like heart rate and muscle tension.\n\n' +
      'If you want to explore a guided breathing exercise, I can help with that too.',
  },
  { role: 'user', content: 'Can you help me? I am feeling very low energy today.' },
  {
    role: 'ai',
    content:
      "You're feeling very low energy today. Would you like to try a mood check-in for about five " +
      'minutes, to see how you doing across different areas? We can also just keep talking if you prefer.',
  },
]

const AR_SAMPLE = [
  { role: 'user', content: 'هل يساعد التنفس العميق فعلاً في تقليل القلق؟' },
  {
    role: 'ai',
    content:
      'نعم، يمكن أن يساعد التنفس العميق في تقليل القلق.\n\n' +
      '1. التنفس البطيء والعميق، خاصة عند إطالة الزفير، يرفع تقلب معدل ضربات القلب المرتبط بتنظيم أفضل للمشاعر.\n\n' +
      '2. تقنيات مثل التنفس الصندوقي تقلل من الإثارة الفسيولوجية وتساعد على إدارة التوتر.\n\n' +
      '3. التنفس الحجابي البطيء ينشط الجهاز العصبي نظير الودي مما يؤدي إلى استجابة تهدئة.',
  },
]

test.beforeAll(async () => {
  loadEnv()
  admin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )
  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const user = users.find((u) => u.email === TEST_EMAIL)
  if (!user) throw new Error(`Test user ${TEST_EMAIL} not found`)

  const mk = async (name: string, rows: { role: string; content: string }[]) => {
    const { data: s } = await admin
      .from('chat_sessions').insert({ user_id: user.id, name }).select().single()
    if (!s) throw new Error('seed failed')
    await admin.from('messages').insert(
      rows.map((r, idx) => ({ session_id: s.id, role: r.role, content: r.content, turn_number: idx + 1 }))
    )
    return s.id as string
  }
  sessionId = await mk('Deep Breathing and Sleep', SAMPLE)
  arSessionId = await mk('التنفس العميق والقلق', AR_SAMPLE)
})

test.afterAll(async () => {
  for (const id of [sessionId, arSessionId]) {
    if (!id) continue
    await admin.from('messages').delete().eq('session_id', id)
    await admin.from('chat_sessions').delete().eq('id', id)
  }
})

test('showcase: English sample chat', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 860 })
  await page.goto(`/chat?session=${sessionId}`)
  await page.waitForLoadState('networkidle')
  await expect(page.getByText(/deep breathing can help reduce anxiety/)).toBeVisible()
  await page.screenshot({ path: 'test-results/showcase-en.png' })
})

test('showcase: Arabic RTL sample chat', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 860 })
  await page.goto(`/chat?session=${arSessionId}`)
  await page.waitForLoadState('networkidle')
  // switch the UI locale to Arabic so the whole shell flips RTL
  await page.getByText('عربي').first().click().catch(() => {})
  // wait for the seeded Arabic answer to actually paint (toggle re-renders the shell)
  await expect(page.getByText(/يمكن أن يساعد التنفس العميق/)).toBeVisible({ timeout: 15_000 })
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: 'test-results/showcase-ar.png' })
})
