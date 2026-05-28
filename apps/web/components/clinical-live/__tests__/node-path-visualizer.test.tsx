import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NodePathVisualizer } from '../node-path-visualizer'

describe('NodePathVisualizer', () => {
  it('renders all 8 nodes', () => {
    render(<NodePathVisualizer firedNodes={[]} turnNumber={0} />)
    expect(screen.getByText('Safety')).toBeDefined()
    expect(screen.getByText('Intent')).toBeDefined()
    expect(screen.getByText('Low Conf.')).toBeDefined()
    expect(screen.getByText('Select')).toBeDefined()
    expect(screen.getByText('Exec')).toBeDefined()
    expect(screen.getByText('Knowledge')).toBeDefined()
    expect(screen.getByText('Respond')).toBeDefined()
    expect(screen.getByText('Gate')).toBeDefined()
  })

  it('marks fired nodes with data-fired="true"', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'freeflow_respond', 'output_gate']}
        turnNumber={1}
      />
    )
    const fired = container.querySelectorAll('[data-fired="true"]')
    expect(fired).toHaveLength(4)
  })

  it('marks unfired nodes with data-fired="false"', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'freeflow_respond', 'output_gate']}
        turnNumber={1}
      />
    )
    const unfired = container.querySelectorAll('[data-fired="false"]')
    expect(unfired).toHaveLength(4) // low_confidence, skill_select, skill_executor, knowledge_retrieve
  })

  it('renders connectors only between consecutive fired nodes', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'skill_select', 'knowledge_retrieve', 'freeflow_respond', 'output_gate']}
        turnNumber={5}
      />
    )
    const connectors = container.querySelectorAll('[data-connector="true"]')
    expect(connectors.length).toBeGreaterThan(0)
    connectors.forEach(c => {
      expect(c.getAttribute('data-both-fired')).toBe('true')
    })
  })

  it('shows crisis short-circuit path correctly', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'crisis_response']}
        turnNumber={6}
      />
    )
    const fired = container.querySelectorAll('[data-fired="true"]')
    expect(fired).toHaveLength(1) // only safety_check from the 8-node list
  })
})
