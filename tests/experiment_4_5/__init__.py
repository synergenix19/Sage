"""Experiment 4.5 — RAG Retrieval Accuracy & Grounding Test Harness.

Covers:
  - test_retrieval_accuracy.py  : PostgresKnowledgeRepository.retrieve() contract
  - test_grounding_prompt.py    : compose_prompt() grounding layer (L4 + knowledge)
  - test_audit_metadata.py      : output_gate knowledge fields in audit row

Node under test:
  knowledge_retrieve_node (Node 6) — info_request RAG path
  knowledge_lookup tool          — freeflow mid-protocol tool path
  compose_prompt                 — L4 knowledge block
  output_gate_node               — knowledge_passage_ids in audit
"""
