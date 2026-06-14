#!/usr/bin/env python3
"""Multi-turn functional probe against LIVE PRODUCTION /chat.

Goal: observe the *engagement layer* behaviour shipped in the last 5-7 merges
(R1 consent-gated entry, R3 engage-then-bridge, R5 criteria-hold, C1 tiebreak,
SF-2 acute routing, L0 persona v2.0.0) end-to-end as a real client would.

Specifically answers the product questions:
  1. Is it MORE ENGAGING (warm, validates before advising, no stock/sycophantic
     openers per L0 v2.0.0)?
  2. Does it ASK before initiating a skill (R1 offer) rather than auto-launching?
  3. How does a skill PROGRESS once accepted (steps advance)?
  4. Are users LOCKED IN, or is there an EASY EXIT mid-skill?

Multi-turn = same session_id per scenario; server holds history via the
LangGraph checkpointer (thread_id == session_id). Each turn we POST only the
latest user message (see server_helpers._build_state — history comes from the
checkpoint, not the request body).

SAFETY: NON-CRISIS inputs only. We must not pollute the prod crisis review queue
or shared prod Supabase with self-harm content. Inputs are everyday
anxiety/work-stress/sadness — enough to trigger skill offers, never the
deterministic crisis path.
"""
import os
import sys
import uuid
import json
import time
import httpx

API_URL = os.environ.get("SAGE_API_URL", "https://sage-api-production-3328.up.railway.app")
API_KEY = os.environ.get(
    "SAGE_API_KEY",
    "8384792dfb576c5d7b975f40c4f21a8eb82fb024eb243570dc1cc9f7a871b328",
)
HEADERS = {"X-Sage-Api-Key": API_KEY, "Content-Type": "application/json"}
TIMEOUT = 120
_RUN = uuid.uuid4().hex[:8]


def turn(client, session_id, message):
    """Send one user message; return (body_text, headers_dict)."""
    payload = {"messages": [{"role": "user", "content": message}], "session_id": session_id}
    chunks = []
    hdrs = {}
    with client.stream("POST", f"{API_URL}/chat", headers=HEADERS, json=payload) as resp:
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        for raw in resp.iter_bytes():
            chunks.append(raw)
    body = b"".join(chunks).decode("utf-8", errors="replace")
    return body, hdrs


def fmt_hdrs(h):
    keys = [
        ("x-sage-intent", "intent"),
        ("x-sage-skill-id", "skill"),
        ("x-sage-active-step-id", "active_step"),
        ("x-sage-step-id", "executed_step"),
        ("x-sage-node-path", "path"),
        ("x-sage-emotional-intensity", "intensity"),
        ("x-sage-crisis-state", "crisis"),
        ("x-sage-semantic-score", "sem"),
    ]
    out = []
    for raw, label in keys:
        v = h.get(raw, "")
        if v not in ("", "none", "0", "[]"):
            out.append(f"{label}={v}")
    return "  ".join(out)


SCENARIOS = [
    {
        "name": "A. Anxiety -> OFFER -> accept -> progress -> EXIT mid-skill",
        "turns": [
            "honestly I've been so anxious this week, my mind keeps racing and I can't switch off at night",
            "yeah okay, that sounds good, let's try it",
            "okay... I can see my phone on the desk, a glass of water, my notebook, the lamp, and the window",
            "actually you know what, I want to stop this, it's not really helping right now",
        ],
    },
    {
        "name": "B. Engagement tone (new L0 v2.0.0 persona, plain venting)",
        "turns": [
            "had a rough day, my manager picked apart my work in front of the whole team and I felt humiliated",
        ],
    },
    {
        "name": "C. DECLINE an offer (is 'no' respected, no re-push?)",
        "turns": [
            "i keep overthinking everything lately, every small decision feels exhausting",
            "no thanks, I don't want an exercise, I just want to vent for a bit",
            "i guess I just feel like I'm not good enough at my job no matter what I do",
        ],
    },
]


def main():
    print(f"=== Sage PROD multi-turn functional probe  run={_RUN} ===")
    print(f"API_URL={API_URL}")
    print(f"time={time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    with httpx.Client(timeout=TIMEOUT) as client:
        # quick liveness
        try:
            r = client.get(f"{API_URL}/health/schema-conformance", headers=HEADERS)
            print(f"[liveness] /health/schema-conformance -> {r.status_code}\n")
        except Exception as e:
            print(f"[liveness] FAILED: {e}\n")

        for sc in SCENARIOS:
            sid = f"functest-{_RUN}-{uuid.uuid4().hex[:6]}"
            print("=" * 88)
            print(f"SCENARIO {sc['name']}")
            print(f"session_id={sid}")
            print("=" * 88)
            for i, msg in enumerate(sc["turns"], 1):
                print(f"\n--- turn {i} ---")
                print(f"USER : {msg}")
                try:
                    body, hdrs = turn(client, sid, msg)
                except Exception as e:
                    print(f"  !! request failed: {e}")
                    break
                crisis = "[[CRISIS_DETECTED]]" in body
                clean = body.replace("[[CRISIS_DETECTED]]", "").strip()
                print(f"SAGE : {clean}")
                print(f"META : {fmt_hdrs(hdrs)}" + ("  **CRISIS**" if crisis else ""))
                time.sleep(0.5)
            print()


if __name__ == "__main__":
    main()
