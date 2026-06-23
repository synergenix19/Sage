"""Deterministic conversational-stall detection.

A "stall" is a stretch where the conversation stops making progress: the user
repeats themselves or gives consecutive low-content replies while the assistant
keeps asking new open questions. Observed in prod (session aa0a9256: four "not
sure" turns; session b3f4971b: a verbatim resend of the same point).

The trigger is computed entirely in code — the LLM never decides whether a stall
occurred (it only renders the change-of-tack once the guard fires). Keeping the
decision deterministic is the invariant; the specific thresholds below are a
PROVISIONAL heuristic pending validation against real transcripts.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Provisional thresholds (heuristic — validate against transcripts before trusting).
_STALL_RUN = 3                 # this many consecutive non-answer turns = stall
_LOW_CONTENT_WORD_MAX = 3      # substantive-vs-trivial cutoff for the repeat rule
_NEAR_DUP_RATIO = 0.9          # normalized similarity that counts as a repeat
_NEAR_DUP_LOOKBACK = 3         # compare the current turn against this many priors

# Deterministic non-answer prefixes. Validated against prod transcripts: this set
# fires on the genuine "not sure" stall (session aa0a9256 t9-11) without firing on
# short skill-flow confirmations like "okay sure" / "lets start" / "no" / "still
# angry", which a bare word-count rule misclassified as stalls.
_NON_ANSWER_PREFIXES = (
    "not sure", "im not sure", "not really sure", "i dont know", "i don't know",
    "idk", "dunno", "dont know", "no idea", "i guess", "not really",
)


def _norm_words(text: str | None) -> list[str]:
    """Lowercase, strip punctuation, split — a deterministic content view."""
    return re.sub(r"[^\w\s]", "", (text or "").lower()).split()


def _is_non_answer(text: str | None) -> bool:
    """A reply that declines to advance the conversation (deterministic match)."""
    normalized = " ".join(_norm_words(text))
    return bool(normalized) and normalized.startswith(_NON_ANSWER_PREFIXES)


def detect_stall(recent_user_messages: list[str] | None) -> bool:
    """Return True when the recent user turns constitute a conversational stall.

    Deterministic: same input always yields the same answer; no model call.
    """
    msgs = [m for m in (recent_user_messages or []) if m and m.strip()]

    # Pattern 1: a run of consecutive non-answers (no forward movement). Short
    # but substantive replies ("no", "still angry") and skill-flow confirmations
    # ("okay sure", "lets start") are NOT non-answers and do not count.
    if len(msgs) >= _STALL_RUN:
        last = msgs[-_STALL_RUN:]
        if all(_is_non_answer(m) for m in last):
            return True

    # Pattern 2: the current turn is a near-verbatim repeat of a recent prior
    # SUBSTANTIVE turn (the user re-sending a real point because they feel
    # unheard). Trivial low-content echoes ("not sure" twice) are deliberately
    # excluded here — those only count under the run-of-3 rule above.
    if msgs and len(_norm_words(msgs[-1])) > _LOW_CONTENT_WORD_MAX:
        current = " ".join(_norm_words(msgs[-1]))
        for prior in msgs[-(_NEAR_DUP_LOOKBACK + 1):-1]:
            prior_norm = " ".join(_norm_words(prior))
            if (
                current
                and prior_norm
                and SequenceMatcher(None, current, prior_norm).ratio() >= _NEAR_DUP_RATIO
            ):
                return True

    return False
