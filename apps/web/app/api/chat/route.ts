// apps/web/app/api/chat/route.ts
import { streamText, generateText } from 'ai'
import { createOpenAI } from '@ai-sdk/openai'
import { createClient } from '@/lib/supabase/server'
import type { Intent } from '@cdai/types'

const openrouter = createOpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: process.env.OPENROUTER_API_KEY!,
})

const CLASSIFIER_MODEL = 'anthropic/claude-haiku-4-5-20251001'
const CHAT_MODEL = 'anthropic/claude-sonnet-4-6'

const KNOWLEDGE_SYSTEM = `You are Sage, a compassionate AI wellbeing assistant partnered with the Community Development Authority of Dubai. When users ask questions about wellness topics, mental health concepts, parenting, or CDA services, provide clear, accurate, and empathetic answers grounded in evidence. Keep responses warm, concise, and culturally sensitive. Never diagnose. Always encourage professional support for serious concerns.`

const EMOTIONAL_SYSTEM = `You are Sage, a warm and skilled AI wellbeing companion. You use CBT and DBT-informed approaches to help users process feelings, gain perspective, and develop coping strategies. Listen actively, validate emotions, and gently guide reflection. Never dismiss feelings. If you detect any crisis signals (suicidal thoughts, self-harm, abuse), include a crisis support message immediately and prominently.`

const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'
const CRISIS_SYSTEM_ADDITION = ` If the user expresses thoughts of suicide, self-harm, or is in immediate danger, prepend your response with exactly "${CRISIS_SIGNAL}" on its own line before your regular response.`

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

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage)
  const systemPrompt = (intent === 'knowledge' ? KNOWLEDGE_SYSTEM : EMOTIONAL_SYSTEM) + CRISIS_SYSTEM_ADDITION

  // Persist user message
  const supabase = await createClient()
  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

  const result = streamText({
    model: openrouter(CHAT_MODEL),
    system: systemPrompt,
    messages: messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })),
    onFinish: async ({ text }) => {
      // Persist AI response
      const isCrisis = text.startsWith(CRISIS_SIGNAL)
      const content = isCrisis ? text.replace(CRISIS_SIGNAL + '\n', '') : text
      await supabase.from('messages').insert({
        session_id: sessionId,
        role: isCrisis ? 'crisis' : 'ai',
        content,
        intent,
      })

      // Name session after first exchange if unnamed
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
      // For pilot, all progress data comes from lib/demo-seed.ts.
      // Real path: score mood 1-5 via a generateText call on the full exchange,
      // insert to mood_scores table; generate a brief insight and insert to session_insights.
    },
  })

  return result.toTextStreamResponse()
}
