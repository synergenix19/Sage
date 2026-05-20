'use client'

interface Alert {
  id: string
  userId: string
  district?: string
  timestamp: string
  severity: 'high' | 'medium'
}

interface AlertsPanelProps {
  alerts: Alert[]
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Recent Crisis Alerts
      </h2>
      {alerts.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No recent alerts.</p>
      ) : (
        <ul className="space-y-3">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className="flex min-h-11 items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-tinted)] px-4 py-2"
            >
              <span
                className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${
                  alert.severity === 'high'
                    ? 'bg-[var(--color-crisis)]'
                    : 'bg-yellow-400'
                }`}
                aria-hidden="true"
              />
              <span className="flex-1 truncate text-sm text-[var(--color-text-primary)]">
                {alert.userId}
                {alert.district && (
                  <span className="ms-2 text-xs text-[var(--color-text-secondary)]">· {alert.district}</span>
                )}
              </span>
              <span className="text-xs text-[var(--color-text-secondary)]">
                {new Date(alert.timestamp).toLocaleString()}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  alert.severity === 'high'
                    ? 'bg-[var(--color-crisis)] text-white'
                    : 'bg-yellow-400 text-yellow-900'
                }`}
              >
                {alert.severity}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
