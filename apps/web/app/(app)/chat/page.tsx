import { ChatInterface } from '@/components/chat/chat-interface'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function ChatPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  // Fetch or create the active session
  const { data: sessions } = await supabase
    .from('chat_sessions')
    .select('*')
    .eq('user_id', user.id)
    .order('updated_at', { ascending: false })
    .limit(1)

  let activeSession = sessions?.[0] ?? null
  if (!activeSession) {
    const { data: newSession } = await supabase
      .from('chat_sessions')
      .insert({ user_id: user.id })
      .select()
      .single()
    activeSession = newSession
  }

  const { data: profile } = await supabase
    .from('user_profiles')
    .select('name, locale')
    .eq('id', user.id)
    .single()

  return (
    <ChatInterface
      initialSession={activeSession}
      userName={profile?.name ?? ''}
      userId={user.id}
    />
  )
}
