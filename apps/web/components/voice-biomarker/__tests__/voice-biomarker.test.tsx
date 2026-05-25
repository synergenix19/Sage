import { render, screen, act, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { VoiceBiomarker } from '../voice-biomarker'

// Note: userEvent is intentionally not used here. This project's pool:forks + jsdom
// configuration causes userEvent's internal async delays to deadlock when
// vi.useFakeTimers() is active. fireEvent (synchronous) is the correct substitute
// for click interactions where pointer-event fidelity is not under test.

describe('VoiceBiomarker', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('shows idle state initially', () => {
    render(<VoiceBiomarker />)
    expect(screen.getByText('Start Recording')).toBeTruthy()
  })

  it('transitions idle → recording → analysing → result', () => {
    render(<VoiceBiomarker />)

    fireEvent.click(screen.getByText('Start Recording'))
    expect(screen.getByText('Recording…')).toBeTruthy()

    act(() => { vi.advanceTimersByTime(30_000) })
    expect(screen.getByText('Analysing your voice sample…')).toBeTruthy()

    act(() => { vi.advanceTimersByTime(2_500) })
    expect(screen.getByText('Record Again')).toBeTruthy()
  })

  it('resets to idle from result', () => {
    render(<VoiceBiomarker />)
    fireEvent.click(screen.getByText('Start Recording'))
    act(() => { vi.advanceTimersByTime(30_000) })
    act(() => { vi.advanceTimersByTime(2_500) })
    fireEvent.click(screen.getByText('Record Again'))
    expect(screen.getByText('Start Recording')).toBeTruthy()
  })
})
