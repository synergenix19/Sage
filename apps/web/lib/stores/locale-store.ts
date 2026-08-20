import { create } from 'zustand'
import type { Locale } from '@cdai/types'

const COOKIE_NAME = 'cdai-locale'
const COOKIE_MAX_AGE_SECONDS = 31536000

interface SetLocaleOptions {
  /**
   * Navigate to this path instead of reloading the current page. Used by the
   * onboarding language step, which advances to the next step rather than
   * staying put.
   */
  redirectTo?: string
}

interface LocaleStore {
  locale: Locale
  /**
   * Single source of truth for a locale change: writes the `cdai-locale`
   * cookie (with its security-relevant attributes), updates the store, and
   * triggers the hard navigation that layout.tsx's server-side cookie read
   * (and the `dir`/`lang` flip) depends on.
   */
  setLocale: (locale: Locale, options?: SetLocaleOptions) => void
}

export const useLocaleStore = create<LocaleStore>()((set) => ({
  locale: 'en',
  setLocale: (locale, options) => {
    document.cookie = `${COOKIE_NAME}=${locale};path=/;max-age=${COOKIE_MAX_AGE_SECONDS};SameSite=Lax;Secure`
    set({ locale })
    if (options?.redirectTo) {
      window.location.href = options.redirectTo
    } else {
      window.location.reload()
    }
  },
}))
