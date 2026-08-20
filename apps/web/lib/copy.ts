import type { Locale } from '@cdai/types'

// ─── COPY REGISTRY — extraction-only (P4 Task 2, Amendment 6) ───────────────
// Every entry below moved VERBATIM out of its original call site — byte-identical, including
// currently-drifted Arabic variants (e.g. two different "Untitled conversation" translations,
// two different apostrophe styles on "Couldn't load history", "retry" vs "Retry" casing). Drift
// is preserved on purpose, under distinct per-site keys: unifying it is Task 2's explicit
// NON-goal (see task-2-brief.md). Fixes are follow-ups tracked in the Task 2 PR body, never
// bundled into this extraction.
//
// CRISIS-UI RULE (Amendment 7): the crisis card, crisis resource list, crisis help panel, the
// chat-interface.tsx crisis-pinning render path, and the chat-header.tsx "Get help now" crisis
// trigger are NEVER migrated into this registry — not for consistency, not in passing. Their
// copy stays exactly where it lives today. Likewise the welcome.tsx crisis contact line stays
// composed locally from lib/crisis-config.ts (CRISIS_CONFIG) rather than being frozen into a
// static registry entry here, so it can never drift from the single crisis-config source.
// ────────────────────────────────────────────────────────────────────────────

const COPY = {
  // — history-panel.tsx —
  'historyPanel.title': { en: 'Past conversations', ar: 'المحادثات السابقة' },
  'historyPanel.newConvo': { en: '+ New conversation', ar: '+ محادثة جديدة' },
  'historyPanel.loading': { en: 'Loading…', ar: 'جار التحميل…' },
  'historyPanel.errorMsg': { en: "Couldn’t load history", ar: 'تعذّر تحميل السجل' },
  'historyPanel.retry': { en: 'retry', ar: 'إعادة المحاولة' },
  'historyPanel.empty': { en: 'No past conversations yet.', ar: 'لا توجد محادثات سابقة.' },
  'historyPanel.untitled': { en: 'Untitled conversation', ar: 'محادثة بدون عنوان' },

  // — welcome.tsx (onboarding step 1) — crisis contact line (3rd line) stays local, sourced
  // live from CRISIS_CONFIG; not registered here.
  'welcome.heading': { en: 'Before you begin', ar: 'قبل أن تبدأ' },
  'welcome.line1': {
    en: 'Sage is an experimental wellbeing tool, not a substitute for professional mental health care.',
    ar: 'سيج أداة تجريبية للعافية، وليست بديلاً عن الرعاية النفسية المتخصصة.',
  },
  'welcome.line2': {
    en: 'Conversations are stored and may be reviewed by our clinical team.',
    ar: 'يتم تخزين المحادثات وقد تراجعها فريقنا السريري.',
  },
  'welcome.cta': { en: 'I understand, continue', ar: 'أفهم وأوافق، متابعة' },

  // — forgot-password/page.tsx —
  'forgotPassword.heading': { en: 'Reset password', ar: 'إعادة تعيين كلمة المرور' },
  'forgotPassword.subtitle': {
    en: "We'll send a reset link to your email",
    ar: 'سنرسل رابط الإعادة إلى بريدك الإلكتروني',
  },
  'forgotPassword.placeholder': { en: 'Email', ar: 'البريد الإلكتروني' },
  'forgotPassword.button': { en: 'Send reset link', ar: 'إرسال رابط الإعادة' },
  'forgotPassword.sent': {
    en: 'Check your email for a reset link.',
    ar: 'تحقق من بريدك الإلكتروني للحصول على رابط الإعادة.',
  },
  'forgotPassword.back': { en: 'Back to sign in', ar: 'العودة إلى تسجيل الدخول' },

  // — reset-password/page.tsx —
  'resetPassword.heading': { en: 'Set new password', ar: 'تعيين كلمة مرور جديدة' },
  'resetPassword.subtitle': {
    en: 'Choose a new password for your account',
    ar: 'اختر كلمة مرور جديدة لحسابك',
  },
  'resetPassword.placeholder': { en: 'New password', ar: 'كلمة المرور الجديدة' },
  'resetPassword.updating': { en: 'Updating...', ar: 'جارٍ التحديث...' },
  'resetPassword.button': { en: 'Update password', ar: 'تحديث كلمة المرور' },

  // — tab-bar.tsx (also read by app-side-nav.tsx via the same ALL_TABS entries) —
  'tabBar.chat': { en: 'Chat', ar: 'محادثة' },
  'tabBar.progress': { en: 'Progress', ar: 'تقدمي' },
  'tabBar.biomarker': { en: 'Voice', ar: 'صوت' },

  // — app-side-nav.tsx — SessionList (own drifted copies of loading/error/retry/untitled)
  'appSideNav.sessionList.loading': { en: 'Loading...', ar: 'جارٍ التحميل...' },
  'appSideNav.sessionList.errorMsg': { en: "Couldn't load history", ar: 'تعذر التحميل' },
  'appSideNav.sessionList.retry': { en: 'Retry', ar: 'إعادة المحاولة' },
  'appSideNav.sessionList.untitled': { en: 'Untitled conversation', ar: 'محادثة بلا عنوان' },
  // — app-side-nav.tsx — chrome
  'appSideNav.newConversationAriaLabel': { en: 'New conversation', ar: 'محادثة جديدة' },
  'appSideNav.newConversationButton': { en: '+ New conversation', ar: '+ محادثة جديدة' },
  'appSideNav.confirmSignOutText': {
    en: 'Sign out of Sage? Your conversation history is saved.',
    ar: 'تسجيل الخروج من Sage؟ سيتم حفظ تاريخ محادثاتك.',
  },
  'appSideNav.signOutIconAriaLabel': { en: 'Sign out', ar: 'تسجيل الخروج' },
  'appSideNav.confirmDialogAriaLabel': { en: 'Confirm sign out', ar: 'تأكيد تسجيل الخروج' },
  'appSideNav.cancelButton': { en: 'Cancel', ar: 'إلغاء' },
  'appSideNav.signOutConfirmButton': { en: 'Sign out', ar: 'تسجيل الخروج' },

  // — input-bar.tsx —
  'inputBar.voiceAriaLabel': { en: 'Voice input', ar: 'الإدخال الصوتي' },
  'inputBar.voiceTitleSupported': { en: 'Voice input', ar: 'الإدخال الصوتي' },
  'inputBar.voiceTitleUnsupported': { en: 'Voice input coming soon', ar: 'الإدخال الصوتي قريباً' },
  'inputBar.messageAriaLabel': { en: 'Message', ar: 'اكتب رسالتك' },
  'inputBar.placeholder': { en: "What's on your mind?", ar: 'وش في البال؟' },
  'inputBar.sendAriaLabel': { en: 'Send', ar: 'إرسال' },

  // — chat-header.tsx — the "Get help now" crisis-help-panel trigger is NOT here (Amendment 7).
  'chatHeader.newConversationAriaLabel': { en: 'New conversation', ar: 'محادثة جديدة' },
  'chatHeader.historyAriaLabel': { en: 'History', ar: 'السجل' },
  'chatHeader.settingsAriaLabel': { en: 'Settings', ar: 'الإعدادات' },

  // — sign-in-form.tsx —
  'signInForm.emailLabel': { en: 'Email', ar: 'البريد الإلكتروني' },
  'signInForm.passwordLabel': { en: 'Password', ar: 'كلمة المرور' },

  // — sign-up-form.tsx — (own keys — cross-file drift is preserved even though these happen to
  // read the same as sign-in-form's today; a future independent edit to either must not silently
  // move the other).
  'signUpForm.emailLabel': { en: 'Email', ar: 'البريد الإلكتروني' },
  'signUpForm.passwordLabel': { en: 'Password', ar: 'كلمة المرور' },

  // — presence-indicator.tsx —
  'presenceIndicator.ariaLabel': { en: 'Sage is with you', ar: 'Sage معك' },

  // — language-toggle.tsx — displayed text is the OTHER language's name, keyed by current locale.
  'languageToggle.label': { en: 'عربي', ar: 'EN' },

  // — settings-panel.tsx —
  'settingsPanel.toggleLocale': {
    en: 'Language: English → العربية',
    ar: 'اللغة: العربية → English',
  },
  'settingsPanel.textSizeLabel': { en: 'Text size', ar: 'حجم النص' },
  'settingsPanel.textSize.sm': { en: 'Small', ar: 'صغير' },
  'settingsPanel.textSize.md': { en: 'Medium', ar: 'متوسط' },
  'settingsPanel.textSize.lg': { en: 'Large', ar: 'كبير' },
  'settingsPanel.signOut': { en: 'Sign out', ar: 'تسجيل الخروج' },
} as const satisfies Record<string, Record<Locale, string>>

export type CopyKey = keyof typeof COPY

/** Registry accessor — modeled on source-card-labels.ts. Falls back to `en` for an unknown locale. */
export function t(key: CopyKey, locale: Locale): string {
  return COPY[key][locale] ?? COPY[key].en
}

// ─── Non-flat-string entries — same extraction, kept as typed exports (source-card-labels.ts
// precedent: a registry can carry more than one shape) rather than forced through t(). ─────────

/** empty-state.tsx prompt chips. */
export const EMPTY_STATE_PROMPT_CHIPS: Record<Locale, string[]> = {
  en: ['How are you feeling today?', "I've been feeling stressed lately", 'I have a question about…'],
  ar: ['كيف حالك اليوم؟', 'أشعر بالتوتر مؤخرًا', 'لديّ سؤال عن…'],
}

/** empty-state.tsx greeting — parametrized on user name, byte-identical to the original template literals. */
export function emptyStateGreeting(name: string, locale: Locale): string {
  return locale === 'ar'
    ? `مرحبًا${name ? `، ${name}` : ''}! أنا Sage. كيف يمكنني دعمك اليوم؟`
    : `Hello${name ? `, ${name}` : ''}! I'm Sage. How can I support you today?`
}
