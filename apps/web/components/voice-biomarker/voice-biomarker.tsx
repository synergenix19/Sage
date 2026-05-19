'use client'
import { useState, useRef, useEffect } from 'react'
import { cn } from '@cdai/ui'

type Phase = 'idle' | 'recording' | 'analysing' | 'result'

// Fake analysis result for the pilot demo
const DEMO_RESULT = {
  stressScore: 32,
  energyLevel: 'Moderate',
  recommendation: 'Your vocal patterns suggest moderate stress. Consider a short breathing exercise.',
}

export function VoiceBiomarker() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [countdown, setCountdown] = useState(30)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => {
      mountedRef.current = false
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  function startRecording() {
    setPhase('recording')
    setCountdown(30)
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!)
          if (mountedRef.current) stopRecording()
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  function stopRecording() {
    if (timerRef.current) clearInterval(timerRef.current)
    setPhase('analysing')
    // Simulate analysis delay
    setTimeout(() => {
      if (mountedRef.current) setPhase('result')
    }, 2500)
  }

  function reset() {
    setPhase('idle')
    setCountdown(30)
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
        Voice Wellbeing Analysis
      </h1>

      {phase === 'idle' && (
        <>
          <p className="max-w-xs text-center text-sm text-[var(--color-text-secondary)]">
            Record a 30-second voice sample for AI wellbeing analysis.
          </p>
          <button
            onClick={startRecording}
            className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
          >
            Start Recording
          </button>
        </>
      )}

      {phase === 'recording' && (
        <>
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-crisis)] animate-pulse" />
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">{countdown}s</p>
          <p className="text-sm text-[var(--color-text-secondary)]">Recording…</p>
          <button
            onClick={stopRecording}
            className="min-h-[44px] rounded-full border border-[var(--color-border)] px-6 text-sm text-[var(--color-text-primary)]"
          >
            Stop
          </button>
        </>
      )}

      {phase === 'analysing' && (
        <p className="text-sm text-[var(--color-text-secondary)]">Analysing your voice sample…</p>
      )}

      {phase === 'result' && (
        <div className={cn(
          'w-full max-w-sm rounded-2xl border border-[var(--color-border)]',
          'bg-[var(--color-surface)] p-5 flex flex-col gap-3'
        )}>
          <div className="flex justify-between">
            <span className="text-sm text-[var(--color-text-secondary)]">Stress Score</span>
            <span className="font-semibold text-[var(--color-text-primary)]">{DEMO_RESULT.stressScore}/100</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-[var(--color-text-secondary)]">Energy Level</span>
            <span className="font-semibold text-[var(--color-text-primary)]">{DEMO_RESULT.energyLevel}</span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] border-t border-[var(--color-border)] pt-3">
            {DEMO_RESULT.recommendation}
          </p>
          <button
            onClick={reset}
            className="min-h-[44px] rounded-full bg-[var(--color-primary)] text-sm text-white"
          >
            Record Again
          </button>
        </div>
      )}
    </div>
  )
}
