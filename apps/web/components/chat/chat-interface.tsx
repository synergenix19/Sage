'use client'
import type { ChatSession } from '@cdai/types'

interface ChatInterfaceProps {
  initialSession: ChatSession | null
  userName: string
  userId: string
}

export function ChatInterface({ userName }: ChatInterfaceProps) {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="text-sm text-[var(--color-text-secondary)]">Chat coming in Task 14…</p>
    </div>
  )
}
