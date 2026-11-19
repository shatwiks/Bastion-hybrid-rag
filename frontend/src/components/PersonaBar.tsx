"use client";

import React, { useState } from "react";
import {
  ArrowLeft,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Upload,
} from "lucide-react";

import { mintDemoToken } from "@/lib/sse-client";
import type {
  DemoTokenSession,
  HealthStatusResponse,
  PersonaType,
  TenantId,
} from "@/types/rag";

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
          {/* Wordmark & System Health (tasteskill ring mark + ui-win__crumb) */}
          <div className="flex items-center gap-2.5 pr-3 sm:border-r sm:border-[var(--shell-rule)]">
            <a
              href="/"
              title="Back to Bastion product landing page"
              className="flex items-center gap-2 rounded hover:opacity-90 transition-opacity"
            >
              <span
                className="taste-mark-ring text-[#6b93f2]"
                aria-hidden="true"
              />
              <span className="text-[19px] font-medium tracking-[-0.025em] text-[var(--shell-ink)]">
                Bastion
              </span>
            </a>
            <span className="text-xs text-[var(--shell-rule)]" aria-hidden="true">
              /
            </span>
            <span className="font-mono text-xs font-medium text-[var(--shell-muted)]">
              workspace
            </span>
            <div className="flex items-center gap-2 leading-none">
              <span
                className="inline-flex items-center gap-1.5 rounded-[3px] border px-1.5 py-0.5 font-mono text-[11px] font-medium"
                style={{
                  backgroundColor: isHealthy
                    ? "rgba(92, 224, 168, 0.1)"
                    : "rgba(255, 255, 255, 0.06)",
                  borderColor: isHealthy
                    ? "rgba(92, 224, 168, 0.28)"
                    : "var(--shell-rule)",
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
                    backgroundColor: isHealthy ? "#5CE0A8" : "#9E9D99",
                  }}
                />
                {isHealthy ? "Live" : "Checking"}
              </span>
            </div>
          </div>

          {/* Role Persona Segmented Control */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden font-mono text-[11px] text-[var(--shell-muted)] sm:inline">
              Access Role:
            </span>
            <div
              role="group"
              aria-label="Select RBAC role persona"
              className="inline-flex max-w-full flex-wrap items-center rounded-[4px] border border-[var(--shell-rule)] bg-[#1b1a15] p-0.5"
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
                        ? "bg-[var(--copper)] text-white"
                        : "text-[var(--shell-muted)] hover:text-[var(--shell-ink)]"
                    }`}
                  >
                    {persona.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Active Scope Readout + Utility Actions */}
        <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">
          {/* Active JWT Scope Readout */}
          {session && (
            <div
              className="hidden items-center gap-2 rounded-[4px] border border-[var(--shell-rule)] bg-[#1b1a15] px-2.5 py-1 text-[11px] xl:flex"
              title={`Allowed roles: ${session.allowed_roles.join(", ")} · Scope hash: ${session.scope_hash}`}
            >
              <span className="font-mono text-[var(--shell-muted)]">
                roles:
              </span>
              <span className="font-mono text-[var(--shell-ink)]">
                {session.allowed_roles.join(", ")}
              </span>
              <span className="text-[var(--shell-rule)]">·</span>
              <span className="font-mono tabular-nums text-[#8cc9a8]">
                {session.scope_hash.slice(0, 12)}
              </span>
            </div>
          )}

          {/* Overview Link */}
          <a
            href="/"
            className="inline-flex h-8 items-center gap-1.5 rounded-[4px] border border-[var(--shell-rule)] bg-[var(--shell-surface)] px-2.5 text-xs font-medium text-[var(--shell-ink)] transition-colors duration-150 hover:bg-[var(--shell-surface-active)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Overview</span>
          </a>

          {/* Re-run Last Query */}
          <button
            type="button"
            disabled={!canRerun}
            onClick={() => onRerunLastQuery(session ?? undefined)}
            title={
              lastQuery
                ? `Re-run "${lastQuery}" under role ${activePersona}`
                : "Ask a question first to re-run under another role"
            }
            className="inline-flex h-8 items-center gap-1.5 rounded-[4px] border border-[var(--shell-rule)] bg-[var(--shell-surface)] px-2.5 text-xs font-medium text-[var(--shell-ink)] transition-colors duration-150 hover:bg-[var(--shell-surface-active)] active:translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isMinting ? "animate-spin" : ""}`}
            />
            <span className="hidden sm:inline">Re-run Under Role</span>
            <span className="sm:hidden">Re-run</span>
          </button>

          {/* Admin Ingestion */}
          <button
            type="button"
            onClick={onOpenAdminModal}
            className="inline-flex h-8 items-center gap-1.5 rounded-[4px] border border-[var(--shell-rule)] bg-[var(--shell-surface)] px-2.5 text-xs font-medium text-[var(--shell-ink)] transition-colors duration-150 hover:bg-[var(--shell-surface-active)] active:translate-y-px cursor-pointer"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Ingest Docs</span>
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
              className={`inline-flex h-8 items-center gap-1.5 rounded-[4px] border px-2.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
                isInspectorOpen
                  ? "border-transparent bg-[var(--ground)] text-[var(--ink)]"
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
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--shell-rule)]/70 bg-[#1b1a15] px-4 py-1 text-[11px] text-[var(--shell-muted)] xl:hidden">
          <span className="truncate font-mono">
            roles: {session.allowed_roles.join(", ")}
          </span>
          <span className="font-mono tabular-nums text-[#8cc9a8]">
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
