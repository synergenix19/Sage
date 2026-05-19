import { describe, it, expect } from 'vitest'
import { sage } from '../configs/sage'

describe('sage tenant config', () => {
  it('has all required brand colors', () => {
    const required = ['primary', 'primaryDark', 'secondary', 'surface',
      'surfaceTinted', 'textPrimary', 'textSecondary', 'border', 'crisis']
    required.forEach(key => {
      expect(sage.brand.colors).toHaveProperty(key)
    })
  })

  it('crisis color is never reused as a primary color', () => {
    expect(sage.brand.colors.crisis).not.toBe(sage.brand.colors.primary)
    expect(sage.brand.colors.crisis).not.toBe(sage.brand.colors.secondary)
  })

  it('capabilities are all booleans', () => {
    Object.values(sage.capabilities).forEach(v => {
      expect(typeof v).toBe('boolean')
    })
  })

  it('copy has no empty strings', () => {
    Object.values(sage.copy).forEach(v => {
      expect(v.trim().length).toBeGreaterThan(0)
    })
  })
})
