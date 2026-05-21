'use client'
import { useState, useRef, useEffect } from 'react'
import { cn } from '@cdai/ui'

interface InputBarProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled }: InputBarProps) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
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
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-full transition-colors',
          listening
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
        aria-label="Voice input"
      >
        🎙
      </button>
      <textarea
        className="flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)]"
        rows={1}
        placeholder="Message…"
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
        className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-primary)] text-white disabled:opacity-40"
        aria-label="Send"
      >
        →
      </button>
    </div>
  )
}
