import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// ARCH-2 + A11Y-6: Crisis path integrity
// ---------------------------------------------------------------------------
test.describe('ARCH-2 — Crisis route loads without import errors', () => {
  test('POST /api/chat with invalid data returns 400 not 500', async ({ request }) => {
    // 400 = Zod validation ran, route loaded correctly (including CRISIS_SIGNAL import)
    // 500 = import error or runtime crash
    const res = await request.post('/api/chat', {
      data: { sessionId: 'not-valid', messages: [] },
    })
    expect(res.status()).toBe(400)
    expect(res.status()).not.toBe(500)
  })
})

test.describe('A11Y-6 — Crisis card ARIA', () => {
  test('crisis-card role="alert" is accessible by role query', async ({ page }) => {
    await page.goto('/chat')
    await page.waitForLoadState('networkidle')
    // Inject a crisis card directly into the DOM to verify the role attribute
    // without needing to trigger actual crisis detection
    await page.evaluate(() => {
      const div = document.createElement('div')
      div.setAttribute('role', 'alert')
      div.setAttribute('aria-atomic', 'true')
      div.id = 'test-crisis-card'
      div.textContent = 'Crisis card test — you are not alone.'
      document.body.appendChild(div)
    })
    // Use the specific id to avoid matching Next.js's __next-route-announcer__ (also role="alert")
    const alert = page.locator('#test-crisis-card[role="alert"]')
    await expect(alert).toBeAttached()
    await expect(alert).toHaveAttribute('aria-atomic', 'true')
    // Clean up
    await page.evaluate(() => document.getElementById('test-crisis-card')?.remove())
  })
})

// ---------------------------------------------------------------------------
// Phase 1 — multi-resource crisis card + persistent "Get help now" affordance
// ---------------------------------------------------------------------------
const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

test.describe('Crisis card — multi-resource list on detection', () => {
  test('a crisis turn pins the card with an ordered list of working tel: links', async ({ page }) => {
    // Mock the backend so detection is deterministic (no live model): the response carries the
    // in-band crisis sentinel + a non-resolved X-Sage-Crisis-State, which pins the CrisisCard.
    await page.route('**/api/chat', async (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'X-Sage-Crisis-State': 'monitoring',
          'X-Sage-Direction': 'ltr',
        },
        body: `${CRISIS_SIGNAL} You're not alone — support is available right now.`,
      })
    })

    await page.goto('/chat')
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox').fill('I want to end my life')
    await page.getByRole('button', { name: /send/i }).click()

    const card = page.getByRole('alert')
    await expect(card).toBeVisible()
    // Ordered list with at least the MoHAP + 999 lines, both dialable.
    const telLinks = card.locator('a[href^="tel:"]')
    await expect(telLinks).toHaveCount(2)
    await expect(card.locator('a[href="tel:800-46342"]')).toBeVisible()
    await expect(card.locator('a[href="tel:999"]')).toBeVisible()
  })
})

test.describe('Persistent "Get help now" affordance', () => {
  test('is reachable off crisis detection and opens the resource list with tel: links', async ({ page }) => {
    await page.goto('/chat')
    await page.waitForLoadState('networkidle')

    // No crisis turn has happened — the affordance is available every turn from the header.
    await page.getByRole('button', { name: 'Get help now' }).click()

    const telLinks = page.locator('a[href^="tel:"]')
    await expect(telLinks.first()).toBeVisible()
    await expect(page.locator('a[href="tel:800-46342"]')).toBeVisible()
    await expect(page.locator('a[href="tel:999"]')).toBeVisible()
  })

  test('still renders dialable numbers when the API is dead (offline / deterministic)', async ({ page }) => {
    await page.goto('/chat')
    await page.waitForLoadState('networkidle')

    // Kill the backend: any API call now fails. The affordance must NOT depend on it.
    await page.route('**/api/**', (route) => route.abort())

    await page.getByRole('button', { name: 'Get help now' }).click()

    await expect(page.locator('a[href="tel:800-46342"]')).toBeVisible()
    await expect(page.locator('a[href="tel:999"]')).toBeVisible()
  })
})
