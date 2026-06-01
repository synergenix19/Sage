// apps/web/app/api/chat/route.ts
import { after } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { CRISIS_SIGNAL, SERVER_ERROR_SIGNAL } from '@/lib/constants'
import { z } from 'zod'

const MessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string().max(8000),
})

const ChatRequestSchema = z.object({
  sessionId: z.string().uuid(),
  messages: z.array(MessageSchema).min(1),
  userId: z.string().optional(),
})

const SAGE_API_URL = process.env.SAGE_API_URL ?? 'http://localhost:8000'

function parseJsonHeader<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try { return JSON.parse(raw) as T } catch { return fallback }
}

export async function POST(req: Request) {
  const parsed = ChatRequestSchema.safeParse(await req.json().catch(() => null))
  if (!parsed.success) return new Response('Bad Request', { status: 400 })

  const { messages, sessionId } = parsed.data

  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) return new Response('Unauthorized', { status: 401 })

  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', sessionId)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })

  const lastMessage = messages[messages.length - 1]?.content ?? ''

  const sageStart = Date.now()
  let sageRes: Response
  try {
    sageRes = await fetch(`${SAGE_API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(process.env.SAGE_API_KEY ? { 'X-Sage-Api-Key': process.env.SAGE_API_KEY } : {}),
      },
      body: JSON.stringify({
        messages:   messages.map((m) => ({ role: m.role, content: m.content })),
        session_id: sessionId,
        user_id:    user.id,
      }),
    })
  // NOTE: On sage-poc failure (503/502/SERVER_ERROR_SIGNAL), neither the user message nor
  // the AI message is persisted. This is intentional — the design requires a single
  // post-response write so that intent (from X-Sage-Intent header) is always present on
  // both rows. Orphaned user messages without a corresponding AI response and intent label
  // would corrupt the audit trail. The client must handle retries.
  } catch (err) {
    console.error('[chat/route] sage backend unreachable:', err)
    return new Response(
      JSON.stringify({ code: 'SAGE_UNAVAILABLE', message: 'Service unavailable' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    )
  }

  if (!sageRes.ok || !sageRes.body) {
    return new Response(
      JSON.stringify({ code: 'SAGE_ERROR', message: 'Upstream error' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    )
  }

  // Intent — authoritative source is Node 2 (intent_route) inside sage-poc graph.
  // Primary intent: 8-way v7 classification. Secondary: blended intent when present.
  const intentClassification          = sageRes.headers.get('X-Sage-Intent') || null
  const secondaryIntentClassification = sageRes.headers.get('X-Sage-Secondary-Intent') || null

  const sageModel    = sageRes.headers.get('X-Sage-Model')
  const skillId      = sageRes.headers.get('X-Sage-Skill-Id') || null
  const stepId       = sageRes.headers.get('X-Sage-Step-Id') || null
  const gatePath     = sageRes.headers.get('X-Sage-Gate-Path') || null

  const sageNodePath      = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Node-Path'), null)
  const crisisFlags       = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Crisis-Flags'), null)
  const sageClinicalFlags = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Clinical-Flags'), null)

  const intensityStr       = sageRes.headers.get('X-Sage-Emotional-Intensity')
  const emotionalIntensity = intensityStr ? (parseInt(intensityStr, 10) || null) : null

  const semanticScoreStr = sageRes.headers.get('X-Sage-Semantic-Score')
  const semanticScore    = (() => {
    if (!semanticScoreStr) return null
    const n = parseFloat(semanticScoreStr)
    return Number.isNaN(n) ? null : n
  })()
  const promptLayers  = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Prompt-Layers'), null)
  const tokenUsage    = parseJsonHeader<object | null>(sageRes.headers.get('X-Sage-Token-Usage'), null)
  const turnNumberStr = sageRes.headers.get('X-Sage-Turn-Number')
  const turnNumber    = turnNumberStr ? (parseInt(turnNumberStr, 10) || null) : null

  const aiMessageId = crypto.randomUUID()

  const [clientStream, persistStream] = sageRes.body.tee()

  // after() schedules work to run after the response is sent and keeps the
  // Vercel function alive until the callback completes. Without it, void IIFE
  // is fire-and-forget: the function freezes mid-TLS-handshake when Supabase
  // insert tries to connect after the client stream ends (ECONNRESET).
  after(async () => {
    try {
      const reader = persistStream.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        accumulated += decoder.decode(value, { stream: true })
      }
      accumulated += decoder.decode()
      const latencyMs = Date.now() - sageStart

      if (accumulated.includes(SERVER_ERROR_SIGNAL)) {
        console.error('[chat/persist] server error sentinel received, skipping persist')
        return
      }

      const isCrisis = accumulated.startsWith(CRISIS_SIGNAL)
      const content  = isCrisis
        ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
        : accumulated

      // Single post-response write: user message + AI message in one batch.
      // Intent is authoritative from sage-poc (X-Sage-Intent / X-Sage-Secondary-Intent).
      // Both rows carry the same intent values for query convenience (no join needed to
      // filter by intent). The AI message row is the authoritative source — it reflects
      // the intent the graph actually processed. See migration 008 for full design rationale.
      // Service-role client bypasses RLS: the background persist block runs
      // outside the Next.js request context, so the user JWT is no longer
      // available for auth.uid(). Ownership was already validated above.
      const { error: insertError } = await createAdminClient().from('messages').insert([
        {
          id:                              crypto.randomUUID(),
          session_id:                      sessionId,
          role:                            'user',
          content:                         lastMessage,
          intent_classification:           intentClassification,
          secondary_intent_classification: secondaryIntentClassification,
        },
        {
          id:                              aiMessageId,
          session_id:                      sessionId,
          role:                            isCrisis ? 'crisis' : 'ai',
          content,
          model:                           sageModel,
          latency_ms:                      latencyMs,
          node_path:                       sageNodePath,
          skill_id:                        skillId,
          step_id:                         stepId,
          gate_path:                       gatePath,
          crisis_flags:                    crisisFlags,
          clinical_flags:                  sageClinicalFlags,
          emotional_intensity:             emotionalIntensity,
          intent_classification:           intentClassification,
          secondary_intent_classification: secondaryIntentClassification,
          semantic_score:                  semanticScore,
          prompt_layers:                   promptLayers,
          token_usage:                     tokenUsage,
          turn_number:                     turnNumber,
          clinical_flags_detail:           sageClinicalFlags?.length
            ? Object.fromEntries(
                sageClinicalFlags.map(flag => [
                  flag,
                  { detected_at: new Date().toISOString(), turn_number: turnNumber },
                ])
              )
            : null,
        },
      ])
      if (insertError) {
        console.error('[chat/persist] message insert failed:', insertError)
      }

      void fetch(`${SAGE_API_URL}/name-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.SAGE_API_KEY ? { 'X-Sage-Api-Key': process.env.SAGE_API_KEY } : {}),
        },
        body: JSON.stringify({ session_id: sessionId, user_id: user.id, message: lastMessage }),
      }).catch((err) => console.warn('[chat/route] name-session error:', err))

      void fetch(`${SAGE_API_URL}/extract-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.SAGE_API_KEY ? { 'X-Sage-Api-Key': process.env.SAGE_API_KEY } : {}),
        },
        body: JSON.stringify({ session_id: sessionId, user_id: user.id }),
      }).catch((err) => console.warn('[chat/route] profile extraction error:', err))
    } catch (err) {
      console.error('[chat/persist] failed:', err)
    }
  })

  const SAGE_HEADERS_WHITELIST = [
    'x-sage-node-path',
    'x-sage-gate-path',
    'x-sage-prompt-layers',
    'x-sage-intent',
    'x-sage-emotional-intensity',
    'x-sage-turn-number',
  ]

  const responseHeaders: Record<string, string> = {
    'Content-Type':         'text/plain; charset=utf-8',
    'X-Sage-Ai-Message-Id': aiMessageId,
  }

  // Crisis state is always forwarded — functional header, not diagnostic.
  const crisisStateHeader = sageRes.headers.get('X-Sage-Crisis-State')
  if (crisisStateHeader) responseHeaders['X-Sage-Crisis-State'] = crisisStateHeader

  if (process.env.SAGE_EXPOSE_DIAGNOSTIC_HEADERS === 'true') {
    for (const header of SAGE_HEADERS_WHITELIST) {
      const value = sageRes.headers.get(header)
      if (value) responseHeaders[header] = value
    }
  }

  return new Response(clientStream, { headers: responseHeaders })
}
