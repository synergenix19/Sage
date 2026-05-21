import * as React from 'react'
import { cn } from '../lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)] transition-shadow duration-200',
        className
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'
