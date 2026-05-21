'use client'

interface Alert {
  id: string
  message: string
  timestamp: string
  severity: 'high' | 'medium'
  targetSection: string
}

interface AlertsPanelProps {
  alerts: Alert[]
  onAlertClick?: (targetSection: string) => void
}

export function AlertsPanel({ alerts, onAlertClick }: AlertsPanelProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Recent Alerts
      </h2>
      {alerts.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No recent alerts.</p>
      ) : (
        <ul className="space-y-3">
          {alerts.map((alert) => (
            <li key={alert.id}>
              <button
                onClick={() => onAlertClick?.(alert.targetSection)}
                className="flex w-full min-h-11 items-start gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-tinted)] px-4 py-3 text-start hover:bg-[var(--color-surface-tinted)]/80 transition-colors duration-200"
              >
                <span
                  className={`mt-0.5 h-2.5 w-2.5 flex-shrink-0 rounded-full ${
                    alert.severity === 'high'
                      ? 'bg-[var(--color-crisis)]'
                      : 'bg-yellow-400'
                  }`}
                  aria-hidden="true"
                />
                <span className="flex-1 text-sm text-[var(--color-text-primary)]">
                  {alert.message}
                </span>
                <span className="flex-shrink-0 text-xs text-[var(--color-text-secondary)]">
                  {new Date(alert.timestamp).toLocaleDateString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
