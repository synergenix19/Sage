import type { TenantBrand } from '@cdai/tenant'

export function buildCssVars(brand: TenantBrand): Record<string, string> {
  return {
    '--color-primary':        brand.colors.primary,
    '--color-primary-dark':   brand.colors.primaryDark,
    '--color-secondary':      brand.colors.secondary,
    '--color-surface':        brand.colors.surface,
    '--color-surface-tinted': brand.colors.surfaceTinted,
    '--color-text-primary':   brand.colors.textPrimary,
    '--color-text-secondary': brand.colors.textSecondary,
    '--color-border':         brand.colors.border,
    '--color-crisis':         brand.colors.crisis,
    '--font-body':            `'${brand.fonts.body}', sans-serif`,
    '--font-arabic':          `'${brand.fonts.arabic}', sans-serif`,
    '--focus-ring-color':     brand.colors.primary,
    '--focus-ring-offset':    '2px',
  }
}

export function cssVarsString(brand: TenantBrand): string {
  const vars = buildCssVars(brand)
  return `:root {\n${Object.entries(vars).map(([k, v]) => `  ${k}: ${v};`).join('\n')}\n}`
}
