'use client'

import { useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { AuditRow } from '@/lib/types/session-audit'

export type SessionAuditStatus = 'waiting' | 'live' | 'locked' | 'reconnecting'

export function useSessionAudit(lockedSessionId: string | null) {
  const [rows, setRows] = useState<AuditRow[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(lockedSessionId)
  const [status, setStatus] = useState<SessionAuditStatus>('waiting')
  const activeSessionRef = useRef<string | null>(lockedSessionId)

  useEffect(() => {
    const supabase = createClient()

    async function bootstrap() {
      // Locked mode already knows its target session; follow-latest mode has to
      // discover it first. Discovering it via a SEPARATE, lightweight query (just the
      // single most-recently-inserted row) — rather than reading session_id off row 0
      // of an already-fetched GLOBAL top-N window and then filtering that same window
      // — is the fix for the truncated-bootstrap bug (latest-session-first): the old
      // approach could silently drop the latest session's own earlier rows whenever
      // another session had also inserted recently enough to crowd them out of the
      // global window. Once the target session_id is known, both modes fetch that
      // session's own complete row set the same way.
      let targetSessionId = lockedSessionId
      if (!targetSessionId) {
        const { data: latest } = await supabase
          .from('session_audit')
          .select('session_id')
          .order('inserted_at', { ascending: false })
          .limit(1)
        targetSessionId = (latest as Pick<AuditRow, 'session_id'>[] | null)?.[0]?.session_id ?? null
      }

      if (targetSessionId) {
        const { data } = await supabase
          .from('session_audit')
          .select('*')
          .eq('session_id', targetSessionId)
          .order('turn_number', { ascending: true })
        if (data?.length) {
          setRows(data as AuditRow[])
          setActiveSessionId(targetSessionId)
          activeSessionRef.current = targetSessionId
        }
        setStatus(lockedSessionId ? 'locked' : (data?.length ? 'live' : 'waiting'))
      }
    }

    bootstrap()

    const channel = supabase
      .channel('session_audit_live')
      .on(
        'postgres_changes' as never,
        { event: 'INSERT', schema: 'public', table: 'session_audit' },
        (payload: { new: AuditRow }) => {
          const newRow = payload.new
          if (lockedSessionId) {
            if (newRow.session_id !== lockedSessionId) return
            setRows(prev => [...prev, newRow])
          } else {
            if (!activeSessionRef.current || newRow.session_id === activeSessionRef.current) {
              activeSessionRef.current = newRow.session_id
              setActiveSessionId(newRow.session_id)
              setRows(prev => [...prev, newRow])
              setStatus('live')
            } else {
              activeSessionRef.current = newRow.session_id
              setActiveSessionId(newRow.session_id)
              setRows([newRow])
              setStatus('live')
            }
          }
        }
      )
      .subscribe((s: string) => {
        if (s === 'SUBSCRIBED') setStatus(lockedSessionId ? 'locked' : 'live')
        if (s === 'CHANNEL_ERROR') setStatus('reconnecting')
      })

    return () => { supabase.removeChannel(channel) }
  }, [lockedSessionId])

  return { rows, latestRow: rows[rows.length - 1] ?? null, activeSessionId, status }
}
