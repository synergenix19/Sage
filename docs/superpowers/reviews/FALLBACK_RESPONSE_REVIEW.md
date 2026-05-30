# Clinical Review: `_VETTED_FALLBACK_RESPONSE`

**Status:** Pending clinician sign-off  
**Priority:** P0 — blocks Gitex production deploy  
**Owner:** Clinical review team  
**Engineering contact:** Rohan  
**Review by:** Before user-facing deployment

---

## What this is

`_VETTED_FALLBACK_RESPONSE` is a static string substituted by `output_gate.py`
when the banned-opener gate cannot produce compliant copy in one retry.

Location: `src/sage_poc/nodes/output_gate.py`, constant `_VETTED_FALLBACK_RESPONSE`

Current placeholder (must be replaced before production):
```
"I'm here with you. What would feel most helpful to share right now?"
```

---

## Why this matters

The banned-opener gate fires when GPT-4o generates a response beginning with
a reflective paraphrase ("It sounds like…", "That sounds…", "I can hear…",
etc.). The gate sends a correction directive and retries once. If the second
attempt also violates, the gate substitutes this fallback.

Without a vetted fallback, the system previously passed the violating response
through to the user (`banned_opener_violation=True`). As of commit `9c81009`,
the fallback substitution is wired and tested — the only remaining gap is the
string itself.

**The fallback fires on two paths:**
1. Retry exhausted: gate caught the violation, retry produced another violation
2. (After regex tightening) Near-match evasion caught: "Sounds like…" (no
   leading banned token) is added to the pattern, caught, retried, second
   attempt also violates

Both paths land on the same string. The frequency is expected to be low after
Fix 1 (the L2 high-intensity guidance change), but it is nonzero, and it fires
on the turns where the user is most distressed — exactly when copy quality
matters most.

**Treat as user-facing copy with measurable frequency, not a rare error message.**

---

## Constraints on the replacement string

All must be satisfied simultaneously:

1. **Must NOT begin with a banned or near-banned opener.**  
   Banned patterns: "It sounds like", "That sounds", "It seems like",
   "I can hear that/how/the", "I can see that/how", "It looks like".  
   Near-banned (known evasion): "Sounds like" (without leading "It"/"That").  
   Do not begin with any structurally-reflective paraphrase.

2. **Khaleeji wellness-companion register.**  
   Warm, open-ended, present. Never clinical distance ("I cannot respond"),
   never deflection ("Let's talk about something else"), never hollow affirmation
   ("That's completely valid").

3. **Safe after any disclosure, including heavy ones.**  
   The gate fires on any turn — including turns where the user disclosed grief,
   suicidal ideation (third-party or direct), or significant distress. The
   string must not read as dismissive, topic-changing, or surprised after heavy
   content. "What would feel most helpful?" is acceptable. "How are you
   doing today?" is not (wrong temporal register after disclosure).

4. **Must work in both English and Arabic turns.**  
   The translation pipeline still runs on this string. The Arabic rendering
   should hold the same register. Review the translated form alongside the EN.

5. **Works on any intent, any skill context.**  
   The fallback fires regardless of whether the turn was general_chat, a skill
   step, or a knowledge response. The string cannot assume a specific context
   ("tell me more about that breathing technique" would be wrong after a
   general_chat turn).

---

## Audit and traceability

When the fallback fires, `output_gate` writes a Supabase `session_audit` row
with `output_gate_fallback_substituted` in `node_path`. This is distinct from
the early-return retry row (`output_gate_banned_opener_retry`). Reviewers can
query:

```sql
SELECT session_id, turn_number, node_path, created_at
FROM session_audit
WHERE 'output_gate_fallback_substituted' = ANY(node_path)
ORDER BY created_at DESC;
```

The model's original (violating) generation is NOT stored separately for this
path (unlike identity-substitution which writes to `identity_substitution_audit`).
If full traceability of the original generation is required for PDPL purposes,
that schema extension should be scoped at the same time as this review.

---

## What the clinician is NOT deciding

- The mechanism (branch, audit write, retry limit) — already implemented and tested
- Whether the fallback fires — the gate logic is fixed
- Arabic translation — the pipeline handles it; review the rendered Arabic form only
- The regex tightening (near-match evasion) — separate engineering decision,
  but should be sequenced AFTER this string is approved (tightening before the
  fallback is wired would convert silent evasions into auditable-but-unhandled exits)

---

## Suggested candidates (for discussion, not prescription)

These are offered as starting points for the review discussion, not
recommendations. Final wording belongs to the clinical team.

| Candidate | Notes |
|-----------|-------|
| "I'm here with you. What feels most important to talk about right now?" | Current placeholder. Warm, open. "Most important" may feel pressuring after heavy disclosure. |
| "Take your time. What's been on your mind?" | Gentle pacing. "What's been on your mind" is broad enough to work in any context. May feel abrupt in formal AR. |
| "I'm listening. What would you like to share?" | Very neutral. Risks reading as passive after a strong disclosure. |
| "What's been weighing on you today?" | Grounded, wellness-register. Does not assume prior disclosure. Works after any turn. |

Constraint check for "What's been weighing on you today?":
- Does not begin with a banned opener ✓
- Warm, open ✓  
- Works after heavy disclosure ✓ (the weight framing invites rather than deflects)
- Works in AR (الأمر الذي يثقل عليك) — needs bilingual review ✓/TBD
- Works on any intent ✓

---

## Sequencing note

**Implement fallback string → then tighten regex** (not the reverse).

If the regex is tightened before this string is approved and deployed, the gate
will catch more evasions (D→C conversion) but C will still exit without a clean
fallback. A reviewer reading audit logs after that change would see
`output_gate_banned_opener_retry` + `output_gate_fallback_substituted` with the
placeholder string in production — which is acceptable temporarily but should
not persist past the first post-Gitex sprint.
