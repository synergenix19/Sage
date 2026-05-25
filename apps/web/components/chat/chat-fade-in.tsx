import type { ReactNode } from 'react'

export function ChatFadeIn({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full flex-col animate-fade-in">
      {children}
    </div>
  )
}
