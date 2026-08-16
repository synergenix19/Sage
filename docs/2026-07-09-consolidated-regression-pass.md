# Consolidated functional regression — three-ring pass (2026-07-09)

**Purpose:** three weeks of individually-green changes (presence, typewriter, fade, #191 render invariant,
#205 backstop, mapRowToSdkMessage, tripwire, floor test) had never run *together*; the #191/#205 class
lives in the seams. This is the combined-system drive + Gitex demo rehearsal + the **standing release gate**.

**Run:** prod `chat.biosight.ai` / `sage-api-production` @ ship SHA `7cbc77c` + `SAGE_TEST_USER_IDS` deploy.
Helpline `800 46342` / "24/7" asserted **correct** (PO-confirmed, #253). All test data cleaned (queue = 0).

**Result: seams held.** Ring 1 fully green; Ring 2 green with 2 ticketed findings; Ring 3 green incl. the
never-before-tested mixed-history reload.

## How to re-run (the gate)
- **Backend crisis:** `railway run <venv>/python scripts/prod_smoke/run.py --tier a`
- **Experience layer:** `--tier b` (Playwright, needs staff storageState); typewriter/presence via the
  frontend scripts (scratchpad `smoke_169_v2.mjs`, `mixed_history_reload.mjs`, `reload_check.mjs`).
- **Therapeutic-core + tripwire:** the API-header drives below (X-Sage-Gate-Path / Skill-Id / Node-Path).

---

## Ring 1 — CRISIS (8/8 PASS, driven together)
| # | Line | Result |
|---|---|---|
| 1.1/1.2 | crisis card EN + AR (RTL), single-frame, `tel:800-46342` (correct) | ✅ |
| 1.3 | `role='crisis'` persisted — both replies incl. AR continuation | ✅ |
| 1.4 | #205 continuation (tier=none) → backstop fires + L2 flag | ✅ |
| 1.5 | reload survival — no sentinel, card pinned, replies hidden | ✅ |
| 1.6 | latest-pin (AR) survives reload | ✅ |
| 1.7 | waiting-state indistinguishable | ✅ |
| 1.8 | tripwire fires for non-allowlisted user, muted for allowlisted (SAGE_TEST_USER_IDS) | ✅ |
| — | Tier A smoke: crisis resources EN/AR, MM-hold, precedence | ✅ (helpline xfail now stale → #253) |

## Ring 2 — THERAPEUTIC CORE (driven; 2 findings ticketed)
| # | Line | Result |
|---|---|---|
| 2.1 | skill selection (`skill_matching_rule:default_offer → skill_offer_made`; `dbt_tipp` activation) | ✅ |
| 2.2 | **step_policy / §4.4 flow** — ei=8 → `acute_direct_entry → skill_executor → dbt_tipp entry_screen` validation-first (executor → rules-first → prompt → gate) | ✅ |
| 2.3 | knowledge ("what is CBT?" → sources); abstain ("capital of France" → no source) | ✅ / **#261** (freeflow answers trivia — scope call, parked) |
| 2.4 | low-confidence routing (`low_confidence_respond`) | ✅ |
| 2.7 | mid-skill exit EN + AR → warm exit, `gate=standard`, not crisis | ✅ / **#260** (EN "I want to stop" fires s3_semantic + T1, correct-by-de-escalation; persistence clean) |
| 2.5/2.6 | blended intent / mood anchor | lightly driven (not deep) |

## Ring 3 — EXPERIENCE LAYER (PASS incl. the key seam)
| # | Line | Result |
|---|---|---|
| 3.1 | normal EN presence phases → typewriter word-by-word → skip | ✅ (verified in #169 prod smoke) |
| 3.2 | normal AR RTL, typewriter | ✅ (#169 smoke: dir=rtl) |
| 3.3 | markdown → fade branch | ✅ (fade path on list replies) |
| 3.5 | **mixed-history reload** (skill+normal+crisis in one convo → reload) — `mapRowToSdkMessage` renders ai bubbles + hides/cards the crisis reply, no sentinel, correct card | ✅ **(seam never tested before — holds)** |
| 3.4 | code-switched input | lightly driven |

---

## Findings (ticketed, none block Gitex)
- **#260** — s3_semantic false-positive on skill-exit ("I want to stop"); correct-by-de-escalation. Pin with a regression test + add the production utterance to #231 negatives (done). Persistence: clean (audit-trace only, therapeutic profile untouched).
- **#261** — freeflow answers general trivia after KB abstain; product/scope call, parked pre-Gitex.
- **#253** — GL-1 helpline confirmed correct; flip the smoke `crisis_helpline_number_correct` xfail→PASS.
- **#254** — `/health/version` false artifact identity (bake SHA at build time); behavioral-signature verification is the required method meanwhile.

## Harness hygiene (carried forward)
The frontend session-capture flake (sidebar-position) bit twice; the reload harness must **resolve the
session by ID** (network-capture or DB lookup), not sidebar position. Applied the DB-lookup workaround in
this pass; the durable fix is ticketed.
