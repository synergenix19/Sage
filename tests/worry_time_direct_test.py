#!/usr/bin/env python3
"""
Worry Time UX test — direct graph invocation (no HTTP server, no checkpointer).
This avoids the Supabase connection pool saturation issue from concurrent test runs.
"""
import asyncio
import json
import sys
import uuid
import os

# Load env before anything else
from dotenv import load_dotenv
load_dotenv('/Users/knowledgebase/Documents/Sage/sage-poc/.env')

sys.path.insert(0, '/Users/knowledgebase/Documents/Sage/sage-poc/src')

from sage_poc.graph import build_graph
from sage_poc.server_helpers import _build_state

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


class FakeMsg:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class FakeReq:
    def __init__(self, messages, session_id=None):
        self.messages = messages
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = None


async def run_turn(graph, history, session_id):
    msgs = [FakeMsg(m['role'], m['content']) for m in history]
    req = FakeReq(msgs, session_id)
    state = _build_state(req)
    state['therapeutic_profile'] = None

    result = await asyncio.wait_for(
        graph.ainvoke(
            state,
            config={'configurable': {'thread_id': session_id}},
        ),
        timeout=60.0
    )
    return {
        'sage': result.get('response', ''),
        'skill_id': result.get('active_skill_id', ''),
        'step_id': result.get('executed_step_id', ''),
        'active_step_id': result.get('active_step_id', ''),
        'intent': result.get('primary_intent', ''),
        'path': result.get('path', []),
        'word_count': len((result.get('response') or '').split()),
    }


async def run_conversation(turns, lang_prefix):
    graph = build_graph(checkpointer=None)
    session_id = f'ux-{lang_prefix}-' + str(uuid.uuid4())[:8]
    history = []
    results = []

    for i, msg in enumerate(turns, 1):
        history.append({'role': 'user', 'content': msg})
        try:
            result = await run_turn(graph, history, session_id)
            result['user'] = msg
            results.append(result)
            history.append({'role': 'assistant', 'content': result['sage']})
            print(f'[{lang_prefix}] Turn {i}: intent={result["intent"]} skill={result["skill_id"]} step={result["step_id"]} words={result["word_count"]}', file=sys.stderr)
            print(f'  USER: {msg[:80]}', file=sys.stderr)
            print(f'  SAGE: {(result["sage"] or "")[:200]}', file=sys.stderr)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            result = {
                'user': msg, 'sage': f'ERROR: {e}',
                'skill_id': '', 'step_id': '', 'active_step_id': '',
                'intent': '', 'path': [], 'word_count': 0,
            }
            results.append(result)
        await asyncio.sleep(0.3)

    return results


async def main():
    print("=== ENGLISH CONVERSATION ===", file=sys.stderr)
    en_results = await run_conversation(EN_TURNS, 'en')

    print("\n=== ARABIC CONVERSATION ===", file=sys.stderr)
    ar_results = await run_conversation(AR_TURNS, 'ar')

    output = {
        'en': {'lang': 'en', 'turns': en_results},
        'ar': {'lang': 'ar', 'turns': ar_results},
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
