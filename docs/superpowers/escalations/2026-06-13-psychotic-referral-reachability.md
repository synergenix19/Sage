# Psychotic-Referral Reachability Gap — Clinical Lead Escalation

**Date:** 2026-06-13
**Severity:** Pre-pilot blocker (pre-existing on master; surfaced by the PR #4 engagement audit, Phase B-3)
**Component:** Graph routing (`_route_after_intent`) vs `psychotic_referral` auto-select (skill_select)
**Raised by:** Engineering, during independent audit of feat/engagement-r1-r3-r5 (live-graph auto-select integrity check)
**Action required from:** Clinical lead — confirm required behavior; authorize the routing fix as a safety change (Rule 1 + clinical sign-off)
**Audit reference:** docs/superpowers/audits/2026-06-13-engagement-pr4-audit.md, finding S2-10

---

## What this is

The `psychotic_referral` skill is designed to auto-select whenever the `psychotic_disclosure` clinical flag is active and the referral has not yet been delivered (`skill_select.py`, psychotic auto-select early-return). The auto-select itself works, and its precedence over the new offer machinery was verified at node level during the audit.

**But the node is unreachable on the most common conversational path.** `_route_after_intent` (graph.py) routes to `skill_select` only for `new_skill`, `info_request`, post-crisis monitoring, and (since PR #4) pending-offer accepts. A turn classified `general_chat` routes directly to freeflow. There is no clinical-flag branch in the router.

**Observed live (audited, real graph, real LLM):** a state carrying `psychotic_disclosure` with the referral undelivered, on a safe `general_chat` message, produced a freeflow response that engaged with the psychotic content — *"…What did the voices say that you found interesting or worth mentioning?"* — with no referral delivered, `psychotic_referral_delivered` still unset.

A user who discloses psychotic symptoms and then continues in ordinary chat register (the typical case: disclosure happens mid-conversation, not as a "new skill request") may never hit a turn that routes to skill_select, so the referral can be deferred indefinitely while freeflow continues to engage with psychotic content under L5 flag adaptations alone.

## Why this is pre-existing, and what PR #4 changed

- The router has had no clinical-flag branch since the psychotic auto-select was introduced; on master the same `general_chat` turn routes the same way. The engagement branch did not cause this.
- Marginal interaction worth knowing: PR #4's offer lifecycle clears stale offers on decline/ignore turns, which removes one incidental route into skill_select (a stale pending-offer accept) that could previously have tripped the auto-select by luck. The reachability gap is the structural issue either way.

## Proposed fix direction (engineering view — needs clinical confirmation)

Add a clinical-flag precedence branch to `_route_after_intent`, placed after the crisis/gate branches and before the confidence gate:

```
if "psychotic_disclosure" in clinical_flags and not psychotic_referral_delivered → skill_select
```

This mirrors the existing post-crisis monitoring forced-routing precedent (short/fragmented messages bypass the confidence gate). It is a control-layer change on a safety path: Rule 1 engineering approval + clinical sign-off required before implementation.

Open clinical questions:
1. Should the referral interrupt on the very next turn regardless of what the user is talking about, or wait for a natural opening within N turns?
2. Is the same reachability guarantee required for any other flag-driven auto-select planned for the future (the fix could be a general flag-routing table rather than a one-off branch)?
3. Until the fix lands: is the L5 prompt adaptation (clinical-flag injection into freeflow) an acceptable interim mitigation, or does pilot exposure need to wait on this fix? (Audit evidence suggests L5 alone did not prevent freeflow from engaging with the content.)

## Evidence basis (added 2026-06-13 — sign-off alignment check)

An independent literature pass converts questions 1 and 3 from open to evidence-backed. Question 2 (general flag-routing table) remains an engineering design choice for the implementation.

**Q1 — interrupt on the NEXT turn; do not wait for a "natural opening."** Every un-redirected turn is an active hazard, not a neutral delay — it is a draw from a documented collusion distribution:
- Stanford / FAccT 2025: even commercially deployed, therapy-tuned bots respond inappropriately to delusions and hallucinations at least 20% of the time (news.stanford.edu/stories/2025/06).
- "The Psychogenic Machine" (arXiv 2509.10970): models systematically confirm rather than challenge delusions (delusion-confirmation score 0.91) and apply no safety intervention in ~40% of scenarios; safety is not emergent from scale.
- Duration-of-untreated-psychosis literature (npj Schizophrenia s41537-017-0034-4; BJPsych care-pathways): referral delay predicts worse outcomes, benefit concentrated under 6 months. A chatbot that keeps chatting casually is functionally a referral-pathway delay point.
- The interrupt must be a *warm interrupt*, not a conversation kill: validate the emotion ("that sounds frightening"), do NOT argue with or explore the content, stay calm/non-alarmed, connect to help (MHFA psychosis guidelines; NSW Health communicating-psychosis). A next-turn redirect that acknowledges feeling before referring is consistent with this; abrupt topic-policing is not.

**Q3 — prompt-level adaptation is acceptable ONLY as the tone of the redirect, never as the gate that decides whether the redirect fires.** The Stanford study tested systems already prompt-/fine-tune-adapted for this population and they still colluded with delusions; the Psychogenic Machine shows safety varies widely and is not reliably instructable. This system is its own Exhibit A — it had clinical prompting in place and still asked "what did the voices say?". Probabilistic instruction reduces but does not eliminate content engagement, and the failure mode (delusion reinforcement) is the one with documented clinical harm (JMIR Mental Health "AI psychosis" e85799; PMC12915070, hospitalization case reports after sycophantic reinforcement loops). Therefore: deterministic routing is the gate; prompt adaptation is defense-in-depth on the redirect's wording only. L5 alone (the current interim) is NOT an acceptable safety mechanism — it is the configuration that already failed in the audit.

**Industry precedent (OpenAI, Oct 2025, sensitive-conversations work, 170+ clinicians):** desired behavior for psychosis/mania is specified as — do not affirm ungrounded beliefs, respond safely and empathically, gently ground in reality, and direct to professional/crisis resources *within the response*, not after rapport-building turns (openai.com/index/strengthening-chatgpt-responses-in-sensitive-conversations).

**Where the evidence is genuinely thin (recorded honestly):** no study directly compares "interrupt next turn" vs "interrupt within N turns" in chatbots; the next-turn recommendation is inferred from per-turn failure rates plus DUP harms (which operate on weeks/months). The strongest *direct* support for immediacy is OpenAI's clinician-built spec, which is expert consensus, not outcome data. No documented harm case is attributable specifically to a *delayed in-product* referral (case reports involve no referral or sustained reinforcement).

This evidence should shorten the clinical session, not lengthen it: two of the three open questions arrive answered. The routing fix itself remains a safety-surface control-layer change requiring Rule 1 + clinical sign-off under the normal gate.

## Queue position

Per the severity-over-tractability convention this belongs in the safety governance queue alongside SK-EN-001 (negation gap) and the crisis-recall gap — it is the most clinically serious finding in the PR #4 audit register and should be triaged in the same review session, not ride as an engagement-feature footnote.
