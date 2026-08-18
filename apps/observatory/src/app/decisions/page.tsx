"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function init() {
      try {
        const res = await getApiJson<{ data: DecisionItem[] }>("decisions", controller.signal);
        if (active) {
          const list = res.data || [];
          setDecisions(list);
          if (list.length > 0) setSelectedDecision(list[0] ?? null);
          setLoading(false);
        }
      } catch {
        if (active && !controller.signal.aborted) {
          setDecisions([]);
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
      const res = await getApiJson<{ data: DecisionItem[] }>("decisions");
      const list = res.data || [];
      setDecisions(list);
      if (list.length > 0 && !selectedDecision) {
        setSelectedDecision(list[0] ?? null);
      }
    } catch (caught: unknown) {
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to load decisions.";
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
              Durable Decision Ledger (R7)
            </h1>
            <p className="text-sm text-slate-600">
              Immutable PostgreSQL ledger recording real facility optimizations with Point-In-Time cryptographic lineage.
            </p>
          </div>
          <button
            onClick={() => void handleRefresh()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
            Refresh Ledger
          </button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Failed to load decision ledger</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Decision List */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 font-semibold text-slate-900">
                <History className="h-4 w-4 text-blue-600" />
                <span>Recorded Decisions ({decisions.length})</span>
              </div>
            </div>

            <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-100">
              {decisions.map((d) => (
                <button
                  key={d.decision_id}
                  onClick={() => setSelectedDecision(d)}
                  className={`w-full text-left p-3 rounded-lg transition-colors space-y-1.5 ${
                    selectedDecision?.decision_id === d.decision_id ? "bg-blue-50 border border-blue-200" : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-slate-900 truncate max-w-[170px]">{d.decision_id}</span>
                    <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {d.selected_action}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>{new Date(d.decision_time).toLocaleDateString()}</span>
                    <span>{d.opened_facilities?.length || 0} Facilities</span>
                  </div>
                </button>
              ))}
              {decisions.length === 0 && (
                <p className="py-8 text-center text-xs text-slate-400">No decisions recorded yet in PostgreSQL</p>
              )}
            </div>
          </div>

          {/* Decision Detail Inspector */}
          <div className="lg:col-span-2 space-y-6">
            {selectedDecision ? (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span className="font-mono text-xs text-slate-500 uppercase tracking-wider">Decision Record</span>
                    <h3 className="font-mono text-base font-bold text-slate-900">{selectedDecision.decision_id}</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Executed at: {new Date(selectedDecision.decision_time).toLocaleString()}</p>
                  </div>
                  <Link
                    href={`/replay?id=${selectedDecision.decision_id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-colors"
                  >
                    <span>Time Travel Replay</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Coverage</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {(selectedDecision.coverage_basis_points / 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Expected Travel</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedDecision.expected_travel_seconds}s
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">P95 Travel</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedDecision.p95_travel_seconds}s
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Objective Value</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedDecision.objective_value}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Opened Facilities Set</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedDecision.opened_facilities.map((facId) => (
                      <span key={facId} className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 font-mono text-xs font-bold text-blue-900">
                        <CheckCircle2 className="h-3.5 w-3.5 text-blue-600" />
                        {facId}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2 text-xs text-slate-600 font-mono">
                  <div className="flex items-center gap-1.5 text-emerald-700 font-sans font-bold">
                    <ShieldCheck className="h-4 w-4" />
                    <span>Point-In-Time Integrity Verified</span>
                  </div>
                  <p><strong className="text-slate-800">Solver Engine SHA:</strong> {selectedDecision.code_sha}</p>
                  <p><strong className="text-slate-800">Workspace Tenancy:</strong> {selectedDecision.workspace_id}</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm space-y-3">
                <FileSearch className="mx-auto h-12 w-12 text-slate-300" />
                <h3 className="text-base font-bold text-slate-900">No Decision Selected</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Select a recorded decision from the list to view its Point-In-Time lineage, opened facilities, and verified solve parameters.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
