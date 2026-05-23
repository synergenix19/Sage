'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Button, Input } from '@cdai/ui'
import { useState } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8, 'Minimum 8 characters'),
})
type Fields = z.infer<typeof schema>

export function SignUpForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
  })
  const [serverError, setServerError] = useState<string | null>(null)
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)

  async function onSubmit(data: Fields) {
    setServerError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    })
    if (error) { setServerError(error.message); return }
    router.push('/onboarding/step-1')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <label htmlFor="signup-email" className="sr-only">{locale === 'ar' ? 'البريد الإلكتروني' : 'Email'}</label>
      <Input id="signup-email" type="email" placeholder={locale === 'ar' ? 'البريد الإلكتروني' : 'Email'} {...register('email')} />
      {errors.email && <p className="text-xs text-[var(--color-crisis)]">{errors.email.message}</p>}
      <label htmlFor="signup-password" className="sr-only">{locale === 'ar' ? 'كلمة المرور' : 'Password'}</label>
      <Input id="signup-password" type="password" placeholder={locale === 'ar' ? 'كلمة المرور' : 'Password'} {...register('password')} />
      {errors.password && <p className="text-xs text-[var(--color-crisis)]">{errors.password.message}</p>}
      {serverError && <p className="text-xs text-[var(--color-crisis)]">{serverError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </Button>
    </form>
  )
}
