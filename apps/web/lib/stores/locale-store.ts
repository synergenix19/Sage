import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale } from '@cdai/types'

interface LocaleStore {
  locale: Locale
  setLocale: (locale: Locale) => void
}

export const useLocaleStore = create<LocaleStore>()(
  persist(
    (set) => ({
      locale: 'en',
      setLocale: (locale) => set({ locale }),
    }),
    { name: 'cdai-locale' }
  )
)
