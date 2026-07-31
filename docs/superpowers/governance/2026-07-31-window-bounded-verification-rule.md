# STANDING INSTRUMENT RULE — window-bounded verification (2026-07-31)

**Born from the 2026-07-30 cardiac characterization:** the demonstrated cardiac phrasing measured 3/3
crisis in one window and 0/6 crisis hours later, fresh sessions, identical text, pinned classifier
(seed + provider pin). The −§1f / −§3a single-variant flickers in the 8/36 re-pin are the same class.
**Time-correlated LLM-routing variance is a measured property of the serving system, and the
determinism pins do not remove it — they only stabilize within a window.**

## The rule
1. **Any verification whose subject routes through the LLM classifier is WINDOW-BOUNDED.** "Stable ×N"
   in one sitting asserts stability of that window, not of the behavior. A claim of stability for a
   bistable-exposed path requires N drives across ≥2 windows separated in time — and records both
   window timestamps.
2. **A clean single-window measurement of a safety-critical LLM-routed path is evidence, not a bound.**
   Phrase it that way in records ("crisis 3/3 in this window"), never as "stays at crisis."
3. **Deterministic-first is the corrective, not more measurement.** Every category that must hold
   unconditionally ends up as a Node-1 / rules-first mechanism (crisis lexicon, CF flags, medical
   red-flag, HR, CF-010, cardiac escalation) — the v7 thesis (Rules Service evaluates first; the LLM
   renders language) re-proven by the instrument. Each flicker found is a datum for moving that surface
   into the deterministic tier, and should be filed as such.

Applies to: conformance category verifications, flip acceptance reads, "×3 stable" claims, and any
recall/precision figure on an LLM-routed path. Extends [[feedback_measurement_parity]] (the Node-2
bistability rider) from "single-run invalid" to "single-WINDOW invalid" for bistable-exposed paths.
