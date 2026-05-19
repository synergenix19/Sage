import { describe, it, expect, beforeEach } from 'vitest'
import { useLocaleStore } from '../locale-store'

describe('useLocaleStore', () => {
  beforeEach(() => useLocaleStore.setState({ locale: 'en' }))

  it('defaults to en', () => {
    expect(useLocaleStore.getState().locale).toBe('en')
  })

  it('setLocale updates locale', () => {
    useLocaleStore.getState().setLocale('ar')
    expect(useLocaleStore.getState().locale).toBe('ar')
  })
})
