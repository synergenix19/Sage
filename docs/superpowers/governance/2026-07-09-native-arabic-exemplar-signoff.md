# Native-Arabic Exemplar Sign-Off — Layer 1 gate

**Date:** 2026-07-09 · **Relayed by:** PO / coordinator (this session) · **Clinician:** vee

**Determination — approved ALL as-is:**
- `ar_neutral` (AI-drafted, unmarked-case strings): **correct as-is, no corrections.**
- `ar_m` / `ar_f` (marked-case gendered): confirmed (previously, ④).
- **Item-5 amendment** (register scores language quality alone; mis-gender is a separate flag): **re-confirmed.**
- **#220 served-path scope-confirm:** 3a (shift approved) / 3b (session-stickiness #221 coming) / 3c (unmarked-stratum = evidence checkpoint) — **confirmed.**

**Controller gate:** encoding check **PASS** (UTF-8 clean, ك→ج preserved).

**Nature of the attestation (recorded honestly):** a **blanket "approved as-is"** attributed to clinician *vee*, **relayed** by the coordinator — NOT a line-edited native correction pass. If the neutral strings later prove imperfect, the provenance shows exactly this. Exemplar **v1.0.1** carries this attestation; content is identical to the prematurely-bumped, quarantined **1.0.0** shakedown.

**Gate status:** exemplar-attestation gate **MET** → Layer 1 proper cleared on v1.0.1.
**Still open downstream:** register KPI needs the **blinded rating pass** (2nd Gulf-native rater); Layer 2 needs the **DPO note**; dev-ledger reconciliation for `013`.

---

## Delivery status update — served-path (#220) prod functional test, 2026-07-09

Prod functional testing of the shipped **#220** translate-out gender fix found:
- **Marked-feminine correction: LIVE in prod, verified.** A feminine-marked turn returned fully feminine (*«إنج تحسّين… عليج… نفسج»*). The headline mis-gendering defect is fixed for real users.
- **Unmarked→neutral: NOT delivered.** An unmarked turn still returned **masculine** (عليك، إنك، تحس) — the weak neutral directive lost to the all-masculine exemplars. Follow-up **PR #256** strengthens the directive (4 masculine forms → **1 consistent residual leak** «لما تحس» in live-LLM testing); the completing step (exemplar neutralization — native-authored) remains owed.

**Sign-off reconciliation (so vee isn't carrying a signature for unshipped behavior):** the ⑧ scope-confirm blessed *"most replies go neutral"* as the stated blast radius. **Marked-feminine correction is live; unmarked-neutral is pending #256 + the exemplar-neutralization follow-up.** This is an **incomplete delivery of the signed policy, not a regression** — unmarked prod behavior is unchanged from before #220 (masculine-leaning).

## Monitoring cadence (formalized — this defect was caught by exactly this)
**Named cadence, weekly through Gitex:** a Gulf-native reviews a handful of served **unmarked + marked** Arabic turns each week. The neutral path **ships incomplete** until #256 + the exemplar neutralization land, so this is not a one-off spot-check — it is the standing monitor that surfaces the residual leak and any regression to the feminine win.

## Mis-gender secondary-metric baseline
The prod functional method now gives the **unmarked stratum a known baseline**: unmarked→masculine (pre-#256), unmarked→single-residual-leak (post-#256). When the **deferred measurement resumes**, the unmarked-stratum mis-gender rate is read against this baseline — one more reason the **measurement-deferral review date is load-bearing**, not open-ended.
