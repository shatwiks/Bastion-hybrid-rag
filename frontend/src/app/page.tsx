"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, RefreshCw, Server, Database, Layers, ShieldCheck } from "lucide-react";

interface HealthData {
  status: string;
  postgres: string;
  redis: string;
  version: string;
}

export default function HealthPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/health`, {
        cache: "no-store",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data: HealthData = await res.json();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to connect to backend API";
      setError(message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <div className="max-w-3xl w-full space-y-8 bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-6 w-6 text-emerald-400" />
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Enterprise Multi-Tenant RAG
              </h1>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Phase 1 Walking Skeleton — Container Topology &amp; Health Tracer
            </p>
          </div>
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium transition-colors cursor-pointer self-start md:self-auto"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Global Status Banner */}
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            error
              ? "bg-rose-950/40 border-rose-800/60 text-rose-200"
              : health?.status === "ok"
              ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
              : "bg-amber-950/40 border-amber-800/60 text-amber-200"
          }`}
        >
          <div className="flex items-center gap-3">
            {error ? (
              <XCircle className="h-6 w-6 text-rose-400 shrink-0" />
            ) : health?.status === "ok" ? (
              <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
            ) : (
              <RefreshCw className="h-6 w-6 text-amber-400 shrink-0 animate-spin" />
            )}
            <div>
              <p className="font-semibold text-base">
                {error
                  ? "Health Check Failed"
                  : health?.status === "ok"
                  ? "All Core Services Operational"
                  : "Degraded Status"}
              </p>
              <p className="text-xs opacity-80 mt-0.5">
                {error
                  ? error
                  : `Target API: ${apiUrl}/api/v1/health • Checked at ${lastChecked || "just now"}`}
              </p>
            </div>
          </div>
          {health?.version && (
            <span className="text-xs px-2.5 py-1 rounded-md bg-slate-800/80 font-mono text-slate-300">
              v{health.version}
            </span>
          )}
        </div>

        {/* Services Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* FastAPI Card */}
          <div className="p-5 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Backend Gateway
              </span>
              <Server className="h-4 w-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-200">Async FastAPI</h3>
              <p className="text-xs text-slate-400 mt-1">Port 8000 • uvloop + Starlette</p>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  health ? "bg-emerald-400 animate-pulse" : "bg-rose-400"
                }`}
              />
              <span className="text-xs font-medium text-slate-300">
                {health ? "Connected (200 OK)" : "Unreachable"}
              </span>
            </div>
          </div>

          {/* Postgres Card */}
          <div className="p-5 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Vector &amp; ACL Store
              </span>
              <Database className="h-4 w-4 text-sky-400" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-200">PostgreSQL 17</h3>
              <p className="text-xs text-slate-400 mt-1">Port 5437 • pgvector + asyncpg</p>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  health?.postgres === "connected"
                    ? "bg-emerald-400"
                    : "bg-rose-400"
                }`}
              />
              <span className="text-xs font-medium text-slate-300">
                {health?.postgres === "connected" ? "Connected (SELECT 1)" : "Disconnected"}
              </span>
            </div>
          </div>

          {/* Redis Card */}
          <div className="p-5 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Semantic Cache
              </span>
              <Layers className="h-4 w-4 text-amber-400" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-200">Redis 8 Alpine</h3>
              <p className="text-xs text-slate-400 mt-1">Port 6379 • RediSearch / RedisVL</p>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  health?.redis === "connected"
                    ? "bg-emerald-400"
                    : "bg-rose-400"
                }`}
              />
              <span className="text-xs font-medium text-slate-300">
                {health?.redis === "connected" ? "Connected (PING)" : "Disconnected"}
              </span>
            </div>
          </div>
        </div>

        {/* Telemetry Payload Card */}
        {health && (
          <div className="rounded-xl bg-slate-950/70 border border-slate-800/80 p-4 font-mono text-xs text-slate-400 space-y-2">
            <div className="flex justify-between items-center text-slate-500 text-[11px] uppercase tracking-wider pb-1 border-b border-slate-800">
              <span>Healthcheck Payload</span>
              <span>GET /api/v1/health</span>
            </div>
            <pre className="text-slate-300 overflow-x-auto">
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </main>
  );
}
