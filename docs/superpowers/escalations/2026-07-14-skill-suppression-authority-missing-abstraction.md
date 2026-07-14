# ESC-2026-07-14 — Skill-suppression authority is a missing abstraction (v7 architectural review)

**Class:** Architecture (v7 deviation, Absolute Rule 1) — not a bug; a missing layer that produces bugs
**Minted:** 2026-07-14 · verified against `master` `ea50e45`
**Route to:** Architecture owner (NOT clinical lead — this is a v7 structural question, not a clinical one)
**Related:** Spec `2026-07-14-bot-behaviour-routing-conformance-design.md` §3.3 · B1 PR #315 · F6 PR #318 · escalation `2026-07-14-medical-redflag-override-absent` (rev. 2)

---

## 1. The finding

**A deterministic signal that overrides the skill layer has no shared mechanism. Every instance is a per-node bolt-on.** There is no single place in the codebase that answers, for a given signal: *does it have authority over the skill layer, what does it suppress, what does it clear, what is its precedence rank, and how is it audited.* Each coupling is hand-wired, independently, with its own semantics.

This is not a maintenance concern. It is the mechanism by which a fifth `medical_response`-style bug ships without anyone noticing — because there is no one place where the question is answered once.

## 2. Evidence — four instances, one missing abstraction

| # | Instance | Where | The bespoke authority |
|---|---|---|---|
| 1 | psychotic-referral redirect | `_route_after_intent` | a hand-wired `if` forcing `skill_select` (psychotic_referral auto-selects) |
| 2 | Routing-SF-2 / v7.2 prepass | `_route_after_intent` | two hand-wired `if`s pulling high-intensity / keyword-matched `general_chat` into `skill_select` |
| 3 | F6 venting suppression (PR #318) | `_route_after_intent` | a hand-wired `if` routing venting to `freeflow` — a *new* signal→authority coupling, added because PI-VI-001 detected venting but **had no authority** to stop the skill layer |
| 4 | B1 `medical_response` skill-clear (PR #315) | `medical_response` node | a terminal that had to be *reminded* (in final review) to clear `active_skill_id`/`active_step_id`/`offered_skill_ids` — or a coping skill resumes after a medical referral |

Instances 3 and 4 are the same bug in two nodes: **detection without authority over the skill layer.** F6 gives a signal routing authority by bolting on a branch; B1's terminal forgot to clear the skill lifecycle because nothing *makes* a skill-overriding decision declare what it clears. Neither is auditable as a member of a class, because there is no class.

## 3. Why it compounds — the trajectory is 37 bolt-ons

BOT BEHAVIOUR is explicit: **every one of its 34 categories carries a "Guard — Do Not Present This Pathway If" block.** Suppression is not a special case in that document — it is a **universal layer** sitting above skill matching (spec §3.3 already names this). The codebase has no representation of that layer.

So the current trajectory is **~37 bespoke branches** in `_route_after_intent` (and terminal nodes), each with:
- its own precedence semantics (does it beat crisis? beat SF-2? beat another guard?),
- its own decision about what to clear (and B1 proves that decision is silently omissible),
- no shared audit record ("a suppression fired, here is which signal and what it withheld"),
- no single review surface where "signal → authority" is checked as a class.

Four bolt-ons already disagree on structure (three are routing `if`s, one is a node return). Thirty-seven will not converge on their own.

## 4. The missing abstraction

A deterministic signal that overrides the skill layer needs **one mechanism**, evaluated in **one place**, that declares for each signal:

```
signal            (the deterministic detector: venting, medical red-flag, psychotic, guard-X…)
→ authority       (does it override the skill layer, and at what precedence rank)
→ suppresses      (route to presence / route to terminal / withhold offer)
→ clears          (active_skill_id, active_step_id, offered_skill_ids — declared, not omissible)
→ audit record    (one row: which signal fired, what it withheld, its precedence)
```

With this, F6 is a table entry, not a branch. B1's skill-clear is a property of the mechanism, not a thing a node can forget. A fifth guard is a row someone reviews against the same five columns. The 34 BOT BEHAVIOUR guards become data in one registry, not 34 more `if`s.

## 5. Why this is a v7 deviation (Absolute Rule 1)

It does **not contradict** the v7 spec — it reveals the spec is **silent where it needed to speak.** The Rules Service defines a **`skill_matching`** rule category (how a matched skill *enters*). There is **no `skill_suppression` category** — no representation of a signal that says *do not present a skill here, and clear what's active.* Suppression is currently implemented as the **absence** of matching, per-node, ad hoc. That silence is the gap, and closing it is an architectural decision that needs the owner's sign-off, not an incremental code change.

## 6. Ask

1. **Ratify or amend the abstraction** in §4 as the v7 representation of skill-suppression authority (a `skill_suppression` Rules-Service category + a single evaluation point + a declared-clears contract + an audit row).
2. **Decide the migration**: F6 (#318) and B1's skill-clear (#315) ship as bolt-ons now (both flag-gated / reviewed); the abstraction is where they and the 34 BOT BEHAVIOUR guards converge, so the per-node instances are retired onto it rather than multiplied.
3. This **outranks the remaining feature queue** (P0b, F5) for *architectural review* — not because it is urgent (nothing is on fire), but because it is the only architectural finding in the investigation; the rest are bugs. A design decision made now costs one review; made after 37 bolt-ons, it costs a rewrite.

---

## Appendix — related process finding (small, cheap, keeps paying)

**Plan-artifact drift, caught three times by between-task review:** B1 Task 3 (`state.get("message_en")` would break the AR path), B1 Task 4 (hand-built audit dict vs `write_session_audit(state)`), F6 Task 2 Step 4 (guard un-scoped on intent → over-suppression). In each, the plan's own **sample code** carried a bug the review caught before it shipped. The plans are being written from a *model* of the code rather than the code, and between-task review is the only thing standing between that and production. **Cheap fix:** verify sample code against the actual tree before a plan is committed. It is not a substitute for review, but it removes a recurring, predictable class of review finding.
