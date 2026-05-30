'use client'
import { useEffect, useState } from 'react'
import { cn } from '@cdai/ui'

const SECTIONS = [
  { id: 'clinical-safety',    label: 'Clinical Safety'    },
  { id: 'system-performance', label: 'System Performance' },
  { id: 'response-quality',   label: 'Response Quality'   },
  { id: 'intelligence',       label: 'Intelligence'       },
  { id: 'population',         label: 'Population'         },
]

export function AdminSectionNav() {
  const [activeId, setActiveId] = useState<string>('clinical-safety')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (intersecting.length > 0) {
          setActiveId(intersecting[0].target.id)
        }
      },
      { threshold: 0.3 }
    )

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [])

  return (
    <aside className="bg-[var(--color-surface)] border-e border-[var(--color-border)] w-60 flex-shrink-0 flex flex-col p-4 gap-1">
      <nav className="flex flex-col gap-1">
        {SECTIONS.map(({ id, label }) => (
          <a
            key={id}
            href={`#${id}`}
            onClick={(e) => {
              e.preventDefault()
              document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
            className={cn(
              'flex min-h-11 items-center rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150',
              activeId === id
                ? 'bg-[var(--color-primary)] text-white'
                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
            )}
          >
            {label}
          </a>
        ))}
      </nav>
    </aside>
  )
}
