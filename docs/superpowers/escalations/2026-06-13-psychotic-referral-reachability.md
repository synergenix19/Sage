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

## Queue position

Per the severity-over-tractability convention this belongs in the safety governance queue alongside SK-EN-001 (negation gap) and the crisis-recall gap — it is the most clinically serious finding in the PR #4 audit register and should be triaged in the same review session, not ride as an engagement-feature footnote.
