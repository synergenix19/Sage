"""Shared pytest configuration for the sage-poc test suite.

State construction is intentionally kept local to each test module so the full
21-field SageState schema is visible at the call site. This file holds only
pytest-level configuration and shared markers.

Test module responsibilities:
- test_nodes.py  — unit tests for individual nodes; uses local make_state()
- test_graph.py  — graph-level and Arabic crisis tests; uses local make_e2e_state()
- test_routing.py — parametrized routing branch tests; uses local make_full_state()
- test_language.py, test_skill_schema.py, test_state.py — standalone unit tests
"""
