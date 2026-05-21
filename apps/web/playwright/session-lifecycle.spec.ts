import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

function getSeedState(): { sessionAId: string } {
  const seedPath = path.resolve(__dirname, '.seed-state.json')
  return JSON.parse(fs.readFileSync(seedPath, 'utf-8'))
}

// ─── helpers ────────────────────────────────────────────────────────────────

async function openHistoryPanel(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'History' }).click()
  // Panel opens; wait for "New conversation" button to be visible
  await expect(page.getByRole('button', { name: /new conversation/i })).toBeVisible()
}

async function clickNewChat(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: /new conversation/i }).click()
}

function newParam(url: string): string | null {
  return new URL(url).searchParams.get('new')
}

// ─── tests ──────────────────────────────────────────────────────────────────

test.describe('New Chat session lifecycle', () => {

  test('TC-1: New Chat from an existing conversation resets to an empty chat', async ({ page }) => {
    const { sessionAId } = getSeedState()

    // Navigate directly to the seeded session so there are visible messages
    await page.goto(`/chat?session=${sessionAId}`)
    await expect(page.getByText('Hello from session A')).toBeVisible()

    // Click New Chat
    await openHistoryPanel(page)
    const urlBefore = page.url()
    await clickNewChat(page)

    // URL must contain a fresh ?new= timestamp param
    await page.waitForURL(/[?&]new=\d{13}-[a-z0-9]+/)
    const urlAfter = page.url()

    expect(newParam(urlAfter)).toBeTruthy()
    expect(urlAfter).not.toBe(urlBefore)

    // Message list must be empty (EmptyState component is rendered)
    await expect(page.getByText('Hello from session A')).not.toBeVisible()
    // No message bubbles; the empty state prompt area should be present
    const bubbles = page.locator('[class*="message-bubble"], [data-role="user"], [data-role="assistant"]')
    await expect(bubbles).toHaveCount(0)
  })

  test('TC-2: Clicking New Chat twice produces different URL params', async ({ page }) => {
    await page.goto('/chat')
    await page.waitForURL(/\/chat/)

    // First New Chat click
    await openHistoryPanel(page)
    await clickNewChat(page)
    await page.waitForURL(/[?&]new=\d{13}-[a-z0-9]+/)
    const firstParam = newParam(page.url())
    const firstUrl = page.url()

    // Second New Chat click — panel closed automatically; re-open.
    // Use waitForFunction (polls in browser context) rather than waitForURL, because
    // waitForURL with a predicate can resolve against the already-current URL before
    // the second navigation fires.
    await openHistoryPanel(page)
    await clickNewChat(page)
    await page.waitForFunction(
      (expected) => window.location.href !== expected,
      firstUrl,
      { timeout: 10_000 }
    )
    const secondParam = newParam(page.url())

    // Both params must be non-null and different
    expect(firstParam).toBeTruthy()
    expect(secondParam).toBeTruthy()
    expect(secondParam).not.toBe(firstParam)

    // Message list must be empty after second click
    const bubbles = page.locator('[class*="message-bubble"], [data-role="user"], [data-role="assistant"]')
    await expect(bubbles).toHaveCount(0)
  })

  test('TC-3: New Chat does not corrupt prior session; session A is retrievable from history', async ({ page }) => {
    const { sessionAId } = getSeedState()

    // Start in session A
    await page.goto(`/chat?session=${sessionAId}`)
    await expect(page.getByText('Hello from session A')).toBeVisible()

    // Navigate to a new session
    await openHistoryPanel(page)
    await clickNewChat(page)
    await page.waitForURL(/[?&]new=\d{13}-[a-z0-9]+/)

    // New session is empty
    await expect(page.getByText('Hello from session A')).not.toBeVisible()

    // Open history panel — session A should appear
    await openHistoryPanel(page)
    await expect(page.getByRole('button', { name: /E2E Session A/i })).toBeVisible()

    // Navigate back to session A
    await page.getByRole('button', { name: /E2E Session A/i }).click()
    await page.waitForURL(`**/chat?session=${sessionAId}`)

    // Original message is intact — no cross-session contamination
    await expect(page.getByText('Hello from session A')).toBeVisible()
  })

})
