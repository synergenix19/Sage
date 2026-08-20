'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button, Input } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { t as tCopy } from '@/lib/copy'

const MIN_PASSWORD_LENGTH = 8

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)
  const t = (key: 'heading' | 'subtitle' | 'placeholder' | 'updating' | 'button') =>
    tCopy(`resetPassword.${key}`, locale)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const supabase = createClient()
    const { error } = await supabase.auth.updateUser({ password })
    setLoading(false)
    if (error) { setError(error.message); return }
    router.push('/chat')
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
          type="password"
          autoComplete="new-password"
          placeholder={t('placeholder')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={MIN_PASSWORD_LENGTH}
          required
        />
        {error && <p className="text-xs text-[var(--color-crisis)]">{error}</p>}
        <Button type="submit" disabled={loading}>
          {loading ? t('updating') : t('button')}
        </Button>
      </form>
    </div>
  )
}
