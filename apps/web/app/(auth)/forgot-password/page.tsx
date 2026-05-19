'use client'
import { useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Button, Input } from '@cdai/ui'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.resetPasswordForEmail(email)
    if (error) { setError(error.message); return }
    setSent(true)
  }

  if (sent) {
    return (
      <div className="text-center flex flex-col gap-4">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Check your email for a reset link.
        </p>
        <Link href="/sign-in" className="text-[var(--color-primary)] text-sm underline-offset-2 hover:underline">
          Back to sign in
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Reset password</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          We'll send a reset link to your email
        </p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        {error && <p className="text-xs text-[var(--color-crisis)]">{error}</p>}
        <Button type="submit">Send reset link</Button>
      </form>
      <p className="text-center text-sm">
        <Link href="/sign-in" className="text-[var(--color-text-secondary)] underline-offset-2 hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  )
}
