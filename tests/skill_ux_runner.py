#!/usr/bin/env python3
"""
Skill UX conversation runner.
Used by sub-agents to test a skill's end-to-end conversation flow.

Usage:
  python3 tests/skill_ux_runner.py --skill box_breathing --lang en
  python3 tests/skill_ux_runner.py --skill box_breathing --lang ar

Output: JSON to stdout with conversation transcript and metadata.
"""
import argparse
import json
import sys
import time
import uuid

import httpx

BASE_URL = "http://localhost:8000"


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
    }


def run_conversation(turns: list[str], session_id: str | None = None) -> list[dict]:
    """
    Run a multi-turn conversation. `turns` is the list of user messages.
    Returns list of turn results (one per user message).
    """
    session_id = session_id or str(uuid.uuid4())
    history: list[dict] = []
    results = []

    for user_msg in turns:
        history.append({"role": "user", "content": user_msg})
        result = send_message(history, session_id)
        history.append({"role": "assistant", "content": result["text"]})
        result["user_msg"] = user_msg
        results.append(result)
        time.sleep(0.3)  # small delay to avoid hammering the server

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True, help="Skill ID to test")
    parser.add_argument("--lang", default="en", choices=["en", "ar"])
    parser.add_argument("--turns", help="JSON array of user messages to send")
    args = parser.parse_args()

    if args.turns:
        turns = json.loads(args.turns)
    else:
        print(json.dumps({"error": "--turns required"}), file=sys.stderr)
        sys.exit(1)

    results = run_conversation(turns)
    output = {
        "skill_id": args.skill,
        "lang": args.lang,
        "turns": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
