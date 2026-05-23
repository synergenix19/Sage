'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Button, Input } from '@cdai/ui'
import { useState } from 'react'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, 'Required'),
})
type Fields = z.infer<typeof schema>

export function SignInForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
  })
  const [serverError, setServerError] = useState<string | null>(null)
  const router = useRouter()

  async function onSubmit(data: Fields) {
    setServerError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithPassword(data)
    if (error) { setServerError(error.message); return }
    router.push('/chat')
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <label htmlFor="signin-email" className="sr-only">Email</label>
      <Input id="signin-email" type="email" placeholder="Email" {...register('email')} />
      {errors.email && <p className="text-xs text-[var(--color-crisis)]">{errors.email.message}</p>}
      <label htmlFor="signin-password" className="sr-only">Password</label>
      <Input id="signin-password" type="password" placeholder="Password" {...register('password')} />
      {errors.password && <p className="text-xs text-[var(--color-crisis)]">{errors.password.message}</p>}
      {serverError && <p className="text-xs text-[var(--color-crisis)]">{serverError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  )
}
