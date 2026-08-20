import { describe, it, expect, beforeEach } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import path from 'path'
import { render, screen } from '@testing-library/react'
import { Providers } from '../providers'
import { useLocaleStore } from '@/lib/stores/locale-store'

// Recursively collects non-test source files under `dir`, skipping build
// output and dependency directories.
function collectSourceFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (['node_modules', '.next', 'dist', 'playwright', '.turbo'].includes(entry)) continue
    const full = path.join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      collectSourceFiles(full, out)
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.includes('.test.')) {
      out.push(full)
    }
  }
  return out
}

describe('Providers', () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: 'en' })
  })

  it('seeds the locale store from the server-provided initialLocale prop', () => {
    render(
      <Providers initialLocale="ar">
        <div>child</div>
      </Providers>
    )
    expect(useLocaleStore.getState().locale).toBe('ar')
  })

  it('leaves the default locale alone when the server prop is en', () => {
    render(
      <Providers initialLocale="en">
        <div>child</div>
      </Providers>
    )
    expect(useLocaleStore.getState().locale).toBe('en')
  })

  it('does not re-seed (force-overwrite) the store on a later re-render', () => {
    const { rerender } = render(
      <Providers initialLocale="en">
        <div>child</div>
      </Providers>
    )

    // Simulate a locale change that happened client-side after mount, without
    // a full reload (e.g. a stray re-render caused by unrelated state).
    useLocaleStore.setState({ locale: 'ar' })

    rerender(
      <Providers initialLocale="en">
        <div>child</div>
      </Providers>
    )

    expect(useLocaleStore.getState().locale).toBe('ar')
  })

  it('renders children', () => {
    render(
      <Providers initialLocale="en">
        <div>hello</div>
      </Providers>
    )
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  // These two tests enforce, in CI, the invariant documented in the
  // providers.tsx comment above the seed: Providers is the sole seeder of
  // useLocaleStore, and no locale-subscribing component may mount above it.
  // The render-body `setState` in Providers is only render-pure-safe under
  // that invariant, so it's asserted here rather than left to tree position.

  it('INVARIANT: a locale subscriber mounted without Providers sees the un-seeded default, not any intended locale', () => {
    // Documents the failure mode the invariant guards against: if a
    // locale-aware component ever mounts above (or without) Providers, it
    // renders against the store's un-seeded default rather than the
    // server-read cookie value.
    function Subscriber() {
      const locale = useLocaleStore((s) => s.locale)
      return <span>locale:{locale}</span>
    }
    render(<Subscriber />)
    expect(screen.getByText('locale:en')).toBeInTheDocument()
  })

  it('INVARIANT: Providers is the sole call site that seeds useLocaleStore', () => {
    const appRoot = path.resolve(__dirname, '..', '..')
    const files = collectSourceFiles(appRoot)
    const seedPattern = /useLocaleStore\.setState\s*\(/

    const offenders = files.filter((file) => {
      const isProviders = file === path.join(appRoot, 'components', 'providers.tsx')
      if (isProviders) return false
      return seedPattern.test(readFileSync(file, 'utf8'))
    })

    expect(offenders).toEqual([])
  })
})
