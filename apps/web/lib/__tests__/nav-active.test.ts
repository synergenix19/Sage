import { describe, it, expect } from 'vitest'
import { isActiveHref, navItemClass } from '../nav-active'

describe('isActiveHref', () => {
  it('is true on an exact match', () => {
    expect(isActiveHref('/chat', '/chat')).toBe(true)
  })

  it('is true on a `/`-bounded child route', () => {
    expect(isActiveHref('/chat/session-123', '/chat')).toBe(true)
  })

  it('is FALSE on a prefix-sibling route — the over-match this unification fixes', () => {
    // /chatbot merely shares '/chat' as a string prefix; it is a different route
    // and must not be treated as the /chat tab being active.
    expect(isActiveHref('/chatbot', '/chat')).toBe(false)
  })

  it('is false when the pathname is unrelated to href', () => {
    expect(isActiveHref('/progress', '/chat')).toBe(false)
  })

  it('handles the root href without matching every route (no accidental `//` prefix match)', () => {
    expect(isActiveHref('/', '/')).toBe(true)
    expect(isActiveHref('/chat', '/')).toBe(false)
  })
})

describe('navItemClass', () => {
  it('returns the active class when active', () => {
    expect(navItemClass(true, 'active-class', 'inactive-class')).toBe('active-class')
  })

  it('returns the inactive class when not active', () => {
    expect(navItemClass(false, 'active-class', 'inactive-class')).toBe('inactive-class')
  })
})
