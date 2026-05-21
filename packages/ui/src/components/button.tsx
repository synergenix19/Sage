import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../lib/utils'

// All sizes meet the 44×44px touch target minimum (iOS HIG / Android guidelines).
// sm is visually compact but padded to 44px height so tap targets are never undersized.
const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-full font-body text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)] focus-visible:ring-offset-[var(--focus-ring-offset)] disabled:pointer-events-none disabled:opacity-50 min-h-[44px] min-w-[44px]',
  {
    variants: {
      variant: {
        primary:  'bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-dark)]',
        outline:  'border border-[var(--color-border)] bg-transparent hover:bg-[var(--color-surface-tinted)]',
        ghost:    'bg-transparent hover:bg-[var(--color-surface-tinted)]',
      },
      size: {
        sm: 'h-11 px-3 text-xs',
        md: 'h-11 px-5',
        lg: 'h-12 px-7 text-base',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
)
Button.displayName = 'Button'
