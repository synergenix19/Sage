import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Providers } from '../providers'
import { useLocaleStore } from '@/lib/stores/locale-store'

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
})
