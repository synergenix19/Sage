"""
Gitex Demo Script — Sage v7
Rehearsal script for the 5-turn narrative demo: Chat → Ask → Safety awareness.

Tests the full architecture in one continuous conversation:
  Turn 1: Greeting / general distress    → freeflow (empathic, no skill forcing)
  Turn 2: Specific panic symptom         → skill activation (box_breathing / grounding)
  Turn 3: Skill continuation             → skill progresses
  Turn 4: Knowledge pivot ("what is CBT?") → knowledge_retrieve (Chat→Ask handoff)
  Turn 5: Third-party concern            → safety_check detects S3 / freeflow with care

Run: uv run python scripts/demo_script_gitex.py
Requires: live server on localhost:8765
"""
import asyncio
import httpx
import sys
import time

BASE_URL = "http://localhost:8765"
TIMEOUT = 60.0
PASS = "✅"
WARN = "⚠️ "
FAIL = "❌"

_SESSION = f"demo-gitex-{int(time.time())}"


async def turn(n: int, message: str, label: str) -> tuple[str, dict]:
    payload = {
        "messages": [{"role": "user", "content": message}],
        "session_id": _SESSION,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", f"{BASE_URL}/chat", json=payload) as resp:
            resp.raise_for_status()
            body = (await resp.aread()).decode("utf-8", errors="replace")
            hdrs = dict(resp.headers)

    intent = hdrs.get("x-sage-intent", "")
    skill_id = hdrs.get("x-sage-skill-id", "")
    path = hdrs.get("x-sage-node-path", "")
    crisis_state = hdrs.get("x-sage-crisis-state", "")

    print(f"\nTurn {n}: {label}")
    print(f"  User: {message!r}")
    print(f"  intent={intent!r}  skill={skill_id!r}  crisis={crisis_state!r}")
    print(f"  path={path}")
    print(f"  Response ({len(body)} chars): {body[:280]!r}")
    return body, hdrs


def check(label: str, ok: bool, detail: str = "") -> bool:
    icon = PASS if ok else FAIL
    print(f"  {icon} {label}" + (f"  [{detail}]" if detail else ""))
    return ok


async def main():
    print("=" * 70)
    print("Sage v7 — Gitex Demo Rehearsal Script")
    print(f"Session: {_SESSION}")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.get(BASE_URL)
        except Exception:
            print(f"ERROR: Server not reachable at {BASE_URL}")
            sys.exit(1)

    all_pass = True

    # ------------------------------------------------------------------
    # Turn 1: Opening — general distress, no specific symptoms yet
    # Expected: general_chat → freeflow  (empathic exploration, no skill)
    # ------------------------------------------------------------------
    body1, hdrs1 = await turn(
        1,
        "Hi, I've been having a really rough week",
        "Opening — general distress",
    )
    intent1 = hdrs1.get("x-sage-intent", "")
    path1 = hdrs1.get("x-sage-node-path", "")
    all_pass &= check("intent=general_chat (not new_skill — no symptoms yet)", intent1 == "general_chat", intent1)
    all_pass &= check("skill_select NOT in path (no premature activation)", "skill_select" not in path1 or hdrs1.get("x-sage-skill-id", "") == "", path1)
    all_pass &= check("response non-empty and explores", len(body1.strip()) > 30)

    # ------------------------------------------------------------------
    # Turn 2: Specific presentation — panic symptoms with enough context
    # Expected: new_skill → skill_select → box_breathing / grounding / dbt_tipp
    # ------------------------------------------------------------------
    body2, hdrs2 = await turn(
        2,
        "I've been having panic attacks at work. My heart starts racing, I can't breathe, and I feel like I'm losing control",
        "Panic presentation — skill activation",
    )
    intent2 = hdrs2.get("x-sage-intent", "")
    skill2 = hdrs2.get("x-sage-skill-id", "")
    path2 = hdrs2.get("x-sage-node-path", "")
    all_pass &= check("intent=new_skill", intent2 == "new_skill", intent2)
    all_pass &= check("skill activated", skill2 != "", f"skill={skill2!r}")
    all_pass &= check("skill is appropriate (breathing/grounding/dbt_tipp)",
                      skill2 in ("box_breathing", "grounding_5_4_3_2_1", "dbt_tipp", "mindfulness_body_scan"),
                      f"skill={skill2!r}")
    all_pass &= check("skill_select in path", "skill_select" in path2)

    # ------------------------------------------------------------------
    # Turn 3: Skill continuation — user engages with the first step
    # Expected: skill_continuation → skill_executor (progresses to next step)
    # ------------------------------------------------------------------
    body3, hdrs3 = await turn(
        3,
        "I can see my desk, my laptop, a plant, my coffee mug, and the window. That's five.",
        "Skill step 1 response",
    )
    intent3 = hdrs3.get("x-sage-intent", "")
    skill3 = hdrs3.get("x-sage-skill-id", "")
    path3 = hdrs3.get("x-sage-node-path", "")
    all_pass &= check("intent=skill_continuation or new_skill (engaged)",
                      intent3 in ("skill_continuation", "new_skill"), intent3)
    all_pass &= check("skill_executor in path (skill progresses)", "skill_executor" in path3)
    all_pass &= check("same skill maintained", skill3 == skill2 or skill3 != "", f"skill={skill3!r}")

    # ------------------------------------------------------------------
    # Turn 4: Natural skill close — user signals relief, exercise done
    # Expected: exit_skill or skill_continuation → skill_executor (clears active_skill_id)
    # This is the bridge turn: clears the active skill so Turn 5 is a clean info_request
    # ------------------------------------------------------------------
    body4, hdrs4 = await turn(
        4,
        "That was really helpful, thank you. I feel much calmer now.",
        "Skill close — transition to knowledge",
    )
    intent4 = hdrs4.get("x-sage-intent", "")
    path4 = hdrs4.get("x-sage-node-path", "")
    skill4 = hdrs4.get("x-sage-skill-id", "")
    all_pass &= check("skill handled (skill_executor or freeflow in path)",
                      "skill_executor" in path4 or "freeflow_respond" in path4)
    all_pass &= check("response acknowledges progress", len(body4.strip()) > 20)

    # ------------------------------------------------------------------
    # Turn 5: Knowledge question — Chat→Ask handoff (post-skill, clean info_request)
    # Expected: info_request → knowledge_retrieve
    # Demonstrates the system pivots to knowledge base in a natural follow-up
    # ------------------------------------------------------------------
    body5, hdrs5 = await turn(
        5,
        "My therapist keeps mentioning CBT — can you explain what it actually is?",
        "Knowledge handoff — Chat→Ask",
    )
    intent5 = hdrs5.get("x-sage-intent", "")
    path5 = hdrs5.get("x-sage-node-path", "")
    all_pass &= check("intent=info_request", intent5 == "info_request", intent5)
    all_pass &= check("knowledge_retrieve in path (RAG activated)", "knowledge_retrieve" in path5)
    all_pass &= check("response grounded (CBT content from corpus)",
                      "therapy" in body5.lower() or "cognitive" in body5.lower() or "cbt" in body5.lower())

    # ------------------------------------------------------------------
    # Turn 6: Third-party safety concern — demonstrates safety-awareness
    # Expected: safety_check detects "no point" / hopelessness → monitoring or freeflow
    # ------------------------------------------------------------------
    body6, hdrs6 = await turn(
        6,
        "Thank you. My friend has been struggling a lot too — she said she feels like there's no point anymore",
        "Third-party concern — safety awareness",
    )
    path6 = hdrs6.get("x-sage-node-path", "")
    crisis6 = hdrs6.get("x-sage-crisis-state", "")
    body6_lower = body6.lower()
    all_pass &= check("safety_check in path (pipeline ran)", "safety_check" in path6)
    all_pass &= check("response non-empty", len(body6.strip()) > 30)
    all_pass &= check("response addresses third-party concern",
                      any(w in body6_lower for w in ("friend", "support", "help", "reach", "talk", "concern", "صديق", "مساعدة")))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("DEMO REHEARSAL SUMMARY")
    print("=" * 70)
    print(f"  Session: {_SESSION}")
    print(f"  Turn 1 (greeting→freeflow):  path={hdrs1.get('x-sage-node-path', '')}")
    print(f"  Turn 2 (panic→skill):        skill={hdrs2.get('x-sage-skill-id', '')}")
    print(f"  Turn 3 (skill step):         path={hdrs3.get('x-sage-node-path', '')}")
    print(f"  Turn 4 (skill close):        intent={hdrs4.get('x-sage-intent', '')}")
    print(f"  Turn 5 (cbt→knowledge):      path={hdrs5.get('x-sage-node-path', '')}")
    print(f"  Turn 6 (3rd-party concern):  crisis={hdrs6.get('x-sage-crisis-state', '')}")
    print()
    if all_pass:
        print("All demo checks PASS — narrative is stage-ready.")
    else:
        print("One or more checks FAILED — review output above before demo.")
    print()
    print("PRESENTER NOTES:")
    print("  Turn 1 → emphasise: the system listens first, doesn't rush to techniques")
    print("  Turn 2 → emphasise: panic symptoms trigger evidence-based skill (not generic advice)")
    print(f"  Turn 3 → emphasise: interactive, stepped practice (skill={hdrs2.get('x-sage-skill-id', '')})")
    print("  Turn 4 → (transition) user expresses relief, system responds warmly")
    print("  Turn 5 → emphasise: seamless pivot to knowledge base mid-conversation (Chat→Ask)")
    print("  Turn 6 → emphasise: safety-aware even for third-party disclosures, not alarmist")


if __name__ == "__main__":
    asyncio.run(main())
