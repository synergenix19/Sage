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

function parseJsonHeader<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try { return JSON.parse(raw) as T } catch { return fallback }
}

export async function POST(req: Request) {
  // route.ts is a deliberate security boundary:
  //   - SAGE_API_URL is a server-side env var; it never reaches the browser
  //   - Supabase persistence happens here, not in the browser
  // All sage-poc calls originate from this server process — CORS headers on sage-poc
  // are irrelevant to this call path.
  const {
    messages,
    sessionId,
    crisisState        = 'none',
    activeSkillId      = null,
    activeStepId       = null,
    clinicalFlags      = [],
    distressTrajectory = [],
  } = await req.json() as {
    messages:            { role: string; content: string }[]
    sessionId:           string
    crisisState?:        string
    activeSkillId?:      string | null
    activeStepId?:       string | null
    clinicalFlags?:      string[]
    distressTrajectory?: number[]
  }

  if (!sessionId || !messages?.length) {
    return new Response('Bad Request', { status: 400 })
  }

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
  const intent = await classifyIntent(lastMessage).catch(() => 'emotional' as Intent)

  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

  const sageStart = Date.now()
  const sageRes = await fetch(`${SAGE_API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages:            messages.map((m) => ({ role: m.role, content: m.content })),
      session_id:          sessionId,
      crisis_state:        crisisState,
      active_skill_id:     activeSkillId,
      active_step_id:      activeStepId,
      clinical_flags:      clinicalFlags,
      distress_trajectory: distressTrajectory,
    }),
  })

  if (!sageRes.ok || !sageRes.body) {
    return new Response('Upstream error', { status: 502 })
  }

  // Existing metadata headers
  const sageModel    = sageRes.headers.get('X-Sage-Model')
  const skillId      = sageRes.headers.get('X-Sage-Skill-Id') || null
  const stepId       = sageRes.headers.get('X-Sage-Step-Id') || null
  const gatePath     = sageRes.headers.get('X-Sage-Gate-Path') || null

  const sageNodePath      = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Node-Path'), null)
  const crisisFlags       = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Crisis-Flags'), null)
  const sageClinicalFlags = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Clinical-Flags'), null)

  const intensityStr       = sageRes.headers.get('X-Sage-Emotional-Intensity')
  const emotionalIntensity = intensityStr ? (parseInt(intensityStr, 10) || null) : null

  // New trace headers (Priority 1)
  const intentClassification = sageRes.headers.get('X-Sage-Intent') || null
  const semanticScoreStr     = sageRes.headers.get('X-Sage-Semantic-Score')
  const semanticScore        = semanticScoreStr ? (parseFloat(semanticScoreStr) || null) : null
  const promptLayers         = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Prompt-Layers'), null)
  const tokenUsage           = parseJsonHeader<object | null>(sageRes.headers.get('X-Sage-Token-Usage'), null)
  const turnNumberStr        = sageRes.headers.get('X-Sage-Turn-Number')
  const turnNumber           = turnNumberStr ? (parseInt(turnNumberStr, 10) || null) : null

  // Deterministic AI message UUID: generated here so it can be used in both
  // the Supabase insert and the response header for the feedback flow.
  const aiMessageId = crypto.randomUUID()

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
      accumulated += decoder.decode()
      const latencyMs = Date.now() - sageStart

      if (accumulated.includes('[[SERVER_ERROR]]')) {
        console.error('[chat/persist] server error sentinel received, skipping persist')
      } else {
        const isCrisis = accumulated.startsWith(CRISIS_SIGNAL)
        const content = isCrisis
          ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
          : accumulated

        await supabase.from('messages').insert({
          id:                    aiMessageId,
          session_id:            sessionId,
          role:                  isCrisis ? 'crisis' : 'ai',
          content,
          intent,
          model:                 sageModel,
          latency_ms:            latencyMs,
          node_path:             sageNodePath,
          skill_id:              skillId,
          step_id:               stepId,
          gate_path:             gatePath,
          crisis_flags:          crisisFlags,
          clinical_flags:        sageClinicalFlags,
          emotional_intensity:   emotionalIntensity,
          // New trace fields
          intent_classification: intentClassification,
          semantic_score:        semanticScore,
          prompt_layers:         promptLayers,
          token_usage:           tokenUsage,
          turn_number:           turnNumber,
          // Timestamped clinical flag detail for clinician timeline and
          // cross-session aggregation (Priority 3). Only written when flags present.
          clinical_flags_detail: sageClinicalFlags?.length
            ? Object.fromEntries(
                sageClinicalFlags.map(flag => [
                  flag,
                  { detected_at: new Date().toISOString(), turn_number: turnNumber },
                ])
              )
            : null,
        })
      }

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
        }).catch(() => ({ text: lastMessage.slice(0, 30) }))
        await supabase.from('chat_sessions')
          .update({ name: sessionName.trim(), updated_at: new Date().toISOString() })
          .eq('id', sessionId)
      }
      // POST-PILOT: Add mood scoring and insight generation here.
    } catch (err) {
      console.error('[chat/persist] failed:', err)
    }
  })()

  // Diagnostic headers forwarded to the browser — controlled by SAGE_EXPOSE_DIAGNOSTIC_HEADERS.
  // Off by default in production. Set to "true" in .env.local or test environment.
  // NOTE: x-sage-crisis-flags contains clinical flag identifiers — review before enabling in prod.
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

  if (process.env.SAGE_EXPOSE_DIAGNOSTIC_HEADERS === 'true') {
    for (const header of SAGE_HEADERS_WHITELIST) {
      const value = sageRes.headers.get(header)
      if (value) responseHeaders[header] = value
    }
  }

  // Ferry headers: read by chat-interface.tsx and sent back on the next request.
  // These are the only sage-poc headers forwarded to the browser — all others
  // are consumed here for Supabase persistence.
  responseHeaders['X-Sage-Crisis-State']        = sageRes.headers.get('X-Sage-Crisis-State') ?? 'none'
  responseHeaders['X-Sage-Skill-Id']            = sageRes.headers.get('X-Sage-Skill-Id') ?? ''
  responseHeaders['X-Sage-Active-Step-Id']      = sageRes.headers.get('X-Sage-Active-Step-Id') ?? ''
  responseHeaders['X-Sage-Clinical-Flags']      = sageRes.headers.get('X-Sage-Clinical-Flags') ?? '[]'
  responseHeaders['X-Sage-Distress-Trajectory'] = sageRes.headers.get('X-Sage-Distress-Trajectory') ?? '[]'

  return new Response(clientStream, { headers: responseHeaders })
}
