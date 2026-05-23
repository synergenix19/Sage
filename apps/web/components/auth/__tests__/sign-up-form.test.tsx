import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SignUpForm } from '../sign-up-form'

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { signUp: vi.fn().mockResolvedValue({ error: null }) },
  }),
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe('SignUpForm accessibility', () => {
  it('email field has an accessible label', () => {
    render(<SignUpForm />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })

  it('password field has an accessible label', () => {
    render(<SignUpForm />)
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })
})
