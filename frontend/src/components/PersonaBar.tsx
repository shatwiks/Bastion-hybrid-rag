"use client";

import React, { useState } from "react";
import {
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  ShieldCheck,
  Upload,
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
}> = [
  {
    id: "public",
    label: "Public",
    tierDescription: "public only",
  },
  {
    id: "support_tier_1",
    label: "Support Tier 1",
    tierDescription: "public + support_tier_1",
  },
  {
    id: "executive",
    label: "Executive",
    tierDescription: "public + support_tier_1 + executive",
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

  const canRerun =
    Boolean(lastQuery.trim()) && Boolean(session) && !isStreaming && !isMinting;

  const isHealthy = health?.status === "ok";

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--shell-rule)] bg-[var(--shell-bg)] text-[var(--shell-ink)]">
      <div className="mx-auto flex w-full max-w-[1680px] min-w-0 flex-wrap items-center justify-between gap-x-4 gap-y-2.5 px-4 py-2.5 lg:px-6">
        {/* Left: Brand Identity + Segmented Tenant & Role Switchers */}
        <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2.5 sm:gap-3.5">
          {/* Wordmark & System Health */}
          <div className="flex items-center gap-2.5 pr-3 sm:border-r sm:border-[var(--shell-rule)]">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-[var(--copper)] text-[#FCFBF8]">
              <ShieldCheck className="h-4 w-4" strokeWidth={2} />
            </span>
            <div className="flex items-center gap-2 leading-none">
              <span className="text-[15px] font-semibold tracking-tight text-[var(--shell-ink)]">
                Bastion
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[11px] font-medium"
                style={{
                  backgroundColor: isHealthy
                    ? "rgba(74, 222, 128, 0.14)"
                    : "rgba(255, 255, 255, 0.08)",
                  color: isHealthy ? "#9CE7C6" : "var(--shell-muted)",
                }}
                title={
                  health
                    ? `Backend ${health.status} · Postgres: ${health.postgres} · Redis: ${health.redis}`
                    : "Checking backend health"
                }
              >
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{
                    backgroundColor: isHealthy ? "#5CE0A8" : "#9EB7BA",
                  }}
                />
                {isHealthy ? "Live" : "Checking"}
              </span>
            </div>
          </div>

          {/* Tenant Segmented Control */}
          <div
            role="group"
            aria-label="Select tenant"
            className="inline-flex max-w-full items-center rounded border border-[var(--shell-rule)] bg-[#0E262A] p-0.5"
          >
            {TENANT_OPTIONS.map((tenant) => {
              const isSelected = activeTenant === tenant.id;
              return (
                <button
                  key={tenant.id}
                  type="button"
                  disabled={isMinting || isStreaming}
                  aria-pressed={isSelected}
                  onClick={() => handleSwitch(tenant.id, activePersona)}
                  className={`rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors duration-150 cursor-pointer disabled:opacity-50 ${
                    isSelected
                      ? "bg-[var(--paper)] text-[var(--ink)] shadow-xs"
                      : "text-[var(--shell-muted)] hover:text-[var(--shell-ink)]"
                  }`}
                >
                  {tenant.label}
                </button>
              );
            })}
          </div>

          {/* Role Persona Segmented Control */}
          <div
            role="group"
            aria-label="Select RBAC role persona"
            className="inline-flex max-w-full flex-wrap items-center rounded border border-[var(--shell-rule)] bg-[#0E262A] p-0.5"
          >
            {PERSONA_OPTIONS.map((persona) => {
              const isSelected = activePersona === persona.id;
              return (
                <button
                  key={persona.id}
                  type="button"
                  disabled={isMinting || isStreaming}
                  aria-pressed={isSelected}
                  title={`Role scope: ${persona.tierDescription}`}
                  onClick={() => handleSwitch(activeTenant, persona.id)}
                  className={`rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors duration-150 cursor-pointer disabled:opacity-50 ${
                    isSelected
                      ? "bg-[var(--copper)] text-[#FCFBF8]"
                      : "text-[var(--shell-muted)] hover:text-[var(--shell-ink)]"
                  }`}
                >
                  {persona.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Active Scope Readout + Utility Actions */}
        <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">
          {/* Active JWT Scope Readout */}
          {session && (
            <div
              className="hidden items-center gap-2 rounded border border-[var(--shell-rule)] bg-[#0E262A] px-2.5 py-1 text-[11px] xl:flex"
              title={`Tenant: ${session.tenant_id} · Allowed roles: ${session.allowed_roles.join(", ")} · Scope hash: ${session.scope_hash}`}
            >
              <span className="font-mono text-[var(--shell-muted)]">
                {session.tenant_id}
              </span>
              <span className="text-[var(--shell-rule)]">/</span>
              <span className="font-mono text-[#D5E4E6]">
                {session.allowed_roles.join(", ")}
              </span>
              <span className="text-[var(--shell-rule)]">·</span>
              <span className="font-mono tabular-nums text-[#8FD4BE]">
                {session.scope_hash.slice(0, 12)}
              </span>
            </div>
          )}

          {/* Re-run Last Query */}
          <button
            type="button"
            disabled={!canRerun}
            onClick={() => onRerunLastQuery(session ?? undefined)}
            title={
              lastQuery
                ? `Re-run "${lastQuery}" under ${activeTenant} / ${activePersona}`
                : "Ask a question first to re-run under another role"
            }
            className="inline-flex h-8 items-center gap-1.5 rounded border border-[var(--shell-rule)] bg-[var(--shell-surface)] px-2.5 text-xs font-medium text-[var(--shell-ink)] transition-colors duration-150 hover:bg-[var(--shell-surface-active)] active:translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isMinting ? "animate-spin" : ""}`}
            />
            <span className="hidden sm:inline">Re-run Last Query Under New Role</span>
            <span className="sm:hidden">Re-run</span>
          </button>

          {/* Admin Ingestion */}
          <button
            type="button"
            onClick={onOpenAdminModal}
            className="inline-flex h-8 items-center gap-1.5 rounded border border-[var(--shell-rule)] bg-[var(--shell-surface)] px-2.5 text-xs font-medium text-[var(--shell-ink)] transition-colors duration-150 hover:bg-[var(--shell-surface-active)] active:translate-y-px cursor-pointer"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Admin Ingestion</span>
          </button>

          {/* Telemetry Inspector Toggle */}
          {onToggleInspector && (
            <button
              type="button"
              onClick={onToggleInspector}
              aria-expanded={isInspectorOpen}
              aria-label={
                isInspectorOpen
                  ? "Collapse Telemetry Inspector"
                  : "Expand Telemetry Inspector"
              }
              className={`inline-flex h-8 items-center gap-1.5 rounded border px-2.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
                isInspectorOpen
                  ? "border-[#D7D2C6]/30 bg-[var(--paper)] text-[var(--ink)]"
                  : "border-[var(--shell-rule)] bg-[var(--shell-surface)] text-[var(--shell-ink)] hover:bg-[var(--shell-surface-active)]"
              }`}
            >
              {isInspectorOpen ? (
                <PanelRightClose className="h-3.5 w-3.5" />
              ) : (
                <PanelRightOpen className="h-3.5 w-3.5" />
              )}
              <span className="hidden md:inline">Inspector</span>
            </button>
          )}
        </div>
      </div>

      {/* Compact Mobile Scope Strip (visible below xl) */}
      {session && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--shell-rule)]/70 bg-[#0E262A] px-4 py-1 text-[11px] text-[var(--shell-muted)] xl:hidden">
          <span className="truncate font-mono">
            {session.tenant_id} · {session.allowed_roles.join(", ")}
          </span>
          <span className="font-mono tabular-nums text-[#8FD4BE]">
            scope:{session.scope_hash}
          </span>
        </div>
      )}

      {/* Mint Error Notice */}
      {mintError && (
        <div
          role="alert"
          className="border-t border-[var(--crimson-rule)] bg-[var(--crimson-soft)] px-4 py-1.5 text-xs text-[var(--crimson)]"
        >
          Unable to switch security context: {mintError}
        </div>
      )}
    </header>
  );
}
