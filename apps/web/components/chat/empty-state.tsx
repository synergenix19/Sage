'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'

const PROMPT_CHIPS: Record<'en' | 'ar', string[]> = {
  en: [
    'How are you feeling today?',
    "I've been feeling stressed lately",
    'I have a question about…',
  ],
  ar: [
    'كيف حالك اليوم؟',
    'أشعر بالتوتر مؤخرًا',
    'لديّ سؤال عن…',
  ],
}

const GREETING: Record<'en' | 'ar', (name: string) => string> = {
  en: (name) => `Hello${name ? `, ${name}` : ''}! I'm Sage. How can I support you today?`,
  ar: (name) => `مرحبًا${name ? `، ${name}` : ''}! أنا Sage. كيف يمكنني دعمك اليوم؟`,
}

interface EmptyStateProps {
  userName: string
  onChipClick: (text: string) => void
}

export function EmptyState({ userName, onChipClick }: EmptyStateProps) {
  const locale = useLocaleStore((s) => s.locale)
  const chips = PROMPT_CHIPS[locale] ?? PROMPT_CHIPS.en
  const greeting = GREETING[locale] ?? GREETING.en

  return (
    <div className="flex flex-1 flex-col items-center justify-end gap-4 px-4 pb-4">
      <div className="w-full rounded-2xl bg-[var(--color-surface-tinted)] px-4 py-3 text-sm">
        {greeting(userName)}
      </div>
      <div className="flex w-full flex-wrap gap-2">
        {chips.map((chip) => (
          <button
            key={chip}
            onClick={() => onChipClick(chip)}
            className="min-h-[44px] rounded-full border border-[var(--color-primary)] px-4 py-2 text-sm text-[var(--color-primary)] transition-colors hover:bg-[var(--color-surface-tinted)]"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  )
}
