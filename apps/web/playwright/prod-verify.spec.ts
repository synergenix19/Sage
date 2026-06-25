import { test, expect, type Locator } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import path from 'path'
import fs from 'fs'

// Verifies the PRODUCTION build (next build + next start) — the artifact Vercel ships —
// not dev mode. Checks: computed-style WCAG AA contrast on the real shipping CSS,
// long-form prose vs neutral bubble, Arabic RTL layout, and mobile width.

function loadEnv() {
  const p = path.resolve(__dirname, '../.env.local')
  if (!fs.existsSync(p)) return
  for (const line of fs.readFileSync(p, 'utf-8').split('\n')) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    const i = t.indexOf('=')
    if (i === -1) continue
    const k = t.slice(0, i).trim()
    if (!process.env[k]) process.env[k] = t.slice(i + 1).trim()
  }
}

const TEST_EMAIL = 'sage-e2e@test.internal'
const LONG = 'VERIFY-LONG: deep breathing\n1. extended exhalation raises HRV\n2. box breathing lowers arousal\n3. diaphragmatic breathing calms'
const SHORT = 'VERIFY-SHORT: sure, I can help.'
const AR_LONG = 'تحقق: التنفس العميق يساعد.\n1. التنفس البطيء يرفع تقلب ضربات القلب\n2. التنفس الصندوقي يقلل التوتر'

let admin: ReturnType<typeof createClient>
let enId: string
let arId: string

// WCAG 2.1 contrast from "rgb(r, g, b)" computed values
function ratioFromRgb(fg: string, bg: string): number {
  const parse = (s: string) => (s.match(/\d+/g) ?? ['0', '0', '0']).slice(0, 3).map(Number)
  const lin = (c: number) => { const x = c / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4 }
  const lum = ([r, g, b]: number[]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  const la = lum(parse(fg)), lb = lum(parse(bg))
  const [hi, lo] = la > lb ? [la, lb] : [lb, la]
  return (hi + 0.05) / (lo + 0.05)
}
async function computed(el: Locator): Promise<{ color: string; bg: string; radius: string }> {
  return el.evaluate((n) => {
    const s = getComputedStyle(n as Element)
    return { color: s.color, bg: s.backgroundColor, radius: s.borderTopLeftRadius }
  })
}

test.beforeAll(async () => {
  loadEnv()
  admin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } })
  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const user = users.find((u) => u.email === TEST_EMAIL)
  if (!user) throw new Error('test user missing')
  const mk = async (name: string, rows: { role: string; content: string }[]) => {
    const { data: s } = await admin.from('chat_sessions').insert({ user_id: user.id, name }).select().single()
    if (!s) throw new Error('seed failed')
    await admin.from('messages').insert(rows.map((r, i) => ({ session_id: s.id, role: r.role, content: r.content, turn_number: i + 1 })))
    return s.id as string
  }
  enId = await mk('Prod Verify EN', [
    { role: 'user', content: 'VERIFY-USER: does breathing help?' },
    { role: 'ai', content: LONG },
    { role: 'ai', content: SHORT },
  ])
  arId = await mk('Prod Verify AR', [
    { role: 'user', content: 'تحقق: هل يساعد التنفس؟' },
    { role: 'ai', content: AR_LONG },
  ])
})

test.afterAll(async () => {
  for (const id of [enId, arId]) {
    if (!id) continue
    await admin.from('messages').delete().eq('session_id', id)
    await admin.from('chat_sessions').delete().eq('id', id)
  }
})

test('PROD: computed-style WCAG AA contrast clears 4.5:1 on shipping CSS', async ({ page }) => {
  await page.goto(`/chat?session=${enId}`)
  await page.waitForLoadState('networkidle')

  // Short assistant turn renders as PROSE now (no bubble) — same as long-form.
  const shortEl = page.getByText('VERIFY-SHORT: sure, I can help.')
  const b = await computed(shortEl)
  expect(b.bg).toBe('rgba(0, 0, 0, 0)')          // no fill
  expect(b.radius).toBe('0px')                    // no bubble shape
  const proseRatio = ratioFromRgb(b.color, 'rgb(255, 255, 255)') // text on white canvas
  expect(proseRatio).toBeGreaterThanOrEqual(4.5)

  // Softened New conversation button (tinted bg, green text)
  const btn = page.locator('aside').getByRole('button', { name: /new conversation/i })
  const c = await computed(btn)
  const btnRatio = ratioFromRgb(c.color, c.bg)
  expect(btnRatio).toBeGreaterThanOrEqual(4.5)

  // Long-form answer: no bubble in shipping CSS (transparent bg, no radius)
  const longEl = page.getByText(/VERIFY-LONG/)
  const l = await computed(longEl)
  expect(l.bg).toBe('rgba(0, 0, 0, 0)')
  expect(l.radius).toBe('0px')

  console.log(`PROD — AI prose ${proseRatio.toFixed(2)}:1 (text ${b.color} on white); button ${btnRatio.toFixed(2)}:1 (text ${c.color} on ${c.bg})`)
})

test('PROD: Arabic RTL layout', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 860 })
  await page.goto(`/chat?session=${arId}`)
  await page.waitForLoadState('networkidle')
  await page.getByText('عربي').first().click().catch(() => {})
  await expect(page.getByText(/التنفس العميق يساعد/)).toBeVisible({ timeout: 15_000 })
  // shell flipped RTL
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  // Long-form Arabic answer renders RTL. History messages carry no authoritative
  // `direction` (page selects only id/role/content), so the element uses dir="auto";
  // with Arabic-leading content that resolves RTL. Assert the COMPUTED direction
  // (what actually renders) rather than the literal attribute.
  const arLong = page.getByText(/التنفس العميق يساعد/)
  const arDir = await arLong.evaluate((n) => getComputedStyle(n as Element).direction)
  expect(arDir).toBe('rtl')
  expect((await arLong.textContent()) ?? '').toContain('2. التنفس الصندوقي')
  await page.screenshot({ path: 'test-results/prod-ar.png' })
})

test('PROD: mobile width (iPhone 390x844)', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/chat?session=${enId}`)
  await page.waitForLoadState('networkidle')
  await expect(page.getByText(/VERIFY-LONG/)).toBeVisible()
  // assistant prose still clears AA at mobile width (text on white canvas)
  const shortEl = page.getByText('VERIFY-SHORT: sure, I can help.')
  const b = await computed(shortEl)
  expect(b.bg).toBe('rgba(0, 0, 0, 0)') // prose, not a bubble
  expect(ratioFromRgb(b.color, 'rgb(255, 255, 255)')).toBeGreaterThanOrEqual(4.5)
  await page.screenshot({ path: 'test-results/prod-mobile.png', fullPage: true })
})
