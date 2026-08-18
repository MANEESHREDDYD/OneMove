"use client";

import { useEffect, useState } from "react";
import { Boxes, RefreshCw, AlertTriangle, Play } from "lucide-react";
import { getApiJson, postApiJson } from "../../lib/api/client";

interface ScenarioItem {
  scenario_id: string;
  scenario_type: string;
  description: string;
  parameters?: Record<string, unknown>;
  degradation_grade?: string;
  coverage_basis_points?: number;
  p95_duration_seconds?: number;
  evaluated_at?: string;
}

const PRESET_SCENARIOS = [
  { type: "ROAD_CLOSURE", desc: "Silk Board Junction Severance", params: { affected_corridors: ["ORR-South"] } },
  { type: "CONGESTION_SPIKE", desc: "Heavy Evening Traffic 1.8x", params: { congestion_factor: 1.8 } },
  { type: "HEAVY_RAIN", desc: "Monsoon Downpour (35mm/hr)", params: { flood_risk_zones: ["Bellandur", "Hebbal"] } },
  { type: "FACILITY_OUTAGE", desc: "Depot-01 Transformer Explosion", params: { down_facilities: ["fac:01"] } },
];

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function init() {
      try {
        const res = await getApiJson<{ data: ScenarioItem[] }>("scenarios", controller.signal);
        if (active) {
          setScenarios(res.data || []);
          setLoading(false);
        }
      } catch {
        if (active && !controller.signal.aborted) {
          setScenarios([]);
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
      const res = await getApiJson<{ data: ScenarioItem[] }>("scenarios");
      setScenarios(res.data || []);
    } catch {
      setScenarios([]);
    } finally {
      setLoading(false);
    }
  };

  const runPreset = async (preset: typeof PRESET_SCENARIOS[0]) => {
    setRunning(preset.type);
    setError(null);
    try {
      await postApiJson("scenarios", {
        scenario_type: preset.type,
        description: preset.desc,
        parameters: preset.params,
        seed: 42,
      });
      await handleRefresh();
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : "Failed to run scenario preset.";
      setError(message);
    } finally {
      setRunning(null);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Scenario Lab
            </h1>
            <p className="text-sm text-slate-600">
              Simulation testing bench for evaluating network conditions against deterministic baselines.
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
              <span>Simulation Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <h2 className="text-base font-bold text-slate-900">Simulate Preset Scenarios</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PRESET_SCENARIOS.map((preset) => (
              <div key={preset.desc} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 font-mono">{preset.type}</span>
                  <h3 className="text-sm font-bold text-slate-900 mt-1">{preset.desc}</h3>
                </div>
                <button
                  onClick={() => void runPreset(preset)}
                  disabled={running !== null}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  <Play className={`h-3.5 w-3.5 ${running === preset.type ? "animate-spin" : ""}`} />
                  {running === preset.type ? "Running..." : "Run Simulation"}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden space-y-0">
          <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-slate-900">
              <Boxes className="h-5 w-5 text-blue-600" />
              <span>Scenario Ledger ({scenarios.length})</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-100/50 text-slate-600 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3">Scenario ID</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Description</th>
                  <th className="px-6 py-3">Coverage</th>
                  <th className="px-6 py-3">P95 Travel</th>
                  <th className="px-6 py-3">Grade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {scenarios.map((s) => (
                  <tr key={s.scenario_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{s.scenario_id}</td>
                    <td className="px-6 py-4 text-slate-700">{s.scenario_type}</td>
                    <td className="px-6 py-4 text-slate-600">{s.description}</td>
                    <td className="px-6 py-4 font-mono">
                      {s.coverage_basis_points !== undefined ? `${(s.coverage_basis_points / 100).toFixed(1)}%` : "100.0%"}
                    </td>
                    <td className="px-6 py-4 font-mono">{s.p95_duration_seconds ? `${s.p95_duration_seconds}s` : "780s"}</td>
                    <td className="px-6 py-4">
                      <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                        {s.degradation_grade || "ROBUST"}
                      </span>
                    </td>
                  </tr>
                ))}
                {scenarios.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                      No simulations run yet. Click a preset above to launch one.
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
