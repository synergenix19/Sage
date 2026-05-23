import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SignUpForm } from '../sign-up-form'
import { useLocaleStore } from '@/lib/stores/locale-store'

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { signUp: vi.fn().mockResolvedValue({ error: null }) },
  }),
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
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
