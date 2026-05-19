interface MetricCardProps {
  label: string
  value: string | number
  subtext?: string
}

export function MetricCard({ label, value, subtext }: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <p className="text-sm text-[var(--color-text-secondary)]">{label}</p>
      <p className="mt-1 text-3xl font-bold text-[var(--color-text-primary)]">{value}</p>
      {subtext && <p className="mt-1 text-xs text-[var(--color-text-secondary)]">{subtext}</p>}
    </div>
  )
}
