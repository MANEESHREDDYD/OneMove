"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Layers, RefreshCw, AlertTriangle, ShieldCheck, MapPin, Database } from "lucide-react";
import { ApiError, getApiJson } from "../../lib/api/client";
import type { MapLayer, MapLayerListResponse, ZoneListResponse, ZoneSummary } from "../../lib/api/types";

const NetworkMap = dynamic(() => import("../../components/map/network-map"), {
  loading: () => (
    <div
      className="h-[36rem] animate-pulse motion-reduce:animate-none rounded-xl border border-slate-300 bg-slate-200"
      aria-label="Loading 94-cell network map"
    />
  ),
  ssr: false,
});

export default function NetworkPage() {
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [layers, setLayers] = useState<MapLayer[]>([]);
  const [selectedZone, setSelectedZone] = useState<ZoneSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadData = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [zonesRes, layersRes] = await Promise.all([
        getApiJson<ZoneListResponse>("zones", signal),
        getApiJson<MapLayerListResponse>("network/map-layers", signal),
      ]);
      setZones(zonesRes.data);
      setLayers(layersRes.data);
      if (zonesRes.data.length > 0 && !selectedZone) {
        setSelectedZone(zonesRes.data[0] ?? null);
      }
    } catch (caught: unknown) {
      if (signal.aborted) return;
      const message =
        caught instanceof ApiError
          ? `${caught.message}${caught.requestId ? ` (Request: ${caught.requestId})` : ""}`
          : caught instanceof Error
            ? caught.message
            : "Failed to load network topology.";
      setError(message);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [selectedZone]);

  useEffect(() => {
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  const filteredZones = zones.filter((z) =>
    z.zone_id.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              94-Cell Network Topology
            </h1>
            <p className="text-sm text-slate-600">
              Bengaluru Urban spatial partitioning (Uber H3 Resolution 8) with verified geographic lineage.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const controller = new AbortController();
                void loadData(controller.signal);
              }}
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
              <span>Network Data Error</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 px-4 py-3 bg-slate-50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-blue-600" />
                  <span className="font-semibold text-sm text-slate-800">Interactive Network Map</span>
                </div>
                <span className="text-xs text-slate-500">
                  {zones.length} Zones • {layers.filter((l) => l.state === "AVAILABLE").length} Layers Active
                </span>
              </div>
              <div className="p-4">
                <NetworkMap zones={zones} layers={layers} />
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <h2 className="text-base font-semibold text-slate-900">Overlaid Geographic Layers</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {layers.map((layer) => (
                  <div key={layer.layer} className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-700">{layer.layer}</span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          layer.state === "AVAILABLE" ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {layer.state}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {layer.returned_feature_count.toLocaleString()} / {layer.total_feature_count.toLocaleString()} features
                    </p>
                    <p className="text-[10px] text-slate-400 font-mono truncate" title={layer.artifact_hash || ""}>
                      Hash: {layer.artifact_hash ? layer.artifact_hash.slice(0, 12) : "n/a"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">Zone Inspector</h2>
                {selectedZone && (
                  <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-mono font-semibold text-blue-800">
                    Res {selectedZone.resolution}
                  </span>
                )}
              </div>

              {selectedZone ? (
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-blue-600" />
                      <span className="font-mono text-sm font-bold text-slate-900">{selectedZone.zone_id}</span>
                    </div>
                    <div className="text-xs text-slate-600 space-y-1">
                      <p><strong className="text-slate-800">Source:</strong> {selectedZone.source}</p>
                      <p><strong className="text-slate-800">Evidence Class:</strong> {selectedZone.evidence_class || "PUBLIC_GEOGRAPHIC"}</p>
                      <p className="truncate font-mono"><strong className="text-slate-800">Artifact Hash:</strong> {selectedZone.artifact_hash || "canonical"}</p>
                      <p><strong className="text-slate-800">Boundary Vertices:</strong> {selectedZone.boundary.length} coordinates</p>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">Select a zone on the map or list to inspect details.</p>
              )}

              <div className="space-y-2">
                <label htmlFor="zone-search" className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Search Zones ({zones.length})
                </label>
                <input
                  id="zone-search"
                  type="text"
                  placeholder="Filter by H3 index..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100 rounded-lg border border-slate-200">
                {filteredZones.map((z) => (
                  <button
                    key={z.zone_id}
                    onClick={() => setSelectedZone(z)}
                    className={`w-full text-left px-3 py-2 text-xs font-mono transition-colors flex items-center justify-between ${
                      selectedZone?.zone_id === z.zone_id ? "bg-blue-50 text-blue-900 font-bold" : "hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <span>{z.zone_id}</span>
                    <span className="text-[10px] text-slate-400 font-sans">94-cell</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
