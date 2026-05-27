export type AuditRow = {
  id: string
  inserted_at: string
  session_id: string
  turn_number: number
  node_path: string[]
  primary_intent: string | null
  secondary_intent: string | null
  intent_confidence: number | null
  active_skill_id: string | null
  active_step_id: string | null
  skill_match_method: string | null
  knowledge_source: string | null
  knowledge_passage_ids: string[]
  knowledge_abstain: boolean | null
  crisis_state: string | null
  crisis_flags: string[]
  clinical_flags: string[]
  engagement: number | null
  emotional_intensity: number | null
  model_version: string | null
  latency_ms: number | null
}
