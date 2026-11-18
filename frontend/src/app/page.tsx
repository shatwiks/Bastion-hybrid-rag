"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { AdminIngestionModal } from "@/components/AdminIngestionModal";
import { ChatViewport } from "@/components/ChatViewport";
import { PersonaBar } from "@/components/PersonaBar";
import { TelemetryInspectorDrawer } from "@/components/TelemetryInspectorDrawer";
import {
  fetchHealthStatus,
  mintDemoToken,
  streamChatQuery,
} from "@/lib/sse-client";
import type {
  ChatHistoryMessage,
  ChatTurn,
  DemoTokenSession,
  HealthStatusResponse,
  PipelineStepUpdate,
} from "@/types/rag";

function upsertPipelineStep(
  steps: PipelineStepUpdate[],
  incoming: PipelineStepUpdate
): PipelineStepUpdate[] {
  const index = steps.findIndex((s) => s.step === incoming.step);
  if (index === -1) {
    return [...steps, incoming].sort((a, b) => a.step - b.step);
  }
  const updated = [...steps];
  updated[index] = incoming;
  return updated;
}

export default function EnterpriseRagWorkspacePage() {
  const [session, setSession] = useState<DemoTokenSession | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);

  const [health, setHealth] = useState<HealthStatusResponse | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState<boolean>(false);

  const streamAbortRef = useRef<AbortController | null>(null);

  const initializeDemoSession = useCallback(async (signal?: AbortSignal) => {
    setIsInitializing(true);
    setInitError(null);
    try {
      const demoSession = await mintDemoToken(
        "acme_corp",
        "support_tier_1",
        signal
      );
      setSession(demoSession);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      const msg =
        err instanceof Error
          ? err.message
          : "Unable to initialize demo security session (backend may still be starting)";
      setInitError(msg);
    } finally {
      setIsInitializing(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    initializeDemoSession(controller.signal);
    return () => controller.abort();
  }, [initializeDemoSession]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const checkHealth = async () => {
      try {
        const res = await fetchHealthStatus(controller.signal);
        if (active) {
          setHealth(res);
        }
      } catch {
        if (active) {
          setHealth(null);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      active = false;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const activeTurn = useMemo(() => {
    if (turns.length === 0) return null;
    if (selectedTurnId) {
      const matched = turns.find((t) => t.id === selectedTurnId);
      if (matched) return matched;
    }
    return turns[turns.length - 1];
  }, [turns, selectedTurnId]);

  const executeQuery = useCallback(
    async (
      query: string,
      targetSession: DemoTokenSession,
      options?: { bypassCache?: boolean }
    ) => {
      const trimmed = query.trim();
      if (!trimmed || isStreaming) return;

      streamAbortRef.current?.abort();
      const abortController = new AbortController();
      streamAbortRef.current = abortController;

      const turnId = `turn-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      // Scope conversational history strictly to turns inside the same tenant + RBAC scope_hash
      const scopedHistory: ChatHistoryMessage[] = [];
      for (const prior of turns) {
        if (
          prior.tenant_id === targetSession.tenant_id &&
          prior.scope_hash === targetSession.scope_hash &&
          !prior.error &&
          !prior.refusal?.refused &&
          prior.content.trim()
        ) {
          scopedHistory.push({ role: "user", content: prior.query });
          scopedHistory.push({ role: "assistant", content: prior.content });
        }
      }

      const initialTurn: ChatTurn = {
        id: turnId,
        role: "assistant",
        query: trimmed,
        content: "",
        tenant_id: targetSession.tenant_id,
        persona: targetSession.persona,
        allowed_roles: targetSession.allowed_roles,
        scope_hash: targetSession.scope_hash,
        isStreaming: true,
        steps: [],
        citations: [],
        refusal: null,
        cacheHit: false,
        cacheSimilarity: null,
        llmCalled: null,
        traceId: null,
        totalLatencyMs: null,
        error: null,
        createdAt: new Date().toISOString(),
      };

      setTurns((prev) => [...prev, initialTurn]);
      setSelectedTurnId(turnId);
      setLastQuery(trimmed);
      setIsStreaming(true);

      const updateTurn = (updater: (current: ChatTurn) => ChatTurn) => {
        setTurns((prev) =>
          prev.map((item) => (item.id === turnId ? updater(item) : item))
        );
      };

      try {
        await streamChatQuery(
          targetSession.access_token,
          {
            query: trimmed,
            chat_history: scopedHistory.slice(-6),
            bypass_cache: options?.bypassCache ?? false,
          },
          {
            onStepUpdate: (stepUpdate) => {
              updateTurn((current) => {
                const nextSteps = upsertPipelineStep(current.steps, stepUpdate);
                let nextCacheHit = current.cacheHit;
                let nextCacheSimilarity = current.cacheSimilarity;

                if (stepUpdate.step === 2) {
                  if (typeof stepUpdate.details.cache_hit === "boolean") {
                    nextCacheHit = stepUpdate.details.cache_hit;
                  }
                  if (typeof stepUpdate.details.similarity_score === "number") {
                    nextCacheSimilarity = stepUpdate.details.similarity_score;
                  }
                }

                return {
                  ...current,
                  steps: nextSteps,
                  cacheHit: nextCacheHit,
                  cacheSimilarity: nextCacheSimilarity,
                };
              });
            },
            onToken: (delta) => {
              updateTurn((current) => ({
                ...current,
                content: current.content + delta,
              }));
            },
            onCitations: (citations) => {
              updateTurn((current) => ({
                ...current,
                citations,
              }));
            },
            onRefusal: (refusal) => {
              updateTurn((current) => ({
                ...current,
                refusal,
              }));
            },
            onDone: (done) => {
              updateTurn((current) => ({
                ...current,
                isStreaming: false,
                traceId: done.trace_id,
                totalLatencyMs: done.total_latency_ms,
                cacheHit: done.cache_hit,
                llmCalled: done.llm_called,
              }));
            },
            onError: (err) => {
              updateTurn((current) => ({
                ...current,
                isStreaming: false,
                error: err.message,
              }));
            },
          },
          abortController.signal
        );
      } catch {
        // Error state already propagated through onError callback
      } finally {
        updateTurn((current) =>
          current.isStreaming ? { ...current, isStreaming: false } : current
        );
        setIsStreaming(false);
      }
    },
    [isStreaming, turns]
  );

  const handleSendQuery = useCallback(
    (query: string, options?: { bypassCache?: boolean }) => {
      if (!session) return;
      void executeQuery(query, session, options);
    },
    [executeQuery, session]
  );

  const handleRerunLastQuery = useCallback(
    (overrideSession?: DemoTokenSession) => {
      const target = overrideSession ?? session;
      if (!target || !lastQuery.trim()) return;
      void executeQuery(lastQuery, target);
    },
    [executeQuery, lastQuery, session]
  );

  const handleStopStreaming = useCallback(() => {
    streamAbortRef.current?.abort();
    setIsStreaming(false);
    setTurns((prev) =>
      prev.map((item) =>
        item.isStreaming ? { ...item, isStreaming: false } : item
      )
    );
  }, []);

  return (
    <div className="flex min-h-screen w-full min-w-0 flex-col overflow-x-clip bg-slate-950 text-slate-100">
      <PersonaBar
        session={session}
        onSessionChange={(nextSession) => setSession(nextSession)}
        lastQuery={lastQuery}
        onRerunLastQuery={handleRerunLastQuery}
        onOpenAdminModal={() => setIsAdminModalOpen(true)}
        isStreaming={isStreaming}
        isInspectorOpen={isInspectorOpen}
        onToggleInspector={() => setIsInspectorOpen((prev) => !prev)}
        health={health}
      />

      {initError && !session && (
        <div
          role="alert"
          className="mx-auto mt-3 flex w-full max-w-[1680px] items-center justify-between gap-3 px-4 lg:px-6"
        >
          <div className="flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-950/40 px-4 py-2.5 text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
              <span>
                Backend session initialization pending: {initError}. Ensure the
                FastAPI server is running on port 8000.
              </span>
            </div>
            <button
              type="button"
              disabled={isInitializing}
              onClick={() => void initializeDemoSession()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/50 bg-amber-500/15 px-3 py-1 font-medium text-amber-100 hover:bg-amber-500/30 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isInitializing ? "animate-spin" : ""}`}
              />
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Split-Pane Enterprise Workspace (60% Chat / 40% Collapsible Telemetry Inspector) */}
      <main className="mx-auto flex w-full max-w-[1680px] min-w-0 flex-1 flex-col gap-4 p-4 lg:flex-row lg:items-stretch lg:px-6 lg:py-4">
        <div
          className={`flex min-h-0 min-w-0 flex-col transition-all duration-200 ${
            isInspectorOpen ? "w-full lg:w-[60%]" : "w-full"
          }`}
        >
          <ChatViewport
            session={session}
            turns={turns}
            isStreaming={isStreaming}
            onSendQuery={handleSendQuery}
            onStopStreaming={handleStopStreaming}
            selectedTurnId={activeTurn?.id ?? null}
            onSelectTurn={(id) => setSelectedTurnId(id)}
          />
        </div>

        {isInspectorOpen && (
          <div className="flex min-h-0 min-w-0 w-full flex-col lg:w-[40%]">
            <TelemetryInspectorDrawer
              turn={activeTurn}
              session={session}
              isOpen={isInspectorOpen}
              onCollapse={() => setIsInspectorOpen(false)}
            />
          </div>
        )}
      </main>

      <AdminIngestionModal
        isOpen={isAdminModalOpen}
        onClose={() => setIsAdminModalOpen(false)}
        session={session}
      />
    </div>
  );
}
