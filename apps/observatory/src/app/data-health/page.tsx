"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function init() {
      try {
        const [healthRes, datasetsRes] = await Promise.all([
          getApiJson<DataHealthResponse>("data-health", controller.signal),
          getApiJson<DatasetListResponse>("datasets", controller.signal),
        ]);
        if (active) {
          setProviders(healthRes.data);
          setEvaluatedAt(healthRes.evaluated_at);
          setDatasets(datasetsRes.data);
          setLoading(false);
        }
      } catch (caught: unknown) {
        if (active && !controller.signal.aborted) {
          const message =
            caught instanceof ApiError
              ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
              : caught instanceof Error
                ? caught.message
                : "Failed to load data health metrics.";
          setError(message);
          setLoading(false);
        }
      }
    }

    void init();
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, datasetsRes] = await Promise.all([
        getApiJson<DataHealthResponse>("data-health"),
        getApiJson<DatasetListResponse>("datasets"),
      ]);
      setProviders(healthRes.data);
      setEvaluatedAt(healthRes.evaluated_at);
      setDatasets(datasetsRes.data);
    } catch (caught: unknown) {
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to load data health metrics.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const freshCount = providers.filter((p) => p.state === "FRESH").length;
  const dqPassCount = providers.filter((p) => p.dq_result === "PASS").length;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Data Health &amp; Freshness SLA (R0/R1)
            </h1>
            <p className="text-sm text-slate-600">
              Real-time monitoring of ingestion freshness, SLA compliance, and data quality reports across providers.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {evaluatedAt && (
              <span className="text-xs text-slate-500">
                Last Evaluated: {new Date(evaluatedAt).toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={() => void handleRefresh()}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
              Refresh Health
            </button>
          </div>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Failed to load data health metrics</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Providers Tracked</span>
              <Activity className="h-5 w-5 text-blue-600" />
            </div>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{providers.length}</p>
            <p className="mt-1 text-xs text-slate-500">{freshCount} of {providers.length} reporting FRESH</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Data Quality Pass</span>
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
            </div>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
              {providers.length ? `${Math.round((dqPassCount / providers.length) * 100)}%` : "N/A"}
            </p>
            <p className="mt-1 text-xs text-slate-500">{dqPassCount} providers passing all automated DQ checks</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Registered Datasets</span>
              <Database className="h-5 w-5 text-purple-600" />
            </div>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{datasets.length}</p>
            <p className="mt-1 text-xs text-slate-500">Canonical datasets with verified cryptographic lineage</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden space-y-0">
          <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">Provider Health &amp; Ingestion Freshness</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-100/50 text-slate-600 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3">Provider ID</th>
                  <th className="px-6 py-3">Datasets</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Observed Freshness</th>
                  <th className="px-6 py-3">SLA Expected</th>
                  <th className="px-6 py-3">DQ Check</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {providers.map((p) => (
                  <tr key={p.provider} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{p.provider}</td>
                    <td className="px-6 py-4 text-slate-700 font-mono text-[11px]">{p.dataset_ids?.join(", ") || "N/A"}</td>
                    <td className="px-6 py-4">{stateBadge(p.state)}</td>
                    <td className="px-6 py-4 font-mono">{p.observed_freshness_seconds !== null ? `${Math.round(p.observed_freshness_seconds / 60)}m` : "N/A"}</td>
                    <td className="px-6 py-4 font-mono">{Math.round(p.expected_freshness_seconds / 60)}m</td>
                    <td className="px-6 py-4">
                      {p.dq_result === "PASS" ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5" /> PASS
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 font-semibold text-amber-700">
                          <AlertTriangle className="h-3.5 w-3.5" /> {p.dq_result}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {providers.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                      No provider telemetry available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
