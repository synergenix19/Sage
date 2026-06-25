import { describe, it, expect } from 'vitest'
import { sage } from '@cdai/tenant/configs/sage'

// WCAG 2.1 relative luminance + contrast ratio (https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio)
function channel(c: number): number {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}
function luminance(hex: string): number {
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}
function ratio(fg: string, bg: string): number {
  const a = luminance(fg)
  const b = luminance(bg)
  const [hi, lo] = a > b ? [a, b] : [b, a]
  return (hi + 0.05) / (lo + 0.05)
}

const AA_NORMAL = 4.5
const WHITE = '#FFFFFF'

describe('WCAG 2.1 AA contrast — chat UI colour pairings', () => {
  const c = sage.brand.colors

  it('softened button / active tab: primaryDark text on surfaceTinted >= 4.5:1', () => {
    expect(ratio(c.primaryDark, c.surfaceTinted)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('neutral assistant bubble: textPrimary on surfaceMuted >= 4.5:1', () => {
    expect(ratio(c.textPrimary, c.surfaceMuted)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('long-form prose: textPrimary on white canvas >= 4.5:1', () => {
    expect(ratio(c.textPrimary, WHITE)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('button hover: white text on primary >= 4.5:1', () => {
    expect(ratio(WHITE, c.primary)).toBeGreaterThanOrEqual(AA_NORMAL)
  })
})
