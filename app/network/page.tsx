'use client';
import React, { useEffect, useState } from 'react';
import { Check, Minus } from 'lucide-react';

type LayerState = {
  name: string
  /** Whether the layer is currently rendered. */
  active: boolean
  /** Why an inactive layer is inactive. */
  reason?: string
}

const LAYERS: LayerState[] = [
  { name: 'OSM Gold Base Map', active: true },
  { name: 'H3 Resolution 9 Grid', active: true },
  { name: 'Live Traffic Flow', active: false, reason: 'no traffic source connected' },
];

export default function NetworkObservatory() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

  const zoneCount = Array.isArray(networkData) ? networkData.length : null;

  return (
    // This route is rendered inside AppShell, which already provides the page's
    // single <main> landmark. The wrapper here was previously a second <main>;
    // two main landmarks on one page is a structural error and leaves assistive
    // technology without an unambiguous "start of content".
    <div className="flex h-screen bg-black text-white overflow-hidden">
      {/* Sidebar Controls */}
      <aside aria-labelledby="observatory-controls-heading" className="w-80 border-r border-neutral-800 p-6 flex flex-col bg-neutral-900 z-10 shadow-xl">
        <h1 id="observatory-controls-heading" className="text-2xl font-bold tracking-tight mb-6">Bengaluru Digital Twin</h1>

        <div className="mb-6">
          <h2 className="text-xs uppercase tracking-wider text-neutral-400 mb-2 font-semibold">Active Layers</h2>
          {/*
            These were three <input type="checkbox"> with `checked readOnly` /
            `disabled`. They looked operable, took keyboard focus, and did
            nothing when activated — a control that lies about being a control.
            Layer selection is not wired to anything, so this is now a plain
            status list: each row states its state in text as well as by icon,
            so the on/off distinction does not depend on colour or on the shape
            of a checkbox (WCAG 1.4.1).
          */}
          <ul className="space-y-2">
            {LAYERS.map((layer) => (
              <li
                key={layer.name}
                className={`flex items-start gap-2 text-sm ${layer.active ? 'text-neutral-300' : 'text-neutral-400'}`}
              >
                {layer.active ? (
                  <Check aria-hidden="true" focusable="false" className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <Minus aria-hidden="true" focusable="false" className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                <span>
                  {layer.name}
                  <span className="block text-xs text-neutral-400">
                    {layer.active ? 'Rendering' : `Not rendering — ${layer.reason}`}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-auto p-4 bg-neutral-800/50 rounded-lg border border-neutral-700/50">
          <div className="text-xs text-neutral-300">Current Time: {new Date().toISOString()}</div>
          <div className="text-xs text-neutral-300 mt-1">Target Mode: Real-time Observation</div>
        </div>
      </aside>

      {/* Map View Area */}
      <section aria-labelledby="observatory-map-heading" className="flex-1 relative bg-[#0a0a0a] flex items-center justify-center">
        <h2 id="observatory-map-heading" className="sr-only">Network topology map</h2>

        {/*
          Async state is announced. `role="status"` (implicit aria-live="polite")
          for the in-flight and settled states, `role="alert"` (assertive) for a
          failure the operator has to act on. Both regions are always present in
          the DOM so the live region is registered before its content changes —
          a region that is inserted at the same moment as its text is frequently
          missed by screen readers.
        */}
        <div role="status" aria-live="polite" className="sr-only">
          {loading
            ? 'Loading network topology.'
            : error
              ? ''
              : zoneCount !== null
                ? `Network topology loaded. ${zoneCount} zones returned.`
                : 'Network topology loaded.'}
        </div>
        <div role="alert" className="sr-only">
          {error ? `Network topology failed to load. ${error}` : ''}
        </div>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-20">
            <div className="animate-pulse text-neutral-300 text-sm tracking-widest">LOADING TOPOLOGY...</div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-20">
            <div className="text-red-300 border border-red-900/50 bg-red-950/40 p-4 rounded text-sm">
              ERROR: {error}
            </div>
          </div>
        )}

        {/*
          Placeholder shown when no traffic data exists. Previously the whole
          block sat inside `opacity-40`, which dropped the already-dim
          neutral-500/600 text well under 3:1 against #0a0a0a. The opacity is now
          confined to the decorative glyph and the text carries full contrast.
        */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <svg aria-hidden="true" focusable="false" className="w-24 h-24 text-neutral-600 mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <p className="text-neutral-300 font-mono tracking-widest text-lg">TRAFFIC DATA NOT YET AVAILABLE</p>
          <p className="text-neutral-400 text-xs mt-2">Waiting for canonical historical backfill or live acquisition</p>
        </div>
      </section>
    </div>
  );
}
