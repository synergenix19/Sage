import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { formatRelativeTime } from '../format-relative-time'

// Fixed "now": Saturday 2026-05-23T14:00:00Z
const NOW = new Date('2026-05-23T14:00:00Z').getTime()

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('formatRelativeTime — under 1 hour', () => {
  it('returns "0m ago" for a timestamp equal to now', () => {
    expect(formatRelativeTime('2026-05-23T14:00:00Z')).toBe('0m ago')
  })

  it('returns "30m ago" for 30 minutes ago', () => {
    expect(formatRelativeTime('2026-05-23T13:30:00Z')).toBe('30m ago')
  })

  it('returns "59m ago" for 59 minutes ago', () => {
    expect(formatRelativeTime('2026-05-23T13:01:00Z')).toBe('59m ago')
  })
})

describe('formatRelativeTime — 1–23 hours', () => {
  it('returns "1h ago" for exactly 1 hour ago', () => {
    expect(formatRelativeTime('2026-05-23T13:00:00Z')).toBe('1h ago')
  })

  it('returns "2h ago" for 2 hours ago', () => {
    expect(formatRelativeTime('2026-05-23T12:00:00Z')).toBe('2h ago')
  })

  it('returns "23h ago" for 23 hours ago', () => {
    expect(formatRelativeTime('2026-05-22T15:00:00Z')).toBe('23h ago')
  })
})

describe('formatRelativeTime — yesterday', () => {
  it('returns "Yesterday" for a timestamp on the previous calendar day', () => {
    // May 22 is yesterday relative to May 23
    expect(formatRelativeTime('2026-05-22T10:00:00Z')).toBe('Yesterday')
  })

  it('returns "Yesterday" for a timestamp 28 hours ago (still previous calendar day)', () => {
    expect(formatRelativeTime('2026-05-22T10:00:00Z')).toBe('Yesterday')
  })
})

describe('formatRelativeTime — this week', () => {
  it('returns the day name for 2 days ago (Thursday)', () => {
    // May 23 - 2 = May 21 = Thursday
    expect(formatRelativeTime('2026-05-21T14:00:00Z')).toBe('Thursday')
  })

  it('returns the day name for 5 days ago (Monday)', () => {
    // May 23 - 5 = May 18 = Monday
    expect(formatRelativeTime('2026-05-18T14:00:00Z')).toBe('Monday')
  })

  it('returns the day name for 6 days ago (Sunday)', () => {
    // May 23 - 6 = May 17 = Sunday
    expect(formatRelativeTime('2026-05-17T14:00:00Z')).toBe('Sunday')
  })
})

describe('formatRelativeTime — older', () => {
  it('returns "MMM D" format for exactly 7 days ago', () => {
    // May 23 - 7 = May 16
    expect(formatRelativeTime('2026-05-16T14:00:00Z')).toBe('May 16')
  })

  it('returns "MMM D" format for 13 days ago', () => {
    expect(formatRelativeTime('2026-05-10T14:00:00Z')).toBe('May 10')
  })

  it('returns "MMM D" format for a different month', () => {
    expect(formatRelativeTime('2026-04-01T14:00:00Z')).toBe('Apr 1')
  })
})

describe('formatRelativeTime — Arabic locale', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-25T14:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('uses ar-AE locale for day-of-week display', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const fourDaysAgo = new Date('2026-05-21T14:00:00Z').toISOString()
    formatRelativeTime(fourDaysAgo, 'ar')
    expect(spy).toHaveBeenCalledWith('ar-AE', expect.objectContaining({ weekday: 'long' }))
    spy.mockRestore()
  })

  it('uses ar-AE locale for month/day display', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const twoWeeksAgo = new Date('2026-05-11T14:00:00Z').toISOString()
    formatRelativeTime(twoWeeksAgo, 'ar')
    expect(spy).toHaveBeenCalledWith('ar-AE', expect.objectContaining({ month: 'short', day: 'numeric' }))
    spy.mockRestore()
  })

  it('returns same relative string for under-1-hour regardless of locale', () => {
    const thirtyMinsAgo = new Date('2026-05-25T13:30:00Z').toISOString()
    expect(formatRelativeTime(thirtyMinsAgo, 'ar')).toBe('30m ago')
  })

  it('defaults to en-US when no locale passed (backward compat)', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const twoWeeksAgo = new Date('2026-05-11T14:00:00Z').toISOString()
    formatRelativeTime(twoWeeksAgo)
    expect(spy).toHaveBeenCalledWith('en-US', expect.any(Object))
    spy.mockRestore()
  })
})
