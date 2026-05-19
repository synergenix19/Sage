import Link from 'next/link'
import { SignUpForm } from '@/components/auth/sign-up-form'
import { tenant } from '@cdai/tenant'

export default function SignUpPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">{tenant.copy.appName}</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">Create your account</p>
      </div>
      <SignUpForm />
      <p className="text-center text-sm text-[var(--color-text-secondary)]">
        Already have an account?{' '}
        <Link href="/sign-in" className="text-[var(--color-primary)] underline-offset-2 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}
