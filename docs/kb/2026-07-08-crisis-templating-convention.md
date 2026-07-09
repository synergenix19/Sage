# Crisis-number templating convention (2026-07-08)

The crisis PHONE NUMBERS are now a true single-config change. Crisis-copy source files no longer
re-embed the literals; they carry `{{crisis_*}}` placeholders that resolve at load time from the one
source of truth, `sage_poc.config.CRISIS_CONFIG`.

## The variable convention

Use these placeholders inside any crisis-copy string. Only numbers (and the ASCII hours string) are
templated — localized prose and labels are left as written.

| Placeholder            | Resolves to `CRISIS_CONFIG[...]` | Current value            |
|------------------------|----------------------------------|--------------------------|
| `{{crisis_number}}`    | `number`                         | `800 46342`              |
| `{{crisis_emergency}}` | `emergency`                      | `999`                    |
| `{{crisis_hours}}`     | `hours`                          | `24/7`                   |
| `{{crisis_label}}`     | `label`                          | `MoHAP Counselling Line` |

Notes:
- `{{crisis_label}}` is supported for completeness but crisis copy currently keeps the label as
  written prose (English and Arabic), so it is not yet used in the files.
- Arabic hours phrases (`على مدار الساعة`, `24 ساعة`) are localized prose and are NOT templated.
  Only the exact ASCII `24/7` maps to `{{crisis_hours}}`.
- To change a crisis number, edit `CRISIS_CONFIG` in `sage_poc/config.py` (ONE place). The frontend
  has its own mirror at `cdai/apps/web/lib/crisis-config.ts` — change BOTH; the cross-stack test
  (`tests/test_crisis_config_cross_stack.py`) fails if they diverge.

## Where resolution happens (do not re-embed literals elsewhere)

The resolver `sage_poc.crisis_copy.resolve_crisis_placeholders_deep` is applied at the lowest shared
read point of each family, so the RESOLVED text is what reaches the LLM / user:

- `rules/loader.py::load_rules` — crisis_content + prompt_injection JSON
- `prompts/loader.py::_load_all_templates` — L0_persona (and all prompt templates)
- `skills/schema.py::load_skill` — all skill JSON (steps, contraindications, escalation_matrix)

## Clinician ownership

Skill JSON and crisis content are clinician-owned. A clinician editing those files MUST keep the
`{{crisis_*}}` variables intact — do not paste a raw phone number back in, and do not rename a
variable. If new crisis copy is authored, use the placeholders above, never a literal number.

## Boot guard (fail-closed backstop)

`sage_poc.crisis_copy.assert_crisis_copy_resolves()` runs at server startup (server.py lifespan). It
loads every crisis-copy source in resolved form and raises `RuntimeError` if ANY unresolved
`{{crisis_...}}` substring remains — a missed resolution point, a typo'd variable
(e.g. `{{crisis_numbr}}`), or a new variable without a mapping. The app then REFUSES TO BOOT rather
than serve a raw placeholder in a crisis message, so a broken variable fails the deploy, not the user.

Defense in depth:
- Boot guard — no unresolved placeholder may ship.
- Conformance test (`tests/test_crisis_helpline_conformance.py`) — resolved output carries
  `CRISIS_CONFIG["number"]`. Consistency only; it asserts nothing about which number is correct.
- Byte-identical test (`tests/test_crisis_templating_byte_identical.py`) — proves the mechanism
  reproduces the pre-templating bytes exactly.

## Future CMS workflow

When crisis copy moves into the CMS, the editor must expose the `{{crisis_*}}` variables as
non-editable tokens (or validate on save that a number literal was not substituted for a variable).
The boot guard remains the deploy-time backstop, but the CMS should reject a broken variable at
author time.
