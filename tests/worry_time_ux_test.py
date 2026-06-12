#!/usr/bin/env python3
"""Worry Time UX test — English and Arabic conversations."""
import json
import sys
import time
import uuid
import httpx

BASE_URL = "http://localhost:8000"

EN_TURNS = [
    "I can't stop worrying, my mind just won't stop — I feel like I'm constantly anxious about everything",
    "Yes, I'd like to try that. Maybe around 7pm after dinner, for about 20 minutes?",
    "I've been worrying a lot about whether I'll lose my job. I think that's an actionable worry — there are actual steps I could take to address it.",
    "Thank you, that was really helpful. I feel a bit clearer now.",
]

AR_TURNS = [
    "ما أقدر أوقف أفكاري، دايم قلقان على كل شي",
    "أيوه، أبي أجرب. ممكن بعد العشاء، حوالي الساعة ثمانية، عشرين دقيقة",
    "أنا قلقان من الشغل، أحس إنه قلق حقيقي وأقدر أسوي فيه شي",
    "شكراً، هذا ساعدني وايد",
]


def send_message(messages: list, session_id: str) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/chat",
        json={"messages": messages, "session_id": session_id},
        timeout=60.0,
    )
    resp.raise_for_status()

    text = resp.text
    is_crisis = text.startswith("[[CRISIS_SIGNAL]]")
    if is_crisis:
        text = text[len("[[CRISIS_SIGNAL]]"):].strip()
    is_error = "[[SERVER_ERROR]]" in text

    h = resp.headers
    return {
        "text": text.strip(),
        "skill_id": h.get("x-sage-skill-id", ""),
        "step_id": h.get("x-sage-step-id", ""),
        "active_step_id": h.get("x-sage-active-step-id", ""),
        "intent": h.get("x-sage-intent", ""),
        "path": json.loads(h.get("x-sage-node-path", "[]")),
        "word_count": len(text.split()),
        "is_crisis": is_crisis,
        "is_error": is_error,
    }


def run_conversation(turns: list, session_id: str | None = None) -> list:
    session_id = session_id or str(uuid.uuid4())
    history: list = []
    results = []

    for user_msg in turns:
        history.append({"role": "user", "content": user_msg})
        try:
            result = send_message(history, session_id)
        except Exception as e:
            result = {
                "text": f"[REQUEST_ERROR: {e}]",
                "skill_id": "", "step_id": "", "active_step_id": "",
                "intent": "", "path": [], "word_count": 0,
                "is_crisis": False, "is_error": True,
            }
        history.append({"role": "assistant", "content": result["text"]})
        result["user_msg"] = user_msg
        results.append(result)
        time.sleep(0.5)

    return results


def main():
    print("=== RUNNING ENGLISH CONVERSATION ===", flush=True)
    en_results = run_conversation(EN_TURNS)
    print(json.dumps({"lang": "en", "turns": en_results}, ensure_ascii=False, indent=2))

    print("\n=== RUNNING ARABIC CONVERSATION ===", flush=True)
    ar_results = run_conversation(AR_TURNS)
    print(json.dumps({"lang": "ar", "turns": ar_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
