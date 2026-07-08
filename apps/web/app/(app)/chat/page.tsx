import { ChatFadeIn } from '@/components/chat/chat-fade-in'
import { ChatInterface } from '@/components/chat/chat-interface'
import { createClient } from '@/lib/supabase/server'
import { hydrateSources } from '@/lib/sources'
import { mapRowToSdkMessage, type MappedMessage, type MessageRow } from '@/lib/message-mapping'
import type { Source } from '@cdai/types'
import { redirect } from 'next/navigation'

type InitialMessage = MappedMessage & { sources?: Source[] }

export default async function ChatPage({
  searchParams,
}: {
  searchParams: Promise<{ session?: string; new?: string }>
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { session: sessionParam, new: newSession } = await searchParams

  let activeSession = null

  // If a specific session is requested, load it (verify ownership)
  if (sessionParam && !newSession) {
    const { data } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('id', sessionParam)
      .eq('user_id', user.id)
      .single()
    activeSession = data ?? null
  }

  // Fall back to most recently updated session (skip if forcing new)
  if (!activeSession && !newSession) {
    const { data: sessions } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('user_id', user.id)
      .order('updated_at', { ascending: false })
      .limit(1)
    activeSession = sessions?.[0] ?? null
  }

  // Create new session if none exists
  if (!activeSession) {
    const { data: newSession, error: insertError } = await supabase
      .from('chat_sessions')
      .insert({ user_id: user.id })
      .select()
      .single()

    if (insertError || !newSession) {
      throw new Error('Failed to create chat session')
    }
    activeSession = newSession
  }

  // Load messages for this session ordered chronologically.
  // Secondary sort by turn_number (NULLS FIRST) breaks ties when user + AI
  // rows share the same created_at from a batch insert — user rows have
  // turn_number=NULL so they always sort before the AI row in the same turn.
  const { data: msgRows } = await supabase
    .from('messages')
    .select('id, role, content, sources')
    .eq('session_id', activeSession.id)
    .order('created_at', { ascending: true })
    .order('turn_number', { ascending: true, nullsFirst: true })

  // All row->message field derivation (role, isCrisis, supabaseId, direction) lives in one tested
  // function so no reload path can drop a field (#191 sibling audit). Sources hydration stays here
  // (UI-specific). Lane 2 Item 1.5 (c): malformed jsonb degrades to no card, never a crash.
  const initialMessages: InitialMessage[] = (msgRows ?? []).map((row) => ({
    ...mapRowToSdkMessage(row as MessageRow),
    sources: hydrateSources(row.sources),
  }))

  const { data: profile } = await supabase
    .from('user_profiles')
    .select('name, locale')
    .eq('id', user.id)
    .single()

  return (
    <ChatFadeIn key={activeSession.id}>
      <ChatInterface
        initialSession={activeSession}
        initialMessages={initialMessages}
        userName={profile?.name ?? ''}
        userId={user.id}
      />
    </ChatFadeIn>
  )
}
