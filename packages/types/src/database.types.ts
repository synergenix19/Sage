export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      chat_sessions: {
        Row: {
          created_at: string
          id: string
          name: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          name?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "chat_sessions_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      checkpoint_blobs: {
        Row: {
          blob: string | null
          channel: string
          checkpoint_ns: string
          thread_id: string
          type: string
          version: string
        }
        Insert: {
          blob?: string | null
          channel: string
          checkpoint_ns?: string
          thread_id: string
          type: string
          version: string
        }
        Update: {
          blob?: string | null
          channel?: string
          checkpoint_ns?: string
          thread_id?: string
          type?: string
          version?: string
        }
        Relationships: []
      }
      checkpoint_migrations: {
        Row: {
          v: number
        }
        Insert: {
          v: number
        }
        Update: {
          v?: number
        }
        Relationships: []
      }
      checkpoint_writes: {
        Row: {
          blob: string
          channel: string
          checkpoint_id: string
          checkpoint_ns: string
          idx: number
          task_id: string
          task_path: string
          thread_id: string
          type: string | null
        }
        Insert: {
          blob: string
          channel: string
          checkpoint_id: string
          checkpoint_ns?: string
          idx: number
          task_id: string
          task_path?: string
          thread_id: string
          type?: string | null
        }
        Update: {
          blob?: string
          channel?: string
          checkpoint_id?: string
          checkpoint_ns?: string
          idx?: number
          task_id?: string
          task_path?: string
          thread_id?: string
          type?: string | null
        }
        Relationships: []
      }
      checkpoints: {
        Row: {
          checkpoint: Json
          checkpoint_id: string
          checkpoint_ns: string
          metadata: Json
          parent_checkpoint_id: string | null
          thread_id: string
          type: string | null
        }
        Insert: {
          checkpoint: Json
          checkpoint_id: string
          checkpoint_ns?: string
          metadata?: Json
          parent_checkpoint_id?: string | null
          thread_id: string
          type?: string | null
        }
        Update: {
          checkpoint?: Json
          checkpoint_id?: string
          checkpoint_ns?: string
          metadata?: Json
          parent_checkpoint_id?: string | null
          thread_id?: string
          type?: string | null
        }
        Relationships: []
      }
      clinician_review_queue: {
        Row: {
          created_at: string
          flags_timeline: Json | null
          id: string
          payload: Json | null
          reason: string
          reviewed_by: string | null
          session_id: string
          severity: string
          source: string
          status: string
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          flags_timeline?: Json | null
          id?: string
          payload?: Json | null
          reason: string
          reviewed_by?: string | null
          session_id: string
          severity?: string
          source?: string
          status?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          flags_timeline?: Json | null
          id?: string
          payload?: Json | null
          reason?: string
          reviewed_by?: string | null
          session_id?: string
          severity?: string
          source?: string
          status?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "clinician_review_queue_reviewed_by_fkey"
            columns: ["reviewed_by"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "clinician_review_queue_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: true
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "clinician_review_queue_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      knowledge_articles: {
        Row: {
          article_id: string
          chunk_embedding: string | null
          chunk_text: string
          chunk_tsv: unknown
          citation_metadata: Json | null
          created_at: string
          id: string
          is_crisis_content: boolean
          language: string
          parent_id: string | null
          source_title: string | null
          source_url: string | null
        }
        Insert: {
          article_id: string
          chunk_embedding?: string | null
          chunk_text: string
          chunk_tsv?: unknown
          citation_metadata?: Json | null
          created_at?: string
          id?: string
          is_crisis_content?: boolean
          language: string
          parent_id?: string | null
          source_title?: string | null
          source_url?: string | null
        }
        Update: {
          article_id?: string
          chunk_embedding?: string | null
          chunk_text?: string
          chunk_tsv?: unknown
          citation_metadata?: Json | null
          created_at?: string
          id?: string
          is_crisis_content?: boolean
          language?: string
          parent_id?: string | null
          source_title?: string | null
          source_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "knowledge_articles_parent_id_fkey"
            columns: ["parent_id"]
            isOneToOne: false
            referencedRelation: "knowledge_articles"
            referencedColumns: ["id"]
          },
        ]
      }
      message_feedback: {
        Row: {
          created_at: string
          id: string
          message_id: string
          user_id: string
          value: number
        }
        Insert: {
          created_at?: string
          id?: string
          message_id: string
          user_id: string
          value: number
        }
        Update: {
          created_at?: string
          id?: string
          message_id?: string
          user_id?: string
          value?: number
        }
        Relationships: [
          {
            foreignKeyName: "message_feedback_message_id_fkey"
            columns: ["message_id"]
            isOneToOne: false
            referencedRelation: "messages"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "message_feedback_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      messages: {
        Row: {
          clinical_flags: Json | null
          clinical_flags_detail: Json | null
          content: string
          created_at: string
          crisis_flags: Json | null
          emotional_intensity: number | null
          gate_path: string | null
          id: string
          intent: string | null
          intent_classification: string | null
          latency_ms: number | null
          model: string | null
          node_path: Json | null
          prompt_layers: Json | null
          role: string
          secondary_intent_classification: string | null
          semantic_score: number | null
          session_id: string
          skill_id: string | null
          sources: Json | null
          step_id: string | null
          token_usage: Json | null
          turn_number: number | null
        }
        Insert: {
          clinical_flags?: Json | null
          clinical_flags_detail?: Json | null
          content: string
          created_at?: string
          crisis_flags?: Json | null
          emotional_intensity?: number | null
          gate_path?: string | null
          id?: string
          intent?: string | null
          intent_classification?: string | null
          latency_ms?: number | null
          model?: string | null
          node_path?: Json | null
          prompt_layers?: Json | null
          role: string
          secondary_intent_classification?: string | null
          semantic_score?: number | null
          session_id: string
          skill_id?: string | null
          sources?: Json | null
          step_id?: string | null
          token_usage?: Json | null
          turn_number?: number | null
        }
        Update: {
          clinical_flags?: Json | null
          clinical_flags_detail?: Json | null
          content?: string
          created_at?: string
          crisis_flags?: Json | null
          emotional_intensity?: number | null
          gate_path?: string | null
          id?: string
          intent?: string | null
          intent_classification?: string | null
          latency_ms?: number | null
          model?: string | null
          node_path?: Json | null
          prompt_layers?: Json | null
          role?: string
          secondary_intent_classification?: string | null
          semantic_score?: number | null
          session_id?: string
          skill_id?: string | null
          sources?: Json | null
          step_id?: string | null
          token_usage?: Json | null
          turn_number?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "messages_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      mood_scores: {
        Row: {
          created_at: string
          id: string
          score: number
          session_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          score: number
          session_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          score?: number
          session_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "mood_scores_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "mood_scores_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      session_audit: {
        Row: {
          active_skill_id: string | null
          active_step_id: string | null
          classifier_context_hash: string | null
          classifier_model: string | null
          classifier_provider: string | null
          classifier_seed: number | null
          classifier_system_fingerprint: string | null
          clinical_flags: string[] | null
          crisis_flags: string[] | null
          crisis_state: string | null
          crisis_tier: string | null
          embedding_timeout: boolean | null
          emotional_intensity: number | null
          engagement: number | null
          fired_safety_routes: string[] | null
          freeflow_gen_ms: number | null
          gate_path: string | null
          id: string
          inserted_at: string
          intent_confidence: number | null
          knowledge_abstain: boolean
          knowledge_passage_ids: string[] | null
          knowledge_query_raw: string | null
          knowledge_query_searched: string | null
          knowledge_retrieval_purpose: string | null
          knowledge_source: string | null
          knowledge_top_similarity: number | null
          latency_ms: number | null
          medical_flags: string[] | null
          model_version: string | null
          node_path: string[]
          precedence_winner: string | null
          primary_intent: string | null
          re_escalation_within_monitoring: boolean | null
          s3_score: number | null
          safety_tier_active: string | null
          screen_answer_class: string | null
          screen_asked: boolean | null
          screen_branch_taken: string | null
          screen_shadow_action: string | null
          screen_shadow_answer_class: string | null
          screen_shadow_branch: string | null
          secondary_intent: string | null
          session_id: string
          skill_match_method: string | null
          tier_rule_id: string | null
          translate_out_ms: number | null
          turn_number: number
          user_id: string | null
        }
        Insert: {
          active_skill_id?: string | null
          active_step_id?: string | null
          classifier_context_hash?: string | null
          classifier_model?: string | null
          classifier_provider?: string | null
          classifier_seed?: number | null
          classifier_system_fingerprint?: string | null
          clinical_flags?: string[] | null
          crisis_flags?: string[] | null
          crisis_state?: string | null
          crisis_tier?: string | null
          embedding_timeout?: boolean | null
          emotional_intensity?: number | null
          engagement?: number | null
          fired_safety_routes?: string[] | null
          freeflow_gen_ms?: number | null
          gate_path?: string | null
          id?: string
          inserted_at?: string
          intent_confidence?: number | null
          knowledge_abstain?: boolean
          knowledge_passage_ids?: string[] | null
          knowledge_query_raw?: string | null
          knowledge_query_searched?: string | null
          knowledge_retrieval_purpose?: string | null
          knowledge_source?: string | null
          knowledge_top_similarity?: number | null
          latency_ms?: number | null
          medical_flags?: string[] | null
          model_version?: string | null
          node_path?: string[]
          precedence_winner?: string | null
          primary_intent?: string | null
          re_escalation_within_monitoring?: boolean | null
          s3_score?: number | null
          safety_tier_active?: string | null
          screen_answer_class?: string | null
          screen_asked?: boolean | null
          screen_branch_taken?: string | null
          screen_shadow_action?: string | null
          screen_shadow_answer_class?: string | null
          screen_shadow_branch?: string | null
          secondary_intent?: string | null
          session_id: string
          skill_match_method?: string | null
          tier_rule_id?: string | null
          translate_out_ms?: number | null
          turn_number: number
          user_id?: string | null
        }
        Update: {
          active_skill_id?: string | null
          active_step_id?: string | null
          classifier_context_hash?: string | null
          classifier_model?: string | null
          classifier_provider?: string | null
          classifier_seed?: number | null
          classifier_system_fingerprint?: string | null
          clinical_flags?: string[] | null
          crisis_flags?: string[] | null
          crisis_state?: string | null
          crisis_tier?: string | null
          embedding_timeout?: boolean | null
          emotional_intensity?: number | null
          engagement?: number | null
          fired_safety_routes?: string[] | null
          freeflow_gen_ms?: number | null
          gate_path?: string | null
          id?: string
          inserted_at?: string
          intent_confidence?: number | null
          knowledge_abstain?: boolean
          knowledge_passage_ids?: string[] | null
          knowledge_query_raw?: string | null
          knowledge_query_searched?: string | null
          knowledge_retrieval_purpose?: string | null
          knowledge_source?: string | null
          knowledge_top_similarity?: number | null
          latency_ms?: number | null
          medical_flags?: string[] | null
          model_version?: string | null
          node_path?: string[]
          precedence_winner?: string | null
          primary_intent?: string | null
          re_escalation_within_monitoring?: boolean | null
          s3_score?: number | null
          safety_tier_active?: string | null
          screen_answer_class?: string | null
          screen_asked?: boolean | null
          screen_branch_taken?: string | null
          screen_shadow_action?: string | null
          screen_shadow_answer_class?: string | null
          screen_shadow_branch?: string | null
          secondary_intent?: string | null
          session_id?: string
          skill_match_method?: string | null
          tier_rule_id?: string | null
          translate_out_ms?: number | null
          turn_number?: number
          user_id?: string | null
        }
        Relationships: []
      }
      session_insights: {
        Row: {
          content: string
          created_at: string
          id: string
          session_id: string
          topic_tag: string
          user_id: string
        }
        Insert: {
          content: string
          created_at?: string
          id?: string
          session_id: string
          topic_tag: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string
          id?: string
          session_id?: string
          topic_tag?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "session_insights_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "session_insights_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      session_summaries: {
        Row: {
          created_at: string
          embedding: string
          id: string
          mood_score: number | null
          safety_level: string
          session_id: string
          skills_used: string[]
          summary_text: string
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          embedding: string
          id?: string
          mood_score?: number | null
          safety_level?: string
          session_id: string
          skills_used?: string[]
          summary_text: string
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          embedding?: string
          id?: string
          mood_score?: number | null
          safety_level?: string
          session_id?: string
          skills_used?: string[]
          summary_text?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "session_summaries_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: true
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "session_summaries_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      shadow_register_eval: {
        Row: {
          clinical_flags: string[] | null
          created_at: string | null
          generation_language: string | null
          id: number
          message_en: string | null
          session_id: string
          shadow_arabic_text: string | null
          shadow_exemplar_version: string | null
          shadow_gen_latency_ms: number | null
          shadow_prompt_hash: string | null
          shadow_timed_out: boolean | null
          tool_loop_iterations: number | null
          turn_number: number
        }
        Insert: {
          clinical_flags?: string[] | null
          created_at?: string | null
          generation_language?: string | null
          id?: never
          message_en?: string | null
          session_id: string
          shadow_arabic_text?: string | null
          shadow_exemplar_version?: string | null
          shadow_gen_latency_ms?: number | null
          shadow_prompt_hash?: string | null
          shadow_timed_out?: boolean | null
          tool_loop_iterations?: number | null
          turn_number: number
        }
        Update: {
          clinical_flags?: string[] | null
          created_at?: string | null
          generation_language?: string | null
          id?: never
          message_en?: string | null
          session_id?: string
          shadow_arabic_text?: string | null
          shadow_exemplar_version?: string | null
          shadow_gen_latency_ms?: number | null
          shadow_prompt_hash?: string | null
          shadow_timed_out?: boolean | null
          tool_loop_iterations?: number | null
          turn_number?: number
        }
        Relationships: []
      }
      tenants: {
        Row: {
          created_at: string
          id: string
          name: string
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
        }
        Relationships: []
      }
      therapeutic_profile_history: {
        Row: {
          created_at: string
          extraction_source: string
          id: string
          session_id: string | null
          snapshot: Json
          user_id: string
        }
        Insert: {
          created_at?: string
          extraction_source: string
          id?: string
          session_id?: string | null
          snapshot: Json
          user_id: string
        }
        Update: {
          created_at?: string
          extraction_source?: string
          id?: string
          session_id?: string | null
          snapshot?: Json
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "therapeutic_profile_history_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_profiles: {
        Row: {
          age_range: string | null
          created_at: string
          id: string
          is_admin: boolean
          locale: string
          name: string | null
          onboarding_complete: boolean
          onboarding_step: number
          role: string | null
          wellness_q1: string | null
          wellness_q2: string | null
        }
        Insert: {
          age_range?: string | null
          created_at?: string
          id: string
          is_admin?: boolean
          locale?: string
          name?: string | null
          onboarding_complete?: boolean
          onboarding_step?: number
          role?: string | null
          wellness_q1?: string | null
          wellness_q2?: string | null
        }
        Update: {
          age_range?: string | null
          created_at?: string
          id?: string
          is_admin?: boolean
          locale?: string
          name?: string | null
          onboarding_complete?: boolean
          onboarding_step?: number
          role?: string | null
          wellness_q1?: string | null
          wellness_q2?: string | null
        }
        Relationships: []
      }
      user_roles: {
        Row: {
          granted_at: string
          granted_by: string | null
          role: Database["public"]["Enums"]["role_key"]
          tenant_id: string
          user_id: string
        }
        Insert: {
          granted_at?: string
          granted_by?: string | null
          role: Database["public"]["Enums"]["role_key"]
          tenant_id: string
          user_id: string
        }
        Update: {
          granted_at?: string
          granted_by?: string | null
          role?: Database["public"]["Enums"]["role_key"]
          tenant_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_roles_granted_by_fkey"
            columns: ["granted_by"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_roles_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_roles_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_therapeutic_profiles: {
        Row: {
          communication_style: string | null
          cultural_preferences: Json
          disclosed_concerns: string[]
          distortion_patterns: string[]
          effective_techniques: string[]
          ineffective_techniques: string[]
          last_extraction_turn: number
          last_updated_at: string
          mood_trajectory: Json
          observations: Json
          persisted_clinical_flags: Json | null
          session_count: number
          total_skills_completed: number
          user_id: string
        }
        Insert: {
          communication_style?: string | null
          cultural_preferences?: Json
          disclosed_concerns?: string[]
          distortion_patterns?: string[]
          effective_techniques?: string[]
          ineffective_techniques?: string[]
          last_extraction_turn?: number
          last_updated_at?: string
          mood_trajectory?: Json
          observations?: Json
          persisted_clinical_flags?: Json | null
          session_count?: number
          total_skills_completed?: number
          user_id: string
        }
        Update: {
          communication_style?: string | null
          cultural_preferences?: Json
          disclosed_concerns?: string[]
          distortion_patterns?: string[]
          effective_techniques?: string[]
          ineffective_techniques?: string[]
          last_extraction_turn?: number
          last_updated_at?: string
          mood_trajectory?: Json
          observations?: Json
          persisted_clinical_flags?: Json | null
          session_count?: number
          total_skills_completed?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_therapeutic_profiles_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: true
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      v_user_roles_for_tenant: {
        Row: {
          roles: Database["public"]["Enums"]["role_key"][] | null
          tenant_id: string | null
          user_id: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_roles_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_roles_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "user_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      get_my_roles: {
        Args: { p_tenant_id: string }
        Returns: Database["public"]["Enums"]["role_key"][]
      }
    }
    Enums: {
      role_key:
        | "member"
        | "clinical_reviewer"
        | "clinician_author"
        | "clinical_approver"
        | "operations_admin"
        | "dpo"
        | "super_admin"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      role_key: [
        "member",
        "clinical_reviewer",
        "clinician_author",
        "clinical_approver",
        "operations_admin",
        "dpo",
        "super_admin",
      ],
    },
  },
} as const
