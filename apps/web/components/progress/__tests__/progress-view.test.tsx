import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProgressView } from '../progress-view'
import type { ProgressData } from '@/lib/progress-queries'

vi.mock('@cdai/tenant', () => ({
  tenant: { copy: { progressHeader: 'Your Progress' } },
}))
vi.mock('../mood-chart', () => ({ MoodChart: () => <div data-testid="mood-chart" /> }))
vi.mock('../topics-scroll', () => ({ TopicsScroll: () => <div data-testid="topics-scroll" /> }))
vi.mock('../insights-list', () => ({ InsightsList: () => <div data-testid="insights-list" /> }))
vi.mock('../engagement-card', () => ({ EngagementCard: () => <div data-testid="engagement-card" /> }))

const emptyData: ProgressData = {
  engagement: { sessionCount: 0, skillsUsedCount: 0 },
  moodTrajectory: [],
  topics: [],
  skills: [],
  clinicalFlags: [],
}

describe('ProgressView', () => {
  it('shows empty state with Start chatting link when no data', () => {
    render(<ProgressView data={emptyData} />)
    expect(screen.getByText(/Your progress will appear here/)).toBeTruthy()
    const link = screen.getByRole('link', { name: 'Start chatting' })
    expect(link.getAttribute('href')).toBe('/chat')
  })

  it('renders engagement card when session count > 0', () => {
    render(<ProgressView data={{ ...emptyData, engagement: { sessionCount: 3, skillsUsedCount: 1 } }} />)
    expect(screen.getByTestId('engagement-card')).toBeTruthy()
  })

  it('renders mood chart when trajectory data exists', () => {
    render(<ProgressView data={{ ...emptyData, moodTrajectory: [{ day: '2026-05-24', avgIntensity: 3, sessionName: null }] }} />)
    expect(screen.getByTestId('mood-chart')).toBeTruthy()
  })

  it('does not show empty state when there is data', () => {
    render(<ProgressView data={{ ...emptyData, engagement: { sessionCount: 1, skillsUsedCount: 0 } }} />)
    expect(screen.queryByText(/Your progress will appear here/)).toBeNull()
  })
})
