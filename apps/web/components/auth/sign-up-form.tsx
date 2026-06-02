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
  const [confirmationPending, setConfirmationPending] = useState(false)
  const [pendingEmail, setPendingEmail] = useState('')
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)

  async function onSubmit(data: Fields) {
    setServerError(null)
    const supabase = createClient()
    const { data: authData, error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    })
    if (error) { setServerError(error.message); return }
    // session is null when Supabase requires email confirmation before login.
    // Show a confirmation-pending screen rather than redirecting to an inaccessible page.
    if (!authData.session) {
      setPendingEmail(data.email)
      setConfirmationPending(true)
      return
    }
    router.push('/step-1')
  }

  if (confirmationPending) {
    return (
      <div className="flex flex-col gap-4 text-center">
        <p className="text-sm font-medium">
          {locale === 'ar' ? 'تحقق من بريدك الإلكتروني' : 'Check your email'}
        </p>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {locale === 'ar'
            ? `أرسلنا رابط التأكيد إلى ${pendingEmail}. بعد التأكيد يمكنك تسجيل الدخول.`
            : `We sent a confirmation link to ${pendingEmail}. Once confirmed you can sign in.`}
        </p>
      </div>
    )
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
