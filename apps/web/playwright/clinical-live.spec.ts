import { test, expect } from '@playwright/test'

const POC_URL = process.env.POC_URL ?? 'http://localhost:8765'

test.describe('Clinical Intelligence Panel (/live)', () => {
  test('panel updates after chat message is sent', async ({ page }) => {
    const SESSION_ID = `playwright-t1-${Date.now()}`

    // Open the /live panel in follow-latest mode
    await page.goto('/live')

    // Expect waiting state initially
    await expect(page.getByText('WAITING')).toBeVisible({ timeout: 5000 })

    // Send a chat message directly to the POC server using Playwright's built-in request API
    const resp = await page.request.post(`${POC_URL}/chat`, {
      data: {
        messages: [{ role: 'user', content: 'I feel a bit stressed today' }],
        session_id: SESSION_ID,
      },
    })
    expect(resp.ok()).toBeTruthy()

    // Panel should switch to LIVE and show the session
    await expect(page.getByText('LIVE')).toBeVisible({ timeout: 10000 })

    // Node path should appear with at least Safety node lit
    await expect(page.locator('[data-fired="true"]').first()).toBeVisible({ timeout: 5000 })

    // Audit log should show Turn 1
    await expect(page.getByText('T1')).toBeVisible({ timeout: 5000 })

    // Intent should be visible
    await expect(page.getByText('general_chat')).toBeVisible({ timeout: 5000 })
  })

  test('?session= lock shows specific session', async ({ page }) => {
    const SESSION_ID = `playwright-t2-${Date.now()}`

    // Pre-send a turn to create session data
    const resp = await page.request.post(`${POC_URL}/chat`, {
      data: {
        messages: [{ role: 'user', content: 'What is anxiety?' }],
        session_id: SESSION_ID,
      },
    })
    expect(resp.ok()).toBeTruthy()

    // Small delay for the async write to land
    await page.waitForTimeout(1000)

    // Open panel locked to this session
    await page.goto(`/live?session=${SESSION_ID}`)

    await expect(page.getByText('LOCKED')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('T1')).toBeVisible({ timeout: 5000 })
  })
})
