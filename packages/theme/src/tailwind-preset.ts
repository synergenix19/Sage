import type { Config } from 'tailwindcss'

export const tailwindPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        primary:        'var(--color-primary)',
        'primary-dark': 'var(--color-primary-dark)',
        secondary:      'var(--color-secondary)',
        surface:        'var(--color-surface)',
        'surface-tinted':'var(--color-surface-tinted)',
        crisis:         'var(--color-crisis)',
      },
      fontFamily: {
        body:   'var(--font-body)',
        arabic: 'var(--font-arabic)',
      },
      transitionDuration: {
        '350': '350ms',
      },
    },
  },
}
