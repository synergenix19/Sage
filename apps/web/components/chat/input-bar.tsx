'use client'
import { useState, useRef, useEffect } from 'react'
import { cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'

interface InputBarProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled }: InputBarProps) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const locale = useLocaleStore((s) => s.locale)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    return () => { recognitionRef.current?.abort() }
  }, [])

  function startVoice() {
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
    <div className="flex items-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <button
        onClick={startVoice}
        aria-label={locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input'}
        aria-pressed={listening}
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-full transition-colors',
          listening
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
      >
        🎙
      </button>
      <textarea
        aria-label={locale === 'ar' ? 'اكتب رسالتك' : 'Message'}
        className="flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)]"
        rows={1}
        placeholder={locale === 'ar' ? 'رسالة...' : 'Message…'}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
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
  )
}
