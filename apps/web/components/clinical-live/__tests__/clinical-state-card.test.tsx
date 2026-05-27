import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ClinicalStateCard } from '../clinical-state-card'
import type { AuditRow } from '@/lib/types/session-audit'

function makeRow(overrides: Partial<AuditRow> = {}): AuditRow {
  return {
    id: '1', inserted_at: '', session_id: '', turn_number: 1,
    node_path: [], primary_intent: 'general_chat', secondary_intent: null,
    intent_confidence: 0.9, active_skill_id: null, active_step_id: null,
    skill_match_method: null, knowledge_source: null, knowledge_passage_ids: [],
    knowledge_abstain: null, crisis_state: 'none', crisis_flags: [],
    clinical_flags: [], engagement: 7, emotional_intensity: 4,
    model_version: 'claude-sonnet-4-6', latency_ms: null, user_id: null,
    ...overrides,
  }
}

describe('ClinicalStateCard', () => {
  it('renders intent', () => {
    render(<ClinicalStateCard row={makeRow({ primary_intent: 'new_skill' })} />)
    expect(screen.getByText('new_skill')).toBeDefined()
  })

  it('shows em dash for null skill fields', () => {
    render(<ClinicalStateCard row={makeRow({ active_skill_id: null })} />)
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThan(0)
  })

  it('shows crisis state as active with red indicator', () => {
    const { container } = render(
      <ClinicalStateCard row={makeRow({ crisis_state: 'active', crisis_flags: ['S1_keyword'] })} />
    )
    const indicator = container.querySelector('[data-crisis="active"]')
    expect(indicator).toBeTruthy()
  })

  it('shows monitoring state with amber indicator', () => {
    const { container } = render(
      <ClinicalStateCard row={makeRow({ crisis_state: 'monitoring' })} />
    )
    const indicator = container.querySelector('[data-crisis="monitoring"]')
    expect(indicator).toBeTruthy()
  })

  it('hides knowledge column when knowledge_source is null', () => {
    render(<ClinicalStateCard row={makeRow({ knowledge_source: null })} />)
    expect(screen.queryByText('Source')).toBeNull()
    expect(screen.queryByText('Passages')).toBeNull()
  })

  it('shows knowledge column when knowledge_source is set', () => {
    render(<ClinicalStateCard row={makeRow({
      knowledge_source: 'node_6',
      knowledge_passage_ids: ['cbt-001-en-000', 'cbt-001-en-001'],
      knowledge_abstain: false,
    })} />)
    expect(screen.getByText('Source')).toBeDefined()
    expect(screen.getByText('node_6')).toBeDefined()
    expect(screen.getByText('cbt-001-en-000')).toBeDefined()
  })

  it('shows clinical flag badges', () => {
    render(<ClinicalStateCard row={makeRow({ clinical_flags: ['substance_use'] })} />)
    expect(screen.getByText('substance_use')).toBeDefined()
  })
})
