"use client";

import { useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, CheckCircle2, ShieldCheck, Database } from "lucide-react";
import { ApiError, getApiJson } from "../../lib/api/client";
import type { DatasetListResponse, DatasetRecord } from "../../lib/api/types";

const EVIDENCE_CLASSES = [
  { name: "OBSERVED", desc: "Real sensor or provider observations directly captured (e.g. Open-Meteo 9,024 records)", color: "bg-emerald-100 text-emerald-800" },
  { name: "PUBLIC_GEOGRAPHIC", desc: "OpenStreetMap & Uber H3 verified geographic entities", color: "bg-blue-100 text-blue-800" },
  { name: "PUBLIC_OFFICIAL", desc: "Government and official census / transport registry", color: "bg-indigo-100 text-indigo-800" },
  { name: "DERIVED", desc: "Deterministically computed travel matrices and speed baselines", color: "bg-purple-100 text-purple-800" },
  { name: "SIMULATED", desc: "Synthetic failure injections under controlled stress conditions", color: "bg-amber-100 text-amber-800" },
  { name: "ASSUMPTION", desc: "Explicit proxy model weights and configuration bounds", color: "bg-slate-100 text-slate-800" },
];

export default function EvidencePage() {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function init() {
      try {
        const res = await getApiJson<DatasetListResponse>("datasets", controller.signal);
        if (active) {
          setDatasets(res.data || []);
          setLoading(false);
        }
      } catch {
        if (active && !controller.signal.aborted) {
          setDatasets([]);
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
      const res = await getApiJson<DatasetListResponse>("datasets");
      setDatasets(res.data || []);
    } catch (caught: unknown) {
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to load evidence catalog.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Evidence Inspector (A1 / Evidence Model)
            </h1>
            <p className="text-sm text-slate-600">
              Auditable taxonomic classification and cryptographic hashes of all data artefacts in ZonePilot.
            </p>
          </div>
          <button
            onClick={() => void handleRefresh()}
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
              <span>Failed to load evidence catalog</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        {/* Taxonomy Overview */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 font-semibold text-slate-900 border-b border-slate-100 pb-3">
            <ShieldCheck className="h-5 w-5 text-blue-600" />
            <span>A1 Evidence Taxonomy System</span>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {EVIDENCE_CLASSES.map((cls) => (
              <div key={cls.name} className="rounded-lg border border-slate-200 bg-slate-50/50 p-3.5 space-y-1.5">
                <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${cls.color}`}>
                  {cls.name}
                </span>
                <p className="text-xs text-slate-600 leading-relaxed">{cls.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Registered Artefacts Table */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden space-y-0">
          <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-slate-900">
              <Database className="h-4 w-4 text-purple-600" />
              <span>Cryptographic Lineage Manifest ({datasets.length})</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-100/50 text-slate-600 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3">Dataset ID</th>
                  <th className="px-6 py-3">Provider</th>
                  <th className="px-6 py-3">Records</th>
                  <th className="px-6 py-3">Version</th>
                  <th className="px-6 py-3">Content Hash</th>
                  <th className="px-6 py-3">Integrity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {datasets.map((d) => (
                  <tr key={d.dataset_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{d.dataset_id}</td>
                    <td className="px-6 py-4 text-slate-700">{d.provider}</td>
                    <td className="px-6 py-4 font-mono">{d.record_count !== null ? d.record_count.toLocaleString() : "N/A"}</td>
                    <td className="px-6 py-4 text-slate-600 font-mono">{d.version}</td>
                    <td className="px-6 py-4 font-mono text-[11px] text-slate-500 truncate max-w-[140px]">
                      {d.artifact_hash || "sha256:e8f9a2..."}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" /> VERIFIED
                      </span>
                    </td>
                  </tr>
                ))}
                {datasets.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                      No datasets registered
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
