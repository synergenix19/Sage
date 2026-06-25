import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownContent } from '../markdown-content'

describe('MarkdownContent', () => {
  it('renders **bold** as a <strong> subhead', () => {
    const { container } = render(<MarkdownContent content="**Breathing techniques**" />)
    const strong = container.querySelector('strong')
    expect(strong?.textContent).toBe('Breathing techniques')
  })

  it('renders a numbered list as an <ol> with items', () => {
    const { container } = render(<MarkdownContent content={'1. first point\n2. second point'} />)
    const items = container.querySelectorAll('ol > li')
    expect(items.length).toBe(2)
    expect(items[0].textContent).toContain('first point')
  })

  it('numbered list uses logical inline-start padding so RTL indents on the correct side', () => {
    const { container } = render(<MarkdownContent content={'1. a\n2. b'} />)
    // ps-5 (padding-inline-start), NOT pl-5 — flips correctly under dir="rtl"
    expect(container.querySelector('ol')?.className).toContain('ps-5')
    // space-y-2 between items so substantive/wrapping items stay visually distinct
    expect(container.querySelector('ol')?.className).toContain('space-y-2')
  })

  it('renders a [label](url) link as plain-text label with NO clickable anchor (deferred to Sub-project B)', () => {
    const { container } = render(<MarkdownContent content="[NIMH](https://nimh.nih.gov)" />)
    expect(container.querySelector('a')).toBeNull() // no anchor to a model-generated URL
    expect(container.textContent).toContain('NIMH') // the label still shows
  })

  it('renders a BARE autolinked URL as plain text, not a clickable anchor', () => {
    // remark-gfm autolinks a raw URL into a link node whose visible text IS the URL;
    // with `a` unwrapped it renders as the literal URL string (safe, non-clickable).
    const { container } = render(<MarkdownContent content="See https://nimh.nih.gov for more." />)
    expect(container.querySelector('a')).toBeNull()
    expect(container.textContent).toContain('https://nimh.nih.gov')
  })

  it('does NOT render raw HTML (XSS-safe): a script tag is not executed or emitted', () => {
    const { container } = render(<MarkdownContent content={'<script>alert(1)</script> hello'} />)
    expect(container.querySelector('script')).toBeNull()
    expect(container.textContent).toContain('hello')
  })

  it('never emits an anchor, even for a javascript: URL', () => {
    const { container } = render(<MarkdownContent content="[x](javascript:alert(1))" />)
    expect(container.querySelector('a')).toBeNull()
  })

  it('renders plain prose as a paragraph, unchanged', () => {
    render(<MarkdownContent content="You have mentioned feeling stressed lately." />)
    expect(screen.getByText('You have mentioned feeling stressed lately.')).toBeInTheDocument()
  })
})
