export function TopicsScroll({ topics }: { topics: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {topics.map((t) => (
        <span
          key={t}
          className="rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
        >
          {t}
        </span>
      ))}
    </div>
  )
}
