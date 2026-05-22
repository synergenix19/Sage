// apps/web/app/api/feedback/route.ts
import { createClient } from '@/lib/supabase/server'

export async function POST(req: Request) {
  const { messageId, value } = await req.json() as {
    messageId: string
    value: unknown
  }

  if (value !== 1 && value !== -1) {
    return new Response('value must be 1 or -1', { status: 400 })
  }

  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return new Response('Unauthorized', { status: 401 })
  }

  const { data: message } = await supabase
    .from('messages')
    .select('session_id')
    .eq('id', messageId)
    .single()
  if (!message) return new Response('Not Found', { status: 404 })

  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', message.session_id)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })

  const { error } = await supabase
    .from('message_feedback')
    .upsert(
      { message_id: messageId, user_id: user.id, value: value as 1 | -1 },
      { onConflict: 'message_id,user_id' }
    )

  if (error) {
    console.error('[feedback] upsert failed:', error)
    return new Response('Internal Server Error', { status: 500 })
  }

  return new Response('OK', { status: 200 })
}
