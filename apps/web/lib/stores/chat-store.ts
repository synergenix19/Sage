import { create } from 'zustand'
import type { ChatMessage, ChatSession } from '@cdai/types'

interface ChatStore {
  activeSession: ChatSession | null
  messages: ChatMessage[]
  isStreaming: boolean
  sessions: ChatSession[]
  setActiveSession: (session: ChatSession | null) => void
  setMessages: (messages: ChatMessage[]) => void
  appendMessage: (message: ChatMessage) => void
  setIsStreaming: (streaming: boolean) => void
  setSessions: (sessions: ChatSession[]) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  activeSession: null,
  messages: [],
  isStreaming: false,
  sessions: [],
  setActiveSession: (session) => set({ activeSession: session }),
  setMessages: (messages) => set({ messages }),
  appendMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  setSessions: (sessions) => set({ sessions }),
}))
