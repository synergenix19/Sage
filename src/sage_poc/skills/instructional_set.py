"""INSTRUCTIONAL_SKILLS: a doc-derived STOPGAP for P0b's `delivery_format` field.

There is no `delivery_format` field on the `Skill` schema yet (that lands in P0b,
per docs/superpowers/specs/2026-07-17-psychoed-mechanism-a-design.md, "Instructional
scoping"). Until then, Mechanism-A's info_request→skill_executor consult needs a way
to know which skills are a bot-led, multi-step *instructional* content walkthrough
(as opposed to an experiential skill like box_breathing, or a single-message /
info-resource item) without inventing a schema field ahead of the clinician-owned
P0b work.

This set is derived from the BOT BEHAVIOUR spec source
(docs/superpowers/specs/bot-behaviour-oracle/bot-behaviour-spec-source-2026-07-08.md)
by taking every per-category "Skills" table row whose **Format** cell reads
**`Instructional`, VERBATIM** — not "skills that teach", not a grep for
teaching-adjacent skills. See tests/test_instructional_set.py for the full
derivation table and the exclusions this deliberately does NOT fold in
(single_message items like worry_time; info_resource / link-handoff items like the
KB article sleep-001).

STOPGAP discipline: this module must NOT be extended by inspection, judgment calls,
or "obviously instructional" reasoning. Any new entry needs a verbatim `Instructional`
Format cell in the spec source doc, cited by line number in the test file's
derivation table.

Convergence: the day P0b lands a `delivery_format` field on `Skill`, this set must
equal `{s.id for s in SKILL_REGISTRY skills if s.delivery_format == "instructional"}`.
tests/test_instructional_set.py pins that convergence as an
`xfail(strict=False)` test today (no field yet) that flips to a real pass/fail
the moment the field exists, forcing reconciliation instead of leaving this as a
third dormant-divergent artifact (after `escalation_matrix` and the activation-map).
"""

from sage_poc.skill_ids import SKILL_REGISTRY

# Skill IDs whose BOT BEHAVIOUR spec Format cell reads "Instructional" verbatim.
# Currently: Sleep Hygiene (S1b category), spec source line 1330 — the doc's sole
# verbatim `Instructional` Format cell (grep-verified: exactly one match for
# `^Instructional$` in the 1842-line spec source).
INSTRUCTIONAL_SKILLS: frozenset[str] = frozenset({
    "sleep_hygiene",
})

# Every member must be a real, registered skill — never a guessed id.
_unknown = INSTRUCTIONAL_SKILLS - set(SKILL_REGISTRY)
assert not _unknown, (
    f"INSTRUCTIONAL_SKILLS contains id(s) not in SKILL_REGISTRY: {sorted(_unknown)}"
)
