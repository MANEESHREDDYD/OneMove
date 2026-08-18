"use client";

import { useCallback, useEffect, useState } from "react";
import type { ComponentType } from "react";
import { Activity, Database, MapPin, RefreshCw, Search, ServerCog, TriangleAlert } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";

import { useAuth } from "../components/auth/auth-provider";
import { ApiError, getApiJson } from "../lib/api/client";
import type {
  DataHealthResponse,
  DatasetListResponse,
  DatasetRecord,
  MapLayer,
  MapLayerListResponse,
  ProviderHealth,
  ZoneListResponse,
  ZoneSummary,
} from "../lib/api/types";

interface ObservatoryData {
  zones: ZoneSummary[];
  datasets: DatasetRecord[];
  providers: ProviderHealth[];
  evaluatedAt: string;
  mapLayers: MapLayer[];
}

const NetworkMap = dynamic(() => import("../components/map/network-map"), {
  loading: () => <div className="h-[32rem] animate-pulse motion-reduce:animate-none rounded-xl border border-slate-300 bg-slate-200" aria-label="Loading network map" />,
  ssr: false,
});

function providerStateClass(state: ProviderHealth["state"]): string {
  if (state === "FRESH") return "bg-emerald-100 text-emerald-800";
  if (state === "DEGRADED") return "bg-amber-100 text-amber-900";
  if (state === "STALE") return "bg-orange-100 text-orange-900";
  return "bg-slate-200 text-slate-800";
}

function formatTimestamp(value: string | null): string {
  if (!value) return "No successful collection";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function ObserverHome() {
  const { role, workspaceId } = useAuth();
  const [data, setData] = useState<ObservatoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [zoneResponse, datasetResponse, healthResponse, mapLayerResponse] = await Promise.all([
        getApiJson<ZoneListResponse>("zones", signal),
        getApiJson<DatasetListResponse>("datasets", signal),
        getApiJson<DataHealthResponse>("data-health", signal),
        getApiJson<MapLayerListResponse>("network/map-layers", signal),
      ]);
      setData({
        zones: zoneResponse.data,
        datasets: datasetResponse.data,
        providers: healthResponse.data,
        evaluatedAt: healthResponse.evaluated_at,
        mapLayers: mapLayerResponse.data,
      });
    } catch (caught: unknown) {
      if (signal.aborted) return;
      const message = caught instanceof ApiError
        ? `${caught.message}${caught.requestId ? ` Request ${caught.requestId}.` : ""}`
        : caught instanceof Error ? caught.message : "Unable to load Observatory data.";
      setError(message);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const task = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(task);
      controller.abort();
    };
  }, [load, reloadKey]);

  const availableDatasets = data?.datasets.filter((dataset) => dataset.availability === "AVAILABLE").length ?? 0;
  const staleProviders = data?.providers.filter((provider) => provider.state !== "FRESH").length ?? 0;

  return (
    <main id="main-content" className="min-h-screen bg-slate-100 px-4 py-6 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-col gap-4 border-b border-slate-300 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Evidence console</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">ZonePilot Observatory</h1>
            <p className="mt-2 text-sm text-slate-600">
              Role {role}{workspaceId ? ` / Workspace ${workspaceId}` : ""}
            </p>
          </div>
          <nav aria-label="Observatory actions" className="flex flex-wrap gap-2">
            <Link className="flex min-h-11 items-center gap-2 rounded-lg border border-slate-400 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" href="/system-health">
              <ServerCog aria-hidden="true" className="h-4 w-4" /> System health
            </Link>
            {role === "OWNER" && (
              <Link className="min-h-11 rounded-lg border border-slate-400 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" href="/qc">
                Study QC
              </Link>
            )}
            <Link className="min-h-11 rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2" href="/capture">
              Capture evidence
            </Link>
          </nav>
        </header>

        {loading && (
          <section aria-live="polite" className="mt-8 grid gap-4 sm:grid-cols-3">
            {["zones", "datasets", "providers"].map((item) => (
              <div className="h-28 animate-pulse motion-reduce:animate-none rounded-xl border border-slate-200 bg-white" key={item}>
                <span className="sr-only">Loading {item}</span>
              </div>
            ))}
          </section>
        )}

        {error && (
          <section className="mt-8 rounded-xl border border-red-300 bg-red-50 p-5 text-red-950" role="alert">
            <div className="flex items-start gap-3">
              <TriangleAlert aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="flex-1">
                <h2 className="font-semibold">Observatory data unavailable</h2>
                <p className="mt-1 text-sm leading-6">{error}</p>
              </div>
              <button
                className="flex min-h-11 items-center gap-2 rounded-lg border border-red-400 px-3 text-sm font-semibold hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600"
                onClick={() => setReloadKey((key) => key + 1)}
                type="button"
              >
                <RefreshCw aria-hidden="true" className="h-4 w-4" /> Retry
              </button>
            </div>
          </section>
        )}

        {!loading && !error && data && (
          <>
            <section aria-label="Network summary" className="mt-8 grid gap-4 sm:grid-cols-3">
              <SummaryCard icon={MapPin} label="Gold H3 cells" value={data.zones.length} />
              <SummaryCard icon={Database} label="Available datasets" value={availableDatasets} />
              <SummaryCard icon={Activity} label="Non-fresh providers" value={staleProviders} />
            </section>

            <section className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950" role="status">
              <p className="font-semibold">ZONE-LEVEL TRAFFIC DATA UNAVAILABLE</p>
              <p className="mt-1 text-sm">
                Provider runs may exist, but no mounted traffic artifact is spatially joined to these H3 cells. The UI does not infer or simulate traffic.
              </p>
            </section>

            <section className="mt-10" aria-labelledby="map-title">
              <div className="mb-4">
                <h2 className="text-xl font-semibold" id="map-title">Evidence map</h2>
                <p className="mt-1 text-sm text-slate-600">
                  OpenStreetMap context, the configured pilot boundary, and H3 cells loaded from the verified Gold artifact.
                </p>
              </div>
              <NetworkMap layers={data.mapLayers} zones={data.zones} />
            </section>

            <section className="mt-10" aria-labelledby="provider-health-title">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold" id="provider-health-title">Provider data health</h2>
                  <p className="mt-1 text-sm text-slate-600">Calculated from collection manifests and configured freshness SLAs.</p>
                </div>
                <p className="text-xs text-slate-600">Evaluated {formatTimestamp(data.evaluatedAt)}</p>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.providers.map((provider) => (
                  <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" key={provider.provider}>
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-semibold capitalize">{provider.provider}</h3>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${providerStateClass(provider.state)}`}>
                        {provider.state}
                      </span>
                    </div>
                    <dl className="mt-4 space-y-2 text-sm">
                      <div className="flex justify-between gap-4"><dt className="text-slate-500">Last success</dt><dd className="text-right">{formatTimestamp(provider.last_successful_collection)}</dd></div>
                      <div className="flex justify-between gap-4"><dt className="text-slate-500">DQ</dt><dd className="font-medium">{provider.dq_result}</dd></div>
                      <div className="flex justify-between gap-4"><dt className="text-slate-500">Datasets</dt><dd>{provider.dataset_ids.length}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>

            <section className="mt-10" aria-labelledby="zone-title">
              <div>
                <h2 className="text-xl font-semibold" id="zone-title">Active pilot zones</h2>
                <p className="mt-1 text-sm text-slate-600">Cells read from the verified Gold network Parquet, not generated in the browser.</p>
              </div>
              {data.zones.length === 0 ? (
                <div className="mt-4 rounded-xl border border-slate-300 bg-white p-8 text-center">
                  <h3 className="font-semibold">NETWORK DATA UNAVAILABLE</h3>
                  <p className="mt-2 text-sm text-slate-600">No verified pilot zones are mounted.</p>
                </div>
              ) : (
                <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {data.zones.slice(0, 24).map((zone) => (
                    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" key={zone.zone_id}>
                      <div className="flex items-start justify-between gap-3">
                        <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-900">H3-R{zone.resolution}</span>
                        {/* Null by contract when there is no observation to classify. */}
                        <span className="text-xs text-slate-600">{zone.evidence_class ?? "No evidence class"}</span>
                      </div>
                      <h3 className="mt-4 break-all font-mono text-base font-semibold">{zone.zone_id}</h3>
                      <p className="mt-2 text-xs leading-5 text-slate-600">
                        Source {zone.source} / {zone.boundary.length} boundary vertices
                      </p>
                      <Link
                        aria-label={`Capture evidence for zone ${zone.zone_id}`}
                        className="mt-5 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-blue-700 px-3 text-sm font-semibold text-blue-800 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                        href={`/capture?zone_id=${encodeURIComponent(zone.zone_id)}`}
                      >
                        <Search aria-hidden="true" className="h-4 w-4" /> Capture evidence
                      </Link>
                    </article>
                  ))}
                </div>
              )}
              {data.zones.length > 24 && <p className="mt-4 text-center text-sm text-slate-600">Showing 24 of {data.zones.length} verified cells.</p>}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function SummaryCard({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: number;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <span aria-hidden="true"><Icon className="h-5 w-5 text-blue-700" /></span>
      <p className="mt-4 text-3xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{label}</p>
    </article>
  );
}
