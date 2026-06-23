PYTHON := .venv/bin/python

# Run the functional test suite. Governance, integration, and slow tests are excluded.
# This must stay green. A red here is a real regression, not governance burn-down.
test:
	$(PYTHON) -m pytest tests/ $(PYTEST_ARGS)

# Slow tests require live LLM credentials.
test-slow:
	$(PYTHON) -m pytest tests/ -m slow $(PYTEST_ARGS)

# Integration tests require live Supabase credentials.
test-integration:
	$(PYTHON) -m pytest tests/ -m integration $(PYTEST_ARGS)

# Phase-0 routing-eval harness (offline; no live path). Already runs inside `make test`
# (tests/ glob); this named lane runs it alone for fast iteration. It also carries the
# flag-off non-regression guard (test_wrong_skill_routing must hold 240/10 with
# SKILL_ROUTING_V2 off) once the live-path wiring lands — that guard is what makes the
# wiring's non-regression a standing build check, not a manual stash-control.
test-routing:
	$(PYTHON) -m pytest tests/routing_eval/ $(PYTEST_ARGS)

# Governance burn-down: approved_by sign-off tracking.
# Expected to fail (red) until clinical sign-off clears all 61 violations.
# Run separately so governance-red and regression-red are distinguishable signals.
# ENFORCEMENT STATUS: convention-based until CI stands up this lane as an automated gate.
# See tests/test_clinical_governance.py for the enforcement status note.
test-governance:
	$(PYTHON) -m pytest tests/ -m governance -v $(PYTEST_ARGS)
