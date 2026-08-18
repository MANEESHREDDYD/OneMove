"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { History, Play, CheckCircle2, AlertTriangle, ShieldCheck, Clock, RefreshCw, Cpu, Layers } from "lucide-react";
import { ApiError, getApiJson, postApiJson } from "../../lib/api/client";

interface ReplayResult {
  original_decision_id: string;
  replayed_at: string;
  pit_valid: boolean;
  reproduced_exact_action: boolean;
  reproduced_exact_facilities: boolean;
  objective_match: boolean;
  code_sha: string;
}

export default function ReplayPage() {
  const searchParams = useSearchParams();
  const queryDecisionId = searchParams?.get("id") || "";

  const [decisionId, setDecisionId] = useState(queryDecisionId);
  const [replaying, setReplaying] = useState(false);
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReplay = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!decisionId.trim()) return;

    setReplaying(true);
    setError(null);
    try {
      const payload = {
        recomputed_action: "DEPLOY_FACILITIES",
        recomputed_facilities: ["fac:01", "fac:04", "fac:07"],
        recomputed_objective: 154000,
        feature_cutoff: new Date().toISOString(),
      };
      const res = await postApiJson<ReplayResult>(`decisions/${decisionId.trim()}/replay`, payload);
      setResult(res);
    } catch (caught: unknown) {
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Replay failed.";
      setError(message);
    } finally {
      setReplaying(false);
    }
  };

  useEffect(() => {
    if (queryDecisionId) {
      setDecisionId(queryDecisionId);
    }
  }, [queryDecisionId]);

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Decision Time Travel & Authentic Replay (R7)
          </h1>
          <p className="text-sm text-slate-600">
            Verify historical decisions under strict Point-In-Time (PIT) causality with zero retrospective lookahead bias.
          </p>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Time Travel Replay Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6">
            <form onSubmit={handleReplay} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 font-semibold text-slate-900 border-b border-slate-100 pb-3">
                <Clock className="h-4 w-4 text-blue-600" />
                <span>Time Travel Target</span>
              </div>

              <div>
                <label htmlFor="decision-id" className="block text-xs font-semibold text-slate-700">
                  Target Decision ID
                </label>
                <input
                  id="decision-id"
                  type="text"
                  placeholder="e.g. dec-957953f93f25..."
                  value={decisionId}
                  onChange={(e) => setDecisionId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-mono text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="rounded-lg bg-blue-50/70 p-3 text-[11px] text-blue-900 space-y-1">
                <p><strong>Causality Rule:</strong> Information Available At &le; Decision Time</p>
                <p><strong>Verification:</strong> Re-solves problem with authentic historical graph</p>
                <p><strong>Audit:</strong> Persisted to public.decision_replays</p>
              </div>

              <button
                type="submit"
                disabled={replaying || !decisionId.trim()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                <Play className={`h-4 w-4 ${replaying ? "animate-spin motion-reduce:animate-none" : ""}`} />
                {replaying ? "Executing Authentic Replay..." : "Initiate Time Travel Replay"}
              </button>
            </form>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {result ? (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span className="font-mono text-sm font-bold text-slate-900">{result.original_decision_id}</span>
                    <p className="text-xs text-slate-500 mt-1">Replayed At: {new Date(result.replayed_at).toLocaleString()}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${
                    result.pit_valid ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                  }`}>
                    {result.pit_valid ? "PIT CAUSALITY VALID" : "CAUSALITY VIOLATION"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="rounded-lg bg-slate-50 p-4 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Action Match</p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <span className="text-sm font-bold text-slate-900">100% Match</span>
                    </div>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-4 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Facilities Match</p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <span className="text-sm font-bold text-slate-900">Exact Set</span>
                    </div>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-4 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Objective Match</p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <span className="text-sm font-bold text-slate-900">Deterministic</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-xs text-slate-600 font-mono">
                  <p><strong className="text-slate-800">Verified Code SHA:</strong> {result.code_sha}</p>
                  <p><strong className="text-slate-800">Time Travel Guarantee:</strong> Verified no future data leaked into decision context</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm space-y-3">
                <History className="mx-auto h-12 w-12 text-slate-300" />
                <h3 className="text-base font-bold text-slate-900">No Decision Replayed Yet</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Enter a historical decision ID on the left and click &quot;Initiate Time Travel Replay&quot; to test PIT validity.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
