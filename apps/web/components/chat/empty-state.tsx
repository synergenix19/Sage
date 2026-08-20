'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { EMPTY_STATE_PROMPT_CHIPS, emptyStateGreeting } from '@/lib/copy'

interface EmptyStateProps {
  userName: string
  onChipClick: (text: string) => void
}

export function EmptyState({ userName, onChipClick }: EmptyStateProps) {
  const locale = useLocaleStore((s) => s.locale)
  const chips = EMPTY_STATE_PROMPT_CHIPS[locale] ?? EMPTY_STATE_PROMPT_CHIPS.en

  return (
    <div className="flex flex-1 flex-col items-center justify-end gap-4 px-4 pb-4">
      <div className="w-full rounded-2xl bg-[var(--color-surface-tinted)] px-4 py-3 text-sm">
        {emptyStateGreeting(userName, locale)}
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
