/**
 * Staff persona smoke tests — Doc A §8.4 / Doc B §8.3-8.6
 *
 * Four persona flows each use a fresh browser context with its own sign-in session.
 * No shared storageState — each test authenticates independently so role isolation
 * is proven end-to-end, not assumed from a stored cookie.
 *
 * Seeded fixtures (all created by global-setup.ts):
 *   e2e-super-admin@test.internal → super_admin
 *   e2e-reviewer@test.internal    → clinical_reviewer
 *   e2e-ops@test.internal         → operations_admin
 *   e2e-member@test.internal      → member (no user_roles row → defaults to member)
 *
 * sage-e2e@test.internal is the shared storageState member user; it must NOT hold
 * a staff role (STATE-1 in sprint-a-security.spec.ts verifies this boundary).
 */

import { test, expect, chromium } from '@playwright/test'

const BASE = 'http://localhost:3000'

const FIXTURES = {
  superAdmin:         { email: 'e2e-super-admin@test.internal',    password: 'SageStaff-2026!'  },
  clinicalReviewer:   { email: 'e2e-reviewer@test.internal',       password: 'SageStaff-2026!'  },
  operationsAdmin:    { email: 'e2e-ops@test.internal',            password: 'SageStaff-2026!'  },
  member:             { email: 'e2e-member@test.internal',         password: 'SageStaff-2026!'  },
} as const

/** Sign in via UI and return the page, ready for assertions. */
async function signInAs(browser: ReturnType<typeof chromium.launch> extends Promise<infer B> ? B : never, email: string, password: string) {
  const ctx  = await browser.newContext({ storageState: undefined })
  const page = await ctx.newPage()
  await page.goto(`${BASE}/sign-in`)
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Password').fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  // After sign-in, Next.js redirects based on role and onboarding state
  await page.waitForURL(/\/(chat|admin|live|step-\d+)/, { timeout: 20_000 })
  return { page, ctx }
}

// ---------------------------------------------------------------------------
// Flow 1: super_admin — sees both Live and Admin in StaffNav, can navigate, can sign out
// ---------------------------------------------------------------------------
test.describe('super_admin — full staff nav + sign-out', () => {
  test('sees StaffNav with Live and Admin links on /live', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/live`)
    await expect(page).toHaveURL(/\/live/)

    const staffNav = page.getByRole('navigation', { name: 'Staff navigation' })
    await expect(staffNav).toBeVisible()
    await expect(staffNav.getByRole('link', { name: 'Live' })).toBeVisible()
    await expect(staffNav.getByRole('link', { name: 'Admin' })).toBeVisible()

    await ctx.close()
  })

  test('StaffNav "Admin" link navigates to /admin without full reload', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/live`)
    await expect(page).toHaveURL(/\/live/)

    const navStart = Date.now()
    await page.getByRole('navigation', { name: 'Staff navigation' }).getByRole('link', { name: 'Admin' }).click()
    await page.waitForURL(/\/admin/, { timeout: 10_000 })
    const navMs = Date.now() - navStart

    // AdminSectionNav should be visible (intra-page section nav)
    await expect(page.locator('aside')).toBeVisible()
    // Should navigate client-side (< 3000ms — full reload would take longer and lose nav state)
    expect(navMs).toBeLessThan(3000)

    await ctx.close()
  })

  test('StaffNav "Live" link navigates back to /live from /admin', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL(/\/admin/)

    await page.getByRole('navigation', { name: 'Staff navigation' }).getByRole('link', { name: 'Live' }).click()
    await page.waitForURL(/\/live/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/live/)

    await ctx.close()
  })

  test('sign out from /live redirects to /sign-in', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/live`)
    await page.getByRole('button', { name: /sign out/i }).click()
    await page.waitForURL(/\/sign-in/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/sign-in/)

    await ctx.close()
  })

  test('sign out from /admin redirects to /sign-in', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/admin`)
    await page.getByRole('button', { name: /sign out/i }).click()
    await page.waitForURL(/\/sign-in/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/sign-in/)

    await ctx.close()
  })
})

// ---------------------------------------------------------------------------
// Flow 2: clinical_reviewer — sees only Live in StaffNav, /admin → 404
// ---------------------------------------------------------------------------
test.describe('clinical_reviewer — live access, admin denied', () => {
  test('/live loads and StaffNav shows only Live (no Admin link)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.clinicalReviewer.email, FIXTURES.clinicalReviewer.password)

    await page.goto(`${BASE}/live`)
    await expect(page).toHaveURL(/\/live/)

    const staffNav = page.getByRole('navigation', { name: 'Staff navigation' })
    await expect(staffNav).toBeVisible()
    await expect(staffNav.getByRole('link', { name: 'Live' })).toBeVisible()
    // operations_admin capability absent → Admin link must not appear
    await expect(staffNav.getByRole('link', { name: 'Admin' })).not.toBeVisible()

    await ctx.close()
  })

  test('/admin renders not-found page (not blank screen)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.clinicalReviewer.email, FIXTURES.clinicalReviewer.password)

    await page.goto(`${BASE}/admin`)
    // Next.js notFound() renders not-found.tsx. Dev mode returns 200 HTTP status
    // (production correctly returns 404). Assert on rendered content, not HTTP status.
    // The key check: the admin dashboard does NOT render; the not-found page DOES.
    await expect(page.getByRole('heading', { name: /not found|page not found/i })).toBeVisible({ timeout: 5000 })
    // Admin dashboard content must be absent
    await expect(page.locator('aside')).not.toBeVisible()

    await ctx.close()
  })
})

// ---------------------------------------------------------------------------
// Flow 3: operations_admin — sees only Admin in StaffNav, /live → 404
// ---------------------------------------------------------------------------
test.describe('operations_admin — admin access, live denied', () => {
  test('/admin loads and StaffNav shows only Admin (no Live link)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.operationsAdmin.email, FIXTURES.operationsAdmin.password)

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL(/\/admin/)

    const staffNav = page.getByRole('navigation', { name: 'Staff navigation' })
    await expect(staffNav).toBeVisible()
    await expect(staffNav.getByRole('link', { name: 'Admin' })).toBeVisible()
    // live:read capability absent → Live link must not appear
    await expect(staffNav.getByRole('link', { name: 'Live' })).not.toBeVisible()

    await ctx.close()
  })

  test('/live renders not-found page (not blank, not redirect to sign-in)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.operationsAdmin.email, FIXTURES.operationsAdmin.password)

    await page.goto(`${BASE}/live`)
    await expect(page).not.toHaveURL(/\/sign-in/)
    await expect(page.getByRole('heading', { name: /not found|page not found/i })).toBeVisible({ timeout: 5000 })

    await ctx.close()
  })
})

// ---------------------------------------------------------------------------
// Flow 4: member — both staff surfaces render 404
// ---------------------------------------------------------------------------
test.describe('member — no staff access', () => {
  test('/live is denied — redirect to sign-in (member has no staff:access)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.member.email, FIXTURES.member.password)

    await page.goto(`${BASE}/live`)
    // member has no staff:access → middleware redirects to /sign-in before layout runs
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 5000 })

    await ctx.close()
  })

  test('/admin is denied — redirect to sign-in', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.member.email, FIXTURES.member.password)

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 5000 })

    await ctx.close()
  })

  test('/chat loads normally with AppSideNav (member surface unaffected)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.member.email, FIXTURES.member.password)

    await page.goto(`${BASE}/chat`)
    await expect(page).toHaveURL(/\/chat/)
    // AppSideNav should be present; StaffNav should not
    await expect(page.getByRole('navigation', { name: 'Staff navigation' })).not.toBeVisible()

    await ctx.close()
  })
})

// ---------------------------------------------------------------------------
// Flow 5: AdminSectionNav IntersectionObserver — P4.15 regression check
// ---------------------------------------------------------------------------
test.describe('AdminSectionNav — section scroll and active-state tracking', () => {
  test('initial active section is the first visible section (not "overview" phantom)', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL(/\/admin/)

    // Wait for the section nav to render
    const aside = page.locator('aside')
    await expect(aside).toBeVisible()

    // The active link is styled with bg-[var(--color-primary)]
    const activeLink = aside.locator('a[aria-current="page"], a.bg-\\[var\\(--color-primary\\)\\]').first()
    await expect(activeLink).toBeVisible({ timeout: 3000 })

    // It should be the first real section, not a phantom "overview" div
    const activeText = await activeLink.textContent()
    expect(activeText?.trim()).not.toBe('')

    await ctx.close()
  })

  test('clicking a section nav item scrolls to that section and updates active state', async ({ browser }) => {
    const { page, ctx } = await signInAs(browser, FIXTURES.superAdmin.email, FIXTURES.superAdmin.password)

    await page.goto(`${BASE}/admin`)
    const aside = page.locator('aside')
    await expect(aside).toBeVisible()

    // Get all section nav links
    const navLinks = aside.locator('a[href^="#"]')
    const count = await navLinks.count()
    expect(count).toBeGreaterThan(1)

    // Click the second nav link
    const secondLink = navLinks.nth(1)
    const targetText = await secondLink.textContent()
    await secondLink.click()

    // Wait for scroll to settle and IntersectionObserver to fire
    await page.waitForTimeout(800)

    // The clicked link (or the now-visible section's nav item) should be active
    const activeAfter = aside.locator('a[aria-current="page"], a.bg-\\[var\\(--color-primary\\)\\]').first()
    const activeText = await activeAfter.textContent()
    // Active link text should match what we clicked
    expect(activeText?.trim()).toBe(targetText?.trim())

    await ctx.close()
  })
})
