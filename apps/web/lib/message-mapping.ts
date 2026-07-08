// Single source of truth for mapping a persisted `messages` row to the client message shape, so
// no reload/history path can silently drop a derived field. Structural sibling to lib/crisis.ts:
// #191's root cause was in-band signaling, and its sibling audit found the SAME history mapping
// ALSO dropped isCrisis, supabaseId (feedback buttons), and direction (RTL) — the
// "someone maps rows and forgets a field" class. Owning ALL derivation here retires that class.

const ARABIC = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/

export type SdkRole = 'user' | 'assistant' | 'system'

export interface MessageRow {
  id: string
  role: string
  content: string
}

export interface MappedMessage {
  id: string
  /** = row id. Restores the feedback wiring on reload (MessageBubble renders FeedbackButtons only when supabaseId is present). */
  supabaseId: string
  role: SdkRole
  content: string
  /** Out-of-band crisis flag for role='crisis' rows (never the in-band sentinel — see lib/crisis.ts / #191). */
  isCrisis?: boolean
  /** Authoritative direction restored from content (no detected_language column is persisted per-message). */
  direction: 'ltr' | 'rtl'
}

export function mapRowToSdkMessage(row: MessageRow): MappedMessage {
  const isCrisisRow = row.role === 'crisis'
  return {
    id: row.id,
    supabaseId: row.id,
    role: row.role === 'ai' || row.role === 'crisis' ? 'assistant' : (row.role as SdkRole),
    content: row.content,
    isCrisis: isCrisisRow ? true : undefined,
    direction: ARABIC.test(row.content) ? 'rtl' : 'ltr',
  }
}
