'use client'
import { useState, useRef, useEffect, useSyncExternalStore } from 'react'
import { cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'

interface InputBarProps {
  onSend: (text: string) => void
  disabled?: boolean
  /** Skip-on-type (spec §3, Minor 1): fired on focus AND on the first keystroke of an
   *  already-focused field, so the caller can finalize an in-progress typewriter reveal. */
  onInteract?: () => void
}

// Voice is a Full Build feature; in browsers without the Web Speech API the mic must
// not present a clickable affordance that dead-ends. Detected via useSyncExternalStore
// so the value is SSR-safe (server snapshot assumes supported, avoiding a flash) without
// a setState-in-effect or a hydration mismatch. Capability never changes mid-session, so
// subscribe is a no-op.
const noopSubscribe = () => () => {}
function getVoiceSupported(): boolean {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any
  return Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition)
}

export function InputBar({ onSend, disabled, onInteract }: InputBarProps) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const supported = useSyncExternalStore(noopSubscribe, getVoiceSupported, () => true)
  const locale = useLocaleStore((s) => s.locale)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    return () => { recognitionRef.current?.abort() }
  }, [])

  function startVoice() {
    if (listening) {
      recognitionRef.current?.abort()
      return
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
    if (!SR) return
    const rec = new SR()
    rec.lang = document.documentElement.lang ?? 'en'
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    rec.onresult = (e: any) => setValue(e.results[0][0].transcript)
    rec.onend = () => setListening(false)
    rec.start()
    recognitionRef.current = rec
    setListening(true)
  }

  function send() {
    const text = value.trim()
    if (!text || disabled) return
    setValue('')
    onSend(text)
  }

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      {/* Center the composer controls to the same reading column as the messages. */}
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
      <button
        onClick={startVoice}
        disabled={!supported}
        aria-label={locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input'}
        title={
          supported
            ? (locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input')
            : (locale === 'ar' ? 'الإدخال الصوتي قريباً' : 'Voice input coming soon')
        }
        aria-pressed={listening}
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-full transition-colors',
          !supported && 'cursor-not-allowed opacity-40',
          listening
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
        >
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      </button>
      <textarea
        aria-label={locale === 'ar' ? 'اكتب رسالتك' : 'Message'}
        className="flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[15px] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)]"
        rows={1}
        placeholder={locale === 'ar' ? 'وش في البال؟' : "What's on your mind?"}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onFocus={onInteract}
        onKeyDown={(e) => {
          // Fires on every keystroke, including the first one on an already-focused
          // field (onFocus alone would miss that case).
          onInteract?.()
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            send()
          }
        }}
      />
      <button
        onClick={send}
        disabled={!value.trim() || disabled}
        aria-label={locale === 'ar' ? 'إرسال' : 'Send'}
        className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-primary)] text-white disabled:opacity-40"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={cn('h-4 w-4', locale === 'ar' && 'scale-x-[-1]')}
        >
          <path d="M3 8h10M9 4l4 4-4 4" />
        </svg>
      </button>
      </div>
    </div>
  )
}
