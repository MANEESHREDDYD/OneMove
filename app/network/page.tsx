'use client';
import React, { useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';
import { Check, Minus } from 'lucide-react';
import { H3NetworkMap, type Zone } from '@/components/demo/H3NetworkMap';

type LayerState = {
  name: string
  /** Whether the layer is currently rendered. */
  active: boolean
  /** Why an inactive layer is inactive. */
  reason?: string
}

const LAYERS: LayerState[] = [
  { name: 'OSM Gold Base Map', active: true },
  // The mounted Gold artifact reports h3_resolution 8, not 9. Naming the wrong
  // resolution on screen is a factual error a reviewer would catch immediately.
  { name: 'H3 Resolution 8 Grid', active: true },
  { name: 'Live Traffic Flow', active: false, reason: 'no traffic source connected' },
];

export default function NetworkObservatory() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // The zones endpoint is tenant-scoped, so the request needs the caller's
    // session and a workspace selector. Fetching it bare returned 401 and the page
    // rendered "Failed to load network topology" over an empty map.
    const load = async () => {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) throw new Error('Sign in to load the network');

        const workspaceId = process.env.NEXT_PUBLIC_DEMO_WORKSPACE_ID;
        const headers: Record<string, string> = {
          Authorization: `Bearer ${session.access_token}`,
        };
        if (workspaceId) headers['x-workspace-id'] = workspaceId;

        const res = await fetch('/api/v1/zones', { headers });
        if (!res.ok) throw new Error(`Failed to load network topology (HTTP ${res.status})`);
        const data = await res.json();
        setZones(Array.isArray(data.data) ? data.data : []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load network topology');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const zoneCount = zones.length > 0 ? zones.length : null;

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
          The network itself. Every polygon is an authentic H3 cell boundary
          returned by /api/v1/zones -- no tile server, no synthetic geometry, and
          nothing placed at an invented coordinate.
        */}
        <div className="absolute inset-0 flex items-center justify-center">
          {loading && (
            <p className="text-neutral-400 font-mono tracking-widest text-sm">LOADING NETWORK…</p>
          )}

          {!loading && !error && zones.length > 0 && (
            <H3NetworkMap zones={zones} width={980} height={680} />
          )}

          {!loading && !error && zones.length === 0 && (
            <p className="text-neutral-300 font-mono tracking-widest text-lg">NETWORK GEOMETRY UNAVAILABLE</p>
          )}
        </div>

        {!loading && !error && zones.length > 0 && (
          <div className="absolute bottom-16 right-8 bg-black/80 border border-neutral-800 rounded-lg px-5 py-4 text-sm backdrop-blur">
            <p className="text-white font-semibold mb-2">Bengaluru Pilot Network</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <dt className="text-neutral-400">Zones</dt>
              <dd className="text-neutral-100 font-mono">{zones.length}</dd>
              <dt className="text-neutral-400">H3 resolution</dt>
              <dd className="text-neutral-100 font-mono">{zones[0]?.resolution ?? 'UNAVAILABLE'}</dd>
              <dt className="text-neutral-400">Evidence</dt>
              <dd>
                <span className="bg-emerald-900/60 text-emerald-200 px-2 py-0.5 rounded font-mono text-[11px]">
                  {zones[0]?.evidence_class ?? 'UNAVAILABLE'}
                </span>
              </dd>
              <dt className="text-neutral-400">Source</dt>
              <dd className="text-neutral-100 font-mono">{zones[0]?.source ?? 'UNAVAILABLE'}</dd>
              <dt className="text-neutral-400">Graph</dt>
              <dd className="text-neutral-100 font-mono">{zones[0]?.source_version ?? 'UNAVAILABLE'}</dd>
            </dl>
          </div>
        )}

      </section>
    </div>
  );
}
