# DRAFT — B1 + F6 go-live announcement (use only when BOTH flags flip)

**Status:** DRAFT. Do not send until `SAGE_MEDICAL_REDFLAG_GUARD` **and** `SAGE_VENTING_SUPPRESSION` are ON in the target environment and every gate below is cleared. Written now so nobody improvises a looser one under pressure.

---

## The announcement (every clause is load-bearing — do not trim)

> **Medical red-flag screening (exact-phrase floor) and venting suppression are live in English.** The medical guard covers the **four-descriptor override list only** — not the Section 6 judgment guards (breathlessness-vs-panic, fainting, confusion), which are **B1-full scope**. **Arabic coverage of both mechanisms is unverified.** Emergency number verified by dial-test record **[ref]**.

## Why each clause is there (it's the thing the thread nearly shipped without)

- **"exact-phrase floor"** — B1-interim is regex over a verbatim phrase list. It is a harm floor, not the detector. Do not let it be described as "medical screening" without the qualifier.
- **"in English"** — every safety mechanism built this cycle is English-verified only.
- **"four-descriptor override list only — not the Section 6 judgment guards"** — empirically confirmed (Q-A): `medical_e3_recall.json` tests the cardiac phrase class, `fainting`/`confusion`/`real-inability-to-breathe` are absent. Announcing "medical screening" without this overclaims coverage the ≥95% gate does not certify.
- **"Arabic coverage… unverified"** — B1's guard has zero native AR (EN-via-translation only, near-zero); F6's PI-VI-001 Khaleeji keywords have never been tested. For a Khaleeji-first product this is the biggest unknown, and it must be stated, not omitted.
- **"verified by dial-test record [ref]"** — the number leading the medical terminal (998, UAE ambulance) is not "verified" until a dial-test/citation record exists (ticket `2026-07-15-emergency-numbers-verification`, M1). **Do not fill `[ref]` with a comment or a web link — only a real record.** The prior "999" (police) shipped because a reality-check was skipped; this clause is the guard against announcing the fix on the same non-evidence.

## Blocked-until (do not announce while any is open)
- B1 flip: Gate 1 (ratify list + 2 variants), Gate 2 dial-test **record** (998), migration `012` deployed. — Gate-2/4 **code** is done; the record and the deploy step are not.
- F6 flip: Gate 3 formal clinical sign-off (PI-VI-001 keyword set).
- The `[ref]` in the announcement resolves to the closed dial-test record, or the announcement does not go out.
