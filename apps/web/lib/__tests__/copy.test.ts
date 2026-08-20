import { describe, it, expect } from 'vitest'
import { t, EMPTY_STATE_PROMPT_CHIPS, emptyStateGreeting } from '../copy'

describe('copy registry — t()', () => {
  it('returns the EN value for a known key', () => {
    expect(t('historyPanel.title', 'en')).toBe('Past conversations')
  })

  it('returns the AR value for a known key', () => {
    expect(t('historyPanel.title', 'ar')).toBe('المحادثات السابقة')
  })

  it('preserves drifted "Untitled conversation" Arabic variants under distinct keys', () => {
    expect(t('historyPanel.untitled', 'ar')).toBe('محادثة بدون عنوان')
    expect(t('appSideNav.sessionList.untitled', 'ar')).toBe('محادثة بلا عنوان')
    expect(t('historyPanel.untitled', 'ar')).not.toBe(t('appSideNav.sessionList.untitled', 'ar'))
  })

  it('preserves drifted "Couldn\'t load history" apostrophe/casing variants under distinct keys', () => {
    expect(t('historyPanel.errorMsg', 'en')).toBe("Couldn’t load history")
    expect(t('appSideNav.sessionList.errorMsg', 'en')).toBe("Couldn't load history")
    expect(t('historyPanel.retry', 'en')).toBe('retry')
    expect(t('appSideNav.sessionList.retry', 'en')).toBe('Retry')
  })

  it('languageToggle.label reads as the OTHER language name for the current locale', () => {
    expect(t('languageToggle.label', 'en')).toBe('عربي')
    expect(t('languageToggle.label', 'ar')).toBe('EN')
  })
})

describe('copy registry — empty-state helpers', () => {
  it('EMPTY_STATE_PROMPT_CHIPS has 3 chips per locale', () => {
    expect(EMPTY_STATE_PROMPT_CHIPS.en).toHaveLength(3)
    expect(EMPTY_STATE_PROMPT_CHIPS.ar).toHaveLength(3)
  })

  it('emptyStateGreeting matches the original template literal with a name', () => {
    expect(emptyStateGreeting('Alex', 'en')).toBe("Hello, Alex! I'm Sage. How can I support you today?")
    expect(emptyStateGreeting('Alex', 'ar')).toBe('مرحبًا، Alex! أنا Sage. كيف يمكنني دعمك اليوم؟')
  })

  it('emptyStateGreeting matches the original template literal without a name', () => {
    expect(emptyStateGreeting('', 'en')).toBe("Hello! I'm Sage. How can I support you today?")
    expect(emptyStateGreeting('', 'ar')).toBe('مرحبًا! أنا Sage. كيف يمكنني دعمك اليوم؟')
  })
})
