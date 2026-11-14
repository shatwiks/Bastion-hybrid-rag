import type {
  CandidateTelemetryRow,
  ChatStreamRequest,
  CitationItem,
  DemoTokenResponse,
  DemoTokenSession,
  DocumentIngestRequest,
  DocumentIngestResponse,
  DocumentListResponse,
  DoneEventPayload,
  HealthStatusResponse,
  ParsedCitationSegment,
  PersonaType,
  PipelineStepUpdate,
  RefusalEventPayload,
  TenantId,
} from "@/types/rag";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const configured =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    DEFAULT_API_BASE_URL;
  return configured.replace(/\/+$/, "");
}

async function extractErrorMessage(res: Response): Promise<string> {
  const fallback = `HTTP ${res.status}: ${res.statusText || "Request failed"}`;
  try {
    const text = await res.text();
    if (!text) return fallback;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
      if (typeof parsed.detail === "string" && parsed.detail.trim()) {
        return parsed.detail;
      }
      if (typeof parsed.message === "string" && parsed.message.trim()) {
        return parsed.message;
      }
      if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
        return parsed.detail
          .map((item) =>
            typeof item === "object" && item !== null && "msg" in item
              ? String((item as { msg: unknown }).msg)
              : JSON.stringify(item)
          )
          .join("; ");
      }
    } catch {
      return text;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

export async function mintDemoToken(
  tenantId: TenantId,
  persona: PersonaType,
  signal?: AbortSignal
): Promise<DemoTokenSession> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/demo-token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tenant_id: tenantId,
      persona,
    }),
    signal,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  const data = (await res.json()) as DemoTokenResponse;
  return {
    ...data,
    tenant_id: (data.tenant_id as TenantId) || tenantId,
    persona,
  };
}

export async function fetchHealthStatus(
  signal?: AbortSignal
): Promise<HealthStatusResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
    method: "GET",
    signal,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  return (await res.json()) as HealthStatusResponse;
}

export async function listDocuments(
  token: string,
  signal?: AbortSignal
): Promise<DocumentListResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/documents`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    signal,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  return (await res.json()) as DocumentListResponse;
}

export async function ingestDocument(
  token: string,
  payload: DocumentIngestRequest,
  signal?: AbortSignal
): Promise<DocumentIngestResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  return (await res.json()) as DocumentIngestResponse;
}

export interface StreamChatCallbacks {
  onStepUpdate?: (step: PipelineStepUpdate) => void;
  onToken?: (delta: string) => void;
  onCitations?: (citations: CitationItem[]) => void;
  onRefusal?: (refusal: RefusalEventPayload) => void;
  onDone?: (done: DoneEventPayload) => void;
  onError?: (error: Error) => void;
}

function dispatchSseFrame(
  rawFrame: string,
  callbacks: StreamChatCallbacks
): void {
  const trimmed = rawFrame.trim();
  if (!trimmed) return;

  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of trimmed.split("\n")) {
    if (line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) return;

  const rawData = dataLines.join("\n");
  let payload: unknown;
  try {
    payload = JSON.parse(rawData);
  } catch {
    return;
  }

  switch (eventName) {
    case "step_update":
      callbacks.onStepUpdate?.(payload as PipelineStepUpdate);
      break;
    case "token": {
      const tokenPayload = payload as { delta?: unknown };
      if (typeof tokenPayload.delta === "string") {
        callbacks.onToken?.(tokenPayload.delta);
      }
      break;
    }
    case "citations": {
      const citPayload = payload as { citations?: unknown };
      if (Array.isArray(citPayload.citations)) {
        callbacks.onCitations?.(citPayload.citations as CitationItem[]);
      }
      break;
    }
    case "refusal":
      callbacks.onRefusal?.(payload as RefusalEventPayload);
      break;
    case "done":
      callbacks.onDone?.(payload as DoneEventPayload);
      break;
    default:
      break;
  }
}

export async function streamChatQuery(
  token: string,
  request: ChatStreamRequest,
  callbacks: StreamChatCallbacks,
  signal?: AbortSignal
): Promise<void> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        query: request.query,
        chat_history: request.chat_history ?? [],
        bypass_cache: request.bypass_cache ?? false,
      }),
      signal,
    });

    if (!res.ok) {
      throw new Error(await extractErrorMessage(res));
    }

    if (!res.body) {
      throw new Error("Streaming response body is unavailable.");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");

      let separatorIndex = buffer.indexOf("\n\n");
      while (separatorIndex !== -1) {
        const frame = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        dispatchSseFrame(frame, callbacks);
        separatorIndex = buffer.indexOf("\n\n");
      }
    }

    const remaining = buffer.replace(/\r\n/g, "\n").trim();
    if (remaining) {
      dispatchSseFrame(remaining, callbacks);
    }
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    const error = err instanceof Error ? err : new Error("SSE stream failed");
    callbacks.onError?.(error);
    throw error;
  }
}

const CITATION_TOKEN_PATTERN = /\[([a-f0-9-]{6,36})\]/gi;

export function parseTextWithCitations(text: string): ParsedCitationSegment[] {
  if (!text) return [];

  const segments: ParsedCitationSegment[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(CITATION_TOKEN_PATTERN)) {
    const matchIndex = match.index ?? 0;
    const raw = match[0];
    const chunkId = match[1];

    if (matchIndex > lastIndex) {
      segments.push({
        type: "text",
        value: text.slice(lastIndex, matchIndex),
      });
    }

    segments.push({
      type: "citation",
      chunkId,
      raw,
    });

    lastIndex = matchIndex + raw.length;
  }

  if (lastIndex < text.length) {
    segments.push({
      type: "text",
      value: text.slice(lastIndex),
    });
  }

  return segments;
}

export function mergeCitationsWithCandidateTelemetry(
  citations: CitationItem[],
  steps: PipelineStepUpdate[]
): CitationItem[] {
  const rankMap = new Map<string, CandidateTelemetryRow>();

  for (const step of steps) {
    const rows =
      step.details.reranked_candidates ?? step.details.candidates ?? [];
    for (const row of rows) {
      const existing = rankMap.get(row.chunk_id);
      rankMap.set(row.chunk_id, {
        ...existing,
        ...row,
      });
    }
  }

  return citations.map((citation) => {
    const row = rankMap.get(citation.chunk_id);
    if (!row) return citation;
    return {
      ...citation,
      dense_rank: citation.dense_rank ?? row.dense_rank,
      sparse_rank: citation.sparse_rank ?? row.sparse_rank,
      rrf_score: citation.rrf_score ?? row.rrf_score,
      rerank_score:
        citation.rerank_score ?? (typeof row.rerank_score === "number" ? row.rerank_score : 0),
    };
  });
}
