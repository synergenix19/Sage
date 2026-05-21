export function TopicsScroll({ topics }: { topics: string[] }) {
  return (
    <div
      className="flex gap-2 overflow-x-auto pb-1"
      style={{
        maskImage: 'linear-gradient(to right, black 85%, transparent)',
        WebkitMaskImage: 'linear-gradient(to right, black 85%, transparent)',
        scrollbarWidth: 'none',
      }}
    >
      {topics.map((t) => (
        <span
          key={t}
          className="flex-shrink-0 whitespace-nowrap rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
        >
          {t}
        </span>
      ))}
    </div>
  )
}
