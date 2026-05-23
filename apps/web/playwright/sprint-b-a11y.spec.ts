import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// A11Y-3: Skip-to-content link
// ---------------------------------------------------------------------------
test.describe('A11Y-3 — Skip-to-content link', () => {
  test('skip link is first focusable element on /chat', async ({ page }) => {
    // Navigate twice: the second navigation clears Chromium's focus-resume state
    // that would otherwise route Tab to a previously-focused viewport element
    // (the chat input bar) instead of the first DOM-order focusable element.
    await page.goto('/chat')
    await page.goto('/chat')
    // Blur any element that received focus during page load, reset to document
    // root, then remove the temporary tabindex so the document is in the same
    // state as a real user pressing Tab for the first time on a fresh page.
    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement)?.blur()
      const html = document.documentElement as HTMLElement
      html.setAttribute('tabindex', '-1')
      html.focus()
      html.removeAttribute('tabindex')
      ;(document.activeElement as HTMLElement)?.blur()
    })
    await page.keyboard.press('Tab')
    const skipLink = page.locator('a[href="#main-content"]')
    await expect(skipLink).toBeFocused()
  })

  test('#main-content target exists on /chat', async ({ page }) => {
    await page.goto('/chat')
    await expect(page.locator('#main-content')).toBeAttached()
  })
})
