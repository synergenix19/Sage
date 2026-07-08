import { describe, it, expect } from 'vitest'
import { mapRowToSdkMessage } from '@/lib/message-mapping'

describe('mapRowToSdkMessage — owns all row->message derivation (#191 sibling; no forgotten fields)', () => {
  it('crisis row → assistant + isCrisis:true, content stays CLEAN (no in-band sentinel)', () => {
    const m = mapRowToSdkMessage({ id: 'r1', role: 'crisis', content: 'You are not alone' })
    expect(m.role).toBe('assistant')
    expect(m.isCrisis).toBe(true)
    expect(m.content).toBe('You are not alone')
    expect(m.content).not.toContain('CRISIS_DETECTED')
  })

  it('ai row → assistant, isCrisis undefined', () => {
    const m = mapRowToSdkMessage({ id: 'r2', role: 'ai', content: 'hello' })
    expect(m.role).toBe('assistant')
    expect(m.isCrisis).toBeUndefined()
  })

  it('user row → user role', () => {
    expect(mapRowToSdkMessage({ id: 'r3', role: 'user', content: 'hi' }).role).toBe('user')
  })

  it('restores supabaseId = row id (reload feedback wiring — sibling gap)', () => {
    expect(mapRowToSdkMessage({ id: 'row-uuid', role: 'ai', content: 'x' }).supabaseId).toBe('row-uuid')
  })

  it('restores direction from content (reload RTL authority — sibling gap)', () => {
    expect(mapRowToSdkMessage({ id: 'a', role: 'ai', content: 'أشعر بالقلق اليوم' }).direction).toBe('rtl')
    expect(mapRowToSdkMessage({ id: 'b', role: 'ai', content: 'I feel anxious today' }).direction).toBe('ltr')
  })
})
