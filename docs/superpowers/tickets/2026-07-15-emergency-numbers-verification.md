# TICKET 2026-07-15 — Emergency/helpline numbers: documented verification before launch

**Owner:** Engineering (dial-test / source-capture) + clinical lead (sign-off)
**Priority:** Pre-launch. The **998 row is a B1 flip gate**; the helpline rows are pre-launch.
**Origin:** BOT BEHAVIOUR's own Resources table says, in bold: *"⚠ Verify before launch… helpline numbers can change."* Nobody has done it. Also: the medical terminal shipped with **999 (police)** for a cardiac emergency until 2026-07-15 — an artifact-conformance miss on the highest-consequence string. Discipline precedent: **GL-1** (crisis helpline flip-flopped repeatedly on unverified claims until a dial-test resolved it).

## The rule this ticket enforces
**No number leads a safety response without a documented verification record** — a dial-test result or a cited authority, dated, attached. A code comment or a doc table is not a verification record. This is the reality-over-artifact rule applied to every number a user might dial in an emergency.

## Numbers to verify (each needs: current value + reachability/hours + a dated dial-test or citation)

| # | Context | Number as shipped | Verify |
|---|---|---|---|
| **M1** | **Medical/cardiac terminal** (`MEDICAL_REFERRAL_TEXT`) — **B1 FLIP GATE** | **998** (UAE ambulance) — leads; 999 removed | Confirm 998 is the current UAE ambulance number and reaches ambulance dispatch. (999 = police, correctly not led.) |
| C1 | Crisis: National Mental Support Line | 800-HOPE / 800-4673 | value + hours (doc/GL-1 said 8am-8pm; prod ruling differs, reconcile) |
| C2 | Crisis: SAKINA (Abu Dhabi) | 800-SAKINA / 800-725462 | value + 24/7 claim |
| C3 | Crisis: DHA | 800 111 | value + hours |
| C4 | Crisis: Sharjah | 800 51115 | value + hours |
| C5 | Crisis: Emergency services | 999 (police, psychiatric-crisis co-response) | confirm intended for the crisis pathway (leave as-is per clinical) |

## Definition of done
- Each row above has a dated verification record (dial-test outcome or cited authority) filed alongside this ticket.
- `MEDICAL_REFERRAL_TEXT`'s 998 record (M1) is attached **before `SAGE_MEDICAL_REDFLAG_GUARD` flips** — it is a B1 flip gate, not just pre-launch.
- Clinical lead signs the reconciled crisis-number set (values + hours), closing the GL-1-class ambiguity for good.
- The `config.py` provenance comment is updated to reference the record ID (replacing "PO-sourced" with the dial-test/citation).

## Non-goals
- Not changing the crisis pathway's use of 999 (psychiatric co-response is a clinical call, per the doc).
- Not a code task beyond swapping a verified value if the dial-test surfaces a changed number.
