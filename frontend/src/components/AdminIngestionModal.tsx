"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileCode2,
  FilePlus2,
  FileText,
  Layers,
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

  const formatTimestamp = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-ingestion-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between gap-4 border-b border-slate-800 bg-slate-900/95 px-6 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <FilePlus2 className="h-5 w-5 text-emerald-400 shrink-0" />
              <h2
                id="admin-ingestion-title"
                className="text-base font-semibold text-white"
              >
                Admin Document Ingestion &amp; Tenant Index
              </h2>
              {session && (
                <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
                  <Lock className="h-3 w-3" />
                  tenant: {session.tenant_id} ({session.persona})
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              Structure-aware Markdown chunking with mandatory tenant_id &amp;
              allowed_roles ACL binding
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Admin Ingestion modal"
            className="rounded-lg border border-slate-700/80 bg-slate-800/80 p-1.5 text-slate-400 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Active Public Persona Warning */}
          {isPublicPersona && !isRbacForbidden && (
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/40 bg-amber-950/35 px-4 py-3 text-xs text-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <div>
                <p className="font-semibold">
                  Active Persona Is Read-Only (public)
                </p>
                <p className="mt-0.5 text-amber-200/85">
                  Document ingestion requires{" "}
                  <code className="font-mono text-amber-100">support_tier_1</code>{" "}
                  or <code className="font-mono text-amber-100">executive</code>{" "}
                  privileges. Submitting under{" "}
                  <code className="font-mono text-amber-100">public</code> will be
                  rejected with HTTP 403 by the backend RBAC guard.
                </p>
              </div>
            </div>
          )}

          {/* HTTP 403 RBAC Permission Error Banner */}
          {isRbacForbidden && (
            <div
              role="alert"
              className="flex items-start gap-3 rounded-xl border border-rose-500/60 bg-rose-950/55 px-4 py-3.5 text-xs text-rose-100"
            >
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-rose-200">
                  HTTP 403 Forbidden — Administrative Ingestion Privileges Required
                </p>
                <p className="leading-relaxed text-rose-200/90">
                  Your active JWT persona (
                  <code className="font-mono font-semibold">
                    {session?.persona ?? "public"}
                  </code>
                  ) does not hold{" "}
                  <code className="font-mono font-semibold">support_tier_1</code>{" "}
                  or <code className="font-mono font-semibold">executive</code>{" "}
                  privileges required by{" "}
                  <code className="font-mono">POST /api/v1/ingest</code>. Switch
                  your role tier in the PersonaBar to ingest documents.
                </p>
                {submitError && (
                  <p className="font-mono text-[11px] text-rose-300/90">
                    Backend detail: {submitError}
                  </p>
                )}
              </div>
            </div>
          )}

          {submitError && !isRbacForbidden && (
            <div
              role="alert"
              className="rounded-xl border border-rose-500/45 bg-rose-950/40 px-4 py-3 text-xs text-rose-200"
            >
              Ingestion Error: {submitError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Left: Markdown Upload & Ingestion Form */}
            <form
              onSubmit={handleSubmit}
              className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 lg:col-span-6"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-300">
                  <FileCode2 className="h-4 w-4 text-indigo-400" />
                  Ingest Markdown Document
                </h3>

                <div>
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
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700 transition-colors cursor-pointer"
                  >
                    <Upload className="h-3.5 w-3.5 text-cyan-400" />
                    Upload .md / .txt
                  </button>
                </div>
              </div>

              {uploadedFileName && (
                <div className="flex items-center justify-between rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-[11px] text-cyan-200">
                  <span className="truncate">Loaded file: {uploadedFileName}</span>
                  <button
                    type="button"
                    onClick={() => setUploadedFileName(null)}
                    className="text-cyan-300 hover:text-white cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
              )}

              {/* Title & Locked Tenant */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label
                    htmlFor="ingest-doc-title"
                    className="mb-1 block text-[11px] font-medium text-slate-300"
                  >
                    Document Title
                  </label>
                  <input
                    id="ingest-doc-title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Storage Cluster Recovery Runbook"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="ingest-tenant-id"
                    className="mb-1 block text-[11px] font-medium text-slate-300"
                  >
                    Bound tenant_id
                  </label>
                  <input
                    id="ingest-tenant-id"
                    type="text"
                    readOnly
                    value={session?.tenant_id ?? "acme_corp"}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 font-mono text-xs text-emerald-300 focus:outline-none cursor-not-allowed"
                    title="Locked to active authenticated tenant_id"
                  />
                </div>
              </div>

              {/* Allowed Roles Checkboxes */}
              <div>
                <span className="mb-1.5 block text-[11px] font-medium text-slate-300">
                  Chunk ACL (allowed_roles)
                </span>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {ALL_ROLE_OPTIONS.map((role) => {
                    const checked = allowedRoles.includes(role);
                    return (
                      <label
                        key={role}
                        className={`flex cursor-pointer items-start gap-2 rounded-lg border px-2.5 py-2 text-xs transition-colors ${
                          checked
                            ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-100"
                            : "border-slate-800 bg-slate-900/70 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleRole(role)}
                          className="mt-0.5 h-3.5 w-3.5 rounded border-slate-600 bg-slate-950 text-indigo-500 focus:ring-indigo-500"
                        />
                        <div className="min-w-0">
                          <div className="font-mono text-[11px] font-semibold">
                            {role}
                          </div>
                          <div className="text-[10px] text-slate-400 leading-tight">
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
                <div className="mb-1 flex items-center justify-between text-[11px]">
                  <label
                    htmlFor="ingest-doc-content"
                    className="font-medium text-slate-300"
                  >
                    Markdown Content
                  </label>
                  <span className="font-mono text-slate-500">
                    {content.length} chars
                  </span>
                </div>
                <textarea
                  id="ingest-doc-content"
                  rows={8}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={"# Section Heading\n\nPaste Markdown runbook, error codes (ERR_409_CONFLICT), or policy text..."}
                  className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs leading-relaxed text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={!session || isSubmitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Chunking, Embedding &amp; Indexing...
                  </>
                ) : (
                  <>
                    <Upload className="h-3.5 w-3.5" />
                    Ingest Document to PostgreSQL + pgvector
                  </>
                )}
              </button>

              {/* HTTP 201 Chunk Breakdown Output */}
              {ingestResult && (
                <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 p-3.5 space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-300">
                      <CheckCircle2 className="h-4 w-4" />
                      HTTP 201 Indexed ({ingestResult.chunks_count} chunks)
                    </span>
                    <span className="font-mono text-[10px] text-emerald-200/80">
                      doc_id: {ingestResult.document_id}
                    </span>
                  </div>

                  <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                    {ingestResult.chunks.map((chunk, idx) => (
                      <div
                        key={chunk.chunk_id}
                        className="flex items-center justify-between gap-2 rounded-lg border border-emerald-500/20 bg-slate-950/70 px-2.5 py-1.5 text-[11px]"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-[10px] text-emerald-400">
                            #{idx + 1}
                          </span>
                          <span className="truncate font-medium text-slate-200">
                            {chunk.section_header || "Document Root"}
                          </span>
                        </div>
                        <span className="shrink-0 font-mono text-[10px] text-slate-400">
                          {chunk.character_count} chars
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </form>

            {/* Right: Tenant Indexed Documents List (GET /api/v1/documents) */}
            <div className="flex flex-col rounded-xl border border-slate-800 bg-slate-950/60 p-4 lg:col-span-6">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-300">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  Indexed Tenant Documents ({documents.length})
                </h3>
                <button
                  type="button"
                  disabled={loadingDocs || !session}
                  onClick={fetchDocuments}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700 transition-colors cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw
                    className={`h-3 w-3 ${loadingDocs ? "animate-spin" : ""}`}
                  />
                  Refresh
                </button>
              </div>

              {docsError && (
                <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-2 text-xs text-rose-200">
                  Failed to fetch documents: {docsError}
                </div>
              )}

              <div className="flex-1 max-h-[440px] overflow-y-auto space-y-2 pr-1">
                {loadingDocs && documents.length === 0 ? (
                  <div className="flex h-40 items-center justify-center text-xs text-slate-400">
                    Loading indexed documents for {session?.tenant_id}...
                  </div>
                ) : documents.length === 0 ? (
                  <div className="flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-400">
                    <FileText className="mb-2 h-5 w-5 text-slate-500" />
                    No documents indexed for{" "}
                    <span className="font-mono text-slate-300">
                      {session?.tenant_id}
                    </span>{" "}
                    yet.
                  </div>
                ) : (
                  documents.map((doc) => {
                    const metaRoles = Array.isArray(doc.doc_metadata?.allowed_roles)
                      ? (doc.doc_metadata.allowed_roles as unknown[]).map(String)
                      : null;

                    return (
                      <div
                        key={doc.id}
                        className="rounded-xl border border-slate-800/90 bg-slate-900/75 p-3 space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h4 className="truncate text-xs font-semibold text-slate-100">
                              {doc.title}
                            </h4>
                            <p className="mt-0.5 font-mono text-[10px] text-slate-500">
                              {formatTimestamp(doc.created_at)}
                            </p>
                          </div>
                          <span className="shrink-0 rounded-md border border-indigo-500/30 bg-indigo-500/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-indigo-200">
                            {doc.chunks_count} chunks
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="rounded border border-slate-700 bg-slate-950 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                            {doc.tenant_id}
                          </span>
                          {metaRoles && metaRoles.length > 0 ? (
                            metaRoles.map((role) => (
                              <span
                                key={role}
                                className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-300"
                              >
                                {role}
                              </span>
                            ))
                          ) : (
                            <span className="rounded border border-slate-700/80 bg-slate-800/80 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                              ACL: chunk-scoped
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
