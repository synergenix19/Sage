import { describe, it, expect, expectTypeOf } from 'vitest'
import type { UserProfile, ChatMessage, Locale, MessageFeedback } from '../index'
import { mapSdkRole } from '../index'

describe('types', () => {
  it('Locale is a union of en and ar', () => {
    expectTypeOf<Locale>().toEqualTypeOf<'en' | 'ar'>()
  })

  it('UserProfile has required fields', () => {
    expectTypeOf<UserProfile>().toHaveProperty('id')
    expectTypeOf<UserProfile>().toHaveProperty('onboardingComplete')
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

  it('MessageFeedback type accepts thumbs up', () => {
    const fb: MessageFeedback = {
      id: 'abc',
      messageId: 'msg-1',
      userId: 'user-1',
      value: 1,
      createdAt: '2026-05-22T00:00:00Z',
    }
    expect(fb.value).toBe(1)
  })

  it('MessageFeedback type accepts thumbs down', () => {
    const fb: MessageFeedback = {
      id: 'abc',
      messageId: 'msg-1',
      userId: 'user-1',
      value: -1,
      createdAt: '2026-05-22T00:00:00Z',
    }
    expect(fb.value).toBe(-1)
  })
})
