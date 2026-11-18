"use client";

import React, { useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  Bot,
  CheckCircle2,
  Cpu,
  FileSearch,
  Lock,
  ShieldAlert,
  Sparkles,
  Square,
  User,
  Zap,
} from "lucide-react";

import { CitationPopover } from "@/components/CitationPopover";
import {
  mergeCitationsWithCandidateTelemetry,
  parseTextWithCitations,
} from "@/lib/sse-client";
import type {
  ChatTurn,
  CitationItem,
  DemoTokenSession,
  GuidedScenario,
} from "@/types/rag";

export const GUIDED_SCENARIOS: GuidedScenario[] = [
  {
    id: "error-code",
    label: "Exact Error Code (Tier 1)",
    badge: "BM25 + RRF",
    query:
      "How do I diagnose and resolve ERR_409_CONFLICT during concurrent storage sync?",
    recommendedPersona: "support_tier_1",
    description: "Tests exact technical error-code recall via hybrid lexical + dense retrieval.",
  },
  {
    id: "hardware-sku",
    label: "Hardware SKU Lookup (Tier 1)",
    badge: "SKU Exact Match",
    query: "What are the specifications and thermal limits for SKU-9921-A?",
    recommendedPersona: "support_tier_1",
    description: "Verifies hyphenated SKU token preservation and technical grounding.",
  },
  {
    id: "executive-ma",
    label: "Executive M&A Strategy (Executive Only)",
    badge: "RBAC Boundary",
    query: "What are the confidential Q3 financial expansion and M&A targets?",
    recommendedPersona: "executive",
    description: "Demonstrates executive-only retrieval vs. public/tier-1 refusal.",
  },
  {
    id: "refusal-trap",
    label: "Out-of-Domain Refusal Trap",
    badge: "< 0.65 Gate",
    query: "How do I calibrate the quantum wormhole flux capacitor?",
    recommendedPersona: "public",
    description: "Triggers deterministic Cross-Encoder refusal with 0 LLM tokens spent.",
  },
];

export interface ChatViewportProps {
  session: DemoTokenSession | null;
  turns: ChatTurn[];
  isStreaming: boolean;
  onSendQuery: (query: string, options?: { bypassCache?: boolean }) => void;
  onStopStreaming?: () => void;
  selectedTurnId?: string | null;
  onSelectTurn?: (turnId: string) => void;
}

export function ChatViewport({
  session,
  turns,
  isStreaming,
  onSendQuery,
  onStopStreaming,
  selectedTurnId,
  onSelectTurn,
}: ChatViewportProps) {
  const [input, setInput] = useState("");
  const [bypassCache, setBypassCache] = useState(false);
  const [activeCitationState, setActiveCitationState] = useState<{
    citation: CitationItem;
    index?: number;
  } | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !session) return;
    onSendQuery(trimmed, { bypassCache });
    setInput("");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const handleScenarioClick = (scenario: GuidedScenario) => {
    if (isStreaming || !session) return;
    onSendQuery(scenario.query, { bypassCache });
  };

  const enrichedCitationsByTurn = useMemo(() => {
    const map = new Map<string, CitationItem[]>();
    for (const turn of turns) {
      map.set(
        turn.id,
        mergeCitationsWithCandidateTelemetry(turn.citations, turn.steps)
      );
    }
    return map;
  }, [turns]);

  const openCitationModal = (
    turn: ChatTurn,
    chunkId: string,
    explicitCitation?: CitationItem,
    explicitIndex?: number
  ) => {
    const enrichedList = enrichedCitationsByTurn.get(turn.id) ?? turn.citations;
    const foundIndex = enrichedList.findIndex(
      (c) =>
        c.chunk_id === chunkId ||
        c.chunk_id.toLowerCase().startsWith(chunkId.toLowerCase())
    );
    const matched =
      explicitCitation ?? (foundIndex >= 0 ? enrichedList[foundIndex] : undefined);

    if (matched) {
      setActiveCitationState({
        citation: matched,
        index: explicitIndex ?? (foundIndex >= 0 ? foundIndex : undefined),
      });
    }
  };

  return (
    <section
      aria-label="Interactive RAG Chat Viewport"
      className="flex h-full min-h-[540px] min-w-0 flex-col rounded-2xl border border-slate-800/90 bg-slate-900/50 shadow-xl overflow-hidden"
    >
      {/* Guided Enterprise Scenario Chips */}
      <div className="border-b border-slate-800/80 bg-slate-900/90 px-4 py-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            Guided Enterprise Scenarios
          </span>
          <span className="text-[11px] text-slate-500">
            Active scope:{" "}
            <span className="font-mono text-slate-300">
              {session ? `${session.tenant_id}/${session.persona}` : "initializing..."}
            </span>
          </span>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {GUIDED_SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              disabled={!session || isStreaming}
              onClick={() => handleScenarioClick(scenario)}
              title={scenario.description}
              className="group flex flex-col items-start rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-left hover:border-indigo-500/50 hover:bg-slate-900 transition-all cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed"
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-200 group-hover:text-white">
                  {scenario.label}
                </span>
                <span className="shrink-0 rounded border border-slate-700 bg-slate-800/90 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                  {scenario.badge}
                </span>
              </div>
              <span className="mt-0.5 line-clamp-1 text-[11px] text-slate-400">
                {scenario.query}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="flex-1 min-w-0 overflow-y-auto px-4 py-4 space-y-4">
        {turns.length === 0 ? (
          <div className="flex h-full min-h-[260px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-6 text-center">
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
              <FileSearch className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">
              Ready to Inspect Pre-Retrieval RBAC &amp; Grounded Generation
            </h3>
            <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-400">
              Select a Guided Enterprise Scenario above or submit a custom query. Switch
              tenants or roles in the PersonaBar and click{" "}
              <span className="font-medium text-indigo-300">
                Re-run Last Query Under New Role
              </span>{" "}
              to verify zero cross-tenant or cross-role leakage.
            </p>
          </div>
        ) : (
          turns.map((turn) => {
            const enrichedCitations =
              enrichedCitationsByTurn.get(turn.id) ?? turn.citations;
            const segments = parseTextWithCitations(turn.content);
            const isSelected = selectedTurnId === turn.id;

            return (
              <article
                key={turn.id}
                onClick={() => onSelectTurn?.(turn.id)}
                className={`rounded-2xl border p-4 transition-colors ${
                  isSelected
                    ? "border-indigo-500/60 bg-slate-900/90 shadow-lg shadow-indigo-950/20"
                    : "border-slate-800/90 bg-slate-950/60 hover:border-slate-700"
                }`}
              >
                {/* User Query Header */}
                <div className="mb-3 flex flex-wrap items-start justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
                      <User className="h-3.5 w-3.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white break-words">
                        {turn.query}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400">
                        <span className="inline-flex items-center gap-1 font-mono text-slate-300">
                          <Lock className="h-3 w-3 text-emerald-400" />
                          {turn.tenant_id}
                        </span>
                        <span>·</span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-indigo-300">
                          {turn.persona}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          scope:{turn.scope_hash.slice(0, 8)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Status / Cache / Latency Pills */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {turn.cacheHit && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-300">
                        <Zap className="h-3 w-3" />
                        Semantic Cache HIT (
                        {turn.totalLatencyMs !== null
                          ? `~${Math.round(turn.totalLatencyMs)}ms`
                          : "~20ms"}
                        )
                      </span>
                    )}
                    {turn.totalLatencyMs !== null && !turn.cacheHit && (
                      <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2 py-0.5 font-mono text-[11px] text-slate-300">
                        {turn.totalLatencyMs.toFixed(0)} ms
                      </span>
                    )}
                    {turn.isStreaming && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/40 bg-indigo-500/15 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-ping" />
                        Streaming
                      </span>
                    )}
                  </div>
                </div>

                {/* Assistant / Refusal Response Body */}
                <div className="flex items-start gap-2.5">
                  <div
                    className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
                      turn.refusal?.refused
                        ? "bg-amber-500/15 border-amber-500/40 text-amber-300"
                        : "bg-indigo-500/15 border-indigo-500/40 text-indigo-300"
                    }`}
                  >
                    {turn.refusal?.refused ? (
                      <ShieldAlert className="h-3.5 w-3.5" />
                    ) : (
                      <Bot className="h-3.5 w-3.5" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1 space-y-3">
                    {/* Deterministic Refusal Gate Alert Banner */}
                    {turn.refusal?.refused && (
                      <div
                        role="alert"
                        className="rounded-xl border border-amber-500/50 bg-gradient-to-br from-amber-950/60 via-rose-950/35 to-slate-950 p-4 shadow-inner"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2 text-amber-200">
                            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                            <span className="text-xs font-bold uppercase tracking-wider">
                              Deterministic Refusal Gate Triggered
                            </span>
                          </div>
                          <span className="rounded-md border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-rose-200">
                            {turn.refusal.reason ?? "below_confidence_threshold"}
                          </span>
                        </div>

                        <p className="mt-2 text-sm leading-relaxed text-amber-100">
                          {turn.refusal.message}
                        </p>

                        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-amber-500/20 pt-2.5 text-xs">
                          <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900/90 px-2 py-1 font-mono text-[11px] text-slate-200">
                            Top Cross-Encoder Score:{" "}
                            <strong className="text-rose-300">
                              {turn.refusal.top_score.toFixed(4)}
                            </strong>{" "}
                            &lt; {turn.refusal.threshold.toFixed(2)} Threshold
                          </span>

                          <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-1 font-mono text-[11px] font-semibold text-emerald-300">
                            <Cpu className="h-3.5 w-3.5" />
                            LLM Called: FALSE (0 Tokens Spent — Hallucination Prevented)
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Streamed Answer with Inline Clickable [chunk_id] Badges */}
                    {turn.content && (
                      <div className="text-sm leading-relaxed text-slate-200 whitespace-pre-wrap break-words">
                        {segments.map((segment, idx) => {
                          if (segment.type === "text") {
                            return <React.Fragment key={idx}>{segment.value}</React.Fragment>;
                          }

                          const citIndex = enrichedCitations.findIndex(
                            (c) =>
                              c.chunk_id === segment.chunkId ||
                              c.chunk_id
                                .toLowerCase()
                                .startsWith(segment.chunkId.toLowerCase())
                          );
                          const matchedCitation =
                            citIndex >= 0 ? enrichedCitations[citIndex] : undefined;

                          return (
                            <button
                              key={`${segment.chunkId}-${idx}`}
                              type="button"
                              disabled={!matchedCitation}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (matchedCitation) {
                                  openCitationModal(
                                    turn,
                                    segment.chunkId,
                                    matchedCitation,
                                    citIndex
                                  );
                                }
                              }}
                              title={
                                matchedCitation
                                  ? `Inspect source: ${matchedCitation.document_title} (${(
                                      matchedCitation.rerank_score * 100
                                    ).toFixed(1)}%)`
                                  : `Source chunk ${segment.chunkId}`
                              }
                              className={`mx-0.5 inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 align-baseline font-mono text-[11px] font-semibold transition-colors ${
                                matchedCitation
                                  ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-300 hover:bg-cyan-500/30 hover:text-white cursor-pointer"
                                  : "border-slate-700 bg-slate-800 text-slate-400 cursor-default"
                              }`}
                            >
                              <span>
                                {citIndex >= 0
                                  ? `[#${citIndex + 1} · ${segment.chunkId.slice(0, 8)}]`
                                  : segment.raw}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {turn.isStreaming && !turn.content && !turn.refusal && (
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
                        Executing 6-Step RBAC RAG Pipeline...
                      </div>
                    )}

                    {turn.error && (
                      <div
                        role="alert"
                        className="rounded-xl border border-rose-500/40 bg-rose-950/40 px-3 py-2 text-xs text-rose-200"
                      >
                        Pipeline Error: {turn.error}
                      </div>
                    )}

                    {/* Source Citation Footer Pills */}
                    {enrichedCitations.length > 0 && (
                      <div className="border-t border-slate-800/80 pt-2.5">
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                            Verified Sources ({enrichedCitations.length})
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Click any citation to inspect chunk text &amp; RRF ranks
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {enrichedCitations.map((citation, idx) => (
                            <button
                              key={citation.chunk_id}
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                openCitationModal(
                                  turn,
                                  citation.chunk_id,
                                  citation,
                                  idx
                                );
                              }}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-900 px-2.5 py-1 text-left text-xs text-slate-200 hover:border-cyan-500/50 hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <span className="font-mono text-[10px] font-semibold text-cyan-400">
                                #{idx + 1}
                              </span>
                              <span className="max-w-[180px] truncate font-medium">
                                {citation.document_title}
                              </span>
                              <span className="font-mono text-[10px] text-emerald-300">
                                {(citation.rerank_score * 100).toFixed(1)}%
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>

      {/* Query Composer */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-slate-800/90 bg-slate-900/95 p-3"
      >
        <div className="flex flex-col gap-2">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!session || isStreaming}
              placeholder={
                session
                  ? `Ask a question as ${session.tenant_id} (${session.persona})...`
                  : "Initializing JWT security session..."
              }
              aria-label="Enterprise RAG query input"
              className="flex-1 min-w-0 resize-none rounded-xl border border-slate-700/90 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
            />

            {isStreaming && onStopStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-xl border border-rose-500/50 bg-rose-600/20 px-4 text-xs font-semibold text-rose-200 hover:bg-rose-600/35 transition-colors cursor-pointer"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!session || isStreaming || !input.trim()}
                className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-xl bg-indigo-600 px-4 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ArrowUp className="h-4 w-4" />
                Send
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-slate-400">
            <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={bypassCache}
                onChange={(e) => setBypassCache(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-indigo-500"
              />
              <span>Bypass Step 2 Semantic Cache (force live Hybrid RRF + Rerank)</span>
            </label>
            <span className="text-slate-500">
              Press <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-[10px]">Enter</kbd> to send ·{" "}
              <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-[10px]">Shift+Enter</kbd> for newline
            </span>
          </div>
        </div>
      </form>

      {/* Source Inspection Popover */}
      <CitationPopover
        citation={activeCitationState?.citation ?? null}
        citationIndex={activeCitationState?.index}
        onClose={() => setActiveCitationState(null)}
      />
    </section>
  );
}
