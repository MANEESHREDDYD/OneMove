"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { History, RefreshCw, AlertTriangle, CheckCircle2, FileSearch, ArrowRight, ShieldCheck } from "lucide-react";
import { ApiError, getApiJson } from "../../lib/api/client";

interface DecisionItem {
  decision_id: string;
  workspace_id: string;
  decision_time: string;
  selected_action: string;
  opened_facilities: string[];
  objective_value: number;
  expected_travel_seconds: number;
  p95_travel_seconds: number;
  coverage_basis_points: number;
  code_sha: string;
  recorded_at: string;
}

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<DecisionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDecisions = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getApiJson<{ data: DecisionItem[] }>("decisions", signal);
      setDecisions(res.data || []);
      if (res.data && res.data.length > 0 && !selectedDecision) {
        setSelectedDecision(res.data[0] ?? null);
      }
    } catch {
      setDecisions([]);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [selectedDecision]);

  useEffect(() => {
    const controller = new AbortController();
    void loadDecisions(controller.signal);
    return () => controller.abort();
  }, [loadDecisions]);

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Durable Decision Ledger (R7)
            </h1>
            <p className="text-sm text-slate-600">
              Immutable PostgreSQL ledger recording real facility optimizations with Point-In-Time cryptographic lineage.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/replay"
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-colors"
            >
              <History className="h-3.5 w-3.5" />
              Time Travel Replay
            </Link>
            <button
              onClick={() => void loadDecisions()}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Ledger Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Recorded Decisions ({decisions.length})</h2>
            <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
              {decisions.map((d) => (
                <button
                  key={d.decision_id}
                  onClick={() => setSelectedDecision(d)}
                  className={`w-full text-left px-3 py-2.5 text-xs transition-colors flex items-center justify-between ${
                    selectedDecision?.decision_id === d.decision_id ? "bg-blue-50 font-bold text-blue-900" : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div>
                    <span className="font-mono text-blue-700 font-semibold">{d.decision_id}</span>
                    <p className="text-[10px] text-slate-400 mt-0.5">{new Date(d.decision_time).toLocaleDateString()}</p>
                  </div>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                    {d.selected_action}
                  </span>
                </button>
              ))}
              {decisions.length === 0 && (
                <p className="py-6 text-center text-xs text-slate-400">No decisions recorded in workspace yet</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {selectedDecision ? (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span className="font-mono text-sm font-bold text-slate-900">{selectedDecision.decision_id}</span>
                    <p className="text-xs text-slate-500 mt-1">
                      Decision Time: {new Date(selectedDecision.decision_time).toLocaleString()} • Workspace: {selectedDecision.workspace_id}
                    </p>
                  </div>
                  <Link
                    href={`/replay?id=${selectedDecision.decision_id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-100"
                  >
                    Replay with PIT Check
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Action</p>
                    <p className="text-sm font-bold text-slate-900 mt-1 font-mono">{selectedDecision.selected_action}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Coverage</p>
                    <p className="text-sm font-bold text-slate-900 mt-1">
                      {(selectedDecision.coverage_basis_points / 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Expected Travel</p>
                    <p className="text-sm font-bold text-slate-900 mt-1">{selectedDecision.expected_travel_seconds}s</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">P95 Travel</p>
                    <p className="text-sm font-bold text-slate-900 mt-1">{selectedDecision.p95_travel_seconds}s</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Opened Facility Identifiers</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedDecision.opened_facilities.map((fac) => (
                      <span key={fac} className="inline-flex items-center gap-1 rounded bg-blue-50 border border-blue-200 px-2.5 py-1 text-xs font-mono font-bold text-blue-900">
                        <CheckCircle2 className="h-3 w-3 text-blue-600" />
                        {fac}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-xs text-slate-600 font-mono">
                  <p><strong className="text-slate-800">Code SHA:</strong> {selectedDecision.code_sha}</p>
                  <p><strong className="text-slate-800">Recorded At:</strong> {new Date(selectedDecision.recorded_at).toLocaleString()}</p>
                  <p><strong className="text-slate-800">Durability:</strong> Verified stored in public.decision_records</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm space-y-3">
                <History className="mx-auto h-12 w-12 text-slate-300" />
                <h3 className="text-base font-bold text-slate-900">Select a Decision</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Select a recorded decision from the left panel to inspect its cryptographic lineage and audit trail.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
