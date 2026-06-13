"""QA script for self_compassion topic testing."""
import httpx
import json
import uuid
import time
import subprocess
import sys
import os
import signal


def find_server_port():
    """Try known ports to find a working one."""
    for port in [8099, 8000, 8001, 8002, 8003]:
        try:
            resp = httpx.get(f"http://localhost:{port}/health/ready", timeout=3.0)
            if resp.status_code == 200:
                return port
        except Exception:
            pass
    return None


def run_query(port, query, label):
    """Run a single query and return results dict."""
    session_id = str(uuid.uuid4())
    messages = [{"role": "user", "content": query}]
    try:
        resp = httpx.post(
            f"http://localhost:{port}/chat",
            json={"messages": messages, "session_id": session_id},
            timeout=90.0,
        )
        text = resp.text
        h = resp.headers
        intent = h.get("x-sage-intent", "")
        path_raw = h.get("x-sage-node-path", "[]")
        skill_id = h.get("x-sage-skill-id", "")
        word_count = len(text.split())
        try:
            path = json.loads(path_raw)
        except Exception:
            path = []
        return {
            "label": label,
            "query": query,
            "status": resp.status_code,
            "text": text,
            "word_count": word_count,
            "intent": intent,
            "path": path,
            "skill_id": skill_id,
            "error": None,
        }
    except Exception as e:
        return {
            "label": label,
            "query": query,
            "status": None,
            "text": "",
            "word_count": 0,
            "intent": "",
            "path": [],
            "skill_id": "",
            "error": str(e),
        }


def main():
    # Check environment variable first for explicit port
    port = None
    env_port = os.environ.get("QA_PORT")
    if env_port:
        try:
            p = int(env_port)
            resp = httpx.get(f"http://localhost:{p}/health/ready", timeout=3.0)
            if resp.status_code == 200:
                port = p
        except Exception:
            pass
    if port is None:
        port = find_server_port()
    if port is None:
        print("ERROR: No server found on ports 8000-8003")
        sys.exit(1)
    print(f"Using server on port {port}")

    queries = [
        ("EN_Q1", "What is self-compassion?"),
        ("EN_Q2", "How do I practice self-compassion?"),
        ("EN_Q3", "Why is self-compassion important?"),
        ("AR_Q1", "ما هي الرحمة الذاتية؟"),
        ("AR_Q2", "كيف أمارس الرحمة مع نفسي؟"),
        ("AR_Q3", "لماذا الرحمة الذاتية مهمة؟"),
    ]

    results = []
    for label, query in queries:
        print(f"\n--- {label}: {query[:60]} ---")
        # Small delay between requests to avoid overloading
        time.sleep(1)
        result = run_query(port, query, label)
        results.append(result)
        print(f"Status: {result['status']}")
        print(f"Intent: {result['intent']}")
        print(f"Path: {result['path']}")
        print(f"Words: {result['word_count']}")
        print(f"Text preview: {result['text'][:300]}")
        if result['error']:
            print(f"Error: {result['error']}")

    # Save results
    with open("/tmp/qa_results_self_compassion.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\nResults saved to /tmp/qa_results_self_compassion.json")
    return results


if __name__ == "__main__":
    main()
