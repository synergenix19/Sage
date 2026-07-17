# TICKET 2026-07-15 — SK-EN-001 negation amendment (GOV-270 rider)

**Origin:** GOV-270 sign-off. SK-EN-001 (core English explicit SI) was **ratified + signed** (it catches most SI), but carries a **known recall gap: ~5/6 SI-with-negation missed** by the substring match (the standing negation gap, e.g. "I would never kill myself" vs "I can't go on"). Signing it recorded the limitation; this ticket closes it.

**Ask:** add negation-aware handling to SK-EN-001 (or a companion rule) so negated-SI phrasings are correctly dispositioned — flagged when the negation is *affirming* intent ("I can't go on"), not suppressed when it *negates* intent ("I would never"). Clinician confirms the negation taxonomy; eng implements + tests against the negated-SI cases.

**Not a deactivation, not a blocker to the sign-off** — the rule runs signed today; this raises its recall. Doc basis: BOT BEHAVIOUR Crisis protocol requires SI detection; negated-SI is in scope.
