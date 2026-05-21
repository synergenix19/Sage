// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '../components/button'

afterEach(cleanup)

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handler = vi.fn()
    render(<Button onClick={handler}>Click</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(handler).toHaveBeenCalledOnce()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Button disabled>No</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('accepts className override', () => {
    render(<Button className="extra-class">X</Button>)
    expect(screen.getByRole('button')).toHaveClass('extra-class')
  })
})
