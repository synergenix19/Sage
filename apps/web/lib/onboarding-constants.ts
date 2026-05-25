// Single-digit only — if step count ever exceeds 9, rewrite the middleware regex in middleware.ts
// (character class [1-N] breaks for N >= 10: [1-10] matches '0', '1', '-', '1' not "integers 1–10")
export const TOTAL_ONBOARDING_STEPS = 6
