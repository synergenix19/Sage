import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useLocaleStore } from '../locale-store'

describe('useLocaleStore', () => {
  let cookieSetSpy: ReturnType<typeof vi.fn<(value: string) => void>>
  let reloadSpy: ReturnType<typeof vi.fn<() => void>>
  let originalLocation: Location

  beforeEach(() => {
    useLocaleStore.setState({ locale: 'en' })

    // document.cookie attributes (path/max-age/SameSite/Secure) never round-trip
    // through a real cookie jar read-back, so assert on the exact assigned
    // string via a setter spy instead.
    cookieSetSpy = vi.fn<(value: string) => void>()
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get: () => '',
      set: cookieSetSpy,
    })

    reloadSpy = vi.fn<() => void>()
    originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, reload: reloadSpy, href: '' },
    })
  })

  afterEach(() => {
    Reflect.deleteProperty(document, 'cookie')
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
  })

  it('defaults to en', () => {
    expect(useLocaleStore.getState().locale).toBe('en')
  })

  it('setLocale updates locale', () => {
    useLocaleStore.getState().setLocale('ar')
    expect(useLocaleStore.getState().locale).toBe('ar')
  })

  it('writes the cdai-locale cookie with the exact security-relevant attributes', () => {
    useLocaleStore.getState().setLocale('ar')
    expect(cookieSetSpy).toHaveBeenCalledTimes(1)
    expect(cookieSetSpy).toHaveBeenCalledWith(
      'cdai-locale=ar;path=/;max-age=31536000;SameSite=Lax;Secure'
    )
  })

  it('writes the cookie for the "en" value too', () => {
    useLocaleStore.getState().setLocale('en')
    expect(cookieSetSpy).toHaveBeenCalledWith(
      'cdai-locale=en;path=/;max-age=31536000;SameSite=Lax;Secure'
    )
  })

  it('reloads the current page by default (no redirect target)', () => {
    useLocaleStore.getState().setLocale('ar')
    expect(reloadSpy).toHaveBeenCalledTimes(1)
    expect(window.location.href).toBe('')
  })

  it('navigates to redirectTo instead of reloading when provided', () => {
    useLocaleStore.getState().setLocale('ar', { redirectTo: '/step-3' })
    expect(reloadSpy).not.toHaveBeenCalled()
    expect(window.location.href).toBe('/step-3')
  })

  it('writes the cookie and updates state before navigating', () => {
    // Order matters: a hard reload/navigation immediately following setLocale
    // must not race the cookie write or the state update.
    const order: string[] = []
    cookieSetSpy.mockImplementation(() => order.push('cookie'))
    reloadSpy.mockImplementation(() => order.push('reload'))
    const unsub = useLocaleStore.subscribe(() => order.push('state'))

    useLocaleStore.getState().setLocale('ar')

    expect(order).toEqual(['cookie', 'state', 'reload'])
    unsub()
  })
})
