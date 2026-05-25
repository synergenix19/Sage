import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ChatFadeIn } from '../chat-fade-in'

describe('ChatFadeIn', () => {
  it('renders children', () => {
    render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    expect(screen.getByText('hello')).toBeTruthy()
  })

  it('does not use a framer-motion motion element', () => {
    const { container } = render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    // framer-motion motion.div injects data-projection-id
    expect(container.querySelector('[data-projection-id]')).toBeNull()
  })

  it('applies animate-fade-in class to wrapper div', () => {
    const { container } = render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    expect(container.firstElementChild?.classList.contains('animate-fade-in')).toBe(true)
  })
})
