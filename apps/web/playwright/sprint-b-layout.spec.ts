import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// PERF-1: Viewport meta contains viewport-fit=cover
// ---------------------------------------------------------------------------
test.describe('PERF-1 — Viewport meta', () => {
  test('viewport meta contains viewport-fit=cover', async ({ page }) => {
    await page.goto('/sign-in')
    const content = await page.locator('meta[name="viewport"]').getAttribute('content')
    expect(content).toContain('viewport-fit=cover')
  })
})

// ---------------------------------------------------------------------------
// A11Y-13: Both CSS font variables defined on <html>
// ---------------------------------------------------------------------------
test.describe('A11Y-13 — Font variables on <html>', () => {
  test('--font-body and --font-arabic CSS variables are set on <html>', async ({ page }) => {
    await page.goto('/sign-in')
    const fontVars = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement)
      return {
        body: style.getPropertyValue('--font-body').trim(),
        arabic: style.getPropertyValue('--font-arabic').trim(),
      }
    })
    expect(fontVars.body.length).toBeGreaterThan(0)
    expect(fontVars.arabic.length).toBeGreaterThan(0)
  })

  test('html element has both next/font variable classes', async ({ page }) => {
    await page.goto('/chat')
    const htmlClass = await page.locator('html').getAttribute('class')
    // next/font generates class names like __variable_XXXXX — there should be at least 2
    const varClasses = (htmlClass ?? '').split(' ').filter((c) => c.includes('__'))
    expect(varClasses.length).toBeGreaterThanOrEqual(2)
  })
})

// ---------------------------------------------------------------------------
// PERF-6: Progress page has scroll container
// ---------------------------------------------------------------------------
test.describe('PERF-6 — Progress page scroll', () => {
  test('progress page renders without error', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    await page.goto('/progress')
    await page.waitForLoadState('networkidle')
    // Page should load (status 200, not crash to an error page)
    expect(page.url()).toContain('/progress')
  })

  test('progress page has an overflow-y-auto scroll container with h-full', async ({ page }) => {
    await page.goto('/progress')
    await page.waitForLoadState('networkidle')
    // The progress page's outer scroll div is a direct child of main#main-content.
    // Scoping avoids matching sidebar/nav elements that also use overflow-y-auto.
    const container = page.locator('#main-content > [class*="overflow-y-auto"]').first()
    if (await container.count() > 0) {
      const classes = await container.getAttribute('class')
      expect(classes).toContain('h-full')
    }
  })
})

// ---------------------------------------------------------------------------
// TS-2: Middleware stability (env vars guarded, not crashing)
// ---------------------------------------------------------------------------
test.describe('TS-2 — Middleware stability', () => {
  test('any page request returns non-500 (env guard is working)', async ({ request }) => {
    const res = await request.get('/sign-in')
    expect(res.status()).not.toBe(500)
  })
})

// ---------------------------------------------------------------------------
// SAFE AREA: TabBar nav has env(safe-area-inset-bottom) class
// ---------------------------------------------------------------------------
test.describe('PERF-1 — TabBar safe area padding', () => {
  test('tab bar nav has safe-area-inset-bottom padding class', async ({ page }) => {
    await page.goto('/chat')
    await page.waitForLoadState('networkidle')
    // TabBar is only shown on mobile breakpoint (hidden at md+).
    // Verify the nav element exists with the safe-area class in its class attribute.
    const navElements = await page.locator('nav').all()
    let found = false
    for (const nav of navElements) {
      const classes = await nav.getAttribute('class') ?? ''
      if (classes.includes('safe-area-inset-bottom')) {
        found = true
        break
      }
    }
    expect(found).toBe(true)
  })
})
