import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// A11Y-3: Skip-to-content link
// ---------------------------------------------------------------------------
test.describe('A11Y-3 — Skip-to-content link', () => {
  test('skip link is first focusable element on /chat', async ({ page }) => {
    await page.goto('/chat')
    await page.keyboard.press('Tab')
    const skipLink = page.locator('a[href="#main-content"]')
    await expect(skipLink).toBeFocused()
  })

  test('#main-content target exists on /chat', async ({ page }) => {
    await page.goto('/chat')
    await expect(page.locator('#main-content')).toBeAttached()
  })
})
