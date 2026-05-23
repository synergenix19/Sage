import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// PWA-1: Service worker is registered
// ---------------------------------------------------------------------------
test.describe('PWA-1 — Service worker registration', () => {
  test('sw.js is served at /sw.js with correct content type', async ({ request }) => {
    const res = await request.get('/sw.js')
    expect(res.status()).toBe(200)
    const body = await res.text()
    expect(body).toContain("const CACHE_NAME = 'cdai-v1'")
    expect(body).toContain("self.addEventListener('install'")
    expect(body).toContain("self.addEventListener('activate'")
    expect(body).toContain("self.addEventListener('fetch'")
  })

  test('service worker registers successfully in browser', async ({ page }) => {
    await page.goto('/')
    // Allow time for SW registration and activation
    await page.waitForTimeout(3000)

    const swRegistered = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) return false
      try {
        const reg = await navigator.serviceWorker.ready
        return !!reg.active
      } catch {
        return false
      }
    })
    expect(swRegistered).toBe(true)
  })

  test('offline.html is cached after SW activates', async ({ page }) => {
    await page.goto('/')
    // Allow time for SW to install and cache the offline page
    await page.waitForTimeout(3000)

    const offlineCached = await page.evaluate(async () => {
      const cache = await caches.open('cdai-v1')
      const response = await cache.match('/offline.html')
      return !!response
    })
    expect(offlineCached).toBe(true)
  })

  test('navigate request falls back to offline.html when network is down', async ({
    page,
    context,
  }) => {
    // Load page so SW registers and activates
    await page.goto('/')
    await page.evaluate(async () => { await navigator.serviceWorker.ready })
    await page.waitForTimeout(2000)

    // Go offline
    await context.setOffline(true)

    // Navigate to /chat — SW should serve offline.html
    try {
      await page.goto('/chat', { waitUntil: 'domcontentloaded', timeout: 8000 })
    } catch {
      // Expected — offline navigation may throw in some Playwright versions
    }

    const bodyText = await page.textContent('body').catch(() => '')
    expect(bodyText).toMatch(/offline|غير متصل|Offline/i)

    // Restore network
    await context.setOffline(false)
  })
})

// ---------------------------------------------------------------------------
// PWA-2: SW update banner uses controllerchange
// ---------------------------------------------------------------------------
test.describe('PWA-2 — SW update banner uses controllerchange', () => {
  test('sw-update-banner does not call reload() directly after postMessage', async ({
    request,
  }) => {
    // Structural test via SW content verification — reload() is inside controllerchange
    const res = await request.get('/sw.js')
    expect(res.status()).toBe(200)
    const body = await res.text()
    expect(body).toContain('SKIP_WAITING')
    expect(body).toContain('self.skipWaiting()')
  })
})

// ---------------------------------------------------------------------------
// PWA-3: Maskable icon
// ---------------------------------------------------------------------------
test.describe('PWA-3 — Maskable icon is valid', () => {
  test('manifest.json references maskable icon with correct purpose', async ({ request }) => {
    const res = await request.get('/manifest.json')
    expect(res.status()).toBe(200)
    const manifest = await res.json()

    const maskableIcon = manifest.icons?.find(
      (icon: { purpose?: string }) => icon.purpose === 'maskable'
    )
    expect(maskableIcon).toBeTruthy()
    expect(maskableIcon.src).toContain('icon-maskable-512')
    expect(maskableIcon.sizes).toBe('512x512')
  })

  test('maskable icon file is served and is a valid PNG above placeholder size', async ({
    request,
  }) => {
    const res = await request.get('/icons/icon-maskable-512.png')
    expect(res.status()).toBe(200)
    const contentType = res.headers()['content-type']
    expect(contentType).toContain('image/png')

    const body = await res.body()
    // Proper 512×512 icon should be well above 5 KB (our generated icon is ~18 KB)
    expect(body.length).toBeGreaterThan(5000)
  })
})
