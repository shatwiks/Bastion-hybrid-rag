"use client";

import React, { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  DatabaseZap,
  Filter,
  GitCompare,
  KeyRound,
  Lock,
  PanelRightClose,
  ShieldAlert,
  ShieldCheck,
  SkipForward,
  Sparkles,
  Zap,
} from "lucide-react";

import type {
  CandidateTelemetryRow,
  ChatTurn,
  DemoTokenSession,
  PipelineStepStatus,
  PipelineStepUpdate,
} from "@/types/rag";

const REFUSAL_THRESHOLD = 0.65;

const STAGE_DEFINITIONS: Array<{
  step: 1 | 2 | 3 | 4 | 5 | 6;
  name: string;
  title: string;
}> = [
  {
    step: 1,
    name: "auth_guardrail",
    title: "Step 1: Auth & Pre-Retrieval RBAC Guardrail",
  },
  {
    step: 2,
    name: "semantic_cache",
    title: "Step 2: Permission-Scoped Redis Semantic Cache",
  },
  {
    step: 3,
    name: "hybrid_retrieval",
    title: "Step 3: Query Rewrite & Hybrid Retrieval (BM25 + pgvector RRF)",
  },
  {
    step: 4,
    name: "rerank_gate",
    title: "Step 4: Cross-Encoder Reranking & Deterministic Refusal Gate",
  },
  {
    step: 5,
    name: "grounded_generation",
    title: "Step 5: Grounded LLM Generation",
  },
  {
    step: 6,
    name: "telemetry_commit",
    title: "Step 6: Async Langfuse Trace & Cache Commit",
  },
];

const STATUS_STYLES: Record<
  PipelineStepStatus,
  { label: string; badgeClass: string; dotClass: string }
> = {
  pending: {
    label: "pending",
    badgeClass: "border-slate-700 bg-slate-800/80 text-slate-400",
    dotClass: "bg-slate-500",
  },
  running: {
    label: "running",
    badgeClass: "border-indigo-500/40 bg-indigo-500/15 text-indigo-300",
    dotClass: "bg-indigo-400 animate-ping",
  },
  completed: {
    label: "completed",
    badgeClass: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
    dotClass: "bg-emerald-400",
  },
  short_circuited: {
    label: "short_circuited",
    badgeClass: "border-amber-500/45 bg-amber-500/15 text-amber-200",
    dotClass: "bg-amber-400",
  },
  skipped: {
    label: "skipped",
    badgeClass: "border-slate-700/80 bg-slate-900 text-slate-500",
    dotClass: "bg-slate-600",
  },
};

export interface TelemetryInspectorDrawerProps {
  turn: ChatTurn | null;
  session: DemoTokenSession | null;
  isOpen: boolean;
  onCollapse: () => void;
}

export function TelemetryInspectorDrawer({
  turn,
  session,
  isOpen,
  onCollapse,
}: TelemetryInspectorDrawerProps) {
  const [showAllCandidates, setShowAllCandidates] = useState(false);
  const [funnelExpanded, setFunnelExpanded] = useState(true);

  const stepMap = useMemo(() => {
    const map = new Map<number, PipelineStepUpdate>();
    if (!turn) return map;
    for (const s of turn.steps) {
      map.set(s.step, s);
    }
    return map;
  }, [turn]);

  const step1 = stepMap.get(1);
  const step2 = stepMap.get(2);
  const step3 = stepMap.get(3);
  const step4 = stepMap.get(4);
  const step5 = stepMap.get(5);
  const step6 = stepMap.get(6);

  const funnelRows: CandidateTelemetryRow[] = useMemo(() => {
    const reranked = step4?.details.reranked_candidates;
    if (Array.isArray(reranked) && reranked.length > 0) {
      return reranked;
    }
    const retrieved = step3?.details.candidates;
    if (Array.isArray(retrieved) && retrieved.length > 0) {
      return retrieved;
    }
    return [];
  }, [step3, step4]);

  const visibleFunnelRows = showAllCandidates
    ? funnelRows
    : funnelRows.slice(0, 10);

  const threshold =
    typeof step4?.details.threshold === "number"
      ? step4.details.threshold
      : REFUSAL_THRESHOLD;

  const topRerankScore =
    typeof step4?.details.top_rerank_score === "number"
      ? step4.details.top_rerank_score
      : turn?.refusal?.top_score ?? null;

  const totalRrfCandidates =
    typeof step3?.details.candidate_count === "number"
      ? step3.details.candidate_count
      : funnelRows.length;

  const selectedTopCount =
    typeof step4?.details.selected_count === "number"
      ? step4.details.selected_count
      : turn?.citations.length ?? 0;

  if (!isOpen) {
    return null;
  }

  return (
    <aside
      aria-label="6-Step Pipeline Telemetry Inspector"
      className="flex h-full min-h-[540px] flex-col rounded-2xl border border-slate-800/90 bg-slate-900/70 shadow-xl overflow-hidden"
    >
      {/* Drawer Header */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-800/90 bg-slate-900/95 px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400 shrink-0" />
            <h2 className="truncate text-sm font-semibold text-white">
              6-Step Pipeline Telemetry Inspector
            </h2>
          </div>
          <p className="mt-0.5 truncate text-[11px] text-slate-400">
            {turn
              ? `Inspecting query · ${turn.tenant_id} / ${turn.persona}`
              : "Submit a query to trace live RBAC, RRF & Cross-Encoder telemetry"}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {turn?.totalLatencyMs != null && (
            <span className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[11px] font-semibold text-cyan-300">
              <Clock className="h-3 w-3 text-cyan-400" />
              {turn.totalLatencyMs.toFixed(1)} ms
            </span>
          )}
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse Telemetry Inspector"
            title="Collapse Telemetry Inspector"
            className="rounded-lg border border-slate-700/80 bg-slate-800/80 p-1.5 text-slate-400 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
          >
            <PanelRightClose className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Scrollable Inspector Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!turn ? (
          <div className="flex h-full min-h-[320px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-6 text-center">
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
              <DatabaseZap className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">
              No Pipeline Execution Selected
            </h3>
            <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-400">
              Launch a scenario or ask a question in the chat pane to inspect live
              step latencies, Redis cache similarity, rewritten query diff, and the
              0.65 Refusal Gate score meter.
            </p>
            {session && (
              <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-2 text-left font-mono text-[11px] text-slate-300">
                <div>
                  <span className="text-slate-500">tenant_id:</span>{" "}
                  {session.tenant_id}
                </div>
                <div>
                  <span className="text-slate-500">allowed_roles:</span>{" "}
                  {session.allowed_roles.join(", ")}
                </div>
                <div>
                  <span className="text-slate-500">scope_hash:</span>{" "}
                  {session.scope_hash}
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            {/* 6-Step Lifecycle Cards */}
            <div className="space-y-2.5">
              {STAGE_DEFINITIONS.map((def) => {
                const step = stepMap.get(def.step);
                const status: PipelineStepStatus = step?.status ?? "pending";
                const statusMeta = STATUS_STYLES[status];
                const latency = step?.latency_ms ?? 0;

                return (
                  <div
                    key={def.step}
                    className={`rounded-xl border p-3 transition-colors ${
                      status === "running"
                        ? "border-indigo-500/50 bg-indigo-950/20"
                        : status === "short_circuited"
                        ? "border-amber-500/45 bg-amber-950/15"
                        : status === "skipped"
                        ? "border-slate-800/70 bg-slate-950/40 opacity-75"
                        : "border-slate-800 bg-slate-950/70"
                    }`}
                  >
                    {/* Stage Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-slate-800 font-mono text-[11px] font-bold text-slate-200 border border-slate-700">
                          {def.step}
                        </span>
                        <span className="truncate text-xs font-semibold text-slate-100">
                          {def.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono text-[11px] text-slate-400">
                          {step ? `${latency.toFixed(1)} ms` : "—"}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${statusMeta.badgeClass}`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClass}`}
                          />
                          {statusMeta.label}
                        </span>
                      </div>
                    </div>

                    {/* Stage-Specific Details */}
                    {def.step === 1 && step1 && (
                      <div className="mt-2.5 grid grid-cols-1 gap-1.5 border-t border-slate-800/80 pt-2 text-[11px]">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-1 text-slate-400">
                            <Lock className="h-3 w-3 text-emerald-400" />
                            tenant_id:
                            <span className="font-mono text-slate-200">
                              {step1.details.tenant_id ?? turn.tenant_id}
                            </span>
                          </span>
                          <span className="inline-flex items-center gap-1 font-mono text-cyan-300">
                            <KeyRound className="h-3 w-3 text-cyan-400" />
                            scope_hash:{" "}
                            {step1.details.scope_hash ?? turn.scope_hash}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="text-slate-400 mr-1">allowed_roles:</span>
                          {(
                            step1.details.allowed_roles ?? turn.allowed_roles
                          ).map((role) => (
                            <span
                              key={role}
                              className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-indigo-200"
                            >
                              {role}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {def.step === 2 && step2 && (
                      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2 text-[11px]">
                        <div className="flex items-center gap-2">
                          {step2.details.cache_hit ? (
                            <span className="inline-flex items-center gap-1 rounded border border-emerald-500/40 bg-emerald-500/15 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-300">
                              <Zap className="h-3 w-3" />
                              HIT
                            </span>
                          ) : step2.details.bypassed ? (
                            <span className="inline-flex items-center gap-1 rounded border border-slate-600 bg-slate-800 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-300">
                              <SkipForward className="h-3 w-3" />
                              BYPASSED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800/90 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-300">
                              MISS
                            </span>
                          )}
                          <span className="text-slate-400">
                            Cosine Similarity:{" "}
                            <span className="font-mono text-slate-200">
                              {typeof step2.details.similarity_score === "number"
                                ? step2.details.similarity_score.toFixed(4)
                                : "0.0000"}
                            </span>
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-slate-400">
                          entity_fingerprint:{" "}
                          <span className="text-cyan-300">
                            {step2.details.entity_fingerprint ?? "none"}
                          </span>
                        </span>
                      </div>
                    )}

                    {def.step === 3 && step3 && (
                      <div className="mt-2.5 space-y-2 border-t border-slate-800/80 pt-2 text-[11px]">
                        {step3.status === "skipped" ? (
                          <p className="text-slate-400 italic">
                            Skipped ({step3.details.reason ?? "semantic_cache_hit"})
                          </p>
                        ) : (
                          <>
                            <div className="grid grid-cols-1 gap-1.5 rounded-lg border border-slate-800 bg-slate-900/70 p-2">
                              <div className="flex items-start gap-1.5">
                                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                                  Original
                                </span>
                                <span className="text-slate-300 break-words">
                                  {step3.details.original_query ?? turn.query}
                                </span>
                              </div>
                              <div className="flex items-start gap-1.5">
                                <span className="inline-flex shrink-0 items-center gap-1 rounded bg-indigo-500/15 border border-indigo-500/30 px-1.5 py-0.5 font-mono text-[10px] text-indigo-300">
                                  <ArrowRight className="h-2.5 w-2.5" />
                                  Rewritten
                                </span>
                                <span className="text-indigo-100 break-words">
                                  {step3.details.rewritten_query ?? turn.query}
                                </span>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="inline-flex items-center gap-1 text-slate-400">
                                <Filter className="h-3 w-3 text-sky-400" />
                                Candidate Pool:{" "}
                                <strong className="font-mono text-slate-200">
                                  {step3.details.candidate_count ?? funnelRows.length}
                                </strong>{" "}
                                chunks (Top-25 RRF)
                              </span>
                              {Array.isArray(step3.details.preserved_tokens) &&
                                step3.details.preserved_tokens.length > 0 && (
                                  <div className="flex flex-wrap items-center gap-1">
                                    <span className="text-slate-500">Preserved:</span>
                                    {step3.details.preserved_tokens.map((tok) => (
                                      <span
                                        key={tok}
                                        className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300"
                                      >
                                        {tok}
                                      </span>
                                    ))}
                                  </div>
                                )}
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {def.step === 4 && step4 && (
                      <div className="mt-2.5 space-y-2 border-t border-slate-800/80 pt-2 text-[11px]">
                        {step4.status === "skipped" ? (
                          <p className="text-slate-400 italic">
                            Skipped ({step4.details.reason ?? "semantic_cache_hit"})
                          </p>
                        ) : (
                          <div className="space-y-2 rounded-lg border border-slate-800 bg-slate-900/75 p-2.5">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="inline-flex items-center gap-1.5 font-semibold text-slate-200">
                                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                                Refusal Gate Confidence Meter
                              </span>
                              {topRerankScore !== null && (
                                <span
                                  className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] font-bold ${
                                    topRerankScore >= threshold
                                      ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                                      : "bg-rose-500/15 text-rose-300 border border-rose-500/40"
                                  }`}
                                >
                                  {topRerankScore >= threshold ? (
                                    <ShieldCheck className="h-3 w-3" />
                                  ) : (
                                    <ShieldAlert className="h-3 w-3" />
                                  )}
                                  {topRerankScore.toFixed(4)} vs {threshold.toFixed(2)} Gate
                                </span>
                              )}
                            </div>

                            {topRerankScore !== null && (
                              <>
                                <div className="relative h-3.5 w-full overflow-hidden rounded-full bg-slate-800">
                                  <div
                                    className={`h-full rounded-full transition-all duration-300 ${
                                      topRerankScore >= threshold
                                        ? "bg-gradient-to-r from-emerald-600 to-emerald-400"
                                        : "bg-gradient-to-r from-rose-600 to-amber-500"
                                    }`}
                                    style={{
                                      width: `${Math.max(
                                        0,
                                        Math.min(100, topRerankScore * 100)
                                      )}%`,
                                    }}
                                  />
                                  {/* 0.65 Threshold Marker */}
                                  <div
                                    className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_rgba(255,255,255,0.9)]"
                                    style={{ left: `${threshold * 100}%` }}
                                    title={`Refusal Gate Threshold: ${threshold.toFixed(2)}`}
                                  />
                                </div>
                                <div className="flex items-center justify-between font-mono text-[10px] text-slate-400">
                                  <span>0.00</span>
                                  <span className="text-amber-300 font-semibold">
                                    Threshold: {threshold.toFixed(2)} Refusal Gate
                                  </span>
                                  <span>1.00</span>
                                </div>
                              </>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
                              <span>
                                Funnel:{" "}
                                <strong className="font-mono text-slate-200">
                                  Top-{totalRrfCandidates}
                                </strong>{" "}
                                →{" "}
                                <strong className="font-mono text-slate-200">
                                  Top-{selectedTopCount}
                                </strong>
                              </span>
                              {step4.details.should_refuse && (
                                <span className="inline-flex items-center gap-1 text-rose-300 font-medium">
                                  <AlertTriangle className="h-3 w-3" />
                                  {step4.details.refusal_reason ?? "below_confidence_threshold"}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {def.step === 5 && step5 && (
                      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2 text-[11px]">
                        <span className="inline-flex items-center gap-1.5 text-slate-300">
                          <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                          llm_called:{" "}
                          <strong
                            className={`font-mono ${
                              step5.details.llm_called
                                ? "text-emerald-300"
                                : "text-amber-300"
                            }`}
                          >
                            {step5.details.llm_called ? "TRUE" : "FALSE"}
                          </strong>
                        </span>
                        <span className="text-slate-400">
                          Cited Chunks:{" "}
                          <strong className="font-mono text-slate-200">
                            {Array.isArray(step5.details.selected_chunk_ids)
                              ? step5.details.selected_chunk_ids.length
                              : turn.citations.length}
                          </strong>
                          {step5.details.model ? ` · ${step5.details.model}` : ""}
                        </span>
                      </div>
                    )}

                    {def.step === 6 && step6 && (
                      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2 text-[11px]">
                        <span className="font-mono text-slate-300 truncate max-w-[230px]">
                          trace_id:{" "}
                          <span className="text-cyan-300">
                            {step6.details.trace_id ?? turn.traceId ?? "—"}
                          </span>
                        </span>
                        <span className="font-mono text-slate-400">
                          total:{" "}
                          <strong className="text-slate-200">
                            {turn.totalLatencyMs !== null
                              ? `${turn.totalLatencyMs.toFixed(1)} ms`
                              : "—"}
                          </strong>
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Candidate Funnel Comparison Table (Top-25 RRF -> Top-5 Cross-Encoder) */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/75 overflow-hidden">
              <button
                type="button"
                onClick={() => setFunnelExpanded((prev) => !prev)}
                className="flex w-full items-center justify-between gap-2 bg-slate-900/90 px-3.5 py-2.5 text-left hover:bg-slate-800/80 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {funnelExpanded ? (
                    <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                  )}
                  <GitCompare className="h-4 w-4 text-cyan-400 shrink-0" />
                  <span className="truncate text-xs font-semibold text-slate-100">
                    Candidate Funnel (Top-{totalRrfCandidates || 25} RRF → Top-
                    {selectedTopCount || 5} Cross-Encoder)
                  </span>
                </div>
                <span className="shrink-0 rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                  {funnelRows.length} rows
                </span>
              </button>

              {funnelExpanded && (
                <div className="border-t border-slate-800/80">
                  {funnelRows.length === 0 ? (
                    <div className="px-4 py-5 text-center text-xs text-slate-400">
                      {step2?.details.cache_hit
                        ? "Semantic Cache HIT short-circuited Step 3 & Step 4 (0 vector/rerank candidates needed)."
                        : "Awaiting hybrid retrieval candidate pool..."}
                    </div>
                  ) : (
                    <>
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse text-left text-[11px]">
                          <thead>
                            <tr className="border-b border-slate-800 bg-slate-900/60 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                              <th className="px-3 py-2">Section Header</th>
                              <th className="px-2 py-2 text-right">Dense #</th>
                              <th className="px-2 py-2 text-right">BM25 #</th>
                              <th className="px-2 py-2 text-right">RRF Score</th>
                              <th className="px-2 py-2 text-right">Cross-Enc</th>
                              <th className="px-3 py-2 text-center">Gate (≥0.65)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/70">
                            {visibleFunnelRows.map((row) => {
                              const hasRerank = typeof row.rerank_score === "number";
                              const passed =
                                hasRerank && (row.rerank_score ?? 0) >= threshold;

                              return (
                                <tr
                                  key={row.chunk_id}
                                  className="hover:bg-slate-900/50 transition-colors"
                                >
                                  <td className="px-3 py-2 max-w-[170px]">
                                    <div className="truncate font-medium text-slate-200">
                                      {row.section_header || "Document Root"}
                                    </div>
                                    <div className="truncate font-mono text-[10px] text-slate-500">
                                      {row.document_title}
                                    </div>
                                  </td>
                                  <td className="px-2 py-2 text-right font-mono text-sky-300">
                                    {row.dense_rank != null ? `#${row.dense_rank}` : "—"}
                                  </td>
                                  <td className="px-2 py-2 text-right font-mono text-indigo-300">
                                    {row.sparse_rank != null ? `#${row.sparse_rank}` : "—"}
                                  </td>
                                  <td className="px-2 py-2 text-right font-mono text-slate-300">
                                    {row.rrf_score.toFixed(4)}
                                  </td>
                                  <td
                                    className={`px-2 py-2 text-right font-mono font-semibold ${
                                      !hasRerank
                                        ? "text-slate-500"
                                        : passed
                                        ? "text-emerald-300"
                                        : "text-rose-300"
                                    }`}
                                  >
                                    {hasRerank
                                      ? (row.rerank_score ?? 0).toFixed(4)
                                      : "—"}
                                  </td>
                                  <td className="px-3 py-2 text-center">
                                    {!hasRerank ? (
                                      <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                                        WAIT
                                      </span>
                                    ) : passed ? (
                                      <span className="inline-flex items-center gap-1 rounded border border-emerald-500/35 bg-emerald-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-300">
                                        <CheckCircle2 className="h-2.5 w-2.5" />
                                        PASS
                                      </span>
                                    ) : (
                                      <span className="rounded border border-rose-500/35 bg-rose-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-rose-300">
                                        FAIL
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      {funnelRows.length > 10 && (
                        <div className="border-t border-slate-800/80 bg-slate-900/40 px-3 py-2 text-center">
                          <button
                            type="button"
                            onClick={() => setShowAllCandidates((prev) => !prev)}
                            className="text-[11px] font-medium text-cyan-300 hover:text-cyan-200 underline cursor-pointer"
                          >
                            {showAllCandidates
                              ? "Show Top 10 Candidates"
                              : `Show All ${funnelRows.length} RRF Candidates`}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
