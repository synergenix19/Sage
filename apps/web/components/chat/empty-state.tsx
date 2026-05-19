const PROMPT_CHIPS = [
  'How are you feeling today?',
  'I have a question about…',
  'I\'ve been feeling stressed lately',
]

interface EmptyStateProps {
  userName: string
  onChipClick: (text: string) => void
}

export function EmptyState({ userName, onChipClick }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-end gap-4 px-4 pb-4">
      <div className="w-full rounded-2xl bg-[var(--color-surface-tinted)] px-4 py-3 text-sm">
        Hello{userName ? `, ${userName}` : ''}! I&apos;m Sage. How can I support you today?
      </div>
      <div className="flex w-full flex-wrap gap-2">
        {PROMPT_CHIPS.map((chip) => (
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
