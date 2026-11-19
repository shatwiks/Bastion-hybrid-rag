"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FilePlus2,
  FileText,
  Lock,
  RefreshCw,
  ShieldAlert,
  Upload,
  X,
} from "lucide-react";

import { ingestDocument, listDocuments } from "@/lib/sse-client";
import type {
  DemoTokenSession,
  DocumentIngestResponse,
  DocumentSummary,
} from "@/types/rag";

const ALL_ROLE_OPTIONS = ["public", "support_tier_1", "executive"] as const;

const ROLE_DESCRIPTIONS: Record<(typeof ALL_ROLE_OPTIONS)[number], string> = {
  public: "Visible to all tenant tiers",
  support_tier_1: "Support Tier 1 & Executive",
  executive: "Executive tier only",
};

export interface AdminIngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  session: DemoTokenSession | null;
}

export function AdminIngestionModal({
  isOpen,
  onClose,
  session,
}: AdminIngestionModalProps) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [allowedRoles, setAllowedRoles] = useState<string[]>([
    "support_tier_1",
    "executive",
  ]);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isRbacForbidden, setIsRbacForbidden] = useState(false);
  const [ingestResult, setIngestResult] =
    useState<DocumentIngestResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchDocuments = useCallback(async () => {
    if (!session?.access_token) return;
    setLoadingDocs(true);
    setDocsError(null);
    try {
      const res = await listDocuments(session.access_token);
      setDocuments(res.documents);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to load tenant documents";
      setDocsError(msg);
    } finally {
      setLoadingDocs(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (!isOpen) return;
    setSubmitError(null);
    setIsRbacForbidden(false);
    fetchDocuments();
  }, [isOpen, fetchDocuments]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const isPublicPersona =
    session != null &&
    !session.allowed_roles.some(
      (r) => r === "support_tier_1" || r === "executive" || r === "admin"
    );

  const toggleRole = (role: string) => {
    setAllowedRoles((prev) => {
      if (prev.includes(role)) {
        return prev.filter((r) => r !== role);
      }
      return [...prev, role];
    });
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      setContent(text);
      setUploadedFileName(file.name);
      if (!title.trim()) {
        setTitle(file.name.replace(/\.(md|markdown|txt)$/i, ""));
      }
      setSubmitError(null);
      setIsRbacForbidden(false);
    } catch {
      setSubmitError("Unable to read selected file as UTF-8 text.");
    } finally {
      event.target.value = "";
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!session) return;

    const cleanTitle = title.trim();
    const cleanContent = content.trim();
    if (!cleanTitle) {
      setSubmitError("Document title is required.");
      return;
    }
    if (!cleanContent) {
      setSubmitError("Markdown or plain-text document content is required.");
      return;
    }
    if (allowedRoles.length === 0) {
      setSubmitError("Select at least one allowed_roles ACL tag.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    setIsRbacForbidden(false);
    setIngestResult(null);

    try {
      const response = await ingestDocument(session.access_token, {
        title: cleanTitle,
        content: cleanContent,
        tenant_id: session.tenant_id,
        allowed_roles: allowedRoles,
        doc_metadata: {
          allowed_roles: allowedRoles,
          source: uploadedFileName ? `upload:${uploadedFileName}` : "admin_editor",
        },
      });

      setIngestResult(response);
      await fetchDocuments();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Document ingestion failed";
      const lower = msg.toLowerCase();
      if (
        lower.includes("403") ||
        lower.includes("forbidden") ||
        lower.includes("administrative ingestion") ||
        lower.includes("lacks")
      ) {
        setIsRbacForbidden(true);
      }
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#26251e]/50 p-3 sm:p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-ingestion-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-[6px] border border-[var(--rule-strong)] bg-[var(--paper)] shadow-[0_24px_60px_-20px_rgba(38,37,30,0.45)] sm:max-w-5xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-[var(--rule)] bg-[var(--ground)] px-5 py-4">
          <div className="min-w-0">
            <h2
              id="admin-ingestion-title"
              className="flex items-center gap-2 text-base font-semibold text-[var(--ink)]"
            >
              <FilePlus2 className="h-4 w-4 shrink-0 text-[var(--copper)]" />
              <span>Admin Document Ingestion</span>
            </h2>
            <p className="mt-0.5 text-xs text-[var(--ink-secondary)]">
              Upload Markdown documents, assign pre-retrieval ACL tags, and inspect structural chunk boundaries.
              {session && (
                <>
                  {" "}
                  Session:{" "}
                  <span className="font-mono font-medium text-[var(--ink)]">
                    {session.tenant_id} / {session.persona}
                  </span>
                </>
              )}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Admin Document Ingestion modal"
            className="rounded border border-[var(--rule)] bg-[var(--paper)] p-1.5 text-[var(--ink-secondary)] transition-colors hover:border-[var(--rule-strong)] hover:text-[var(--ink)] cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Two-Column Body */}
        <div className="grid flex-1 grid-cols-1 divide-y divide-[var(--rule)] overflow-y-auto lg:grid-cols-12 lg:divide-x lg:divide-y-0">
          {/* Left: Ingestion Form */}
          <div className="p-5 lg:col-span-7">
            {/* Public Persona Warning */}
            {isPublicPersona && (
              <div
                role="status"
                className="mb-4 flex items-start gap-2.5 rounded border border-[var(--ochre-rule)] bg-[var(--ochre-soft)] p-3 text-xs text-[var(--ochre)]"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="font-semibold">Public persona active.</span>{" "}
                  Ingestion requires <span className="font-mono">support_tier_1</span>{" "}
                  or <span className="font-mono">executive</span> role. Submitting now
                  will demonstrate live backend <span className="font-mono">HTTP 403</span>{" "}
                  enforcement.
                </div>
              </div>
            )}

            {/* HTTP 403 / Validation Error */}
            {submitError && (
              <div
                role="alert"
                className="mb-4 flex items-start gap-2.5 rounded border border-[var(--crimson-rule)] bg-[var(--crimson-soft)] p-3.5 text-xs text-[var(--crimson)]"
              >
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="font-semibold">
                    {isRbacForbidden
                      ? "HTTP 403 Forbidden — RBAC Ingestion Guard"
                      : "Document Ingestion Error"}
                  </div>
                  <p className="mt-0.5 text-[var(--ink)]">{submitError}</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Upload Row */}
              <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-dashed border-[var(--rule-strong)] bg-[var(--ground)]/60 px-3.5 py-2.5">
                <div className="text-xs text-[var(--ink-secondary)]">
                  {uploadedFileName ? (
                    <span>
                      Loaded file:{" "}
                      <strong className="font-mono text-[var(--ink)]">
                        {uploadedFileName}
                      </strong>
                    </span>
                  ) : (
                    <span>Upload a .md, .markdown, or .txt file, or paste below.</span>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".md,.markdown,.txt,text/markdown,text/plain"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded border border-[var(--rule-strong)] bg-[var(--paper)] px-2.5 py-1.5 text-xs font-medium text-[var(--ink)] transition-colors hover:border-[var(--copper)] hover:text-[var(--copper)] cursor-pointer"
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload .md File
                </button>
              </div>

              {/* Title + Read-only Tenant */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label
                    htmlFor="ingest-doc-title"
                    className="mb-1 block text-xs font-semibold text-[var(--ink-secondary)]"
                  >
                    Document Title
                  </label>
                  <input
                    id="ingest-doc-title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Helios Payment Gateway Runbook"
                    className="w-full rounded border border-[var(--rule-strong)] bg-[var(--paper)] px-3 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:border-[var(--copper)] focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="ingest-tenant-id"
                    className="mb-1 flex items-center gap-1 text-xs font-semibold text-[var(--ink-secondary)]"
                  >
                    <Lock className="h-3 w-3 text-[var(--ink-muted)]" />
                    Tenant Scope
                  </label>
                  <input
                    id="ingest-tenant-id"
                    type="text"
                    readOnly
                    value={session?.tenant_id ?? ""}
                    className="w-full rounded border border-[var(--rule)] bg-[var(--ground)] px-3 py-2 font-mono text-xs text-[var(--ink-secondary)] focus:outline-none"
                  />
                </div>
              </div>

              {/* Allowed Roles ACL */}
              <div>
                <span className="mb-1.5 block text-xs font-semibold text-[var(--ink-secondary)]">
                  Allowed Roles (Pre-Retrieval ACL)
                </span>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {ALL_ROLE_OPTIONS.map((role) => {
                    const checked = allowedRoles.includes(role);
                    return (
                      <label
                        key={role}
                        className={`flex items-start gap-2 rounded border p-2.5 text-xs transition-colors cursor-pointer ${
                          checked
                            ? "border-[var(--copper)] bg-[var(--copper-soft)]"
                            : "border-[var(--rule)] bg-[var(--paper)] hover:border-[var(--rule-strong)]"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleRole(role)}
                          className="mt-0.5 h-3.5 w-3.5 accent-[var(--copper)]"
                        />
                        <div className="min-w-0">
                          <div className="font-mono font-semibold text-[var(--ink)]">
                            {role}
                          </div>
                          <div className="text-[11px] text-[var(--ink-muted)]">
                            {ROLE_DESCRIPTIONS[role]}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Markdown Content Editor */}
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label
                    htmlFor="ingest-doc-content"
                    className="text-xs font-semibold text-[var(--ink-secondary)]"
                  >
                    Markdown Content
                  </label>
                  <span className="font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
                    {content.length.toLocaleString()} chars
                  </span>
                </div>
                <textarea
                  id="ingest-doc-content"
                  rows={8}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="# Document Heading&#10;&#10;## Section&#10;Paste Markdown tables, error codes, or CLI runbooks…"
                  className="w-full resize-y rounded border border-[var(--rule-strong)] bg-[var(--paper)] p-3 font-mono text-xs leading-relaxed text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:border-[var(--copper)] focus:outline-none"
                />
              </div>

              {/* Submit Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <span className="text-xs text-[var(--ink-muted)]">
                  Auto-invalidates tenant Redis semantic cache on commit.
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || !session}
                  className="inline-flex h-9 items-center gap-2 rounded bg-[var(--copper)] px-4 text-xs font-semibold text-[#FCFBF8] transition-colors hover:bg-[var(--copper-hover)] active:translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Upload className="h-3.5 w-3.5" />
                  )}
                  {isSubmitting ? "Chunking & Embedding…" : "Ingest Document"}
                </button>
              </div>
            </form>

            {/* HTTP 201 Chunk Summary */}
            {ingestResult && (
              <div className="mt-5 rounded border border-[var(--jade-rule)] bg-[var(--jade-soft)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-[var(--jade)]">
                    <CheckCircle2 className="h-4 w-4" />
                    Ingested {ingestResult.chunks_count} structural chunks
                  </span>
                  <span className="font-mono text-[11px] text-[var(--ink-secondary)]">
                    doc_id: {ingestResult.document_id}
                  </span>
                </div>

                <ul className="mt-3 divide-y divide-[var(--jade-rule)]/70 rounded border border-[var(--jade-rule)] bg-[var(--paper)]">
                  {ingestResult.chunks.map((chunk, index) => (
                    <li
                      key={chunk.chunk_id}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-xs"
                    >
                      <div className="min-w-0">
                        <span className="mr-2 font-mono text-[11px] font-semibold text-[var(--copper)]">
                          #{index + 1}
                        </span>
                        <span className="truncate font-medium text-[var(--ink)]">
                          {chunk.section_header || "Document Root"}
                        </span>
                      </div>
                      <span className="shrink-0 font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
                        {chunk.character_count} chars
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right: Indexed Tenant Documents */}
          <div className="bg-[var(--ground)]/60 p-5 lg:col-span-5">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold text-[var(--ink)]">
                Indexed Tenant Documents ({documents.length})
              </h3>
              <button
                type="button"
                onClick={() => void fetchDocuments()}
                disabled={loadingDocs}
                className="inline-flex items-center gap-1 rounded border border-[var(--rule)] bg-[var(--paper)] px-2 py-1 text-[11px] font-medium text-[var(--ink-secondary)] hover:border-[var(--rule-strong)] hover:text-[var(--ink)] cursor-pointer disabled:opacity-50"
              >
                <RefreshCw
                  className={`h-3 w-3 ${loadingDocs ? "animate-spin" : ""}`}
                />
                Refresh
              </button>
            </div>

            {docsError && (
              <div
                role="alert"
                className="mb-3 rounded border border-[var(--crimson-rule)] bg-[var(--crimson-soft)] p-2.5 text-xs text-[var(--crimson)]"
              >
                {docsError}
              </div>
            )}

            {loadingDocs && documents.length === 0 ? (
              <div className="space-y-2 py-4">
                <div className="h-12 animate-pulse rounded bg-[var(--mineral)]" />
                <div className="h-12 animate-pulse rounded bg-[var(--mineral)]" />
                <div className="h-12 animate-pulse rounded bg-[var(--mineral)]" />
              </div>
            ) : documents.length === 0 ? (
              <p className="py-6 text-center text-xs text-[var(--ink-muted)]">
                No documents indexed for this tenant yet.
              </p>
            ) : (
              <ul className="divide-y divide-[var(--rule)] rounded border border-[var(--rule)] bg-[var(--paper)]">
                {documents.map((doc) => {
                  const metaRoles = Array.isArray(doc.doc_metadata?.allowed_roles)
                    ? (doc.doc_metadata.allowed_roles as string[])
                    : [];

                  return (
                    <li key={doc.id} className="px-3.5 py-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <FileText className="h-3.5 w-3.5 shrink-0 text-[var(--ink-muted)]" />
                          <span className="truncate text-xs font-semibold text-[var(--ink)]">
                            {doc.title}
                          </span>
                        </div>
                        <span className="shrink-0 font-mono text-[11px] tabular-nums text-[var(--ink-muted)]">
                          {doc.chunks_count} chunks
                        </span>
                      </div>

                      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-1.5 text-[11px]">
                        <span className="font-mono text-[var(--ink-muted)]">
                          {doc.tenant_id}
                        </span>
                        {metaRoles.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {metaRoles.map((r) => (
                              <span
                                key={r}
                                className="rounded border border-[var(--rule)] bg-[var(--ground)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ink-secondary)]"
                              >
                                {r}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
