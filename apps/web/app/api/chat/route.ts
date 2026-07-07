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

// A single Sage turn can legitimately take 15-50s (sequential LLM calls + cross-region
// checkpoint I/O + buffered, non-streamed ainvoke). Without this override the Vercel
// function uses the short platform default and severs the request before the backend can
// respond — failing users who go through the route even though direct-to-backend succeeds.
// Set just above the backend's own ceiling (AINVOKE_TIMEOUT_SECONDS=55) so the backend's
// result or [[SERVER_ERROR]] is what wins, not this layer. Pairs with the browser's
// FIRST_BYTE_TIMEOUT_MS (58s) so the three ceilings are ordered backend < client < Vercel.
export const maxDuration = 60

// Vercel(Mumbai) -> Railway TLS connections intermittently reset DURING establishment
// ("Client network socket disconnected before secure TLS connection was established",
// ECONNRESET). It surfaces as a fast 3-5s 503 -> "tap to retry" for any user, on new or
// existing chats. Because the reset happens before the request reaches the backend, the
// turn was NEVER processed — so retrying is safe (no double checkpoint / audit / persist).
// Only connection-ESTABLISHMENT errors are retried; a mid-stream failure is not (it would
// risk double-processing). A single retry catches a healthy connection.
function _isTransientConnError(err: unknown): boolean {
  const cause = (err as { cause?: { code?: string } } | null)?.cause
  const code = cause?.code ?? ''
  const msg = String(cause ?? err)
  return (
    ['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'UND_ERR_SOCKET', 'UND_ERR_CONNECT_TIMEOUT'].includes(code) ||
    /socket disconnected|other side closed|network socket|fetch failed/i.test(msg)
  )
}

async function fetchSageChat(init: RequestInit, attempts = 3): Promise<Response> {
  let lastErr: unknown
  for (let i = 0; i < attempts; i++) {
    try {
      return await fetch(`${SAGE_API_URL}/chat`, init)
    } catch (err) {
      lastErr = err
      if (!_isTransientConnError(err) || i === attempts - 1) throw err
      // Observable on purpose: a successful retry would otherwise be silent, making
      // "no resets fired" and "resets absorbed into 200s" indistinguishable in the logs.
      // This line + a 200 on the same request is the positive confirmation signal.
      console.warn(
        `[chat/route] backend TLS connection reset (attempt ${i + 1}/${attempts}), retrying:`,
        (err as { cause?: unknown } | null)?.cause ?? err,
      )
      await new Promise((r) => setTimeout(r, 250 * (i + 1)))
    }
  }
  throw lastErr
}

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
    sageRes = await fetchSageChat({
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

  // KB source cards (X-Sage-Sources) — raw ASCII-escaped JSON string, forwarded
  // verbatim to the browser below. Not parsed/re-stringified here: forwarding the
  // original string byte-for-byte avoids a lossy decode/re-encode round trip, and
  // the frontend (Task 6) does its own JSON.parse from the response header.
  const sourcesHeader = sageRes.headers.get('X-Sage-Sources')
  // Skill-delivered media (X-Sage-Skill-Media) — a SEPARATE header from X-Sage-Sources
  // (skill media is not a retrieved KB passage; see sage-poc _skill_media_header). Forwarded
  // raw to the browser below and merged into the persisted sources so a reopened conversation
  // shows it. Absent unless SAGE_SKILL_MEDIA_ENABLED + a media step, and on any safety gate_path.
  const skillMediaHeader = sageRes.headers.get('X-Sage-Skill-Media')

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

      // Lane 2 Item 1.5: persist EXACTLY the parsed, already-deduped/capped/typed
      // sourcesHeader list (stored == rendered) — never the raw passage set. Parsed
      // here (not re-derived) so the persisted artifact is byte-identical to what the
      // live turn rendered from the same header string.
      let parsedSources: unknown = null
      if (sourcesHeader) {
        try { parsedSources = JSON.parse(sourcesHeader) } catch { parsedSources = null }
      }
      // Merge skill-delivered media into the persisted sources as a video entry, so a reopened
      // conversation renders it via the same SourceCard (Item 1.5). Crisis turns never carry it
      // (backend allowlist); !isCrisis is belt-and-braces. Malformed → skip, keep KB sources.
      if (skillMediaHeader && !isCrisis) {
        try {
          const m = JSON.parse(skillMediaHeader)
          const entry = { type: m.type, title: m.title ?? '', url: m.url, citation: m.provider ?? '' }
          parsedSources = [...(Array.isArray(parsedSources) ? parsedSources : []), entry]
        } catch { /* malformed → skip */ }
      }

      // Single post-response write: user message + AI message in one batch.
      // Intent is authoritative from sage-poc (X-Sage-Intent / X-Sage-Secondary-Intent).
      // Both rows carry the same intent values for query convenience (no join needed to
      // filter by intent). The AI message row is the authoritative source — it reflects
      // the intent the graph actually processed. See migration 008 for full design rationale.
      // Service-role client bypasses RLS: the background persist block runs
      // outside the Next.js request context, so the user JWT is no longer
      // available for auth.uid(). Ownership was already validated above.
      //
      // Explicit timestamps ensure user row sorts before ai row when both are
      // inserted in the same batch (PostgreSQL evaluates DEFAULT now() once per
      // statement, giving both rows the same microsecond, making order undefined).
      const batchNow = new Date()
      const aiCreatedAt = new Date(batchNow.getTime() + 1)
      const { error: insertError } = await createAdminClient().from('messages').insert([
        {
          id:                              crypto.randomUUID(),
          session_id:                      sessionId,
          role:                            'user',
          content:                         lastMessage,
          created_at:                      batchNow.toISOString(),
          intent_classification:           intentClassification,
          secondary_intent_classification: secondaryIntentClassification,
        },
        {
          id:                              aiMessageId,
          session_id:                      sessionId,
          role:                            isCrisis ? 'crisis' : 'ai',
          created_at:                      aiCreatedAt.toISOString(),
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
          // Safety invariant (b): crisis turns never carry sources — backend already
          // suppresses X-Sage-Sources on any safety gate_path, this is belt-and-braces.
          sources:                         isCrisis ? null : parsedSources,
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

  // Text direction is always forwarded — functional (drives RTL rendering), present on
  // every assistant turn, not just info answers. Authoritative over the client's dir="auto".
  const directionHeader = sageRes.headers.get('X-Sage-Direction')
  if (directionHeader) responseHeaders['X-Sage-Direction'] = directionHeader

  // KB source cards are always forwarded — functional (drives the Source Card / video
  // embed render, Task 6), not diagnostic. It must NOT sit behind the
  // SAGE_EXPOSE_DIAGNOSTIC_HEADERS whitelist below: that flag is explicitly
  // production-disabled (see .env.example), which would silently suppress source
  // cards for every real user. Absent on non-KB turns and on any safety gate_path
  // (backend allowlist) — see _sources_header in sage-poc.
  if (sourcesHeader) responseHeaders['X-Sage-Sources'] = sourcesHeader
  // Forwarded raw (already ascii-safe from the backend), same as X-Sage-Sources and for the
  // same reason: the client parses it and renders via VideoEmbed. Not behind the diagnostic
  // whitelist below (which is prod-disabled) — that would suppress skill videos for real users.
  if (skillMediaHeader) responseHeaders['X-Sage-Skill-Media'] = skillMediaHeader

  if (process.env.SAGE_EXPOSE_DIAGNOSTIC_HEADERS === 'true') {
    for (const header of SAGE_HEADERS_WHITELIST) {
      const value = sageRes.headers.get(header)
      if (value) responseHeaders[header] = value
    }
  }

  return new Response(clientStream, { headers: responseHeaders })
}
