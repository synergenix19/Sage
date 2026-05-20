// apps/web/app/api/chat/route.ts
import { generateText } from 'ai'
import { createOpenAI } from '@ai-sdk/openai'
import { createClient } from '@/lib/supabase/server'
import type { Intent } from '@cdai/types'

const openrouter = createOpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: process.env.OPENROUTER_API_KEY!,
})

const CLASSIFIER_MODEL = 'anthropic/claude-haiku-4-5-20251001'
const SAGE_API_URL = process.env.SAGE_API_URL ?? 'http://localhost:8000'
const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

async function classifyIntent(message: string): Promise<Intent> {
  const { text } = await generateText({
    model: openrouter(CLASSIFIER_MODEL),
    prompt: `Classify this message as "knowledge" (asking for information or resources) or "emotional" (seeking support, sharing feelings). Reply with exactly one word.\n\nMessage: "${message}"`,
    maxOutputTokens: 5,
  })
  return text.trim().toLowerCase().startsWith('k') ? 'knowledge' : 'emotional'
}

export async function POST(req: Request) {
  const { messages, sessionId } = await req.json() as {
    messages: { role: string; content: string }[]
    sessionId: string
  }

  if (!sessionId || !messages?.length) {
    return new Response('Bad Request', { status: 400 })
  }

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage)

  const supabase = await createClient()
  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

  const sageRes = await fetch(`${SAGE_API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      session_id: sessionId,
    }),
  })

  if (!sageRes.ok || !sageRes.body) {
    return new Response('Upstream error', { status: 502 })
  }

  const [clientStream, persistStream] = sageRes.body.tee()

  void (async () => {
    try {
      const reader = persistStream.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        accumulated += decoder.decode(value, { stream: true })
      }
      accumulated += decoder.decode() // flush: releases any buffered incomplete multi-byte sequence

      const isCrisis = accumulated.startsWith(CRISIS_SIGNAL)
      const content = isCrisis
        ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
        : accumulated

      await supabase.from('messages').insert({
        session_id: sessionId,
        role: isCrisis ? 'crisis' : 'ai',
        content,
        intent,
      })

      const { data: session } = await supabase
        .from('chat_sessions')
        .select('name')
        .eq('id', sessionId)
        .single()

      if (session && !session.name) {
        const { text: sessionName } = await generateText({
          model: openrouter(CLASSIFIER_MODEL),
          prompt: `Give this conversation a short title (3-5 words, no quotes):\n\nUser: "${lastMessage}"`,
          maxOutputTokens: 15,
        })
        await supabase.from('chat_sessions')
          .update({ name: sessionName.trim(), updated_at: new Date().toISOString() })
          .eq('id', sessionId)
      }
      // POST-PILOT: Add mood scoring and insight generation here.
      // Real path: score mood 1-5 via a generateText call on the full exchange,
      // insert to mood_scores table; generate a brief insight and insert to session_insights.
    } catch (err) {
      console.error('[chat/persist] failed:', err)
    }
  })()

  return new Response(clientStream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
