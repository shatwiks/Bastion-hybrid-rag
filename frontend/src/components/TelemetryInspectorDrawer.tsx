"use client";

import React, { useMemo, useState } from "react";
import {
  Activity,
  ChevronDown,
  ChevronRight,
  PanelRightClose,
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
    title: "Auth & Pre-Retrieval RBAC",
  },
  {
    step: 2,
    name: "semantic_cache",
    title: "Permission-Scoped Redis Cache",
  },
  {
    step: 3,
    name: "hybrid_retrieval",
    title: "Query Rewrite & Hybrid RRF",
  },
  {
    step: 4,
    name: "rerank_gate",
    title: "Cross-Encoder & Refusal Gate",
  },
  {
    step: 5,
    name: "grounded_generation",
    title: "Grounded Generation",
  },
  {
    step: 6,
    name: "telemetry_commit",
    title: "Langfuse Trace & Cache Commit",
  },
];

const STATUS_META: Record<
  PipelineStepStatus,
  { label: string; textColor: string; bgColor: string; borderColor: string; numBg: string; numInk: string }
> = {
  pending: {
    label: "Pending",
    textColor: "var(--ink-muted)",
    bgColor: "transparent",
    borderColor: "var(--rule)",
    numBg: "var(--mineral)",
    numInk: "var(--ink-secondary)",
  },
  running: {
    label: "Running",
    textColor: "var(--copper)",
    bgColor: "var(--copper-soft)",
    borderColor: "var(--copper-rule)",
    numBg: "var(--copper)",
    numInk: "#FCFBF8",
  },
  completed: {
    label: "Completed",
    textColor: "var(--jade)",
    bgColor: "var(--jade-soft)",
    borderColor: "var(--jade-rule)",
    numBg: "var(--jade)",
    numInk: "#FCFBF8",
  },
  short_circuited: {
    label: "Blocked",
    textColor: "var(--crimson)",
    bgColor: "var(--crimson-soft)",
    borderColor: "var(--crimson-rule)",
    numBg: "var(--crimson)",
    numInk: "#FCFBF8",
  },
  skipped: {
    label: "Skipped",
    textColor: "var(--ink-muted)",
    bgColor: "var(--mineral)",
    borderColor: "var(--rule)",
    numBg: "var(--mineral)",
    numInk: "var(--ink-muted)",
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

  const scorePct =
    topRerankScore !== null
      ? Math.max(0, Math.min(100, topRerankScore * 100))
      : 0;
  const thresholdPct = Math.max(0, Math.min(100, threshold * 100));
  const passesGate =
    topRerankScore !== null &&
    topRerankScore >= threshold &&
    !turn?.refusal?.refused;

  const originalQuery =
    typeof step3?.details.original_query === "string"
      ? step3.details.original_query
      : turn?.query ?? "";
  const rewrittenQuery =
    typeof step3?.details.rewritten_query === "string"
      ? step3.details.rewritten_query
      : "";
  const wasRewritten =
    Boolean(step3?.details.was_rewritten) &&
    rewrittenQuery.length > 0 &&
    rewrittenQuery !== originalQuery;
  const preservedTokens = Array.isArray(step3?.details.preserved_tokens)
    ? (step3.details.preserved_tokens as string[])
    : [];

  const cacheHit = Boolean(step2?.details.cache_hit ?? turn?.cacheHit);
  const cacheBypassed = Boolean(step2?.details.bypass_cache);
  const cacheSimilarity =
    typeof step2?.details.similarity_score === "number"
      ? step2.details.similarity_score
      : turn?.cacheSimilarity ?? null;
  const entityFingerprint =
    typeof step2?.details.entity_fingerprint === "string"
      ? step2.details.entity_fingerprint
      : null;

  if (!isOpen) return null;

  return (
    <aside
      aria-label="6-Step Pipeline Telemetry Inspector"
      className="flex h-full min-h-[540px] min-w-0 flex-col bg-[var(--ground)]"
    >
      {/* Inspector Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[var(--rule)] px-5 py-3.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 shrink-0 text-[var(--copper)]" />
            <h2 className="truncate text-sm font-semibold text-[var(--ink)]">
              6-Step Pipeline Telemetry
            </h2>
          </div>
          <p className="mt-0.5 truncate font-mono text-[11px] text-[var(--ink-muted)]">
            {turn
              ? `${turn.tenant_id} / ${turn.persona}`
              : session
              ? `Ready · ${session.tenant_id} / ${session.persona}`
              : "Awaiting security context"}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {typeof turn?.totalLatencyMs === "number" && (
            <span className="rounded border border-[var(--rule)] bg-[var(--paper)] px-2 py-0.5 font-mono text-[11px] tabular-nums font-medium text-[var(--ink)]">
              {turn.totalLatencyMs.toFixed(1)} ms
            </span>
          )}
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse telemetry inspector drawer"
            title="Collapse Inspector"
            className="rounded border border-[var(--rule)] bg-[var(--paper)] p-1.5 text-[var(--ink-secondary)] transition-colors hover:border-[var(--rule-strong)] hover:text-[var(--ink)] cursor-pointer"
          >
            <PanelRightClose className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Scrollable Telemetry Rail */}
      <div className="min-w-0 flex-1 overflow-y-auto px-5 py-4">
        {/* 6-Step Hairline Transit Rail */}
        <ol className="divide-y divide-[var(--rule)] border-t border-b border-[var(--rule)]">
          {STAGE_DEFINITIONS.map((stage) => {
            const liveStep = stepMap.get(stage.step);
            const status: PipelineStepStatus = liveStep?.status ?? "pending";
            const isStep2CacheHit =
              stage.step === 2 && status === "short_circuited" && cacheHit;
            const style = isStep2CacheHit
              ? {
                  ...STATUS_META.completed,
                  label: "Cache Hit",
                }
              : STATUS_META[status];

            return (
              <li key={stage.step} className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-xs font-mono text-[11px] font-semibold tabular-nums"
                      style={{
                        backgroundColor: style.numBg,
                        color: style.numInk,
                      }}
                    >
                      {stage.step}
                    </span>
                    <span className="truncate text-[13px] font-semibold text-[var(--ink)]">
                      {stage.title}
                    </span>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    {typeof liveStep?.latency_ms === "number" && (
                      <span className="font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
                        {liveStep.latency_ms.toFixed(1)} ms
                      </span>
                    )}
                    <span
                      className="rounded-xs border px-1.5 py-0.5 text-[10.5px] font-medium"
                      style={{
                        color: style.textColor,
                        backgroundColor: style.bgColor,
                        borderColor: style.borderColor,
                      }}
                    >
                      {style.label}
                    </span>
                  </div>
                </div>

                {/* Step 1 Details */}
                {stage.step === 1 && (step1 || session) && (
                  <div className="mt-2 ml-7.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-[var(--ink-secondary)]">
                    <span>
                      tenant:{" "}
                      <strong className="font-medium text-[var(--ink)]">
                        {String(step1?.details.tenant_id ?? session?.tenant_id ?? "—")}
                      </strong>
                    </span>
                    <span>
                      roles:{" "}
                      <strong className="font-medium text-[var(--ink)]">
                        {(
                          (step1?.details.allowed_roles as string[] | undefined) ??
                          session?.allowed_roles ??
                          []
                        ).join(", ")}
                      </strong>
                    </span>
                    <span className="truncate text-[var(--ink-muted)]">
                      hash:{" "}
                      {String(step1?.details.scope_hash ?? session?.scope_hash ?? "—")}
                    </span>
                  </div>
                )}

                {/* Step 2 Details */}
                {stage.step === 2 && step2 && (
                  <div className="mt-2 ml-7.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                    <span
                      className="rounded-xs border px-1.5 py-0.5 font-mono text-[10.5px] font-semibold"
                      style={
                        cacheHit
                          ? {
                              color: "var(--jade)",
                              backgroundColor: "var(--jade-soft)",
                              borderColor: "var(--jade-rule)",
                            }
                          : {
                              color: "var(--ink-secondary)",
                              backgroundColor: "var(--paper)",
                              borderColor: "var(--rule)",
                            }
                      }
                    >
                      {cacheHit ? "HIT" : cacheBypassed ? "BYPASSED" : "MISS"}
                    </span>
                    <span className="font-mono text-[11px] tabular-nums text-[var(--ink-secondary)]">
                      sim:{" "}
                      <strong className="text-[var(--ink)]">
                        {cacheSimilarity !== null
                          ? cacheSimilarity.toFixed(4)
                          : "0.0000"}
                      </strong>
                    </span>
                    {entityFingerprint && (
                      <span className="truncate font-mono text-[11px] text-[var(--ink-muted)]">
                        fp: {entityFingerprint}
                      </span>
                    )}
                  </div>
                )}

                {/* Step 3 Details: Original vs Rewritten Query + Pool */}
                {stage.step === 3 && step3 && status !== "skipped" && (
                  <div className="mt-2 ml-7.5 space-y-1.5 text-xs">
                    <div className="rounded border border-[var(--rule)] bg-[var(--paper)] px-2.5 py-2 space-y-1">
                      <div className="flex items-start gap-2">
                        <span className="w-16 shrink-0 font-mono text-[10.5px] text-[var(--ink-muted)]">
                          Original
                        </span>
                        <span className="text-[12px] text-[var(--ink-secondary)]">
                          {originalQuery}
                        </span>
                      </div>
                      {rewrittenQuery && (
                        <div className="flex items-start gap-2 border-t border-[var(--rule)]/70 pt-1">
                          <span
                            className="w-16 shrink-0 font-mono text-[10.5px] font-medium"
                            style={{
                              color: wasRewritten
                                ? "var(--copper)"
                                : "var(--ink-muted)",
                            }}
                          >
                            {wasRewritten ? "Rewritten" : "Final"}
                          </span>
                          <span className="text-[12px] font-medium text-[var(--ink)]">
                            {rewrittenQuery}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-[var(--ink-muted)]">
                      <span className="tabular-nums">
                        Candidate pool:{" "}
                        <strong className="text-[var(--ink)]">
                          {Number(
                            step3.details.candidate_count ?? funnelRows.length
                          )}
                        </strong>{" "}
                        chunks
                      </span>
                      {preservedTokens.length > 0 && (
                        <span className="truncate text-[var(--copper)]">
                          Preserved: {preservedTokens.join(", ")}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Step 4 Signature Move: Calibrated 0.65 Vernier Confidence Gauge */}
                {stage.step === 4 &&
                  status !== "skipped" &&
                  (step4 || topRerankScore !== null) && (
                  <div className="mt-2.5 ml-7.5 rounded border border-[var(--rule)] bg-[var(--paper)] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-[var(--ink)]">
                        Refusal Gate Vernier Gauge
                      </span>
                      <span
                        className="font-mono text-[12px] tabular-nums font-semibold"
                        style={{
                          color:
                            topRerankScore === null
                              ? "var(--ink-muted)"
                              : passesGate
                              ? "var(--jade)"
                              : "var(--crimson)",
                        }}
                      >
                        {topRerankScore !== null
                          ? `${topRerankScore.toFixed(4)} vs ${threshold.toFixed(2)} ${
                              passesGate ? "PASS" : "REFUSED"
                            }`
                          : "Scoring…"}
                      </span>
                    </div>

                    {/* Calibrated Vernier Scale */}
                    <div className="mt-2.5">
                      <div className="relative h-3 w-full overflow-hidden rounded-xs bg-[var(--mineral)]">
                        {/* Safe / Refusal zone hairline tint */}
                        <div
                          className="absolute inset-y-0 left-0 bg-[#E6DCD8]/60"
                          style={{ width: `${thresholdPct}%` }}
                        />
                        {/* Active Score Fill */}
                        <div
                          className="relative h-full transition-all duration-200"
                          style={{
                            width: `${scorePct}%`,
                            backgroundColor:
                              topRerankScore === null
                                ? "var(--rule-strong)"
                                : passesGate
                                ? "var(--jade)"
                                : "var(--crimson)",
                          }}
                        />
                        {/* Precision 0.65 Gate Pin */}
                        <div
                          className="absolute inset-y-0 w-0.5 bg-[var(--ink)]"
                          style={{ left: `${thresholdPct}%` }}
                          title={`Refusal Gate Threshold: ${threshold.toFixed(2)}`}
                        />
                      </div>

                      {/* Vernier Ticks */}
                      <div className="relative mt-1 flex justify-between font-mono text-[10px] tabular-nums text-[var(--ink-muted)]">
                        <span>0.00</span>
                        <span>0.25</span>
                        <span>0.50</span>
                        <span className="font-semibold text-[var(--ink)]">
                          {threshold.toFixed(2)} gate
                        </span>
                        <span>1.00</span>
                      </div>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--rule)]/70 pt-2 font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
                      <span>
                        Funnel:{" "}
                        <strong className="text-[var(--ink)]">
                          Top-{Number(step4?.details.input_candidates ?? funnelRows.length)}
                        </strong>{" "}
                        →{" "}
                        <strong className="text-[var(--ink)]">
                          Top-{Number(step4?.details.accepted_chunks ?? turn?.citations.length ?? 0)}
                        </strong>
                      </span>
                      {turn?.refusal?.refused && (
                        <span className="font-semibold text-[var(--crimson)]">
                          LLM Skipped · 0 Tokens
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Step 5 Details */}
                {stage.step === 5 && step5 && (
                  <div className="mt-2 ml-7.5 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-[var(--ink-secondary)]">
                    <span>
                      llm_called:{" "}
                      <strong
                        style={{
                          color:
                            step5.details.llm_called === false
                              ? "var(--ochre)"
                              : "var(--jade)",
                        }}
                      >
                        {step5.details.llm_called === false ? "FALSE" : "TRUE"}
                      </strong>
                    </span>
                    <span className="tabular-nums text-[var(--ink-muted)]">
                      cited: {Number(step5.details.cited_chunks ?? turn?.citations.length ?? 0)}
                      {step5.details.model ? ` · ${String(step5.details.model)}` : ""}
                    </span>
                  </div>
                )}

                {/* Step 6 Details */}
                {stage.step === 6 && step6 && (
                  <div className="mt-2 ml-7.5 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-[var(--ink-muted)]">
                    <span className="truncate">
                      trace:{" "}
                      <span className="text-[var(--ink-secondary)]">
                        {String(step6.details.trace_id ?? turn?.traceId ?? "—")}
                      </span>
                    </span>
                    {typeof turn?.totalLatencyMs === "number" && (
                      <span className="tabular-nums text-[var(--ink)]">
                        {turn.totalLatencyMs.toFixed(1)} ms
                      </span>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ol>

        {/* Collapsible Candidate Funnel Table (Top-25 RRF -> Top-5 Cross-Encoder) */}
        <div className="mt-5">
          <button
            type="button"
            onClick={() => setFunnelExpanded((prev) => !prev)}
            className="flex w-full items-center justify-between py-2 text-left cursor-pointer"
          >
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--ink)]">
              {funnelExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 text-[var(--ink-muted)]" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-[var(--ink-muted)]" />
              )}
              Candidate Funnel (RRF → Cross-Encoder)
            </span>
            <span className="font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
              {funnelRows.length} rows
            </span>
          </button>

          {funnelExpanded && (
            <div className="overflow-hidden rounded border border-[var(--rule)] bg-[var(--paper)]">
              {funnelRows.length === 0 ? (
                <div className="px-3.5 py-5 text-center text-xs text-[var(--ink-muted)]">
                  {cacheHit
                    ? "Semantic Cache HIT — hybrid retrieval skipped."
                    : turn
                    ? "No candidate chunks matched the active tenant/role scope."
                    : "Run a query to inspect Dense, BM25, RRF, and Cross-Encoder ranks."}
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[440px] border-collapse text-left text-[11.5px]">
                      <thead>
                        <tr className="border-b border-[var(--rule)] bg-[var(--ground)] text-[10.5px] font-semibold text-[var(--ink-secondary)]">
                          <th className="px-3 py-2">Source</th>
                          <th className="px-2 py-2 text-right">Dense</th>
                          <th className="px-2 py-2 text-right">BM25</th>
                          <th className="px-2 py-2 text-right">RRF</th>
                          <th className="px-2 py-2 text-right">Rerank</th>
                          <th className="px-3 py-2 text-right">Gate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--rule)]/70">
                        {visibleFunnelRows.map((row, idx) => {
                          const hasRerank = typeof row.rerank_score === "number";
                          const rowPasses =
                            hasRerank && (row.rerank_score ?? 0) >= threshold;

                          return (
                            <tr
                              key={`${row.chunk_id}-${idx}`}
                              className="transition-colors hover:bg-[var(--ground)]/60"
                            >
                              <td className="max-w-[165px] px-3 py-2">
                                <div className="truncate font-medium text-[var(--ink)]">
                                  {row.document_title || row.chunk_id.slice(0, 8)}
                                </div>
                                <div className="truncate font-mono text-[10px] text-[var(--ink-muted)]">
                                  {row.section_header || row.chunk_id.slice(0, 10)}
                                </div>
                              </td>
                              <td className="px-2 py-2 text-right font-mono tabular-nums text-[var(--ink-secondary)]">
                                {row.dense_rank ? `#${row.dense_rank}` : "—"}
                              </td>
                              <td className="px-2 py-2 text-right font-mono tabular-nums text-[var(--ink-secondary)]">
                                {row.sparse_rank ? `#${row.sparse_rank}` : "—"}
                              </td>
                              <td className="px-2 py-2 text-right font-mono tabular-nums text-[var(--ink)]">
                                {typeof row.rrf_score === "number"
                                  ? row.rrf_score.toFixed(4)
                                  : "—"}
                              </td>
                              <td
                                className="px-2 py-2 text-right font-mono tabular-nums font-semibold"
                                style={{
                                  color: !hasRerank
                                    ? "var(--ink-muted)"
                                    : rowPasses
                                    ? "var(--jade)"
                                    : "var(--crimson)",
                                }}
                              >
                                {hasRerank ? row.rerank_score!.toFixed(4) : "—"}
                              </td>
                              <td className="px-3 py-2 text-right font-mono text-[10.5px]">
                                {!hasRerank ? (
                                  <span className="text-[var(--ink-muted)]">…</span>
                                ) : rowPasses ? (
                                  <span className="font-semibold text-[var(--jade)]">
                                    PASS
                                  </span>
                                ) : (
                                  <span className="text-[var(--ink-muted)]">
                                    DROP
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
                    <div className="border-t border-[var(--rule)] bg-[var(--ground)]/60 px-3 py-2 text-center">
                      <button
                        type="button"
                        onClick={() => setShowAllCandidates((prev) => !prev)}
                        className="text-xs font-medium text-[var(--copper)] hover:text-[var(--copper-hover)] cursor-pointer"
                      >
                        {showAllCandidates
                          ? "Show top 10 candidates"
                          : `Show all ${funnelRows.length} candidates`}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
