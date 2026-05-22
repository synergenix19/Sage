/**
 * TC-4: CBT Thought Record Full Flow (E2E Frontend)
 *
 * Validates the entire stack for a 3-turn CBT thought record:
 *   User UI → Next.js route.ts → FastAPI server.py → LangGraph graph
 *   → compose_prompt (L3 wrapper) → LLM → streaming response → chat UI
 *
 * What this test verifies:
 *   - P1-4 fix: "Goal:" / "Technique:" labels never appear in LLM responses
 *   - Conversational framing: responses contain a question mark (Socratic)
 *   - Routing: x-sage-skill-id is cbt_thought_record on skill turns
 *   - Routing: x-sage-gate-path is "standard" on all turns
 *   - Routing: x-sage-node-path includes skill_executor and freeflow_respond
 *
 * Prerequisites:
 *   - Both servers running: `uv run uvicorn sage_poc.server:app` (port 8000)
 *     and `pnpm dev` in apps/web (port 3000)
 *   - SAGE_EXPOSE_DIAGNOSTIC_HEADERS=true in .env.local
 *   - Global setup has run (auth state seeded)
 */
import { test, expect, type Response } from '@playwright/test'

// ─── helpers ─────────────────────────────────────────────────────────────────

/** Send a message in the chat input and return once the AI response has appeared. */
async function sendMessage(
  page: import('@playwright/test').Page,
  message: string,
): Promise<{ responseText: string; headers: Record<string, string> }> {
  // Count assistant bubbles before sending — the count increment is a permanent DOM signal,
  // unlike the typing indicator which appears and disappears too fast for Playwright to catch.
  const assistantBubbles = page.locator('div.flex.flex-col.items-start div.rounded-2xl')
  const beforeCount = await assistantBubbles.count()

  // Set up response header capture before clicking so we don't miss it
  const responsePromise = page.waitForResponse(
    (res) => res.url().includes('/api/chat') && res.request().method() === 'POST',
    { timeout: 45_000 },
  )

  // Fill and submit
  await page.getByPlaceholder('Message…').fill(message)
  await page.getByRole('button', { name: 'Send' }).click()

  // Capture headers (resolves when response headers arrive, stream still in progress)
  const chatResponse = await responsePromise
  const headers: Record<string, string> = {}
  for (const key of [
    'x-sage-node-path',
    'x-sage-skill-id',
    'x-sage-gate-path',
    'x-sage-prompt-layers',
    'x-sage-intent',
    'x-sage-emotional-intensity',
    'x-sage-turn-number',
    'x-sage-ai-message-id',
  ]) {
    const value = chatResponse.headers()[key]
    if (value) headers[key] = value
  }

  // Wait for a new assistant bubble to appear in the DOM
  await expect(assistantBubbles).toHaveCount(beforeCount + 1, { timeout: 90_000 })

  // Brief stabilization — bubble exists but streaming may still be appending tokens
  await page.waitForTimeout(3000)

  // Read the last assistant message
  const count = await assistantBubbles.count()
  const responseText = count > 0
    ? await assistantBubbles.nth(count - 1).innerText()
    : ''

  return { responseText, headers }
}

function parseNodePath(raw: string | undefined): string[] {
  if (!raw) return []
  try { return JSON.parse(raw) as string[] } catch { return [] }
}

// ─── test ────────────────────────────────────────────────────────────────────

test.describe('TC-4: CBT Thought Record Full Flow', () => {

  test('3-turn CBT skill flow validates full stack including P1-4 fix', async ({ page }) => {
    // LLM streaming can take 10-20s per turn × 3 turns + overhead = ~90s minimum.
    // Override the global 30s config timeout for this test.
    test.setTimeout(180_000)
    // Navigate to a fresh chat session
    await page.goto('/chat')
    await page.waitForURL(/\/chat/)

    // ── Turn 1: Trigger skill activation ──────────────────────────────────────
    const turn1 = await sendMessage(
      page,
      'I keep telling myself I\'m worthless and everything is my fault',
    )

    // UI: response appeared and completed
    expect(turn1.responseText.length).toBeGreaterThan(10)

    // P1-4 fix: old form labels must never appear in the LLM response
    expect(turn1.responseText).not.toContain('Goal:')
    expect(turn1.responseText).not.toContain('Technique:')

    // Conversational framing: Socratic question expected
    expect(turn1.responseText).toContain('?')

    // Routing: standard gate path
    expect(turn1.headers['x-sage-gate-path']).toBe('standard')

    // Routing: node path includes freeflow_respond
    const nodePath1 = parseNodePath(turn1.headers['x-sage-node-path'])
    expect(nodePath1).toContain('freeflow_respond')

    console.log('[TC-4 Turn 1] skill-id:', turn1.headers['x-sage-skill-id'])
    console.log('[TC-4 Turn 1] node-path:', turn1.headers['x-sage-node-path'])
    console.log('[TC-4 Turn 1] prompt-layers:', turn1.headers['x-sage-prompt-layers'])
    console.log('[TC-4 Turn 1] response (first 100):', turn1.responseText.slice(0, 100))

    // ── Turn 2: High-intensity validation hold ────────────────────────────────
    const turn2 = await sendMessage(
      page,
      'I just feel like such a failure',
    )

    expect(turn2.responseText.length).toBeGreaterThan(10)
    expect(turn2.responseText).not.toContain('Goal:')
    expect(turn2.responseText).not.toContain('Technique:')

    // Gate path must remain standard
    expect(turn2.headers['x-sage-gate-path']).toBe('standard')

    // Skill must still be active on turn 2 (if skill was triggered on turn 1)
    // skill_id is present if skill_executor ran
    const skillId2 = turn2.headers['x-sage-skill-id']
    if (skillId2) {
      expect(skillId2).toBe('cbt_thought_record')
      const nodePath2 = parseNodePath(turn2.headers['x-sage-node-path'])
      expect(nodePath2).toContain('skill_executor')
      expect(nodePath2).toContain('freeflow_respond')
    }

    console.log('[TC-4 Turn 2] skill-id:', turn2.headers['x-sage-skill-id'])
    console.log('[TC-4 Turn 2] node-path:', turn2.headers['x-sage-node-path'])
    console.log('[TC-4 Turn 2] response (first 100):', turn2.responseText.slice(0, 100))

    // ── Turn 3: Step advancement — response engages with evidence ────────────
    const turn3 = await sendMessage(
      page,
      'My colleague actually told me I did good work on the project last week',
    )

    expect(turn3.responseText.length).toBeGreaterThan(10)
    expect(turn3.responseText).not.toContain('Goal:')
    expect(turn3.responseText).not.toContain('Technique:')

    // Gate path must remain standard
    expect(turn3.headers['x-sage-gate-path']).toBe('standard')

    // Node path must include freeflow_respond
    const nodePath3 = parseNodePath(turn3.headers['x-sage-node-path'])
    expect(nodePath3).toContain('freeflow_respond')

    console.log('[TC-4 Turn 3] skill-id:', turn3.headers['x-sage-skill-id'])
    console.log('[TC-4 Turn 3] node-path:', turn3.headers['x-sage-node-path'])
    console.log('[TC-4 Turn 3] response (first 100):', turn3.responseText.slice(0, 100))

    // ── Final: All 3 user messages visible in chat ────────────────────────────
    await expect(page.getByText("I keep telling myself I'm worthless")).toBeVisible()
    await expect(page.getByText("I just feel like such a failure")).toBeVisible()
    await expect(page.getByText('My colleague actually told me')).toBeVisible()
  })

})
