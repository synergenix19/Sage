"""Psychoed Mechanism-A: the disposition set the info_request consult is scoped to.

AXIS DISTINCTION (read before editing — this set exists because the two were once fused):
  - DISPOSITION = what response does a presentation get? (a skill / presence / referral /
    KB). This set, and `target_presentations`, and skill_select's matching, are all
    disposition. It is node-4 / Rules-Service territory.
  - DELIVERY   = how is a skill rendered? (video / guided / instructional / single_message /
    info_resource). That is `delivery_format` (P0b) and `instructional_set.py`. It is
    node-5 / executor territory.
  Neither field may ever appear in the other's decision. Scoping this consult by delivery
  format (2026-07-17, first draft) returned {sleep_hygiene} and recovered nothing of the
  psychoed cluster, because the cluster's prescribed skills are guided-conversation format,
  not Instructional. This set is scoped by DISPOSITION instead. See
  docs/superpowers/specs/2026-07-17-psychoed-mechanism-a-design.md.

DERIVATION (doc-derived, from the layer-1 corpus's per-category `expected_skill_family`):
  §1f -> psychoed_anxiety | §6d -> {assertive_communication, psychoed_anxiety}
  §3c -> psychoed_depression | S2c -> {grief_loss, psychoed_depression}
  (§4a is Mechanism B; §7c is a matching gap routed to the clinician packet -- both OUT.)

Doc-derived engineering config (like B1's referral variants), listed in the clinician
packet's third-ask so clinical sees which skills become reachable via info-intent -- keeping
the no-silent-routing-authority principle intact.
"""
from __future__ import annotations

INFO_REQUEST_SKILL_CONSULT_SET: frozenset[str] = frozenset(
    {
        "psychoed_anxiety",
        "psychoed_depression",
        "assertive_communication",
        "grief_loss",
    }
)
