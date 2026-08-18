"use client";

import { useState } from "react";
import { FlaskConical, CheckCircle2, ShieldCheck, ArrowUpRight, Clock, Award, FileText } from "lucide-react";

interface Experiment {
  id: string;
  title: string;
  category: string;
  hypothesis: string;
  status: "VALIDATED" | "ACTIVE" | "PENDING";
  metrics: Record<string, string>;
  evidenceDoc: string;
}

const EXPERIMENTS: Experiment[] = [
  {
    id: "EXP-01",
    title: "Deterministic Facility Optimization vs Baseline",
    category: "R3 Optimization",
    hypothesis: "Multi-scenario CP-SAT solver achieves >99.0% coverage with <850s P95 travel compared to single-scenario heuristic.",
    status: "VALIDATED",
    metrics: {
      "Coverage Gain": "+14.2%",
      "P95 Latency Reduction": "-180s",
      "Solve Time": "<1.5s",
      "Determinism": "100% Lexicographical",
    },
    evidenceDoc: "docs/EXPERIMENTS.md#exp-01",
  },
  {
    id: "EXP-02",
    title: "Resilience Under Compound Monsoon Flooding",
    category: "R4 Resilience",
    hypothesis: "Dynamic road network rerouting sustains network connectivity with zero disconnected cells under 35mm/hr rain.",
    status: "VALIDATED",
    metrics: {
      "Coverage Maintained": "99.1%",
      "Disconnected Cells": "0 / 94",
      "Degradation Grade": "ROBUST",
    },
    evidenceDoc: "docs/EXPERIMENTS.md#exp-02",
  },
  {
    id: "EXP-03",
    title: "Point-In-Time Causality & Anti-Leakage",
    category: "R7 Decision Ledger",
    hypothesis: "Strict temporal feature cutoffs guarantee zero retroactive lookahead bias across 100% of replayed decisions.",
    status: "VALIDATED",
    metrics: {
      "Temporal Leakage": "0.0%",
      "Replay Fidelity": "100.0% Exact",
      "Lineage Verifications": "153 / 153",
    },
    evidenceDoc: "docs/EXPERIMENTS.md#exp-03",
  },
  {
    id: "EXP-04",
    title: "Shadow Evaluation & Regret Tracking",
    category: "R7 Prospective Validation",
    hypothesis: "Prospective decision freezes bound regret to within ±50s of actual future observed transit durations.",
    status: "VALIDATED",
    metrics: {
      "Mean Regret": "18.4s",
      "Freeze Window": "2.0 hrs",
      "Evaluation State": "EVALUATED",
    },
    evidenceDoc: "docs/EXPERIMENTS.md#exp-04",
  },
];

export default function ExperimentsPage() {
  const [selectedExp, setSelectedExp] = useState<Experiment>(EXPERIMENTS[0]!);

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Experiment Registry (EXP-01..04)
          </h1>
          <p className="text-sm text-slate-600">
            Formal experimental benchmark suites evaluating optimization, resilience, PIT causality, and prospective shadow validation.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-3">
            {EXPERIMENTS.map((exp) => (
              <button
                key={exp.id}
                onClick={() => setSelectedExp(exp)}
                className={`w-full text-left rounded-xl border p-5 transition-all shadow-sm flex flex-col justify-between space-y-3 ${
                  selectedExp.id === exp.id
                    ? "border-blue-500 bg-blue-50/40 ring-1 ring-blue-500"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                    {exp.id}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                    <CheckCircle2 className="h-3 w-3" /> {exp.status}
                  </span>
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">{exp.title}</h2>
                  <p className="text-xs text-slate-500 mt-0.5">{exp.category}</p>
                </div>
              </button>
            ))}
          </div>

          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <span className="text-xs font-mono font-bold text-blue-600 uppercase tracking-wider">{selectedExp.id} • {selectedExp.category}</span>
                  <h2 className="text-xl font-bold text-slate-900 mt-1">{selectedExp.title}</h2>
                </div>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                  {selectedExp.status}
                </span>
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Experimental Hypothesis</h3>
                <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700 border border-slate-200 leading-relaxed">
                  {selectedExp.hypothesis}
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Validated Key Metrics</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Object.entries(selectedExp.metrics).map(([key, val]) => (
                    <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{key}</p>
                      <p className="text-base font-bold text-slate-900 mt-1 font-mono">{val}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-blue-50/50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-blue-900 font-medium">
                  <FileText className="h-4 w-4 text-blue-600" />
                  <span>Documented in repository specification</span>
                </div>
                <span className="font-mono text-xs text-blue-700 underline">{selectedExp.evidenceDoc}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
