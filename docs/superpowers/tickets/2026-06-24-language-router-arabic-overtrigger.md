# Ticket: Language router over-triggers Arabic on a single Arabic-block glyph (incl. punctuation)

**Filed:** 2026-06-24 · **Source:** prod observation (rohansarda@gmail.com pasted an English message that contained the Arabic question mark `؟`; Sage replied entirely in Khaleeji)
**Status:** open · **Type:** small fix, own mini-tranche · **Safety-adjacent (crisis-path language)** · **Not a regression**
**Related but DISTINCT:** `2026-06-24-arabic-question-stacking-translate-after-gate.md` — same `؟`/EN↔AR surface, **different layer**. That one is gate-ordering / translate-after-gate (resolved only by native-Arabic generation). **This one is the language router** (which language to answer in). Do **not** conflate them or fix them in one pass: a router threshold change is not a generation-architecture change.

## Symptom
An overwhelmingly-English message returns a fully Arabic (Khaleeji) reply. The model understands the
content fine; it just answers in the wrong language. Silent: nothing errors, content is correct, only
the language is wrong — so it will **not** surface in logs as a failure.

## Root cause (confirmed by repro)
`src/sage_poc/language.py:30`:
```python
if re.search(r'[؀-ۿ]', text):   # ANY char in U+0600–U+06FF
    return "ar"
```
The override fires on **any** Arabic-Unicode-block character — including Arabic **punctuation**
(`؟` U+061F, `،` U+060C, `؛` U+061B), which appears in copy-pasted text without the user writing Arabic.
Confirmed repro (`.venv` `detect_language`):
- `"...does the double-؟ ever land..."` → `'ar'`
- same sentence with ASCII `?` → `'en'`
- `"hello how are you ؟"` → `'ar'`

The override is intentional for **code-switching** (a bilingual user mixing Arabic words into English
should get Arabic). The flaw is that it treats lone Arabic *punctuation* as a full Arabic message.

## Why it's worth doing (not an edge case)
The triggering class — pasted text with Arabic punctuation, a bilingual user typing `؟`, any copy-paste
from an Arabic source — is the **everyday behaviour of the target population** (UAE/Khaleeji bilinguals).
An English-typing user getting fluent-but-wrong-language Arabic back is a real trust hit, and it is
**silent** (worse than a crash, which at least logs).

## Why this is NOT a hot-patch — the asymmetric crisis risk
`detect_language` also drives the **crisis path's response language**. The current heuristic
**over**-triggers Arabic (English flips to AR on a stray glyph). A letter-based fix **narrows** the
trigger, so the risk it introduces is the **opposite, costlier error**: an Arabic-script crisis message
that is punctuation-heavy, Arabizi, or code-switched now fails to flip to `ar` and gets an **English
crisis card**. **Under-detecting Arabic on the crisis path is far costlier than answering an English
info-request in Arabic.** The one-line diff is not the work — **the crisis EN/AR regression is the work.**

## Threshold decision (pin it deliberately, encode in tests)
Move the trigger from "any block char" to Arabic **letters**, then choose consciously:
- **Letter-presence** (`[ء-ي]`, ≥1 Arabic letter) — best **code-switching fidelity**; still flips
  a 99%-English sentence containing one genuine Arabic word (correct for code-switching, debatable for an
  English sentence quoting a single Arabic term). **Recommended default.**
- **Count/ratio** — more robust against a single quoted word, but has its own edge on very short messages.
Encode the chosen boundary in tests with explicit cases (one Arabic word → `ar`; lone `؟`/`،` in English
→ `en`; short Arabic message → `ar`) so the intent can't be silently re-broken later.

## Scope as its own mini-tranche (full discipline)
1. **Failing test** reproducing the English-text-with-`؟` → `ar` flip (and the lone-punctuation cases).
2. **Letter-based fix** in `language.py`, with the threshold decision pinned by the test cases above.
3. **Crisis EN/AR regression as the HARD gate** — Arabic crisis (incl. punctuation-heavy / Arabizi /
   code-switched) must still route to `ar` and produce the Arabic crisis card; English crisis still EN.
   This gate, not the diff, decides ship-readiness.
4. **Same final-SHA discipline:** fetch origin + resolve the real merge SHA, full-suite on the actual
   merge tree, staging smoke (crisis EN/AR), then promote on its own clean merge.

## Do NOT
- Bundle into the already-closed D3/D4/D5 release.
- Flip it in without the crisis EN/AR regression.
- Merge it with the question-stacking ticket as "fix the Arabic `؟` stuff."
