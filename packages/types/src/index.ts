export type Locale = 'en' | 'ar'
export type UserRole = 'parent' | 'service_user' | 'professional'
export type MessageRole = 'user' | 'ai' | 'system' | 'crisis'
export type Intent = 'knowledge' | 'emotional'
export type AgeRange = 'under-18' | '18-24' | '25-34' | '35-44' | '45-54' | '55+'

export interface UserProfile {
  id: string
  name: string
  ageRange: AgeRange
  role: UserRole
  locale: Locale
  isAdmin: boolean
  onboardingComplete: boolean
  onboardingStep: number
  wellnessQ1: string | null
  wellnessQ2: string | null
  createdAt: string
}

export interface ChatSession {
  id: string
  userId: string
  name: string | null
  createdAt: string
  updatedAt: string
}

// Knowledge-base source surfaced alongside an AI reply (X-Sage-Sources response
// header). 'article' renders as a link, 'video' as an embedded player.
export interface Source {
  type: 'article' | 'video'
  title: string
  url: string
  citation: string
}

export interface ChatMessage {
  id: string
  sessionId: string
  role: MessageRole
  content: string
  intent: Intent | null
  createdAt: string
  /** Authoritative text direction from the backend (X-Sage-Direction, derived from
   *  detected_language). When absent, the renderer falls back to dir="auto". */
  direction?: 'ltr' | 'rtl'
  /** KB sources for this reply (X-Sage-Sources), present only on ordinary
   *  content-gate turns with at least one usable source. Absent elsewhere. */
  sources?: Source[]
}

export interface SessionInsight {
  id: string
  sessionId: string
  userId: string
  content: string
  topicTag: string
  createdAt: string
}

export interface MoodScore {
  id: string
  userId: string
  sessionId: string
  score: number
  createdAt: string
}

export interface MessageFeedback {
  id: string
  messageId: string
  userId: string
  value: 1 | -1
  createdAt: string
}

// Maps Vercel AI SDK role strings to internal MessageRole.
// The SDK uses 'assistant'; our type uses 'ai'. Handles all four roles with a safe fallback.
export function mapSdkRole(sdkRole: string): MessageRole {
  switch (sdkRole) {
    case 'assistant': return 'ai'
    case 'user':      return 'user'
    case 'system':    return 'system'
    case 'crisis':    return 'crisis'
    default:          return 'ai'
  }
}
