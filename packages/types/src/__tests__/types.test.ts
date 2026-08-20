import { describe, it, expect, expectTypeOf } from 'vitest'
import type { ChatMessage, Locale } from '../index'
import { mapSdkRole } from '../index'

describe('types', () => {
  it('Locale is a union of en and ar', () => {
    expectTypeOf<Locale>().toEqualTypeOf<'en' | 'ar'>()
  })

  it('ChatMessage role covers all four variants', () => {
    expectTypeOf<ChatMessage['role']>().toEqualTypeOf<'user' | 'ai' | 'system' | 'crisis'>()
  })

  it('mapSdkRole maps all SDK roles to internal MessageRole', () => {
    expect(mapSdkRole('assistant')).toBe('ai')
    expect(mapSdkRole('user')).toBe('user')
    expect(mapSdkRole('system')).toBe('system')
    expect(mapSdkRole('crisis')).toBe('crisis')
    expect(mapSdkRole('unknown')).toBe('ai')
  })
})
