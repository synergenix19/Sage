#!/usr/bin/env python3
import sys
from sage_poc.graph import build_graph
from sage_poc.state import SageState


def make_initial_state() -> SageState:
    return {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


def main():
    print("\n=== SageAI Graph Routing POC ===")
    print("Type your message (Arabic or English). 'quit' to exit.\n")

    graph = build_graph()
    state = make_initial_state()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        state["raw_message"] = user_input

        result = graph.invoke(state)

        print(f"\nSage: {result['response']}")
        print(f"[Path: {' → '.join(result['path'])}]")

        if result.get("active_skill_id"):
            print(f"[Skill: {result['active_skill_id']} | Used: {result.get('executed_step_id')} → Next: {result.get('active_step_id')}]")

        if result.get("secondary_intent"):
            print(f"[Blended intent: {result.get('primary_intent')} + {result.get('secondary_intent')}]")

        if result.get("clinical_flags"):
            print(f"[CLINICAL FLAGS: {', '.join(result['clinical_flags'])}]")

        if result.get("escalation_triggered"):
            esc = result["escalation_triggered"]
            print(f"[ESCALATION {esc['level']}] {esc['reason']}")

        print()

        state = {
            **make_initial_state(),
            "active_skill_id": result.get("active_skill_id"),
            "active_step_id": result.get("active_step_id"),
            "conversation_history": result.get("conversation_history", []),
            "turn_count": result.get("turn_count", 0),
            "engagement": result.get("engagement", 7),
            "emotional_intensity": result.get("emotional_intensity", 5),
        }


if __name__ == "__main__":
    main()
