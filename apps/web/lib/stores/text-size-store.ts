import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type TextSize = 'sm' | 'md' | 'lg'

interface TextSizeStore {
  size: TextSize
  setSize: (size: TextSize) => void
}

export const useTextSizeStore = create<TextSizeStore>()(
  persist(
    (set) => ({
      size: 'md',
      setSize: (size) => set({ size }),
    }),
    { name: 'cdai-text-size' }
  )
)
