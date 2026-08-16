"""§1c anxiety-track referral — the ONE deterministic message the derealization terminal renders.

⚠️ DRAFT copy, pending Vee's ratification (docs/superpowers/governance/
2026-07-28-1c-anxiety-referral-copy-for-vee.md). The mechanism ships flag-gated OFF
(DEREALIZATION_DETECTION_ENABLED) and is INERT until this copy is signed + pinned in
signed_clinical_fields.json + the flag flipped — mirroring HR-1 / Node-8. The LLM never composes
this terminal (safety-exit templated-copy class). Every phone number is a {{crisis_*}} placeholder
resolved at render from the single source (crisis_copy / CRISIS_RESOURCES) — no literals.

RESOURCE SET (BOT BEHAVIOUR-aligned, pending Vee ratification): the National support line (by day) +
the 24/7 Abu Dhabi line — the "see-someone" referral tier per doc §1c L151 ("escalate to referral
rather than presenting the standard tools"). NO 999/emergency line: the doc (L1830) reserves emergency
services for the crisis/danger tier and explicitly contrasts it with "see someone soon", and this
terminal is reached only when the turn is NOT a crisis. Including 999 here would be the §1c
over-escalation shape in copy form.
"""

# EN — account-framed ("what you're describing"), anxiety-normalising (NOT the psychosis register),
# refers (does NOT hand a grounding skill — Vee 1c, doc wins). See-someone tier: no 999 (doc L151/L1830).
DEREALIZATION_REFERRAL_EN = (
    "What you're describing — feeling like things around you aren't real, or feeling disconnected "
    "from yourself — can happen when anxiety becomes very intense. It's real, it's more common than "
    "you'd think, and it's something a mental health professional can help you understand and work "
    "through. In the UAE, you can reach the {{crisis_label}} on {{crisis_number}}, free, "
    "{{crisis_hours}}; and at any hour, day or night, the Abu Dhabi support line {{crisis_alt_24_7}} "
    "is available free, 24/7. You don't have to navigate this alone."
)

# AR (Khaleeji) — hours localised; INTERIM DRAFT pending the same native-Khaleeji review as the
# #313 AR corpus. Mnemonics kept Latin (digits authoritative).
DEREALIZATION_REFERRAL_AR = (
    "اللي تصفه — إنك تحس إن الأشياء حولك مو حقيقية، أو تحس إنك منفصل عن نفسك — ممكن يصير لما القلق "
    "يصير شديد جداً. هذا شي حقيقي، وأكثر انتشاراً مما تتوقع، ومتخصص نفسي يقدر يساعدك تفهمه وتتجاوزه. "
    "في الإمارات، تقدر تتواصل مع خط الدعم النفسي الوطني على {{crisis_number}}، مجاناً، من الساعة ٨ "
    "الصبح إلى ٨ المسا يومياً؛ وفي أي وقت، ليل أو نهار، خط سكينة في أبوظبي {{crisis_alt_24_7}} "
    "متوفر مجاناً على مدار الساعة. ما أنت لوحدك في هذا."
)


def derealization_referral_text(lang: str) -> str:
    """The rendered (crisis-placeholders resolved) referral for the turn's language."""
    from sage_poc.crisis_copy import resolve_crisis_placeholders  # noqa: PLC0415

    template = DEREALIZATION_REFERRAL_AR if lang == "ar" else DEREALIZATION_REFERRAL_EN
    return resolve_crisis_placeholders(template)
