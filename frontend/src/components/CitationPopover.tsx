"use client";

import React, { useEffect } from "react";
import { FileText, Layers, Shield, X } from "lucide-react";

import type { CitationItem } from "@/types/rag";

export interface CitationPopoverProps {
  citation: CitationItem | null;
  onClose: () => void;
  citationIndex?: number;
}

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
    (citation.dense_rank !== undefined && citation.dense_rank !== null) ||
    (citation.sparse_rank !== undefined && citation.sparse_rank !== null) ||
    (citation.rrf_score !== undefined && citation.rrf_score !== null);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#26251e]/50 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="citation-popover-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-[6px] border border-[var(--rule-strong)] bg-[var(--paper)] shadow-[0_24px_60px_-20px_rgba(38,37,30,0.45)]"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-[var(--rule)] bg-[var(--ground)] px-5 py-4">
          <div className="min-w-0 space-y-1">
            <h2
              id="citation-popover-title"
              className="flex items-center gap-2 text-base font-semibold text-[var(--ink)]"
            >
              <FileText className="h-4 w-4 shrink-0 text-[var(--copper)]" />
              <span className="truncate">{citation.document_title}</span>
            </h2>

            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--ink-secondary)]">
              <span className="inline-flex items-center gap-1">
                <Layers className="h-3.5 w-3.5 text-[var(--ink-muted)]" />
                <span className="truncate">
                  {citation.section_header || "Document Root"}
                </span>
              </span>
              <span className="font-mono text-[11px] text-[var(--ink-muted)]">
                {typeof citationIndex === "number" ? `#${citationIndex + 1} · ` : ""}
                {citation.chunk_id}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close source inspection popover"
            className="rounded border border-[var(--rule)] bg-[var(--paper)] p-1.5 text-[var(--ink-secondary)] transition-colors hover:border-[var(--rule-strong)] hover:text-[var(--ink)] cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Metadata Bar (Hairline Architectural Grid — zero nested rounded boxes) */}
        <div className="grid grid-cols-1 divide-y divide-[var(--rule)] border-b border-[var(--rule)] bg-[var(--paper)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          {/* Chunk ACL */}
          <div className="px-5 py-3.5">
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-[var(--ink-secondary)]">
              <Shield className="h-3.5 w-3.5 text-[var(--jade)]" />
              Allowed Roles (Chunk ACL)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {citation.allowed_roles.map((role) => (
                <span
                  key={role}
                  className="rounded border border-[var(--rule)] bg-[var(--ground)] px-2 py-0.5 font-mono text-[11px] font-medium text-[var(--ink)]"
                >
                  {role}
                </span>
              ))}
            </div>
          </div>

          {/* Cross-Encoder Score */}
          <div className="px-5 py-3.5">
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="font-semibold text-[var(--ink-secondary)]">
                Cross-Encoder Confidence
              </span>
              <span
                className="font-mono tabular-nums font-semibold"
                style={{
                  color: passesThreshold ? "var(--jade)" : "var(--crimson)",
                }}
              >
                {scorePct.toFixed(1)}% ({citation.rerank_score.toFixed(4)})
              </span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-xs bg-[var(--mineral)]">
              <div
                className="h-full transition-all duration-200"
                style={{
                  width: `${scorePct}%`,
                  backgroundColor: passesThreshold
                    ? "var(--jade)"
                    : "var(--crimson)",
                }}
              />
              <div
                className="absolute inset-y-0 w-0.5 bg-[var(--ink)]"
                style={{ left: "65%" }}
                title="0.65 Refusal Gate Threshold"
              />
            </div>
            <div className="mt-1 flex justify-between font-mono text-[10px] tabular-nums text-[var(--ink-muted)]">
              <span>0.00</span>
              <span>0.65 gate</span>
              <span>1.00</span>
            </div>
          </div>
        </div>

        {/* Retrieval Provenance Strip */}
        <div className="border-b border-[var(--rule)] bg-[var(--ground)]/60 px-5 py-2.5">
          {hasRankMetadata ? (
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div>
                <div className="text-[11px] text-[var(--ink-muted)]">Dense Rank</div>
                <div className="font-mono tabular-nums font-semibold text-[var(--ink)]">
                  {citation.dense_rank ? `#${citation.dense_rank}` : "—"}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-[var(--ink-muted)]">BM25 Rank</div>
                <div className="font-mono tabular-nums font-semibold text-[var(--ink)]">
                  {citation.sparse_rank ? `#${citation.sparse_rank}` : "—"}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-[var(--ink-muted)]">RRF Score</div>
                <div className="font-mono tabular-nums font-semibold text-[var(--ink)]">
                  {typeof citation.rrf_score === "number"
                    ? citation.rrf_score.toFixed(6)
                    : "—"}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-[var(--ink-secondary)]">
              Served directly from the permission-scoped Redis semantic cache (Steps 3–5 bypassed).
            </p>
          )}
        </div>

        {/* Verified Chunk Content */}
        <div className="p-5">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-semibold text-[var(--ink-secondary)]">
              Verified Source Excerpt
            </span>
            <span className="font-mono text-[11px] text-[var(--ink-muted)]">
              Escaped plain text
            </span>
          </div>
          <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap break-words rounded border border-[var(--rule)] bg-[var(--ground)] p-4 font-mono text-[12.5px] leading-relaxed text-[var(--ink)]">
            {citation.content}
          </pre>
        </div>
      </div>
    </div>
  );
}
