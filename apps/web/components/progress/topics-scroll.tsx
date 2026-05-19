'use client'
import { useRef, useEffect, useState } from 'react'

export function TopicsScroll({ topics }: { topics: string[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [overflows, setOverflows] = useState(false)

  useEffect(() => {
    const el = scrollRef.current
    if (el) setOverflows(el.scrollWidth > el.clientWidth)
  }, [topics])

  return (
    <div className="relative">
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide"
        style={overflows ? { maskImage: 'linear-gradient(to right, black 85%, transparent)' } : {}}
      >
        {topics.map((t) => (
          <span
            key={t}
            className="shrink-0 rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
