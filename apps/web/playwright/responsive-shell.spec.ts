import { test, expect, type Page } from '@playwright/test'
import path from 'path'
import fs from 'fs'
import { execSync } from 'child_process'

const AUTH_STATE = path.resolve(__dirname, '.auth-state.json')
const GLOBAL_SETUP = path.resolve(__dirname, 'global-setup.ts')

/** Re-run global setup to get a fresh Supabase session after sign-out invalidates the old one. */
function refreshAuthState() {
  execSync(`npx tsx "${GLOBAL_SETUP}"`, {
    cwd: path.resolve(__dirname, '..'),
    timeout: 30_000,
    stdio: 'pipe',
  })
}

/**
 * Inject the current auth-state cookies into a page's browser context.
 * Use this in beforeEach for describe blocks that run after the sign-out test
 * invalidates the shared session.
 */
async function injectFreshCookies(page: Page) {
  const state = JSON.parse(fs.readFileSync(AUTH_STATE, 'utf-8'))
  await page.context().clearCookies()
  await page.context().addCookies(state.cookies)
  if (state.origins) {
    for (const origin of state.origins) {
      if (origin.localStorage?.length) {
        await page.goto(origin.origin)
        for (const { name, value } of origin.localStorage) {
          await page.evaluate(
            ([k, v]: [string, string]) => localStorage.setItem(k, v),
            [name, value]
          )
        }
      }
    }
  }
}

const DESKTOP = { width: 1440, height: 900 }
const TABLET  = { width: 768,  height: 1024 }
const MOBILE  = { width: 393,  height: 852 }

// storageState is set globally in playwright.config.ts — all tests start authenticated
async function goToApp(page: Page) {
  await page.goto('/chat')
  await page.waitForURL('**/chat**', { timeout: 10_000 })
}

// ─── Desktop Layout ───────────────────────────────────────────────────────────

test.describe('Desktop layout (1440px)', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('sidebar is visible', async ({ page }) => {
    await expect(page.locator('aside')).toBeVisible()
  })

  test('TabBar is hidden on desktop', async ({ page }) => {
    // The TabBar nav has md:hidden — on desktop Chromium it should not be visible
    // We locate the nav that's a sibling of main inside the content wrapper
    const contentNav = page.locator('main + nav, main ~ nav').first()
    await expect(contentNav).toBeHidden()
  })

  test('sidebar shows app name', async ({ page }) => {
    await expect(page.locator('aside').getByText(/sage/i)).toBeVisible()
  })

  test('sidebar shows Chat and Progress nav links', async ({ page }) => {
    const sidebar = page.locator('aside')
    await expect(sidebar.getByRole('link', { name: /^chat$/i })).toBeVisible()
    await expect(sidebar.getByRole('link', { name: /^progress$/i })).toBeVisible()
  })

  test('active route Chat is highlighted', async ({ page }) => {
    const chatLink = page.locator('aside').getByRole('link', { name: /^chat$/i })
    const bgColor = await chatLink.evaluate(
      (el) => getComputedStyle(el).backgroundColor
    )
    // Should not be transparent — has a background color when active
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
    expect(bgColor).not.toBe('transparent')
  })

  test('clicking Progress navigates and updates active state', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: /^progress$/i }).click()
    await page.waitForURL('**/progress**')
    const progressLink = sidebar.getByRole('link', { name: /^progress$/i })
    const bgColor = await progressLink.evaluate(
      (el) => getComputedStyle(el).backgroundColor
    )
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
  })

  test('user email is displayed in sidebar footer', async ({ page }) => {
    const sidebar = page.locator('aside')
    await expect(sidebar.getByText('sage-e2e@test.internal')).toBeVisible()
  })

  test('user avatar shows first letter of email', async ({ page }) => {
    // sage-e2e@test.internal → first letter 'S'
    const sidebar = page.locator('aside')
    await expect(sidebar.getByText('S', { exact: true })).toBeVisible()
  })

  test('content area fills remaining width (no dead gutters)', async ({ page }) => {
    const sidebarBox = await page.locator('aside').boundingBox()
    const mainBox    = await page.locator('main').boundingBox()
    expect(sidebarBox).not.toBeNull()
    expect(mainBox).not.toBeNull()
    const totalWidth = sidebarBox!.width + mainBox!.width
    // Together they should fill most of the 1440px viewport
    expect(totalWidth).toBeGreaterThan(DESKTOP.width * 0.9)
  })

  test('no horizontal scrollbar', async ({ page }) => {
    const hasHScroll = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    )
    expect(hasHScroll).toBe(false)
  })
})

// ─── Mobile Layout ────────────────────────────────────────────────────────────

test.describe('Mobile layout (393px)', () => {
  test.use({ viewport: MOBILE })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('sidebar is hidden on mobile', async ({ page }) => {
    await expect(page.locator('aside')).toBeHidden()
  })

  test('TabBar is visible on mobile', async ({ page }) => {
    // TabBar renders as a <nav> at the bottom — look for nav links in it
    const navLinks = page.locator('nav').getByRole('link')
    const count = await navLinks.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  test('no horizontal scrollbar on mobile', async ({ page }) => {
    const hasHScroll = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    )
    expect(hasHScroll).toBe(false)
  })
})

// ─── Tablet Boundary (768px) ──────────────────────────────────────────────────

test.describe('Tablet portrait (768px) — breakpoint boundary', () => {
  test.use({ viewport: TABLET })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('sidebar is visible at exactly 768px', async ({ page }) => {
    await expect(page.locator('aside')).toBeVisible()
  })

  test('sidebar and content do not overlap', async ({ page }) => {
    const sidebarBox = await page.locator('aside').boundingBox()
    const mainBox    = await page.locator('main').boundingBox()
    expect(sidebarBox).not.toBeNull()
    expect(mainBox).not.toBeNull()
    // LTR: sidebar right edge should be at or before content left edge
    const sidebarRight = sidebarBox!.x + sidebarBox!.width
    expect(sidebarRight).toBeLessThanOrEqual(mainBox!.x + 2) // 2px tolerance
  })
})

// ─── Sign-Out Flow (non-destructive) ─────────────────────────────────────────

test.describe('Sign-out confirmation flow', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('sign-out icon opens confirmation dialog', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    await expect(sidebar.getByRole('dialog')).toBeVisible()
  })

  test('confirmation shows correct text', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    await expect(
      sidebar.getByText(/sign out of sage/i)
    ).toBeVisible()
  })

  test('Cancel dismisses confirmation', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    await sidebar.getByRole('button', { name: /cancel/i }).click()
    await expect(sidebar.getByRole('dialog')).toBeHidden()
  })

  test('Escape dismisses confirmation', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    await sidebar.getByRole('dialog').press('Escape')
    await expect(sidebar.getByRole('dialog')).toBeHidden()
  })

  test('focus lands on Cancel when confirmation opens', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    const cancelButton = sidebar.getByRole('button', { name: /cancel/i })
    await expect(cancelButton).toBeFocused()
  })

  test('Tab cycles focus within confirmation (focus trap)', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()

    // Cancel is focused first
    await expect(sidebar.getByRole('button', { name: /cancel/i })).toBeFocused()

    // Tab → Sign out
    await page.keyboard.press('Tab')
    await expect(sidebar.getByRole('button', { name: /^sign out$/i })).toBeFocused()

    // Tab → back to Cancel (trapped)
    await page.keyboard.press('Tab')
    await expect(sidebar.getByRole('button', { name: /cancel/i })).toBeFocused()

    // Shift+Tab → back to Sign out
    await page.keyboard.press('Shift+Tab')
    await expect(sidebar.getByRole('button', { name: /^sign out$/i })).toBeFocused()
  })
})

// ─── ARIA / Semantics ─────────────────────────────────────────────────────────

test.describe('ARIA semantics (desktop)', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('sidebar root is <aside>', async ({ page }) => {
    const tagName = await page.locator('aside').first().evaluate((el) => el.tagName)
    expect(tagName.toLowerCase()).toBe('aside')
  })

  test('nav links live inside <nav>', async ({ page }) => {
    const sidebar = page.locator('aside')
    const nav = sidebar.locator('nav').first()
    await expect(nav).toBeVisible()
    await expect(nav.getByRole('link', { name: /chat/i })).toBeVisible()
  })

  test('sign-out icon has aria-label', async ({ page }) => {
    const btn = page.locator('aside').getByRole('button', { name: /sign out/i })
    await expect(btn).toHaveAttribute('aria-label', /sign out/i)
  })

  test('confirmation dialog has role=dialog and aria-modal', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    const dialog = sidebar.getByRole('dialog')
    await expect(dialog).toHaveAttribute('aria-modal', 'true')
    await expect(dialog).toHaveAttribute('aria-label', /confirm sign out/i)
  })

  test('avatar div has aria-hidden', async ({ page }) => {
    const avatarDiv = page.locator('aside [aria-hidden="true"]').first()
    await expect(avatarDiv).toBeAttached()
  })
})

// ─── PWA Manifest ─────────────────────────────────────────────────────────────

test.describe('PWA manifest', () => {
  test('orientation is set to "any"', async ({ page }) => {
    const response = await page.goto('/manifest.json')
    const manifest = await response!.json()
    expect(manifest.orientation).toBe('any')
  })
})

// ─── Resize Behavior ──────────────────────────────────────────────────────────

test.describe('Resize behavior', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP)
    await goToApp(page)
  })

  test('sidebar appears and disappears cleanly on resize', async ({ page }) => {
    // Desktop: sidebar visible
    await expect(page.locator('aside')).toBeVisible()

    // Resize to mobile
    await page.setViewportSize(MOBILE)
    await expect(page.locator('aside')).toBeHidden()

    // Resize back to desktop
    await page.setViewportSize(DESKTOP)
    await expect(page.locator('aside')).toBeVisible()
  })
})

// ─── Chat Scroll ──────────────────────────────────────────────────────────────

test.describe('Chat scroll — no double scrollbar', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('body does not scroll when on chat route', async ({ page }) => {
    await page.waitForLoadState('networkidle')
    const bodyOverflow = await page.evaluate(() => getComputedStyle(document.body).overflow)
    const bodyHeight   = await page.evaluate(() => document.body.scrollHeight > document.body.clientHeight)
    // Body should not be independently scrollable
    expect(bodyHeight).toBe(false)
  })
})

// ─── Sign-Out Destructive (runs LAST to avoid invalidating shared auth) ───────

test.describe('Sign-out confirmation flow — destructive', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ page }) => { await goToApp(page) })

  test('confirming sign-out redirects to /sign-in', async ({ page }) => {
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: /sign out/i }).click()
    // Click Sign out inside the dialog
    await sidebar.getByRole('dialog').getByRole('button', { name: /sign out/i }).click()
    await page.waitForURL('**/sign-in**', { timeout: 10_000 })
    expect(page.url()).toContain('/sign-in')
  })
})
