'use client'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { ResponsivePanel } from '@cdai/ui'

interface TestingGuidePanelProps {
  open: boolean
  onClose: () => void
}

export function TestingGuidePanel({ open, onClose }: TestingGuidePanelProps) {
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Clinical Testing Guide">
      <div className="space-y-5 text-sm text-[var(--color-text-primary)]">
        <p className="text-[var(--color-text-secondary)]">
          Please use the chatbot as a real user would, based on your own patient types and the
          kinds of questions you typically receive. Test across a wide range of demographics,
          presenting issues, communication styles, and complexity levels.
        </p>
        <p className="text-[var(--color-text-secondary)]">
          We also encourage stress-testing the system with edge cases such as rapid topic changes,
          contradictory inputs, long or unstructured messages, repeated or rephrased questions, and
          references to prior conversations. Please flag any bugs, inconsistencies, hallucinations,
          loss of context, or other unexpected behaviour.
        </p>

        <Section title="1. Onboarding">
          <Item>Is the onboarding clear, relevant, and sufficient for later conversations?</Item>
          <Item>Is anything missing or unnecessary?</Item>
        </Section>

        <Section title="2. Tone &amp; Therapeutic Style">
          <Item>Does it feel empathetic, natural, and supportive?</Item>
          <Item>Does it validate emotions appropriately before moving into solutions?</Item>
          <Item>Does it avoid premature assumptions or &ldquo;diagnosing&rdquo;?</Item>
          <Item>Does it adapt appropriately to different user tones?</Item>
        </Section>

        <Section title="3. Depth of Conversation">
          <Item>Does it go beyond surface-level responses?</Item>
          <Item>Does it ask useful, meaningful follow-up questions?</Item>
          <Item>Does it support deeper exploration of issues?</Item>
        </Section>

        <Section title="4. Handling Complex Emotions">
          <Item>How well does it manage multiple or conflicting emotions?</Item>
          <Item>How does it handle long &ldquo;brain dump&rdquo; messages?</Item>
          <Item>Does it identify the key emotional themes?</Item>
        </Section>

        <Section title="5. Context &amp; Memory (Within Chat)">
          <Item>Does it remember and use earlier details correctly?</Item>
          <Item>Does it avoid repeating questions or losing context?</Item>
          <Item>Does it build naturally on prior messages?</Item>
        </Section>

        <Section title="6. Memory (Across Chats)">
          <Item>Does it appropriately recall relevant past conversations in a new chat?</Item>
          <Item>Is recalled information accurate and helpful?</Item>
        </Section>

        <Section title="General Feedback">
          <Item>Key strengths?</Item>
          <Item>Key issues or concerns?</Item>
          <Item>Most important improvements?</Item>
        </Section>
      </div>
    </ResponsivePanel>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 font-semibold text-[var(--color-text-primary)]">{title}</h3>
      <ul className="space-y-1">{children}</ul>
    </div>
  )
}

function Item({ children }: { children: ReactNode }) {
  return (
    <li className="flex gap-2 text-[var(--color-text-secondary)]">
      <span className="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]">•</span>
      <span>{children}</span>
    </li>
  )
}
