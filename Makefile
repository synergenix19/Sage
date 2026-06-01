PYTHON := .venv/bin/python

# Run the full test suite under the project venv.
# conftest.py will exit immediately with a clear error if the wrong
# interpreter is used (asyncpg guard).
test:
	$(PYTHON) -m pytest tests/ $(PYTEST_ARGS)

# Slow tests require live LLM credentials.
test-slow:
	$(PYTHON) -m pytest tests/ -m slow $(PYTEST_ARGS)

# Integration tests require live Supabase credentials.
test-integration:
	$(PYTHON) -m pytest tests/ -m integration $(PYTEST_ARGS)
