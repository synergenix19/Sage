import * as React from 'react'
import { cn } from '../lib/utils'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-xl bg-[var(--color-surface-tinted)] ring-1 ring-black/5 p-4', className)}
      {...props}
    />
  )
)
Card.displayName = 'Card'
