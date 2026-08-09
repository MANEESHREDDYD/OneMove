'use client';
import React, { useEffect, useState } from 'react';

export default function NetworkObservatory() {
  const [networkData, setNetworkData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Attempt to fetch actual network state
    fetch('/api/v1/zones')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load network topology');
        return res.json();
      })
      .then(data => {
        setNetworkData(data.data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      {/* Sidebar Controls */}
      <aside className="w-80 border-r border-neutral-800 p-6 flex flex-col bg-neutral-900 z-10 shadow-xl">
        <h1 className="text-2xl font-bold tracking-tight mb-6">Bengaluru Digital Twin</h1>
        
        <div className="mb-6">
          <h2 className="text-xs uppercase tracking-wider text-neutral-500 mb-2 font-semibold">Active Layers</h2>
          <div className="space-y-2">
            <label className="flex items-center space-x-2 text-sm text-neutral-300">
              <input type="checkbox" checked readOnly className="form-checkbox bg-neutral-800 border-neutral-600 rounded text-blue-500" />
              <span>OSM Gold Base Map</span>
            </label>
            <label className="flex items-center space-x-2 text-sm text-neutral-300">
              <input type="checkbox" checked readOnly className="form-checkbox bg-neutral-800 border-neutral-600 rounded text-blue-500" />
              <span>H3 Resolution 9 Grid</span>
            </label>
            <label className="flex items-center space-x-2 text-sm text-neutral-500 opacity-50">
              <input type="checkbox" disabled className="form-checkbox bg-neutral-800 border-neutral-700 rounded text-blue-500" />
              <span>Live Traffic Flow</span>
            </label>
          </div>
        </div>

        <div className="mt-auto p-4 bg-neutral-800/50 rounded-lg border border-neutral-700/50">
          <div className="text-xs text-neutral-400">Current Time: {new Date().toISOString()}</div>
          <div className="text-xs text-neutral-400 mt-1">Target Mode: Real-time Observation</div>
        </div>
      </aside>

      {/* Main Map View Area */}
      <main className="flex-1 relative bg-[#0a0a0a] flex items-center justify-center">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-20">
            <div className="animate-pulse text-neutral-400 text-sm tracking-widest">LOADING TOPOLOGY...</div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-20">
            <div className="text-red-400 border border-red-900/50 bg-red-950/20 p-4 rounded text-sm">
              ERROR: {error}
            </div>
          </div>
        )}
        
        {/* Placeholder for map when traffic is absent */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none opacity-40">
          <svg className="w-24 h-24 text-neutral-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <div className="text-neutral-500 font-mono tracking-widest text-lg">TRAFFIC DATA NOT YET AVAILABLE</div>
          <div className="text-neutral-600 text-xs mt-2">Waiting for canonical historical backfill or live acquisition</div>
        </div>
      </main>
    </div>
  );
}
