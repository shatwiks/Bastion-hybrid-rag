export type TenantId = "acme_corp" | "globex_corp";

export type PersonaType = "public" | "support_tier_1" | "executive";

export interface DemoTokenRequest {
  tenant_id: TenantId;
  persona?: PersonaType;
  custom_roles?: string[];
}

export interface DemoTokenResponse {
  access_token: string;
  token_type: string;
  tenant_id: TenantId;
  allowed_roles: string[];
  scope_hash: string;
  expires_in: number;
}

export interface DemoTokenSession extends DemoTokenResponse {
  persona: PersonaType;
}

export interface CitationItem {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section_header: string;
  content: string;
  allowed_roles: string[];
  rerank_score: number;
  dense_rank?: number | null;
  sparse_rank?: number | null;
  rrf_score?: number | null;
}

export interface CandidateTelemetryRow {
  chunk_id: string;
  document_title: string;
  section_header: string;
  dense_rank: number | null;
  sparse_rank: number | null;
  rrf_score: number;
  rerank_score?: number;
}

export type PipelineStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "short_circuited"
  | "skipped";

export type PipelineStepName =
  | "auth_guardrail"
  | "semantic_cache"
  | "hybrid_retrieval"
  | "rerank_gate"
  | "grounded_generation"
  | "telemetry_commit";

export type RefusalReason =
  | "no_accessible_chunks"
  | "below_confidence_threshold"
  | string;

export interface PipelineStepDetails {
  // Step 1: auth_guardrail
  tenant_id?: string;
  allowed_roles?: string[];
  scope_hash?: string;

  // Step 2: semantic_cache
  cache_hit?: boolean;
  bypassed?: boolean;
  similarity_score?: number;
  entity_fingerprint?: string;
  entry_id?: string;

  // Step 3: hybrid_retrieval
  original_query?: string;
  rewritten_query?: string;
  was_rewritten?: boolean;
  preserved_tokens?: string[];
  candidate_count?: number;
  retrieval_latency_ms?: number;
  candidates?: CandidateTelemetryRow[];

  // Step 4: rerank_gate
  top_rerank_score?: number;
  threshold?: number;
  should_refuse?: boolean;
  refusal_reason?: RefusalReason | null;
  selected_count?: number;
  reranked_candidates?: CandidateTelemetryRow[];

  // Step 5: grounded_generation
  llm_called?: boolean;
  model?: string;
  mode?: string;
  token_usage?: Record<string, number>;
  selected_chunk_ids?: string[];

  // Step 6: telemetry_commit
  trace_id?: string;
  cache_written?: boolean;
  cache_entry_id?: string | null;
  refused?: boolean;
  langfuse_enabled?: boolean;

  // Generic skip/error reason
  reason?: string;
  [key: string]: unknown;
}

export interface PipelineStepUpdate {
  step: 1 | 2 | 3 | 4 | 5 | 6;
  name: PipelineStepName | string;
  label: string;
  status: PipelineStepStatus;
  latency_ms: number;
  details: PipelineStepDetails;
}

export interface RefusalEventPayload {
  refused: boolean;
  reason: RefusalReason | null;
  message: string;
  top_score: number;
  threshold: number;
}

export interface DoneEventPayload {
  trace_id: string;
  total_latency_ms: number;
  cache_hit: boolean;
  refused: boolean;
  llm_called: boolean;
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatStreamRequest {
  query: string;
  chat_history?: ChatHistoryMessage[];
  bypass_cache?: boolean;
}

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  query: string;
  content: string;
  tenant_id: TenantId;
  persona: PersonaType;
  allowed_roles: string[];
  scope_hash: string;
  isStreaming: boolean;
  steps: PipelineStepUpdate[];
  citations: CitationItem[];
  refusal: RefusalEventPayload | null;
  cacheHit: boolean;
  cacheSimilarity: number | null;
  llmCalled: boolean | null;
  traceId: string | null;
  totalLatencyMs: number | null;
  error: string | null;
  createdAt: string;
}

export interface HealthStatusResponse {
  status: string;
  postgres: string;
  redis: string;
  version: string;
}

export interface DocumentIngestRequest {
  title: string;
  content: string;
  tenant_id: TenantId | string;
  allowed_roles: string[];
  doc_metadata?: Record<string, unknown>;
}

export interface DocumentChunkSummary {
  chunk_id: string;
  section_header: string;
  character_count: number;
}

export interface DocumentIngestResponse {
  document_id: string;
  title: string;
  tenant_id: string;
  chunks_count: number;
  chunks: DocumentChunkSummary[];
}

export interface DocumentSummary {
  id: string;
  title: string;
  tenant_id: string;
  chunks_count: number;
  doc_metadata: Record<string, unknown>;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
  total: number;
}

export type ParsedCitationSegment =
  | {
      type: "text";
      value: string;
    }
  | {
      type: "citation";
      chunkId: string;
      raw: string;
    };

export interface GuidedScenario {
  id: string;
  label: string;
  badge: string;
  query: string;
  recommendedPersona?: PersonaType;
  description: string;
}
