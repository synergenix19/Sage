-- Tier 0 native-Arabic shadow measurement. Isolated restricted table (holds clinical
-- response text — shadow_arabic_text — same retention class as identity_substitution_audit's
-- original_response_text). Populated only when SAGE_NATIVE_ARABIC_SHADOW is on.
-- message_en + clinical_flags are stored so an OFFLINE gate-replay evaluates mirroring
-- rules on the REAL user message (Blocking #3), not on the shadow text itself.
-- tool_loop_iterations + shadow_timed_out support the zero-tool primary comparison and
-- timeout-censoring (Blocking #2). The served (shipped) Arabic arm is NOT stored here —
-- it is joined offline from the messages store by (session_id, turn_number).
-- Isolated from session_audit by design: shadow text never touches SageState or the
-- main audit row (containment boundary for the shadow-measure feature).
CREATE TABLE IF NOT EXISTS shadow_register_eval (
  id                       bigint generated always as identity primary key,
  session_id               text    not null,
  turn_number              integer not null,
  message_en               text,
  clinical_flags           text[],
  shadow_arabic_text       text,
  shadow_prompt_hash       text,
  shadow_exemplar_version  text,
  generation_language      text,
  shadow_gen_latency_ms    integer,
  tool_loop_iterations     integer,
  shadow_timed_out         boolean default false,
  created_at               timestamptz default now(),
  unique (session_id, turn_number)
);
