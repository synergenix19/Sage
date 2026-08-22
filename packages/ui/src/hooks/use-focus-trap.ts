'use client'
import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Shared dialog focus-trap behavior for overlay panels (BottomSheet, ResponsivePanel's desktop
 * drawer). Promoted from AppSideNav's hand-rolled sign-out confirmation (A11Y-4/5): on open, it
 * moves focus to the first focusable element inside the container and restores focus to whatever
 * was focused before opening on close; while open, Tab/Shift+Tab cycle within the container
 * (focus never escapes to the obscured page behind the backdrop) and Escape calls onClose.
 *
 * "One tap away, no gates" (crisis surfaces): the trap must never make dismissal or reaching
 * content it wraps HARDER — it only prevents focus from LEAVING the container, it never withholds
 * focus from anything the container renders. The trap cycles through every focusable descendant
 * (Tab order = DOM order), so nothing inside the dialog is ever unreachable by keyboard.
 *
 * `onClose` is read through a ref so passing a fresh closure every render (the common case with an
 * inline arrow function) does not re-run the open/close transition effect and steal focus back
 * to the first element on every unrelated re-render.
 */
export function useFocusTrap<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const containerRef = useRef<T | null>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  // Initial focus placement + focus restoration — runs once per open/close transition, not on
  // every render while open (deliberately excludes onClose from its dependency array).
  useEffect(() => {
    if (!open) return
    previouslyFocused.current = document.activeElement as HTMLElement | null
    const container = containerRef.current
    const first = container?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
    ;(first ?? container)?.focus()
    return () => {
      previouslyFocused.current?.focus?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // Escape-to-close + Tab trap. Registered on `document` (not the container) so it also catches
  // events dispatched/bubbled from outside a not-yet-focused container in tests and edge cases.
  useEffect(() => {
    if (!open) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onCloseRef.current()
        return
      }
      if (e.key !== 'Tab') return
      const node = containerRef.current
      if (!node) return
      const focusable = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) return
      const firstEl = focusable[0]
      const lastEl = focusable[focusable.length - 1]
      const active = document.activeElement
      if (e.shiftKey) {
        if (active === firstEl || !node.contains(active)) {
          e.preventDefault()
          lastEl.focus()
        }
      } else if (active === lastEl || !node.contains(active)) {
        e.preventDefault()
        firstEl.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  return containerRef
}
