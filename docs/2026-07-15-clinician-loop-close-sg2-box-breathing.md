# Clinician Loop-Close — SG-2 box_breathing caveat is LIVE (2026-07-15)

**For the clinician who signed the box_breathing caveat (via PO, 2026-07-14) — the loop closes both ways.**

Your signed text now delivers to real users on prod, verified live in-browser:
- **Verbatim:** *"Before we start, if you have asthma, a breathing condition, or a heart condition, we'll keep this gentle and skip the breath-hold. Just let me know and we'll adjust."*
- **Exactly once**, **before** the breathing instruction.
- **English AND Arabic** (translate-out; the AR render is faithful).
- **Doc-conformant by your own document's rule:** single-firing is what BOT BEHAVIOUR L71 requires — a cleared red-flag screen isn't repeated.

**Evidence (transcripts):** `memory/assets/2026-07-15-box-breathing-caveat-CLEAN-single-fire-EN-prod.png` and `…-AR-firing-prod.png`.

**Backstory (why it took a fix to get here):** the caveat mechanism had been shipped but was silently inert for every skill (an undeclared state channel dropped it between graph nodes); caught only by driving it live, then fixed structurally (#319). Your text was correct throughout — the delivery pipe was broken.

**What this unblocks:** the same mechanism is ready for the **seven remaining acute-skill caveats** (PMR, body-scan, mindfulness-meditation, safe-place, ACT, box_breathing-already-done, stop; grounding → SG-7) whenever their texts return signed. By construction they'll land single-sourced (#321), so they can't duplicate the way dbt_tipp's did. Those signed texts are also the natural companions to the #311 routing fix.

*Recorded by the command session; PO relays. Sibling packet: `docs/2026-07-14-acute-skill-caveat-signoff-packet.md`.*
