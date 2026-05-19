import type { TenantConfig } from '../types'

export const sage: TenantConfig = {
  brand: {
    logo: '/logos/sage.svg',
    colors: {
      primary:       '#4A7C59',
      primaryDark:   '#3D6A4B',
      secondary:     '#2D6B6B',
      surface:       '#F9F8F6',
      surfaceTinted: '#EAF0EA',
      textPrimary:   '#111827',
      textSecondary: '#6B7280',
      border:        '#E5E7EB',
      crisis:        '#DC2626',
    },
    fonts: { body: 'Plus Jakarta Sans', arabic: 'IBM Plex Arabic' },
    supportUrl: 'https://sage.cda.ae/support',
    locales: ['en', 'ar'],
  },
  // Tenant capabilities replace standalone feature flags — there is no separate flags system.
  capabilities: {
    voiceBiomarker:   false,
    adminDashboard:   true,
    onboardingWizard: true,
    rtl:              true,
    demoSeed:         true,
  },
  copy: {
    appName:            'Sage',
    tagline:            'Your personal wellbeing companion',
    onboardingGreeting: 'Welcome to Sage',
    progressHeader:     'My Progress',
    adminHeader:        'Community Insights',
  },
}
