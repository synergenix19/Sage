type MetricVariant = 'default' | 'alert' | 'ok'

interface MetricCardProps {
  label: string
  value: string | number
  subtext?: string
  variant?: MetricVariant
}

const variantStyles: Record<MetricVariant, string> = {
  default: 'border-[var(--color-border)] bg-[var(--color-surface)]',
  alert:   'border-[var(--color-crisis)] bg-[var(--color-crisis)]/5',
  ok:      'border-[var(--color-primary)] bg-[var(--color-surface-tinted)]',
}

const variantValueStyles: Record<MetricVariant, string> = {
  default: 'text-[var(--color-text-primary)]',
  alert:   'text-[var(--color-crisis)]',
  ok:      'text-[var(--color-primary)]',
}

export function MetricCard({ label, value, subtext, variant = 'default' }: MetricCardProps) {
  return (
    <div className={`rounded-2xl border p-5 ${variantStyles[variant]}`}>
      <p className="text-sm text-[var(--color-text-secondary)]">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${variantValueStyles[variant]}`}>{value}</p>
      {subtext && <p className="mt-1 text-xs text-[var(--color-text-secondary)]">{subtext}</p>}
    </div>
  )
}
