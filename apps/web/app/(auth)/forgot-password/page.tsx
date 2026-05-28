'use client'
import { useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Button, Input } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'

const LABELS = {
  heading:     { en: 'Reset password',                    ar: 'إعادة تعيين كلمة المرور' },
  subtitle:    { en: "We'll send a reset link to your email", ar: 'سنرسل رابط الإعادة إلى بريدك الإلكتروني' },
  placeholder: { en: 'Email',                             ar: 'البريد الإلكتروني' },
  button:      { en: 'Send reset link',                   ar: 'إرسال رابط الإعادة' },
  sent:        { en: 'Check your email for a reset link.',ar: 'تحقق من بريدك الإلكتروني للحصول على رابط الإعادة.' },
  back:        { en: 'Back to sign in',                   ar: 'العودة إلى تسجيل الدخول' },
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const locale = useLocaleStore((s) => s.locale)
  const t = (key: keyof typeof LABELS) => LABELS[key][locale] ?? LABELS[key].en

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
    })
    if (error) { setError(error.message); return }
    setSent(true)
  }

  if (sent) {
    return (
      <div className="text-center flex flex-col gap-4" dir={locale === 'ar' ? 'rtl' : 'ltr'}>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t('sent')}
        </p>
        <Link href="/sign-in" className="text-[var(--color-primary)] text-sm underline-offset-2 hover:underline">
          {t('back')}
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6" dir={locale === 'ar' ? 'rtl' : 'ltr'}>
      <div className="text-center">
        <h1 className="text-2xl font-semibold">{t('heading')}</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          {t('subtitle')}
        </p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input
          type="email"
          placeholder={t('placeholder')}
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        {error && <p className="text-xs text-[var(--color-crisis)]">{error}</p>}
        <Button type="submit">{t('button')}</Button>
      </form>
      <p className="text-center text-sm">
        <Link href="/sign-in" className="text-[var(--color-text-secondary)] underline-offset-2 hover:underline">
          {t('back')}
        </Link>
      </p>
    </div>
  )
}
