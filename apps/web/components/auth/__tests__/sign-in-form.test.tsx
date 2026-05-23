import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SignInForm } from '../sign-in-form'
import { useLocaleStore } from '@/lib/stores/locale-store'

const mockSignIn = vi.fn().mockResolvedValue({ error: null })

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: mockSignIn,
    },
  }),
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))
// eslint-disable-next-line @typescript-eslint/no-explicit-any
vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

describe('SignInForm', () => {
  beforeEach(() => {
    mockSignIn.mockReset()
    mockSignIn.mockResolvedValue({ error: null })
  })

  it('shows validation error when email is empty', async () => {
    render(<SignInForm />)
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('calls signInWithPassword with entered credentials', async () => {
    render(<SignInForm />)
    await userEvent.type(screen.getByPlaceholderText('Email'), 'test@example.com')
    await userEvent.type(screen.getByPlaceholderText('Password'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })

  it('email field has an accessible label', () => {
    render(<SignInForm />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })

  it('password field has an accessible label', () => {
    render(<SignInForm />)
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })
})

describe('SignInForm — Arabic locale', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  it('renders Arabic labels for email and password', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar', setLocale: () => {} }))
    render(<SignInForm />)
    expect(screen.getByLabelText('البريد الإلكتروني')).toBeInTheDocument()
    expect(screen.getByLabelText('كلمة المرور')).toBeInTheDocument()
  })
})
