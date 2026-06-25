import { test, expect } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

// Controller verification for Sub-project A on the PRODUCTION build: a numbered list
// renders as a real <ol>, bold renders as <strong> (B-readiness), and — the load-bearing
// check — an Arabic list indents on the RIGHT (logical ps-5 under RTL).

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
  enId = await mk('Markdown EN', [
    { role: 'user', content: 'does deep breathing help?' },
    { role: 'ai', content: '**Deep breathing** can help:\n\n1. Slow, extended exhalation\n2. Box breathing\n3. Diaphragmatic breathing' },
  ])
  arId = await mk('Markdown AR', [
    { role: 'user', content: 'هل يساعد التنفس العميق؟' },
    { role: 'ai', content: 'نعم، التنفس العميق يساعد:\n\n1. التنفس البطيء وإطالة الزفير\n2. التنفس الصندوقي\n3. التنفس الحجابي' },
  ])
})

test.afterAll(async () => {
  for (const id of [enId, arId]) {
    await admin.from('messages').delete().eq('session_id', id)
    await admin.from('chat_sessions').delete().eq('id', id)
  }
})

test('EN: numbered list renders as <ol>, bold as <strong>', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 760 })
  await page.goto(`/chat?session=${enId}`)
  await page.waitForLoadState('networkidle')
  await expect(page.locator('ol > li')).toHaveCount(3)
  await expect(page.locator('strong', { hasText: 'Deep breathing' })).toBeVisible()
  // no clickable anchors in the ASSISTANT message content (sidebar nav uses <a>, so scope to the log)
  await expect(page.getByRole('log').locator('a')).toHaveCount(0)
  await page.screenshot({ path: 'test-results/md-en.png' })
})

test('AR (RTL): list renders as <ol> and indents on the RIGHT (load-bearing)', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 760 })
  await page.goto(`/chat?session=${arId}`)
  await page.waitForLoadState('networkidle')
  await page.getByText('عربي').first().click().catch(() => {})
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

  const ol = page.locator('ol').first()
  await expect(ol).toBeVisible()
  const box = await ol.evaluate((el) => {
    const s = getComputedStyle(el as Element)
    return { dir: s.direction, padLeft: parseFloat(s.paddingLeft), padRight: parseFloat(s.paddingRight) }
  })
  // logical ps-5 under RTL must resolve to padding on the RIGHT, not the left
  expect(box.dir).toBe('rtl')
  expect(box.padRight).toBeGreaterThan(box.padLeft)
  console.log(`AR <ol> — dir=${box.dir} padRight=${box.padRight} padLeft=${box.padLeft}`)
  await page.screenshot({ path: 'test-results/md-ar.png' })
})
