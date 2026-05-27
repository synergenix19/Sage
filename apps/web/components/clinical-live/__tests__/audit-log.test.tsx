import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuditLog } from '../audit-log'
import type { AuditRow } from '@/lib/types/session-audit'

function makeRow(n: number, overrides: Partial<AuditRow> = {}): AuditRow {
  return {
    id: String(n), inserted_at: '', session_id: 'sess-001',
    turn_number: n, node_path: [], primary_intent: 'general_chat',
    secondary_intent: null, intent_confidence: null,
    active_skill_id: null, active_step_id: null, skill_match_method: null,
    knowledge_source: null, knowledge_passage_ids: [], knowledge_abstain: null,
    crisis_state: 'none', crisis_flags: [], clinical_flags: [],
    engagement: 7, emotional_intensity: 4, model_version: null, latency_ms: null,
    user_id: null,
    ...overrides,
  }
}

describe('AuditLog', () => {
  it('renders empty state when no rows', () => {
    render(<AuditLog rows={[]} />)
    expect(screen.getByText(/waiting/i)).toBeDefined()
  })

  it('renders one row per turn', () => {
    render(<AuditLog rows={[makeRow(1), makeRow(2), makeRow(3)]} />)
    expect(screen.getByText('T1')).toBeDefined()
    expect(screen.getByText('T2')).toBeDefined()
    expect(screen.getByText('T3')).toBeDefined()
  })

  it('shows the most recent turn first', () => {
    const { container } = render(<AuditLog rows={[makeRow(1), makeRow(2)]} />)
    const rows = container.querySelectorAll('tr[data-turn]')
    expect(rows[0].getAttribute('data-turn')).toBe('2')
    expect(rows[1].getAttribute('data-turn')).toBe('1')
  })

  it('renders skill_id when active', () => {
    render(<AuditLog rows={[makeRow(1, { active_skill_id: 'box_breathing' })]} />)
    expect(screen.getByText('box_breathing')).toBeDefined()
  })

  it('renders crisis state', () => {
    render(<AuditLog rows={[makeRow(1, { crisis_state: 'monitoring' })]} />)
    expect(screen.getByText('monitoring')).toBeDefined()
  })
})
