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
      if (lockedSessionId) {
        const { data } = await supabase
          .from('session_audit')
          .select('*')
          .eq('session_id', lockedSessionId)
          .order('turn_number', { ascending: true })
        if (data?.length) {
          setRows(data as AuditRow[])
          setActiveSessionId(lockedSessionId)
        }
        setStatus('locked')
      } else {
        const { data } = await supabase
          .from('session_audit')
          .select('*')
          .order('inserted_at', { ascending: false })
          .limit(20)
        if (data?.length) {
          const latestSession = (data as AuditRow[])[0].session_id
          const sessionRows = (data as AuditRow[])
            .filter(r => r.session_id === latestSession)
            .reverse()
          activeSessionRef.current = latestSession
          setRows(sessionRows)
          setActiveSessionId(latestSession)
          setStatus('live')
        }
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
