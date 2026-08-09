import React from 'react';

export default function ExecutiveDashboard() {
  return (
    <div className="min-h-screen bg-neutral-900 text-white p-8">
      <header className="mb-8 border-b border-neutral-800 pb-4">
        <h1 className="text-3xl font-bold tracking-tight">Network Executive View</h1>
        <p className="text-neutral-400 mt-2">Real-time Defensible Metrics & System Integrity</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-neutral-800 p-6 rounded-lg border border-neutral-700">
          <h2 className="text-sm uppercase tracking-wider text-neutral-400 mb-1">Network Status</h2>
          <div className="text-2xl font-semibold text-emerald-400">HEALTHY</div>
          <div className="text-xs text-neutral-500 mt-2">Source: Provider Diagnostics</div>
        </div>
        
        <div className="bg-neutral-800 p-6 rounded-lg border border-neutral-700">
          <h2 className="text-sm uppercase tracking-wider text-neutral-400 mb-1">P95 Route Time</h2>
          <div className="text-2xl font-semibold text-neutral-500">PENDING DATA</div>
          <div className="text-xs text-neutral-500 mt-2">Source: TomTom Routing Engine</div>
        </div>

        <div className="bg-neutral-800 p-6 rounded-lg border border-neutral-700">
          <h2 className="text-sm uppercase tracking-wider text-neutral-400 mb-1">Data Freshness</h2>
          <div className="text-2xl font-semibold text-yellow-400">DEGRADED</div>
          <div className="text-xs text-neutral-500 mt-2">Source: ZonePilot Ops Ledger</div>
        </div>
      </div>

      <section className="bg-neutral-800 rounded-lg border border-neutral-700 p-6">
        <h2 className="text-xl font-semibold mb-4">Latest Decision Outcomes</h2>
        <div className="text-neutral-500 text-sm italic">
          No prospective decisions have been frozen yet.
        </div>
      </section>
    </div>
  );
}
