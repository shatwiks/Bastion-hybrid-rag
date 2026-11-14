"use client";

import React, { useEffect } from "react";
import {
  FileText,
  Layers,
  Shield,
  Sparkles,
  X,
} from "lucide-react";

import type { CitationItem } from "@/types/rag";

export interface CitationPopoverProps {
  citation: CitationItem | null;
  onClose: () => void;
  citationIndex?: number;
}

const ROLE_BADGE_STYLES: Record<string, string> = {
  public: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  support_tier_1: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  executive: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  admin: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export function CitationPopover({
  citation,
  onClose,
  citationIndex,
}: CitationPopoverProps) {
  useEffect(() => {
    if (!citation) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [citation, onClose]);

  if (!citation) return null;

  const scorePct = Math.max(0, Math.min(100, citation.rerank_score * 100));
  const passesThreshold = citation.rerank_score >= 0.65;
  const hasRankMetadata =
    citation.dense_rank !== undefined && citation.dense_rank !== null ||
    citation.sparse_rank !== undefined && citation.sparse_rank !== null ||
    citation.rrf_score !== undefined && citation.rrf_score !== null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="citation-popover-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 bg-slate-900/95 px-5 py-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-md bg-cyan-500/15 border border-cyan-500/30 px-2 py-0.5 font-mono text-[11px] font-semibold text-cyan-300">
                {typeof citationIndex === "number" ? `#${citationIndex + 1} · ` : ""}
                {citation.chunk_id}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${
                  passesThreshold
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                    : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                }`}
              >
                <Sparkles className="h-3 w-3" />
                Cross-Encoder: {scorePct.toFixed(1)}% ({citation.rerank_score.toFixed(4)})
              </span>
            </div>

            <h2
              id="citation-popover-title"
              className="flex items-center gap-2 text-base font-semibold text-white"
            >
              <FileText className="h-4 w-4 shrink-0 text-indigo-400" />
              <span className="truncate">{citation.document_title}</span>
            </h2>

            <p className="flex items-center gap-1.5 text-xs text-slate-400">
              <Layers className="h-3.5 w-3.5 shrink-0 text-slate-500" />
              <span className="truncate">{citation.section_header || "Document Root"}</span>
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close source inspection popover"
            className="rounded-lg border border-slate-700/80 bg-slate-800/80 p-1.5 text-slate-400 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-5">
          {/* RBAC Roles & Confidence Score Bar */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <Shield className="h-3.5 w-3.5 text-emerald-400" />
                Allowed Roles (Chunk ACL)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {citation.allowed_roles.map((role) => (
                  <span
                    key={role}
                    className={`rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium ${
                      ROLE_BADGE_STYLES[role] ??
                      "bg-slate-800 text-slate-200 border-slate-700"
                    }`}
                  >
                    {role}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="mb-1.5 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <span>Rerank Confidence</span>
                <span className="font-mono text-slate-200">
                  {scorePct.toFixed(1)}% / 65.0% gate
                </span>
              </div>
              <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all ${
                    passesThreshold ? "bg-emerald-500" : "bg-amber-500"
                  }`}
                  style={{ width: `${scorePct}%` }}
                />
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-rose-400"
                  style={{ left: "65%" }}
                  title="0.65 Refusal Gate Threshold"
                />
              </div>
            </div>
          </div>

          {/* RRF Rank Breakdown */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Hybrid RRF Rank Breakdown
              </span>
              {!hasRankMetadata && (
                <span className="text-[11px] text-amber-300/90">
                  Served from Semantic Cache (RRF bypassed)
                </span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-2 font-mono text-xs">
              <div className="rounded-lg border border-slate-800/80 bg-slate-900/70 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">Dense #</div>
                <div className="mt-0.5 font-semibold text-sky-300">
                  {citation.dense_rank != null ? `#${citation.dense_rank}` : "—"}
                </div>
              </div>
              <div className="rounded-lg border border-slate-800/80 bg-slate-900/70 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">BM25 #</div>
                <div className="mt-0.5 font-semibold text-indigo-300">
                  {citation.sparse_rank != null ? `#${citation.sparse_rank}` : "—"}
                </div>
              </div>
              <div className="rounded-lg border border-slate-800/80 bg-slate-900/70 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">RRF Score</div>
                <div className="mt-0.5 font-semibold text-emerald-300">
                  {citation.rrf_score != null ? citation.rrf_score.toFixed(6) : "—"}
                </div>
              </div>
            </div>
          </div>

          {/* Full Chunk Content (Rendered strictly as escaped React text node) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <span>Retrieved Source Chunk Content</span>
              <span className="font-mono text-[10px] text-slate-500">
                doc_id: {citation.document_id}
              </span>
            </div>
            <div className="max-h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-4">
              <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-200">
                {citation.content}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
