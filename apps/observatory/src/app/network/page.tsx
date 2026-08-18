"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Layers, RefreshCw, AlertTriangle, MapPin } from "lucide-react";
import { ApiError, getApiJson } from "../../lib/api/client";
import type { MapLayerListResponse, MapLayer, ZoneListResponse, ZoneSummary } from "../../lib/api/types";

const DynamicNetworkMap = dynamic(
  () => import("../../components/map/network-map"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[600px] w-full items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium text-slate-500">
        Initializing Interactive Map Canvas...
      </div>
    ),
  }
);

export default function NetworkPage() {
  const [layers, setLayers] = useState<MapLayer[]>([]);
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function init() {
      try {
        const [layersRes, zonesRes] = await Promise.all([
          getApiJson<MapLayerListResponse>("network/map-layers", controller.signal),
          getApiJson<ZoneListResponse>("zones", controller.signal),
        ]);
        if (active) {
          setLayers(layersRes.data);
          setZones(zonesRes.data);
          setLoading(false);
        }
      } catch (caught: unknown) {
        if (active && !controller.signal.aborted) {
          const message = caught instanceof ApiError ? caught.message : "Failed to load network topology.";
          setError(message);
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
      const [layersRes, zonesRes] = await Promise.all([
        getApiJson<MapLayerListResponse>("network/map-layers"),
        getApiJson<ZoneListResponse>("zones"),
      ]);
      setLayers(layersRes.data);
      setZones(zonesRes.data);
    } catch (caught: unknown) {
      const message = caught instanceof ApiError ? caught.message : "Failed to load network topology.";
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
              94-Cell Network Topology &amp; GIS Layers (R1)
            </h1>
            <p className="text-sm text-slate-600">
              Authentic spatial partition of Bengaluru Urban across 94 Uber H3 Resolution 8 hexagon cells.
            </p>
          </div>
          <button
            onClick={() => void handleRefresh()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
            Refresh Topology
          </button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Topology Service Warning</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 font-semibold text-slate-900 border-b border-slate-100 pb-3">
                <Layers className="h-4 w-4 text-blue-600" />
                <span>GIS Layer Information</span>
              </div>

              <div className="rounded-lg bg-blue-50/70 p-3 text-[11px] text-blue-900 space-y-1">
                <p><strong>Spatial Index:</strong> Uber H3 Res 8 (~0.737 km&sup2; per cell)</p>
                <p><strong>Pilot Area:</strong> Bengaluru Urban Core (94 cells)</p>
                <p><strong>Evidence Class:</strong> PUBLIC_GEOGRAPHIC</p>
                <p><strong>Active GIS Layers:</strong> {layers.length}</p>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Zone Inspector</h2>
              {selectedZone ? (
                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 font-mono font-bold text-slate-900">
                    <MapPin className="h-4 w-4 text-red-500" />
                    <span>{selectedZone}</span>
                  </div>
                  <p className="text-slate-600">Resolution: H3 Index Res 8</p>
                  <p className="text-slate-600">Demand Weight: 1.0 (Baseline)</p>
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  {zones.length > 0
                    ? `Tracking ${zones.length} active spatial hexagons`
                    : "No zones loaded"}
                </p>
              )}
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="rounded-xl border border-slate-200 bg-white p-2 shadow-sm overflow-hidden min-h-[600px]">
              <DynamicNetworkMap layers={layers} zones={zones} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
