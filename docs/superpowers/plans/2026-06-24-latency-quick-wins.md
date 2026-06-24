# Latency Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Rev 2 (2026-06-24, post-review):** Reordered after measuring the checkpoint write amplification (see "Measured root cause" below). The headline fix is now LangGraph `durability="exit"` (Task 1), not pool sizing. Pool sizing reframed as a p95/tail fix. Region move keeps a genuine mixed-region canary. Measurement window parameterized to deploy time.

**Goal:** Cut user-felt response latency by attacking the *outside-the-graph* half of the latency (~8.5s of the ~17s p50), which measurement shows is dominated by per-turn checkpoint write amplification shipped cross-Pacific.

**Measured root cause (prod, 200 real-user threads):** The bulk of the outside-graph time is LangGraph checkpoint persistence. LangGraph 1.1.10 defaults `durability="async"`, writing a checkpoint at **every super-step**. Prod reality: **7.48 checkpoint rows/turn + ~105 `checkpoint_writes` rows/turn** = ~110+ INSERT-class round-trips per turn, each crossing **SFO→Mumbai (~220ms RTT)** on a **4-connection pool**. Blobs are small (conversation_history 0.3→4.9KB over 38 turns), so **round-trip COUNT, not blob size, is the driver.** Three independent levers, in impact order: (1) cut the write COUNT (`durability="exit"` → ~1 write/turn), (2) cut per-round-trip RTT (co-locate Railway with Supabase, ~220ms→~65ms), (3) cut contention (size the pools — p95/tail).

**Architecture:** (1) Set `durability="exit"` on the per-turn `ainvoke` so checkpoints persist once at graph exit instead of per super-step — cross-turn memory is preserved (the exit checkpoint is still written), only intra-turn resumability is dropped (a chat turn does not need it; Sage uses no mid-graph interrupts). (2) Move Railway's 3 replicas from `sfo` to Railway's region closest to Mumbai (Singapore) via a mixed-region canary. (3) Size the checkpointer psycopg pool (default 4) and verify the session-mode asyncpg pool — relieves remaining contention under load.

**Tech Stack:** FastAPI + LangGraph (`AsyncPostgresSaver`), psycopg `AsyncConnectionPool`, asyncpg, Supabase Postgres (transaction pooler on `:6543`), Railway (deploy/region), pytest.

## Global Constraints (verified facts — do not re-derive)
- Backend repo: `sage-poc`. Canonical branch context for these edits: `feat/2026-06-24-conversational-style` (tip `e5edd91`). Create a feature branch off it.
- Prod measurement source: Supabase project `tcekehffneiqcdyhzobi` (Sage_POC). Get `DATABASE_URL` via `railway variables --json` (project `sage-api`, env `production`). Query read-only with `sage-poc/.venv/bin/python` + `psycopg`. Tables: `messages.latency_ms` (end-to-end), `session_audit.latency_ms` (graph-only), joined on `session_id + turn_number`. Exclude synthetic sessions by UUID-shape (`session_id ~ '^[0-9a-f]{8}-...'`).
- Prod env already set: `AINVOKE_TIMEOUT_SECONDS=55`, `CHECKPOINT_DATABASE_URL=…ap-south-1.pooler.supabase.com:6543` (transaction mode → raising client pool size is safe; `prepare_threshold=None` already set), `DATABASE_URL=…ap-south-1.pooler.supabase.com:5432` (session mode).
- Railway prod: project `sage-api`, service `sage-api`, env `production`, currently `multiRegionConfig: {sfo: {numReplicas: 3}}`.
- Baseline to beat (matched real-user, 06-23→24): end-to-end p50 ≈ 17.1s; graph p50 ≈ 7.4s; **per-turn outside-graph DELTA p50 ≈ 8,474ms**. The DELTA is the number these changes must move.
- Do NOT change clinical content, prompts, routing, or model selection in this plan — infra only, no clinical sign-off required.
- Frequent commits. One reviewable deliverable per task.

---

## File Structure

- `sage-poc/server.py` — Task 1: pass `durability="exit"` to the per-turn `graph.ainvoke` (line 322 region). Task 3: extract `_build_saver_pool(checkpoint_url)` with explicit `min_size`/`max_size`.
- `sage-poc/src/sage_poc/config.py` — Task 3: add `CHECKPOINT_POOL_MIN_SIZE` / `CHECKPOINT_POOL_MAX_SIZE` env-backed constants (mirrors existing `DB_POOL_MAX_SIZE` pattern).
- `sage-poc/tests/test_server.py` — Task 1: assert `ainvoke` is called with `durability="exit"`. Task 3: assert the saver pool is built with the configured sizes.
- Railway service config (no repo file) — Task 2 region change, via dashboard; verified via `railway status --json`.
- `scratchpad/latency_measure.py` + `scratchpad/ckpt_measure.py` (throwaway, not committed) — baseline/after measurement queries (the second counts checkpoint writes/turn).

---

## Task 0: Capture the baseline (measurement harness)

**Files:**
- Create (throwaway, do NOT commit): `scratchpad/latency_measure.py`

**Interfaces:**
- Produces: a repeatable command `python latency_measure.py <SINCE_ISO>` that prints `{e2e_p50/p95, graph_p50/p95, delta_p50/p95, n}` for real-user turns since a timestamp. **Each AFTER run MUST pass the deploy timestamp** so pre-change traffic does not dilute the result.

- [ ] **Step 1: Write the measurement script (window is a required arg)**

```python
# scratchpad/latency_measure.py  — READ ONLY.
# Usage: python latency_measure.py '2026-06-24T18:00:00Z'   (the change's deploy time)
#        python latency_measure.py                          (defaults to last 2 days, for BEFORE only)
import sys, subprocess, json, psycopg

def prod_url() -> str:
    out = subprocess.run(["railway", "variables", "--json"], capture_output=True, text=True).stdout
    return json.loads(out)["DATABASE_URL"]

since = sys.argv[1] if len(sys.argv) > 1 else None
# CRITICAL: AFTER a deploy, pass the deploy timestamp. Re-using a fixed "last 2 days"
# window mixes pre-change traffic into the AFTER sample and shrinks the apparent effect.
where_time = "created_at >= %(since)s" if since else "created_at >= now() - interval '2 days'"
params = {"since": since} if since else {}

UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
SQL = f"""
WITH m AS (
  SELECT session_id, turn_number, latency_ms AS e2e
  FROM messages
  WHERE role IN ('ai','crisis') AND latency_ms IS NOT NULL
    AND {where_time} AND session_id::text ~ '{UUID}'
), g AS (
  SELECT session_id, turn_number, latency_ms AS graph
  FROM session_audit
  WHERE latency_ms IS NOT NULL
    AND {where_time} AND session_id::text ~ '{UUID}'
)
SELECT m.e2e, g.graph FROM m JOIN g USING (session_id, turn_number);
"""

def pct(xs, p):
    xs = sorted(xs); k = max(0, min(len(xs)-1, int(round((p/100)*(len(xs)-1)))))
    return xs[k] if xs else None

with psycopg.connect(prod_url()) as conn, conn.cursor() as cur:
    cur.execute(SQL, params)
    rows = cur.fetchall()
e2e=[r[0] for r in rows]; graph=[r[1] for r in rows]; delta=[r[0]-r[1] for r in rows]
print(f"window since={since or 'last 2 days'}  n={len(rows)}")
print(f"e2e   p50={pct(e2e,50)}  p95={pct(e2e,95)}")
print(f"graph p50={pct(graph,50)}  p95={pct(graph,95)}")
print(f"DELTA p50={pct(delta,50)}  p95={pct(delta,95)}  (outside-graph; target: shrink this)")
```

- [ ] **Step 2: Run it and record the baseline**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python scratchpad/latency_measure.py`
Expected: `n` ~240, e2e p50 ≈ 16–17k ms, graph p50 ≈ 7–7.5k ms, **DELTA p50 ≈ 8,000–8,500 ms**. Paste into the PR as "BEFORE". For every AFTER run, pass the deploy timestamp and let traffic accumulate ≥30–60 min so n is meaningful.

No commit (throwaway script).

---

> **Recommended ship order: Task 1 → Task 3 → Task 2.** Durability first (biggest lever, smallest blast radius, one line, instantly reversible), then region, then pool. All three are independent and individually shippable.

## Task 1: Reduce checkpoint write amplification — `durability="exit"` (headline fix)

**Why this is the headline:** prod shows ~7.48 checkpoint rows/turn + ~105 `checkpoint_writes` rows/turn (one set per super-step, because LangGraph 1.1.10 defaults `durability="async"`). `durability="exit"` persists a single checkpoint at graph exit instead — a ~7× cut in checkpoint round-trips, each of which is currently a cross-Pacific INSERT. Cross-turn memory is preserved (the exit checkpoint is still written and read by the next turn's `aget`); only intra-turn resumability is dropped, which a single chat turn does not need (Sage issues one `ainvoke` per turn and uses no mid-graph interrupts).

**Pre-ship verification (completed 2026-06-24, code-confirmed):**
- *No interrupts.* No `interrupt()` / `NodeInterrupt` / `Command(resume)` / `interrupt_before|after` anywhere in `src/` — the graph never pauses for human input mid-turn (crisis/escalation resolves within one turn → END). `durability="exit"` breaks no resume path.
- *PDPL audit is independent of the checkpoint.* `session_audit` is written by `write_session_audit` (`audit.py:157`) via a Supabase REST POST to `/rest/v1/session_audit` (`audit.py:140`), fire-and-forget from `output_gate` (`output_gate.py:595`) — a separate write path, not a checkpoint byproduct. `durability="exit"` cannot drop audit rows; audit completeness is unchanged.
- *History source.* `_build_state` (`server_helpers.py:135`) passes only `req.messages[-1]`; `conversation_history` is reconstructed from the **checkpoint**, mutated only at `output_gate` (terminal node), so a turn failing before `output_gate` appends nothing under EITHER mode — exit does not regress it. *Separate pre-existing issue, NOT caused by this change: an unretried failed turn drops its message from future context (history comes only from the checkpoint, request supplies only the latest message) — roadmap, not this PR.*
- *clinical_flags / active_issues retention on a crashed turn — EMPIRICALLY VERIFIED NEUTRAL (`tests/test_durability_exit.py`).* Initial hypothesis was that a flag detected on a turn crashing before `output_gate` would be lost under exit. The test disproved it: a value set at node 1 of a crashing turn is **retained under exit too**, because LangGraph still records the completed node's pending write (`get_state` shows it; `safety_check` reads exactly this as carry-forward). So exit is neutral for clinical-flag retention, not just the happy path. Measured write collapse: a 3-node success run drops from 9 writes (async) → 1 (exit). Residual: a true pod death mid-turn loses intra-turn state — the same tiny window `async` has between a node finishing and its flush; not a new clinical exposure.

**Files:**
- Modify: `sage-poc/server.py` (the `graph.ainvoke(...)` call, ~line 322-326)
- Test: `sage-poc/tests/test_server.py`

**Interfaces:**
- Produces: per-turn `ainvoke` invoked with `durability="exit"`.

- [ ] **Step 1: Locate the existing multi-turn / checkpoint-resume test to use as the regression guard**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && grep -rln "thread_id\|conversation_history\|multi.turn\|second turn\|aget\|checkpoint" tests/ | head`
Purpose: identify the test(s) that prove cross-turn state persists. These MUST still pass after the change (they prove `durability="exit"` did not break conversation memory). Note their paths.

- [ ] **Step 2: Write the failing test (ainvoke receives `durability="exit"`)**

In `tests/test_server.py`, mirror the existing graph-monkeypatch pattern used by the freeflow/skill response-path tests. Add:

```python
def test_chat_invokes_graph_with_durability_exit(monkeypatch):
    """The per-turn ainvoke must use durability='exit' to avoid per-super-step
    checkpoint write amplification (each write is a cross-region INSERT)."""
    import server
    from fastapi.testclient import TestClient

    captured = {}

    class _FakeGraph:
        checkpointer = None
        async def ainvoke(self, state, config=None, **kwargs):
            captured["kwargs"] = kwargs
            return {"response": "ok", "path": ["freeflow_respond"], "is_safe": True,
                    "turn_count": 1}
        # stale-skill pre-check calls graph.checkpointer.aget; make it a no-op
    class _FakeCk:
        async def aget(self, *a, **k): return None
    fg = _FakeGraph(); fg.checkpointer = _FakeCk()

    monkeypatch.setattr(server.app.state, "_graph", fg, raising=False)
    monkeypatch.setattr(server.app.state, "_db_pool", None, raising=False)
    # bypass readiness + api-key guards per the existing test helpers in this module
    server.app.dependency_overrides[server.require_ready] = lambda: None
    server.app.dependency_overrides[server.require_api_key] = lambda: None
    try:
        client = TestClient(server.app)
        r = client.post("/chat", json={"session_id": "t1",
              "messages": [{"role": "user", "content": "hi"}]})
        assert r.status_code == 200
    finally:
        server.app.dependency_overrides.clear()

    assert captured["kwargs"].get("durability") == "exit"
```

(If this module already has a helper that builds the app/client with guards bypassed, use it instead of the inline override — match the file's established pattern.)

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_server.py::test_chat_invokes_graph_with_durability_exit -v`
Expected: FAIL — `captured["kwargs"].get("durability")` is `None` (the call passes no `durability`).

- [ ] **Step 4: Implement — add `durability="exit"` to the ainvoke call**

In `server.py`, change the invoke (currently):

```python
        result = await asyncio.wait_for(
            graph.ainvoke(
                state,
                config={"configurable": {"thread_id": req.session_id}},
            ),
            timeout=AINVOKE_TIMEOUT_SECONDS,
        )
```

to:

```python
        result = await asyncio.wait_for(
            graph.ainvoke(
                state,
                config={"configurable": {"thread_id": req.session_id}},
                # Persist one checkpoint at graph exit, not per super-step. Prod showed
                # ~7.5 checkpoint writes/turn (each a cross-region INSERT). Cross-turn
                # memory is preserved (exit checkpoint still written); only intra-turn
                # resumability is dropped, which a single chat turn does not use.
                durability="exit",
            ),
            timeout=AINVOKE_TIMEOUT_SECONDS,
        )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_server.py::test_chat_invokes_graph_with_durability_exit -v`
Expected: PASS.

- [ ] **Step 6: Run the durability + regression guard (BUILT — `tests/test_durability_exit.py`)**

The guard exists and is green: it pins (1) write collapse (3-node turn: 9 writes async → 1 exit), (2) flag retention on a crashed turn under both modes, (3) flag preservation across a successful turn under exit. Plus the kwarg test in `test_server.py`.

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_durability_exit.py tests/test_server.py -m "not slow" -q`
Expected: all PASS (last run: 30 passed). If `test_flag_retained_on_crashed_turn[exit]` ever fails, STOP: a LangGraph upgrade changed pending-write behaviour and exit would now drop crashed-turn state.

- [ ] **Step 7: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "perf(checkpointer): durability=exit — one checkpoint write/turn, not per super-step

Prod measured ~7.5 checkpoint + ~105 checkpoint_writes rows per turn (LangGraph
default durability=async writes per super-step), each a cross-region INSERT.
durability=exit persists once at graph exit. Cross-turn memory preserved; only
intra-turn resumability dropped (unused — one ainvoke per chat turn, no interrupts).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 8: Deploy and measure (windowed)**

Deploy to Railway production. After healthy, record the deploy timestamp `T`. Let ≥30–60 min of real traffic accumulate, then:
Run: `.venv/bin/python scratchpad/latency_measure.py '<T ISO8601>'` and re-run `scratchpad/ckpt_measure.py`.
Expected: `ckpts_per_turn` drops toward ~1; DELTA p50 drops materially (this is the change expected to move p50 most). Record as "AFTER Task 1".

---

## Task 2: Size the connection pools (p95 / tail fix — NOT the p50 lever)

**Reframe:** pool sizing relieves *contention*, which shows up at p95/p99 under concurrency, not at the p50. Ship it for tail stability, not as the headline. Two pools to address — sizing only the checkpoint pool leaves the session-mode pool as a second serialization point.

**Files:**
- Modify: `sage-poc/src/sage_poc/config.py` (after line 42)
- Modify: `sage-poc/server.py:204-208` (extract `_build_saver_pool`, use config sizes)
- Test: `sage-poc/tests/test_server.py`

**Interfaces:**
- Produces: `config.CHECKPOINT_POOL_MIN_SIZE: int`, `config.CHECKPOINT_POOL_MAX_SIZE: int`; `server._build_saver_pool(checkpoint_url: str) -> AsyncConnectionPool`.

- [ ] **Step 1: Pre-flight — confirm Supabase headroom for BOTH pools**

Two pools hit Supabase: the **checkpointer** (psycopg, transaction mode `:6543`, currently default 4) and the **asyncpg** memory/profile/audit pool (session mode `:5432`, `DB_POOL_MAX_SIZE=20`). Session-mode connections hold a backend connection for their lifetime, so the asyncpg pool is the one that can exhaust `max_connections`: `3 replicas × 20 = 60` backend connections today. Confirm headroom before raising either.

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -c "import subprocess,json,psycopg; u=json.loads(subprocess.run(['railway','variables','--json'],capture_output=True,text=True).stdout)['DATABASE_URL']; c=psycopg.connect(u); cur=c.cursor(); cur.execute('show max_connections'); print('max_connections',cur.fetchone()[0]); cur.execute(\"select count(*) from pg_stat_activity\"); print('current_connections',cur.fetchone()[0])"`
Expected: prints `max_connections` and current usage. Sanity budget: `3 × CHECKPOINT_POOL_MAX_SIZE` (10 → 30, but transaction-mode-multiplexed so cheap on backend) **plus** `3 × DB_POOL_MAX_SIZE` (60, session-mode, real backend connections) must stay under `max_connections`. If headroom is tight: keep the asyncpg pool where it is (60 already), and rely on transaction-mode multiplexing for the checkpoint side; or raise the Supabase pooler "Pool Size" (Database → Connection Pooling). **Decision to record in the PR:** is the asyncpg pool a p95 bottleneck (check `pg_stat_activity` for waits during peak), or is 20/replica sufficient? Only resize it if the data says so — do not raise blindly into a connection-limit wall.

- [ ] **Step 2: Add config constants**

In `config.py`, immediately after line 42 (`HTTP_MAX_KEEPALIVE = …`), add:

```python
# Checkpointer (LangGraph AsyncPostgresSaver) psycopg pool sizing. The library default is
# min=max=4, which serialized per-turn checkpoint read+write under the 58-user load (the hot
# pool — touched every turn). Connects via CHECKPOINT_DATABASE_URL (Supabase transaction mode,
# :6543) so client connections multiplex over fewer backend connections — raising max_size is
# safe. NOTE: effective load on the pooler = numReplicas × CHECKPOINT_POOL_MAX_SIZE.
CHECKPOINT_POOL_MIN_SIZE = int(os.getenv("SAGE_CHECKPOINT_POOL_MIN_SIZE", "2"))
CHECKPOINT_POOL_MAX_SIZE = int(os.getenv("SAGE_CHECKPOINT_POOL_MAX_SIZE", "10"))
```

- [ ] **Step 3: Write the failing test**

In `tests/test_server.py`, add:

```python
def test_build_saver_pool_uses_configured_sizes(monkeypatch):
    import server
    captured = {}

    class _FakePool:
        def __init__(self, conninfo=None, open=None, min_size=None, max_size=None, kwargs=None):
            captured.update(
                conninfo=conninfo, open=open, min_size=min_size,
                max_size=max_size, kwargs=kwargs,
            )

    monkeypatch.setattr(server, "AsyncConnectionPool", _FakePool)
    monkeypatch.setattr(server.config, "CHECKPOINT_POOL_MIN_SIZE", 2, raising=False)
    monkeypatch.setattr(server.config, "CHECKPOINT_POOL_MAX_SIZE", 10, raising=False)

    server._build_saver_pool("postgresql://x@host:6543/db")

    assert captured["min_size"] == 2
    assert captured["max_size"] == 10
    assert captured["open"] is False
    assert captured["kwargs"] == {"prepare_threshold": None}
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_server.py::test_build_saver_pool_uses_configured_sizes -v`
Expected: FAIL with `AttributeError: module 'server' has no attribute '_build_saver_pool'` (or `config`).

- [ ] **Step 5: Implement — import config + extract the helper**

In `server.py`, ensure `config` is importable as an attribute (near the existing config imports add `from sage_poc import config` if not already present, so the test's `server.config` resolves). Then, above the `lifespan` function, add the helper:

```python
def _build_saver_pool(checkpoint_url: str) -> AsyncConnectionPool:
    # Explicit sizing: psycopg default is min=max=4. CHECKPOINT_DATABASE_URL is Supabase
    # transaction mode (:6543), so client conns multiplex over backend conns — sizing up
    # relieves per-turn checkpoint contention without exhausting backend connections.
    return AsyncConnectionPool(
        conninfo=checkpoint_url,
        open=False,
        min_size=config.CHECKPOINT_POOL_MIN_SIZE,
        max_size=config.CHECKPOINT_POOL_MAX_SIZE,
        kwargs={"prepare_threshold": None},
    )
```

Then replace the inline construction at `server.py:204-208`:

```python
            saver_pool = _build_saver_pool(checkpoint_url)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_server.py::test_build_saver_pool_uses_configured_sizes -v`
Expected: PASS.

- [ ] **Step 7: Run the broader server test module (no regressions)**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_server.py -q`
Expected: all pass (or only the known pre-existing module-scope fixture flakes documented in the test-server-fixture-contamination audit — re-run any flaky one in isolation to confirm).

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/config.py server.py tests/test_server.py
git commit -m "perf(checkpointer): size saver_pool (env-configurable) instead of default 4

The LangGraph AsyncPostgresSaver psycopg pool used the library default
min=max=4, serializing per-turn checkpoint read+write under load. Extract
_build_saver_pool and size it from SAGE_CHECKPOINT_POOL_MIN/MAX_SIZE
(default 2/10). Safe under Supabase transaction pooler (:6543).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 9: Deploy and verify in prod**

Deploy the branch to Railway production. After deploy is healthy (`/health/ready` returns 200), record the deploy timestamp `T`, wait ≥30–60 min of real traffic, then re-run `scratchpad/latency_measure.py '<T>'`.
Expected: **p95 DELTA improves** (contention relief shows at the tail, not p50). Record as "AFTER pool". If the env override is needed, set it without redeploying code: `railway variables --set SAGE_CHECKPOINT_POOL_MAX_SIZE=15` then `railway redeploy`.

---

## Task 3: Co-locate Railway compute with the Supabase region (genuine mixed-region canary)

> **POC-disposable — NOT a production topology decision.** Singapore is chosen only to cut POC latency against the *existing* Mumbai Supabase. It does **not** set production architecture: per v7, production clinical inference is self-hosted in **Azure UAE North** for PDPL / UAE Health Data Law residency, and Singapore/Mumbai would not be compliant for clinical data. The system prompt waives sovereignty for the POC, so this is fine now — but "we chose Singapore" must never be read as an architecture decision. By contrast, **Task 1 (durability) and Task 2 (pool) are portable** — correct regardless of where the graph runs — and carry forward to the sovereign UAE North build.

**Files:**
- Railway service config (no repo file). Change is verified via `railway status --json`.

**Interfaces:**
- Produces: production replicas running in Railway's region closest to Supabase `ap-south-1` (Mumbai), replacing `sfo`, rolled out via a mixed-region canary.

- [ ] **Step 1: Confirm the cross-region gap and pick the target region**

Run: `railway status --json | /Users/knowledgebase/Documents/Sage/sage-poc/.venv/bin/python -c "import sys,json,re; s=json.dumps(json.load(sys.stdin)); print('multiRegion:', re.findall(r'multiRegionConfig[^}]*}', s))"`
Expected: shows `{'sfo': {'numReplicas': 3}}` (US-West). Supabase is `ap-south-1` (Mumbai). Target = Railway's region nearest Mumbai. In the Railway dashboard (Service `sage-api` → Settings → Regions), list available regions and pick the closest to Mumbai — expected **Southeast Asia (Singapore)**; if an India/Middle-East region is offered, prefer it. Record the chosen region code.

Rationale to capture in the PR: SFO→Mumbai ≈ 220ms RTT; Singapore→Mumbai ≈ 60–70ms. Even after Task 1 cuts checkpoint writes to ~1/turn, the per-turn reads (checkpoint `aget`, profile, prior-context) plus that exit write still cross-region; co-locating cuts each ~3.4×. Data residency is unchanged — Supabase stays in Mumbai; only compute moves (and moves *closer* to the UAE user base than SFO).

- [ ] **Step 2: Genuine mixed-region canary — `{sfo: 1, singapore: 2}`**

`multiRegionConfig` supports mixed regions, so run a real canary rather than an all-or-nothing cutover. In the Railway dashboard (Service `sage-api` → Settings → Regions / replicas), set the chosen region to 2 replicas and keep `sfo` at 1 — target `{sfo: 1, <singapore>: 2}`, total still 3. (Region is a service setting; the CLI has no `region set` command as of v4.44 — use the dashboard.) This triggers a redeploy of the moved replicas.

Compare the two regions directly: because both serve live traffic simultaneously, you can attribute latency to region. If per-instance metrics are available, compare; otherwise rely on the windowed before/after in Step 5 plus error-rate watch. Proceed to full cutover only if the in-region replicas are healthy and not worse.

Note on warmup: each new-region instance runs BGE-M3 + classifier warmup on boot; `/health/ready` stays 503 until warm (`server.py _warmup_task`), so Railway won't route traffic to a cold instance. Confirm `/health/ready` is 200 in the new region before widening.

- [ ] **Step 2b: Full cutover**

Once the canary is healthy, set the chosen region to 3 replicas and `sfo` to 0 → `{<singapore>: 3}`.

- [ ] **Step 3: Verify the region actually changed**

Run: `railway status --json | /Users/knowledgebase/Documents/Sage/sage-poc/.venv/bin/python -c "import sys,json,re; s=json.dumps(json.load(sys.stdin)); print(re.findall(r'multiRegionConfig[^}]*}', s))"`
Expected: the region key is now the chosen region (e.g. `asia-southeast1`/`singapore`), `numReplicas: 3`. Also confirm health: `curl -s https://sage-api-production-3328.up.railway.app/health/ready` → 200.

- [ ] **Step 4: Quick in-region RTT sanity check (optional but recommended)**

From a one-off run inside the service (Railway shell or a temporary `/health` probe), or by reasoning from the DB query latency: re-run a single prod checkpoint read timing if instrumented. Minimum: confirm the app is healthy and serving in the new region.

- [ ] **Step 5: Measure the effect (windowed)**

Record the full-cutover timestamp `T`. After ≥30–60 min of real traffic, run `scratchpad/latency_measure.py '<T>'`.
Expected: **DELTA p50 drops** (cuts per-round-trip RTT on the remaining reads + exit write). Record as "AFTER region". Compare against BEFORE, AFTER-Task-1 (durability), and AFTER-pool.

- [ ] **Step 6: Rollback criterion**

If end-to-end p50 does NOT improve (or regresses), or error rate rises: revert the region to `sfo` in the dashboard, redeploy, confirm `/health/ready` 200. Fully reversible, no data migration.

---

## Endgame (not a quick win — flagged for the roadmap)

- **Co-locate Supabase too.** Railway has no Mumbai region, so Railway-Singapore ↔ Supabase-Mumbai still pays ~65ms/round-trip. The clean endgame is both compute and DB in one region (<5ms). At POC there's no sovereignty blocker, BUT this prod Supabase project (`tcekehffneiqcdyhzobi`) holds the live chat history + audit data currently being used for these RCAs — "disposable" has a real cost here. Treat as a planned migration (recreate in the chosen region, migrate or accept loss), not a quick win.
- **Real token streaming is the perceived-latency headline.** Even after all three tasks land, graph compute stays ~7.4s and the user still watches a spinner for it, because the response is buffered to populate the `X-Sage-*` headers (`server.py:364`). Moving those diagnostics off the header channel so tokens stream is the single biggest *felt* win — but it's a frontend+backend change, out of scope for this infra-only pass. Tracked in `Sage_Latency_RCA_2026-06-24.md` Tier 2.

---

## Task 4: Decide and document

- [ ] **Step 1: Compile the before/after table**

Assemble BEFORE / AFTER-durability / AFTER-region / AFTER-pool rows of `{n, e2e_p50, e2e_p95, graph_p50, DELTA_p50, DELTA_p95, ckpts_per_turn}` from the recorded windowed runs (each AFTER row uses its own deploy timestamp as the window start). Confirm graph p50 is unchanged (none of these touch graph compute), `ckpts_per_turn` fell to ~1 after Task 1, and DELTA p50 shrank after Tasks 1 and 3.

- [ ] **Step 2: Update the audit doc**

Append the measured results to `Sage_Latency_RCA_2026-06-24.md` §7, closing the "internal split of the ~8.5s" open item with the now-measured attribution (checkpoint write amplification vs cross-region RTT vs contention). Commit.

```bash
git add Sage_Latency_RCA_2026-06-24.md
git commit -m "docs(latency): record before/after for durability + region + pool quick wins

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:** Headline fix (durability=exit) = Task 1. Pool sizing (p95) = Task 2. Region co-location = Task 3. Baseline + windowed verification = Tasks 0 and 4. The post-review reframe (write amplification is the whale; pool is tail-only; measurement window must be deploy-anchored; genuine mixed-region canary; asyncpg pool also checked; Supabase co-location + streaming flagged as endgame) is all incorporated. Covered.

**Placeholder scan:** All steps carry exact files, commands, code, and expected output. Deliberately deferred-and-*measured* (not assumed): the Railway region code (read live from the dashboard), the Supabase connection headroom (measured in Task 2 Step 1), and the cross-turn regression test paths (located in Task 1 Step 1).

**Type consistency:** `CHECKPOINT_POOL_MIN_SIZE` / `CHECKPOINT_POOL_MAX_SIZE` defined in config (Task 2), consumed in `_build_saver_pool` and asserted in its test under the same names. `durability="exit"` asserted in the Task 1 test matches the kwarg added to `graph.ainvoke`. `latency_measure.py <SINCE_ISO>` signature is consistent across all AFTER steps.

**Risk notes:** Task 1 is one line, reversible by removing the kwarg; the cross-turn regression guard (Step 6) is the gate that proves conversation memory survives. Task 2 is reversible via env var. Task 3 uses a mixed-region canary and is reversible with no data migration. None touch clinical content, prompts, routing, or models — no clinical sign-off. Connection budget accounts for both the transaction-mode checkpoint pool and the session-mode asyncpg pool (`3 × 20 = 60`) against `max_connections`.

**Out of scope (later passes, in `Sage_Latency_RCA_2026-06-24.md`):** real token streaming (the perceived-latency headline; frontend+backend), Supabase region co-location (a migration), eliminating the redundant pre-`ainvoke` checkpoint read, and gating `knowledge_lookup` by intent.
