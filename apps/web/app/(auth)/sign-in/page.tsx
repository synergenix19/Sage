import Link from 'next/link'
import { SignInForm } from '@/components/auth/sign-in-form'
import { tenant } from '@cdai/tenant'

export default function SignInPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">{tenant.copy.appName}</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">Sign in to continue</p>
      </div>
      <SignInForm />
      <p className="text-center text-sm text-[var(--color-text-secondary)]">
        No account?{' '}
        <Link href="/sign-up" className="text-[var(--color-primary)] underline-offset-2 hover:underline">
          Sign up
        </Link>
      </p>
      <p className="text-center text-sm">
        <Link href="/forgot-password" className="text-[var(--color-text-secondary)] underline-offset-2 hover:underline">
          Forgot password?
        </Link>
      </p>
    </div>
  )
}
