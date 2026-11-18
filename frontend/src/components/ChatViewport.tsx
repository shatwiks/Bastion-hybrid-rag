"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUp,
  ChevronDown,
  FileSearch,
  ShieldAlert,
  Square,
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
    description:
      "Tests exact technical error-code recall via hybrid lexical + dense retrieval.",
  },
  {
    id: "hardware-sku",
    label: "Hardware SKU Lookup (Tier 1)",
    badge: "SKU Exact Match",
    query: "What are the specifications and thermal limits for SKU-9921-A?",
    recommendedPersona: "support_tier_1",
    description:
      "Verifies hyphenated SKU token preservation and technical grounding.",
  },
  {
    id: "executive-ma",
    label: "Executive M&A Strategy (Executive Only)",
    badge: "RBAC Boundary",
    query: "What are the confidential Q3 financial expansion and M&A targets?",
    recommendedPersona: "executive",
    description:
      "Demonstrates executive-only retrieval vs. public/tier-1 refusal.",
  },
  {
    id: "refusal-trap",
    label: "Out-of-Domain Refusal Trap",
    badge: "< 0.65 Gate",
    query: "How do I calibrate the quantum wormhole flux capacitor?",
    recommendedPersona: "public",
    description:
      "Triggers deterministic Cross-Encoder refusal with 0 LLM tokens spent.",
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

function renderFormattedText(value: string): React.ReactNode {
  const parts = value.split(/(`[^`\n]+`)/g);
  return parts.map((part, i) => {
    if (part.length >= 2 && part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded border border-[var(--rule)] bg-[var(--ground)] px-1.5 py-0.5 font-mono text-[12.5px] text-[var(--ink)] break-all"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
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
  const [showQuickScenarios, setShowQuickScenarios] = useState(false);
  const [activeCitationState, setActiveCitationState] = useState<{
    citation: CitationItem;
    index?: number;
  } | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const threadEndRef = useRef<HTMLDivElement | null>(null);

  const latestTurn = turns.length > 0 ? turns[turns.length - 1] : null;
  const latestRefused = Boolean(latestTurn?.refusal?.refused);
  const latestDone = Boolean(latestTurn && !latestTurn.isStreaming);

  useEffect(() => {
    if (turns.length === 0) return;
    threadEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, latestRefused, latestDone]);

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !session) return;
    onSendQuery(trimmed, { bypassCache });
    setInput("");
    setShowQuickScenarios(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const handleScenarioClick = (scenario: GuidedScenario) => {
    if (isStreaming || !session) return;
    setShowQuickScenarios(false);
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
      className="flex h-full min-h-[540px] min-w-0 flex-col bg-[var(--paper)]"
    >
      {/* Conversation Thread / Empty State */}
      <div className="min-w-0 flex-1 overflow-y-auto px-5 py-6 sm:px-8">
        {turns.length === 0 ? (
          <div className="mx-auto flex h-full max-w-[68ch] flex-col justify-center py-6">
            <div className="mb-6">
              <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
                Ask your authorized knowledge base
              </h1>
              <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-secondary)]">
                Every query runs pre-retrieval SQL RBAC, hybrid dense + BM25 search, and a{" "}
                <span className="font-mono text-[13px] text-[var(--ink)]">0.65</span>{" "}
                Cross-Encoder refusal gate.
                {session && (
                  <>
                    {" "}
                    Active scope:{" "}
                    <span className="font-mono text-[12.5px] font-medium text-[var(--ink)]">
                      {session.tenant_id}
                    </span>{" "}
                    ({session.allowed_roles.join(", ")}).
                  </>
                )}
              </p>
            </div>

            {/* Clean Hairline Scenario List (collapses once first turn begins) */}
            <div className="border-t border-[var(--rule)]">
              <div className="flex items-center justify-between py-2.5 text-xs font-medium text-[var(--ink-muted)]">
                <span>Guided Enterprise Scenarios</span>
                <span className="hidden sm:inline">Click any row to execute live</span>
              </div>
              <div className="divide-y divide-[var(--rule)] border-t border-b border-[var(--rule)]">
                {GUIDED_SCENARIOS.map((scenario) => (
                  <button
                    key={scenario.id}
                    type="button"
                    disabled={isStreaming || !session}
                    onClick={() => handleScenarioClick(scenario)}
                    className="group flex w-full items-start justify-between gap-4 py-3 text-left transition-colors duration-150 hover:bg-[var(--ground)]/70 px-2.5 -mx-2.5 rounded cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-[var(--ink)] group-hover:text-[var(--copper)] transition-colors">
                          {scenario.label}
                        </span>
                        <span className="rounded border border-[var(--rule)] bg-[var(--ground)] px-1.5 py-0.5 font-mono text-[10.5px] font-medium text-[var(--ink-secondary)]">
                          {scenario.badge}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs leading-relaxed text-[var(--ink-secondary)]">
                        {scenario.query}
                      </p>
                    </div>
                    <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[var(--ink-muted)] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-[var(--copper)]" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-[74ch] divide-y divide-[var(--rule)]">
            {turns.map((turn) => {
              const isSelected = selectedTurnId === turn.id;
              const enrichedCitations =
                enrichedCitationsByTurn.get(turn.id) ?? turn.citations;
              const parsedSegments = parseTextWithCitations(turn.content);

              return (
                <article
                  key={turn.id}
                  onClick={() => onSelectTurn?.(turn.id)}
                  className={`py-6 first:pt-1 transition-colors duration-150 ${
                    onSelectTurn ? "cursor-pointer" : ""
                  }`}
                >
                  {/* User Query Header */}
                  <div
                    className={`rounded border px-4 py-3 transition-colors ${
                      isSelected
                        ? "border-[var(--copper-rule)] bg-[var(--ground)]/85"
                        : "border-[var(--rule)] bg-[var(--ground)]/45 hover:border-[var(--rule-strong)]"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[var(--ink-muted)]">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono font-medium text-[var(--ink-secondary)]">
                          {turn.tenant_id}
                        </span>
                        <span>/</span>
                        <span className="font-mono text-[var(--ink-secondary)]">
                          {turn.persona}
                        </span>
                        <span className="font-mono text-[10.5px]">
                          scope:{turn.scope_hash.slice(0, 8)}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {turn.cacheHit && (
                          <span className="inline-flex items-center gap-1 rounded border border-[var(--jade-rule)] bg-[var(--jade-soft)] px-1.5 py-0.5 font-mono text-[10.5px] font-semibold text-[var(--jade)]">
                            <Zap className="h-3 w-3" />
                            Semantic Cache HIT
                            {typeof turn.totalLatencyMs === "number"
                              ? ` (~${Math.round(turn.totalLatencyMs)}ms)`
                              : ""}
                          </span>
                        )}
                        {typeof turn.totalLatencyMs === "number" && (
                          <span className="font-mono tabular-nums text-[11px] text-[var(--ink-muted)]">
                            {turn.totalLatencyMs.toFixed(0)} ms
                          </span>
                        )}
                        {isSelected && (
                          <span className="text-[10.5px] font-semibold text-[var(--copper)]">
                            Inspecting
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="mt-1.5 text-[15px] font-semibold leading-snug text-[var(--ink)]">
                      {turn.query}
                    </p>
                  </div>

                  {/* Assistant Response Area */}
                  <div className="mt-4 pl-1">
                    {/* Deterministic Refusal Banner */}
                    {turn.refusal?.refused ? (
                      <div
                        role="alert"
                        className="rounded border border-[var(--crimson-rule)] bg-[var(--crimson-soft)] p-4"
                      >
                        <div className="flex items-start gap-3">
                          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[var(--crimson)]" />
                          <div className="min-w-0 flex-1 space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <h3 className="text-sm font-semibold text-[var(--crimson)]">
                                Deterministic Refusal Gate Triggered
                              </h3>
                              <span className="rounded border border-[var(--crimson-rule)] bg-[var(--paper)] px-2 py-0.5 font-mono text-[11px] font-medium text-[var(--crimson)]">
                                {turn.refusal.reason}
                              </span>
                            </div>

                            <p className="max-w-[65ch] text-sm leading-relaxed text-[var(--ink)]">
                              {turn.refusal.message}
                            </p>

                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-[var(--crimson-rule)]/70 pt-2 font-mono text-[11px] tabular-nums text-[var(--ink-secondary)]">
                              <span>
                                Top Cross-Encoder:{" "}
                                <strong className="text-[var(--crimson)]">
                                  {turn.refusal.top_score.toFixed(4)}
                                </strong>{" "}
                                &lt; {turn.refusal.threshold.toFixed(2)}
                              </span>
                              <span>
                                LLM Called:{" "}
                                <strong className="text-[var(--jade)]">
                                  FALSE (0 Tokens Spent — Hallucination Prevented)
                                </strong>
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : turn.error ? (
                      <div
                        role="alert"
                        className="flex items-start gap-2.5 rounded border border-[var(--crimson-rule)] bg-[var(--crimson-soft)] p-3.5 text-sm text-[var(--crimson)]"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <div>
                          <div className="font-semibold">
                            Pipeline request failed
                          </div>
                          <p className="mt-0.5 text-xs text-[var(--ink)]">
                            {turn.error}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {/* Grounded Streaming Prose (68ch reading measure) */}
                        <div className="max-w-[68ch] whitespace-pre-wrap break-words text-[15px] leading-[1.68] text-[var(--ink)]">
                          {parsedSegments.length > 0 ? (
                            parsedSegments.map((seg, idx) => {
                              if (seg.type === "text") {
                                return (
                                  <React.Fragment key={idx}>
                                    {renderFormattedText(seg.value)}
                                  </React.Fragment>
                                );
                              }

                              const citIndex = enrichedCitations.findIndex(
                                (c) =>
                                  c.chunk_id === seg.chunkId ||
                                  c.chunk_id
                                    .toLowerCase()
                                    .startsWith(seg.chunkId.toLowerCase())
                              );
                              const matchedCitation =
                                citIndex >= 0
                                  ? enrichedCitations[citIndex]
                                  : undefined;
                              const shortLabel =
                                citIndex >= 0
                                  ? `#${citIndex + 1} · ${seg.chunkId.slice(0, 8)}`
                                  : seg.chunkId.slice(0, 8);

                              return (
                                <button
                                  key={idx}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openCitationModal(
                                      turn,
                                      seg.chunkId,
                                      matchedCitation,
                                      citIndex >= 0 ? citIndex : undefined
                                    );
                                  }}
                                  title={
                                    matchedCitation
                                      ? `${matchedCitation.document_title} — ${matchedCitation.section_header} (${(
                                          matchedCitation.rerank_score * 100
                                        ).toFixed(1)}%)`
                                      : `Inspect source chunk ${seg.chunkId}`
                                  }
                                  className="mx-0.5 inline-flex items-center rounded border border-[var(--copper-rule)] bg-[var(--copper-soft)] px-1.5 py-0.5 align-baseline font-mono text-[11px] font-semibold text-[var(--copper)] transition-colors duration-150 hover:border-[var(--copper)] hover:bg-[var(--copper)] hover:text-[#FCFBF8] cursor-pointer"
                                >
                                  [{shortLabel}]
                                </button>
                              );
                            })
                          ) : turn.isStreaming ? (
                            <div className="space-y-2 py-1" aria-live="polite">
                              <div className="h-3.5 w-3/4 animate-pulse rounded bg-[var(--mineral)]" />
                              <div className="h-3.5 w-1/2 animate-pulse rounded bg-[var(--mineral)]" />
                              <p className="pt-1 font-mono text-xs text-[var(--ink-muted)]">
                                Executing RBAC retrieval &amp; Cross-Encoder verification…
                              </p>
                            </div>
                          ) : null}

                          {turn.isStreaming && turn.content.length > 0 && (
                            <span
                              aria-hidden="true"
                              className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-[var(--copper)]"
                            />
                          )}
                        </div>

                        {/* Verified Sources Hairline Strip */}
                        {enrichedCitations.length > 0 && (
                          <div className="border-t border-[var(--rule)] pt-3">
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                              <span className="inline-flex items-center gap-1.5 font-semibold text-[var(--ink-secondary)]">
                                <FileSearch className="h-3.5 w-3.5 text-[var(--jade)]" />
                                Verified Sources ({enrichedCitations.length})
                              </span>
                              <span className="text-[11px] text-[var(--ink-muted)]">
                                Select a source to inspect chunk text, ACL &amp; RRF ranks
                              </span>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              {enrichedCitations.map((cit, citIdx) => (
                                <button
                                  key={cit.chunk_id}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openCitationModal(
                                      turn,
                                      cit.chunk_id,
                                      cit,
                                      citIdx
                                    );
                                  }}
                                  className="inline-flex max-w-full items-center gap-2 rounded border border-[var(--rule)] bg-[var(--ground)] px-2.5 py-1 text-left text-xs text-[var(--ink)] transition-colors duration-150 hover:border-[var(--copper)] hover:bg-[var(--copper-soft)] cursor-pointer"
                                >
                                  <span className="font-mono text-[11px] font-semibold text-[var(--copper)]">
                                    #{citIdx + 1}
                                  </span>
                                  <span className="max-w-[200px] truncate font-medium">
                                    {cit.document_title}
                                  </span>
                                  <span className="font-mono text-[11px] tabular-nums text-[var(--jade)]">
                                    {(cit.rerank_score * 100).toFixed(1)}%
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
            <div ref={threadEndRef} aria-hidden="true" className="h-1" />
          </div>
        )}
      </div>

      {/* Collapsible Preset Scenarios Strip (available once chat has started) */}
      {turns.length > 0 && showQuickScenarios && (
        <div className="border-t border-[var(--rule)] bg-[var(--ground)] px-5 py-3 sm:px-8">
          <div className="mx-auto max-w-[74ch]">
            <div className="mb-2 flex items-center justify-between text-xs font-medium text-[var(--ink-secondary)]">
              <span>Guided Enterprise Scenarios</span>
              <button
                type="button"
                onClick={() => setShowQuickScenarios(false)}
                className="text-[var(--ink-muted)] hover:text-[var(--ink)] cursor-pointer"
              >
                Hide
              </button>
            </div>
            <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {GUIDED_SCENARIOS.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  disabled={isStreaming || !session}
                  onClick={() => handleScenarioClick(scenario)}
                  className="flex items-center justify-between gap-2 rounded border border-[var(--rule)] bg-[var(--paper)] px-3 py-2 text-left text-xs transition-colors hover:border-[var(--copper)] cursor-pointer disabled:opacity-50"
                >
                  <span className="truncate font-medium text-[var(--ink)]">
                    {scenario.label}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-[var(--ink-muted)]">
                    {scenario.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Query Composer */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-[var(--rule)] bg-[var(--paper)] px-5 py-3.5 sm:px-8"
      >
        <div className="mx-auto max-w-[74ch]">
          <div className="flex items-end gap-2 rounded-[5px] border border-[var(--rule-strong)] bg-[var(--paper)] p-1.5 transition-colors focus-within:border-[var(--copper)]">
            <textarea
              ref={inputRef}
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!session || isStreaming}
              placeholder={
                session
                  ? `Ask a question as ${session.tenant_id} (${session.persona})…`
                  : "Initializing security session…"
              }
              aria-label="Ask enterprise RAG question"
              className="max-h-36 min-h-[44px] flex-1 resize-none bg-transparent px-2.5 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:outline-none disabled:opacity-60"
            />

            {isStreaming && onStopStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                aria-label="Stop streaming response"
                className="inline-flex h-10 items-center gap-1.5 rounded bg-[var(--crimson)] px-3.5 text-xs font-semibold text-[#FCFBF8] transition-colors hover:bg-[#8e2020] cursor-pointer"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || !session || isStreaming}
                aria-label="Send query"
                className="inline-flex h-10 items-center gap-1.5 rounded bg-[var(--copper)] px-4 text-xs font-semibold text-[#FCFBF8] transition-colors duration-150 hover:bg-[var(--copper-hover)] active:translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-45"
              >
                <span>Ask</span>
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--ink-muted)]">
            <div className="flex flex-wrap items-center gap-4">
              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={bypassCache}
                  onChange={(e) => setBypassCache(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-[var(--rule-strong)] accent-[var(--copper)]"
                />
                <span>Bypass semantic cache</span>
              </label>

              {turns.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowQuickScenarios((prev) => !prev)}
                  className="inline-flex items-center gap-1 font-medium text-[var(--ink-secondary)] hover:text-[var(--copper)] cursor-pointer"
                >
                  <span>Guided Scenarios</span>
                  <ChevronDown
                    className={`h-3.5 w-3.5 transition-transform duration-150 ${
                      showQuickScenarios ? "rotate-180" : ""
                    }`}
                  />
                </button>
              )}
            </div>

            <span className="hidden sm:inline">
              Enter to send · Shift+Enter for newline
            </span>
          </div>
        </div>
      </form>

      {/* Source Inspection Modal */}
      <CitationPopover
        citation={activeCitationState?.citation ?? null}
        citationIndex={activeCitationState?.index}
        onClose={() => setActiveCitationState(null)}
      />
    </section>
  );
}
