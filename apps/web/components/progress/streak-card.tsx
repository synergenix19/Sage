import { Card } from '@cdai/ui'

export function StreakCard({ streak }: { streak: number }) {
  return (
    <Card className="flex items-center gap-4">
      <span className="text-3xl">🔥</span>
      <div>
        <p className="text-2xl font-semibold">{streak} days</p>
        <p className="text-xs text-[var(--color-text-secondary)]">with Sage</p>
      </div>
    </Card>
  )
}
