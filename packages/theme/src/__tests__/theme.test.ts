import { describe, it, expect } from 'vitest'
import { buildCssVars } from '../css-vars'
import { sage } from '@cdai/tenant/configs/sage'

describe('buildCssVars', () => {
  it('emits a CSS variable for every brand color', () => {
    const vars = buildCssVars(sage.brand)
    expect(vars['--color-primary']).toBe('#4A7C59')
    expect(vars['--color-crisis']).toBe('#DC2626')
  })

  it('emits font variables', () => {
    const vars = buildCssVars(sage.brand)
    expect(vars['--font-body']).toContain('Plus Jakarta Sans')
    expect(vars['--font-arabic']).toContain('IBM Plex Arabic')
  })

  it('produces one var per brand color key (9 colors + 2 fonts + 2 focus + 3 clinical = 16)', () => {
    const vars = buildCssVars(sage.brand)
    expect(Object.keys(vars)).toHaveLength(16)
  })
})
