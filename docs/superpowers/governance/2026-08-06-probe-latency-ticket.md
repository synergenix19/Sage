# Ticket: window-2 probe HTTP timeouts — RESOLVED to harness artifact, with one standing rider (2026-08-06)

**Finding:** two grief window-2 probe turns lost their HTTP bodies to ~16-minute client-side timeouts
while the audit rows recorded correct served dispositions.

**Data check (this closes the "probably"):** `session_audit.latency_ms` over the last 7 days of real
turns (n=39): p50 4.4s, p95 6.9s, p99/max 8.8s — **zero turns over 60s server-side, on any day.** The
serving path cannot reach the observed order; the hang was the probe client's HTTP transport (curl
connection through the tunnel), not turn processing. A real user's crisis-card turn is bounded by the
measured graph latency, not by this incident.

**Standing rider (pre-existing, re-confirmed by the same data):** graph-side p95 6.9s still exceeds the
<3s p95 KPI — this is the known latency-audit item (p50 17s full-turn incl. outside-graph span), not new.
**Owner: PO/infra (latency audit workstream). Check: none further on the 16-min incident; KPI item rides
its existing audit.**
