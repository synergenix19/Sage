import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SignUpForm } from '../sign-up-form'
import { useLocaleStore } from '@/lib/stores/locale-store'

const mockSignUp = vi.fn()
const mockPush = vi.fn()

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({ auth: { signUp: mockSignUp } }),
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))
vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

beforeEach(() => {
  mockSignUp.mockResolvedValue({ error: null })
  mockPush.mockClear()
})

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

describe('SignUpForm — Arabic locale', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  it('renders Arabic labels for email and password', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar', setLocale: () => {} }))
    render(<SignUpForm />)
    expect(screen.getByLabelText('البريد الإلكتروني')).toBeInTheDocument()
    expect(screen.getByLabelText('كلمة المرور')).toBeInTheDocument()
  })
})

describe('SignUpForm — submission', () => {
  it('redirects to /step-1 after successful sign-up', async () => {
    const user = userEvent.setup()
    render(<SignUpForm />)
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/step-1'))
  })

  it('displays server error when signUp returns an error', async () => {
    mockSignUp.mockResolvedValueOnce({ error: { message: 'User already registered' } })
    const user = userEvent.setup()
    render(<SignUpForm />)
    await user.type(screen.getByLabelText('Email'), 'existing@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    await waitFor(() => expect(screen.getByText('User already registered')).toBeInTheDocument())
    expect(mockPush).not.toHaveBeenCalled()
  })
})
