import { test, expect, type Locator } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

function loadEnv() {
  const p = path.resolve(__dirname, '../.env.local')
  if (!fs.existsSync(p)) return
  for (const line of fs.readFileSync(p, 'utf-8').split('\n')) {
    const t = line.trim(); if (!t || t.startsWith('#')) continue
    const i = t.indexOf('='); if (i === -1) continue
    const k = t.slice(0, i).trim(); if (!process.env[k]) process.env[k] = t.slice(i + 1).trim()
  }
}

let admin: ReturnType<typeof createClient>
let enId: string
let arId: string

async function fontPx(el: Locator): Promise<number> {
  return el.evaluate((n) => parseFloat(getComputedStyle(n as Element).fontSize))
}

test.beforeAll(async () => {
  loadEnv()
  admin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } })
  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const user = users.find((u) => u.email === 'sage-e2e@test.internal')!
  const mk = async (name: string, rows: { role: string; content: string }[]) => {
    const { data: s } = await admin.from('chat_sessions').insert({ user_id: user.id, name }).select().single()
    await admin.from('messages').insert(rows.map((r, i) => ({ session_id: s!.id, role: r.role, content: r.content, turn_number: i + 1 })))
    return s!.id as string
  }
  enId = await mk('Coping with Stress', [
    { role: 'user', content: "I've been feeling stressed lately" },
    { role: 'ai', content: "You've mentioned feeling stressed lately. It's understandable to feel this way, especially if there are pressures or challenges you're facing. What's been contributing to your stress, if you feel like sharing?" },
  ])
  arId = await mk('التعامل مع التوتر', [
    { role: 'user', content: 'أشعر بالتوتر مؤخراً' },
    { role: 'ai', content: 'لقد ذكرت أنك تشعر بالتوتر مؤخراً. من المفهوم أن تشعر بهذا، خاصة إذا كانت هناك ضغوط أو تحديات تواجهها. ما الذي يساهم في توترك، إذا كنت ترغب في المشاركة؟' },
  ])
})

test.afterAll(async () => {
  for (const id of [enId, arId]) {
    await admin.from('messages').delete().eq('session_id', id)
    await admin.from('chat_sessions').delete().eq('id', id)
  }
})

test('EN: centered column + consistent input/output font size', async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 760 })
  await page.goto(`/chat?session=${enId}`)
  await page.waitForLoadState('networkidle')
  await page.getByRole('textbox').fill('Does deep breathing help with anxiety?')

  // font-size parity: assistant output === composer input
  const outPx = await fontPx(page.getByText(/understandable to feel this way/))
  const inPx = await fontPx(page.getByRole('textbox'))
  console.log(`EN font px — output ${outPx}, input ${inPx}`)
  expect(inPx).toBe(outPx)

  await page.screenshot({ path: 'test-results/final-en.png' })
})

test('AR: centered column + consistent input/output font size (RTL)', async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 760 })
  await page.goto(`/chat?session=${arId}`)
  await page.waitForLoadState('networkidle')
  await page.getByText('عربي').first().click().catch(() => {})
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await page.getByRole('textbox').fill('هل يساعد التنفس العميق في تقليل القلق؟')

  const outPx = await fontPx(page.getByText(/تشعر بالتوتر مؤخرا/))
  const inPx = await fontPx(page.getByRole('textbox'))
  console.log(`AR font px — output ${outPx}, input ${inPx}`)
  expect(inPx).toBe(outPx)

  await page.screenshot({ path: 'test-results/final-ar.png' })
})
