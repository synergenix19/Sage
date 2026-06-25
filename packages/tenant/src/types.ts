export interface TenantBrand {
  logo: string
  colors: {
    primary: string
    primaryDark: string
    secondary: string
    surface: string
    surfaceTinted: string
    surfaceMuted: string
    textPrimary: string
    textSecondary: string
    border: string
    crisis: string
  }
  fonts: { body: string; arabic: string }
  supportUrl: string
  locales: string[]
}

export interface TenantCapabilities {
  voiceBiomarker: boolean
  adminDashboard: boolean
  onboardingWizard: boolean
  rtl: boolean
  demoSeed: boolean
}

export interface TenantCopy {
  appName: string
  tagline: string
  onboardingGreeting: string
  progressHeader: string
  adminHeader: string
}

export interface TenantConfig {
  brand: TenantBrand
  capabilities: TenantCapabilities
  copy: TenantCopy
}
