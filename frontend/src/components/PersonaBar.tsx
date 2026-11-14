"use client";

import React, { useState } from "react";
import {
  Building2,
  DatabaseZap,
  KeyRound,
  Lock,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  ShieldCheck,
  Upload,
  Users,
} from "lucide-react";

import { mintDemoToken } from "@/lib/sse-client";
import type {
  DemoTokenSession,
  HealthStatusResponse,
  PersonaType,
  TenantId,
} from "@/types/rag";

const TENANT_OPTIONS: Array<{ id: TenantId; label: string }> = [
  { id: "acme_corp", label: "Acme Corp" },
  { id: "globex_corp", label: "Globex Corp" },
];

const PERSONA_OPTIONS: Array<{
  id: PersonaType;
  label: string;
  tierDescription: string;
  activeClass: string;
}> = [
  {
    id: "public",
    label: "Public",
    tierDescription: "public only",
    activeClass:
      "bg-sky-500/20 text-sky-200 border-sky-400/60 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]",
  },
  {
    id: "support_tier_1",
    label: "Support Tier 1",
    tierDescription: "public + support_tier_1",
    activeClass:
      "bg-indigo-500/20 text-indigo-200 border-indigo-400/60 shadow-[0_0_0_1px_rgba(129,140,248,0.25)]",
  },
  {
    id: "executive",
    label: "Executive",
    tierDescription: "public + support_tier_1 + executive",
    activeClass:
      "bg-amber-500/20 text-amber-200 border-amber-400/60 shadow-[0_0_0_1px_rgba(251,191,36,0.25)]",
  },
];

export interface PersonaBarProps {
  session: DemoTokenSession | null;
  onSessionChange: (session: DemoTokenSession) => void;
  lastQuery: string;
  onRerunLastQuery: (overrideSession?: DemoTokenSession) => void;
  onOpenAdminModal: () => void;
  isStreaming?: boolean;
  isInspectorOpen?: boolean;
  onToggleInspector?: () => void;
  health?: HealthStatusResponse | null;
}

export function PersonaBar({
  session,
  onSessionChange,
  lastQuery,
  onRerunLastQuery,
  onOpenAdminModal,
  isStreaming = false,
  isInspectorOpen,
  onToggleInspector,
  health,
}: PersonaBarProps) {
  const [isMinting, setIsMinting] = useState(false);
  const [mintError, setMintError] = useState<string | null>(null);

  const activeTenant: TenantId = session?.tenant_id ?? "acme_corp";
  const activePersona: PersonaType = session?.persona ?? "public";

  const handleSwitch = async (nextTenant: TenantId, nextPersona: PersonaType) => {
    if (
      isMinting ||
      isStreaming ||
      (session &&
        session.tenant_id === nextTenant &&
        session.persona === nextPersona)
    ) {
      return;
    }

    setIsMinting(true);
    setMintError(null);
    try {
      const nextSession = await mintDemoToken(nextTenant, nextPersona);
      onSessionChange(nextSession);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to mint demo JWT token";
      setMintError(msg);
    } finally {
      setIsMinting(false);
    }
  };

  const canRerun = Boolean(lastQuery.trim()) && Boolean(session) && !isStreaming && !isMinting;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/90 bg-slate-950/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1680px] flex-col gap-2.5 px-4 py-3 lg:flex-row lg:items-center lg:justify-between lg:px-6">
        {/* Left: Brand + Tenant + Persona Selectors */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-2 border-r border-slate-800">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-tight text-slate-100">
                  Enterprise RAG
                </span>
                {health && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium border ${
                      health.status === "ok"
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                        : "bg-amber-500/10 text-amber-300 border-amber-500/30"
                    }`}
                    title={`Postgres: ${health.postgres} | Redis: ${health.redis}`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        health.status === "ok" ? "bg-emerald-400" : "bg-amber-400"
                      }`}
                    />
                    {health.status === "ok" ? "LIVE" : "DEGRADED"}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 leading-tight">
                Pre-Retrieval RBAC Isolation
              </p>
            </div>
          </div>

          {/* Tenant Selector */}
          <div
            className="inline-flex items-center rounded-lg border border-slate-800 bg-slate-900/90 p-0.5"
            role="group"
            aria-label="Tenant Selector"
          >
            <span className="px-2 text-[11px] font-medium text-slate-400 inline-flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5 text-slate-500" />
              Tenant
            </span>
            {TENANT_OPTIONS.map((tenant) => {
              const selected = activeTenant === tenant.id;
              return (
                <button
                  key={tenant.id}
                  type="button"
                  aria-pressed={selected}
                  disabled={isMinting || isStreaming}
                  onClick={() => handleSwitch(tenant.id, activePersona)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                    selected
                      ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                      : "text-slate-400 hover:text-slate-200 border border-transparent"
                  }`}
                >
                  {tenant.label}
                </button>
              );
            })}
          </div>

          {/* Role Persona Pills */}
          <div
            className="inline-flex flex-wrap items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/90 p-0.5"
            role="group"
            aria-label="Role Persona Selector"
          >
            <span className="px-2 text-[11px] font-medium text-slate-400 inline-flex items-center gap-1">
              <Users className="h-3.5 w-3.5 text-slate-500" />
              Role
            </span>
            {PERSONA_OPTIONS.map((persona) => {
              const selected = activePersona === persona.id;
              return (
                <button
                  key={persona.id}
                  type="button"
                  aria-pressed={selected}
                  disabled={isMinting || isStreaming}
                  title={`Roles: ${persona.tierDescription}`}
                  onClick={() => handleSwitch(activeTenant, persona.id)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                    selected
                      ? persona.activeClass
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {persona.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Center/Right: Live SecurityContext Badge + Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 lg:justify-end">
          {/* Security Context Display */}
          <div
            className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/75 px-3 py-1.5 text-xs"
            aria-label="Active JWT Security Context"
          >
            <div className="flex items-center gap-1.5 text-slate-400">
              {isMinting ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-indigo-400" />
              ) : (
                <Lock className="h-3.5 w-3.5 text-emerald-400" />
              )}
              <span className="font-mono text-[11px] text-slate-300">
                {session ? session.tenant_id : activeTenant}
              </span>
            </div>

            <span className="text-slate-700">|</span>

            <div className="flex flex-wrap items-center gap-1">
              {(session?.allowed_roles ?? ["public"]).map((role) => (
                <span
                  key={role}
                  className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-200 border border-slate-700/80"
                >
                  {role}
                </span>
              ))}
            </div>

            <span className="text-slate-700">|</span>

            <div
              className="flex items-center gap-1 font-mono text-[11px] text-cyan-300"
              title="Canonical SHA-256 RBAC scope_hash partitioning PostgreSQL retrieval and Redis Semantic Cache"
            >
              <KeyRound className="h-3 w-3 text-cyan-400" />
              <span className="text-slate-400">scope_hash:</span>
              <span>{session?.scope_hash ?? "minting..."}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!canRerun}
              onClick={() => onRerunLastQuery(session ?? undefined)}
              title={
                lastQuery.trim()
                  ? `Re-run query under ${activeTenant} / ${activePersona}: "${lastQuery}"`
                  : "Send a query first to enable one-click RBAC re-run"
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-600/20 px-3 py-1.5 text-xs font-medium text-indigo-200 hover:bg-indigo-600/35 hover:border-indigo-400/60 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isStreaming ? "animate-spin" : ""}`}
              />
              <span>Re-run Last Query Under New Role</span>
            </button>

            <button
              type="button"
              onClick={onOpenAdminModal}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/90 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700/90 hover:text-white transition-colors cursor-pointer"
            >
              <Upload className="h-3.5 w-3.5 text-emerald-400" />
              <span>Admin Ingestion</span>
            </button>

            {onToggleInspector && (
              <button
                type="button"
                onClick={onToggleInspector}
                aria-expanded={Boolean(isInspectorOpen)}
                title={
                  isInspectorOpen
                    ? "Collapse Telemetry Inspector"
                    : "Expand Telemetry Inspector"
                }
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
              >
                {isInspectorOpen ? (
                  <PanelRightClose className="h-3.5 w-3.5 text-cyan-400" />
                ) : (
                  <PanelRightOpen className="h-3.5 w-3.5 text-cyan-400" />
                )}
                <DatabaseZap className="h-3.5 w-3.5 hidden sm:inline text-slate-400" />
                <span className="hidden xl:inline">Inspector</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {mintError && (
        <div
          role="alert"
          className="border-t border-rose-900/60 bg-rose-950/70 px-6 py-1.5 text-xs text-rose-200 flex items-center justify-between"
        >
          <span>JWT Persona Switch Failed: {mintError}</span>
          <button
            type="button"
            onClick={() => setMintError(null)}
            className="text-rose-300 underline hover:text-white cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}
    </header>
  );
}
