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

# Governance burn-down: approved_by sign-off tracking.
# Expected to fail (red) until clinical sign-off clears all 61 violations.
# Run separately so governance-red and regression-red are distinguishable signals.
# ENFORCEMENT STATUS: convention-based until CI stands up this lane as an automated gate.
# See tests/test_clinical_governance.py for the enforcement status note.
test-governance:
	$(PYTHON) -m pytest tests/ -m governance -v $(PYTEST_ARGS)
