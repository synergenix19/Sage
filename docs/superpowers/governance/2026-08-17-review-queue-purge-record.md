# Clinician review queue — test-row purge record (2026-08-17)

Owner ruling: purge post-export. Executed: the single test-user row (created 2026-06-08,
carrying a month of upsert-appended probe timeline) exported to
`evidence/2026-08-17-review-queue-test-row-export.json` (895 bytes), then DELETE 1.
Post-purge count: 40 rows, all non-test, untouched. Rationale (owner's): synthetic
clinical data on a clinical surface pollutes reviewer-queue analytics and normalizes test
residue on the surface class the SF-1 exclusion was just built for; PDPL data-minimization
concurs. Forward protection: the is_test_user notify suppression (merged #448).
