import { describe, it, expectTypeOf } from 'vitest'
import type { UserProfile, ChatMessage, Locale } from '../index'

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
})
