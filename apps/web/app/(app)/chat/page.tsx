import { ChatInterface } from '@/components/chat/chat-interface'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

type SdkRole = 'user' | 'assistant' | 'system'
interface InitialMessage { id: string; role: SdkRole; content: string }

export default async function ChatPage({
  searchParams,
}: {
  searchParams: Promise<{ session?: string }>
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { session: sessionParam } = await searchParams

  let activeSession = null

  // If a specific session is requested, load it (verify ownership)
  if (sessionParam) {
    const { data } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('id', sessionParam)
      .eq('user_id', user.id)
      .single()
    activeSession = data ?? null
  }

  // Fall back to most recently updated session
  if (!activeSession) {
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

  // Load messages for this session ordered chronologically
  const { data: msgRows } = await supabase
    .from('messages')
    .select('id, role, content')
    .eq('session_id', activeSession.id)
    .order('created_at', { ascending: true })

  const initialMessages: InitialMessage[] = (msgRows ?? []).map((row) => ({
    id: row.id as string,
    role: (row.role === 'ai' || row.role === 'crisis' ? 'assistant' : row.role) as SdkRole,
    content: row.role === 'crisis' ? `${CRISIS_SIGNAL}${row.content as string}` : row.content as string,
  }))

  const { data: profile } = await supabase
    .from('user_profiles')
    .select('name, locale')
    .eq('id', user.id)
    .single()

  return (
    <ChatInterface
      initialSession={activeSession}
      initialMessages={initialMessages}
      userName={profile?.name ?? ''}
      userId={user.id}
    />
  )
}
