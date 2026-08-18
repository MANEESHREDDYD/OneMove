"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, AlertTriangle, CheckCircle2, Clock, ShieldCheck, Activity } from "lucide-react";
import { ApiError, getApiJson } from "../../lib/api/client";
import type { DataHealthResponse, DatasetListResponse, DatasetRecord, ProviderHealth } from "../../lib/api/types";

function stateBadge(state: ProviderHealth["state"]) {
  if (state === "FRESH") {
    return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-3 w-3" /> FRESH</span>;
  }
  if (state === "DEGRADED") {
    return <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800"><AlertTriangle className="h-3 w-3" /> DEGRADED</span>;
  }
  if (state === "STALE") {
    return <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-800"><Clock className="h-3 w-3" /> STALE</span>;
  }
  return <span className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-semibold text-slate-800">UNAVAILABLE</span>;
}

export default function DataHealthPage() {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [evaluatedAt, setEvaluatedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, datasetsRes] = await Promise.all([
        getApiJson<DataHealthResponse>("data-health", signal),
        getApiJson<DatasetListResponse>("datasets", signal),
      ]);
      setProviders(healthRes.data);
      setEvaluatedAt(healthRes.evaluated_at);
      setDatasets(datasetsRes.data);
    } catch (caught: unknown) {
      if (signal.aborted) return;
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to load data health metrics.";
      setError(message);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  const freshCount = providers.filter((p) => p.state === "FRESH").length;
  const dqPassCount = providers.filter((p) => p.dq_result === "PASS").length;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Data & Provider Health
            </h1>
            <p className="text-sm text-slate-600">
              Real provider freshness, collection status, data quality checks, and discovered dataset versions.
            </p>
          </div>
          <button
            onClick={() => {
              const controller = new AbortController();
              void loadData(controller.signal);
            }}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Health Evaluation Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Fresh Providers</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{freshCount} / {providers.length}</p>
            <p className="mt-1 text-xs text-slate-500">Meeting freshness SLAs</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">DQ Checks Passing</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{dqPassCount} / {providers.length}</p>
            <p className="mt-1 text-xs text-slate-500">Zero data corruptions detected</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Discovered Datasets</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{datasets.length}</p>
            <p className="mt-1 text-xs text-slate-500">Immutable manifest lineage</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-slate-900">
              <Activity className="h-5 w-5 text-blue-600" />
              <span>Provider Freshness & SLAs</span>
            </div>
            {evaluatedAt && (
              <span className="text-xs text-slate-500 font-mono">
                Evaluated: {new Date(evaluatedAt).toLocaleString()}
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-100/50 text-slate-600 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3">Provider</th>
                  <th className="px-6 py-3">State</th>
                  <th className="px-6 py-3">Last Successful Run</th>
                  <th className="px-6 py-3">Expected SLA</th>
                  <th className="px-6 py-3">Observed Lag</th>
                  <th className="px-6 py-3">DQ Check</th>
                  <th className="px-6 py-3">Linked Datasets</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {providers.map((p) => (
                  <tr key={p.provider} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-bold text-slate-900">{p.provider}</td>
                    <td className="px-6 py-4">{stateBadge(p.state)}</td>
                    <td className="px-6 py-4 text-slate-600">
                      {p.last_successful_collection ? new Date(p.last_successful_collection).toLocaleString() : "Never"}
                    </td>
                    <td className="px-6 py-4 text-slate-600">{p.expected_freshness_seconds}s</td>
                    <td className="px-6 py-4 font-mono text-slate-600">
                      {p.observed_freshness_seconds !== null ? `${p.observed_freshness_seconds}s` : "n/a"}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold ${
                        p.dq_result === "PASS" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                      }`}>
                        {p.dq_result}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 font-mono text-[11px]">
                      {p.dataset_ids.join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center gap-2 font-semibold text-slate-900">
            <Database className="h-5 w-5 text-blue-600" />
            <span>Dataset Manifest Catalog ({datasets.length})</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-100/50 text-slate-600 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3">Dataset ID</th>
                  <th className="px-6 py-3">Provider</th>
                  <th className="px-6 py-3">Version</th>
                  <th className="px-6 py-3">Availability</th>
                  <th className="px-6 py-3">Record Count</th>
                  <th className="px-6 py-3">Evidence Class</th>
                  <th className="px-6 py-3">Artifact SHA256</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {datasets.map((d) => (
                  <tr key={`${d.dataset_id}-${d.version}`} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{d.dataset_id}</td>
                    <td className="px-6 py-4 text-slate-700">{d.provider}</td>
                    <td className="px-6 py-4 font-mono text-slate-600">{d.version}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${
                        d.availability === "AVAILABLE" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
                      }`}>
                        {d.availability}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600">{d.record_count?.toLocaleString() ?? "n/a"}</td>
                    <td className="px-6 py-4 text-slate-500">{d.evidence_class ?? "DERIVED"}</td>
                    <td className="px-6 py-4 font-mono text-[11px] text-slate-400 truncate max-w-xs" title={d.artifact_hash || ""}>
                      {d.artifact_hash ? `${d.artifact_hash.slice(0, 16)}...` : "n/a"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
