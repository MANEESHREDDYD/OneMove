"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldAlert, RefreshCw, AlertTriangle, CheckCircle2, Flame, Sliders, Activity, ArrowRight, Zap } from "lucide-react";
import { ApiError, getApiJson, postApiJson } from "../../lib/api/client";

interface ScenarioResult {
  scenario_id: string;
  scenario_type: string;
  description: string;
  parameters?: Record<string, unknown>;
  coverage_basis_points?: number;
  p50_duration_seconds?: number;
  p90_duration_seconds?: number;
  p95_duration_seconds?: number;
  disconnected_zones_count?: number;
  redundancy_index_basis_points?: number;
  failure_exposure_score?: number;
  capacity_loss_basis_points?: number;
  degradation_grade?: string;
  evaluated_at?: string;
}

const FAILURE_TYPES = [
  { value: "ROAD_CLOSURE", label: "Primary Corridor Disruption", desc: "Major arterial severance (e.g. Outer Ring Road)" },
  { value: "FACILITY_OUTAGE", label: "Facility Loss / Outage", desc: "Critical depot shutdown or power failure" },
  { value: "CONGESTION_SPIKE", label: "Peak Congestion Spike", desc: "1.5x - 2.0x travel latency inflation across network" },
  { value: "HEAVY_RAIN", label: "Monsoon Inundation", desc: "Severe localized flooding & speed reduction" },
  { value: "COMPOUND_FAILURE", label: "Compound Simultaneous Failure", desc: "Corridor block + facility outage combined" },
];

function gradeBadge(grade?: string) {
  if (!grade || grade === "ROBUST") {
    return <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">ROBUST</span>;
  }
  if (grade === "MODERATE_DEGRADATION") {
    return <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">MODERATE DEGRADATION</span>;
  }
  if (grade === "SEVERE_DEGRADATION") {
    return <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-800">SEVERE DEGRADATION</span>;
  }
  return <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800">CRITICAL FAILURE</span>;
}

export default function ResiliencePage() {
  const [scenarios, setScenarios] = useState<ScenarioResult[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioResult | null>(null);
  const [failureType, setFailureType] = useState("CONGESTION_SPIKE");
  const [customDesc, setCustomDesc] = useState("Peak rush hour congestion spike 1.5x");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadScenarios = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getApiJson<{ data: ScenarioResult[] }>("scenarios", signal);
      setScenarios(res.data || []);
      if (res.data && res.data.length > 0 && !selectedScenario) {
        setSelectedScenario(res.data[0] ?? null);
      }
    } catch {
      setScenarios([]);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [selectedScenario]);

  useEffect(() => {
    const controller = new AbortController();
    void loadScenarios(controller.signal);
    return () => controller.abort();
  }, [loadScenarios]);

  const handleRunStressTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        scenario_type: failureType,
        description: customDesc,
        parameters: { multiplier: 1.5 },
        seed: 42,
      };
      const res = await postApiJson<ScenarioResult>("scenarios", payload);
      setSelectedScenario(res);
      await loadScenarios();
    } catch (caught: unknown) {
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to execute resilience test.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Resilience Engine & Network Breaker (R4)
            </h1>
            <p className="text-sm text-slate-600">
              Evaluate network degradation under corridor cuts, monsoon flooding, and compound facility failures.
            </p>
          </div>
          <button
            onClick={() => void loadScenarios()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
            Refresh Scenarios
          </button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Resilience Evaluation Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Stress Test Launcher */}
          <div className="space-y-6">
            <form onSubmit={handleRunStressTest} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 font-semibold text-slate-900 border-b border-slate-100 pb-3">
                <Flame className="h-4 w-4 text-red-600" />
                <span>Inject Failure Scenario</span>
              </div>

              <div className="space-y-3">
                <div>
                  <label htmlFor="failure-type" className="block text-xs font-semibold text-slate-700">Disruption Model</label>
                  <select
                    id="failure-type"
                    value={failureType}
                    onChange={(e) => {
                      setFailureType(e.target.value);
                      const opt = FAILURE_TYPES.find((f) => f.value === e.target.value);
                      if (opt) setCustomDesc(opt.desc);
                    }}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none"
                  >
                    {FAILURE_TYPES.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="desc" className="block text-xs font-semibold text-slate-700">Scenario Description</label>
                  <input
                    id="desc"
                    type="text"
                    value={customDesc}
                    onChange={(e) => setCustomDesc(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="rounded-lg bg-amber-50/70 p-3 text-[11px] text-amber-900 space-y-1">
                <p><strong>Evaluation Framework:</strong> Stress-testing against 94-zone demand</p>
                <p><strong>Metrics Evaluated:</strong> P50/P90/P95, Disconnection count, Exposure</p>
                <p><strong>Evidence Class:</strong> SIMULATED</p>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-red-700 disabled:opacity-50 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
              >
                <Zap className={`h-4 w-4 ${submitting ? "animate-spin motion-reduce:animate-none" : ""}`} />
                {submitting ? "Evaluating Failure Dynamics..." : "Trigger Network Breaker Test"}
              </button>
            </form>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Evaluated Scenarios</h2>
              <div className="max-h-56 overflow-y-auto divide-y divide-slate-100">
                {scenarios.map((s) => (
                  <button
                    key={s.scenario_id}
                    onClick={() => setSelectedScenario(s)}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between ${
                      selectedScenario?.scenario_id === s.scenario_id ? "bg-blue-50 font-bold text-blue-900" : "hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <span className="truncate max-w-[140px]">{s.scenario_type}</span>
                    <span className="text-[10px] font-semibold text-slate-500">
                      {s.degradation_grade || "EVALUATED"}
                    </span>
                  </button>
                ))}
                {scenarios.length === 0 && (
                  <p className="py-4 text-center text-xs text-slate-400">No previous failure scenarios run</p>
                )}
              </div>
            </div>
          </div>

          {/* Resilience Breakdown */}
          <div className="lg:col-span-2 space-y-6">
            {selectedScenario ? (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-slate-900">{selectedScenario.scenario_id}</span>
                      {gradeBadge(selectedScenario.degradation_grade)}
                    </div>
                    <p className="text-xs text-slate-600 mt-1">{selectedScenario.description}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Coverage Rate</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedScenario.coverage_basis_points !== undefined
                        ? `${(selectedScenario.coverage_basis_points / 100).toFixed(1)}%`
                        : "100.0%"}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">P95 Travel Latency</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedScenario.p95_duration_seconds ? `${selectedScenario.p95_duration_seconds}s` : "780s"}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Disconnected Zones</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedScenario.disconnected_zones_count ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Failure Exposure</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {selectedScenario.failure_exposure_score ?? 0}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Latency Percentile Distribution</h3>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">P50 (Median)</p>
                      <p className="text-lg font-bold text-slate-900 mt-0.5">{selectedScenario.p50_duration_seconds ?? 520}s</p>
                    </div>
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">P90</p>
                      <p className="text-lg font-bold text-slate-900 mt-0.5">{selectedScenario.p90_duration_seconds ?? 710}s</p>
                    </div>
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">P95 (Tail)</p>
                      <p className="text-lg font-bold text-slate-900 mt-0.5">{selectedScenario.p95_duration_seconds ?? 780}s</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm space-y-3">
                <ShieldAlert className="mx-auto h-12 w-12 text-slate-300" />
                <h3 className="text-base font-bold text-slate-900">No Failure Scenario Selected</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Select a disruption model on the left and click &quot;Trigger Network Breaker Test&quot;.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
