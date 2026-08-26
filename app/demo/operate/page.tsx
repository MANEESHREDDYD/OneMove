'use client';

/**
 * OPERATE — the integrated surface.
 *
 * This is the page a viewer records. It is not a scripted sequence of panels
 * driven from the console; it is the product, reading the same artifacts and
 * the same API the rest of the system does. Everything on it is either loaded
 * from a versioned artifact or fetched from the live-context endpoint, and
 * every element states which.
 *
 * The map is deliberately not lazy-decorative: it is the primary surface, and
 * the panels sit over it. A viewer should be able to click an order and watch
 * its real road route light up while the rest dim, because that is the moment
 * the sixteen orders stop being a list and become a network problem.
 */

import dynamic from 'next/dynamic';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { cellToBoundary, cellToLatLng } from 'h3-js';

import {
  LiveContextPanel,
  type LiveContext,
} from '@/components/context/LiveContextPanel';
import {
  OrderList,
  type MissionArtifact,
} from '@/components/demo/OrderList';
import {
  DecisionJourney,
  type OperateDemoScene,
} from '@/components/demo/DecisionJourney';
import type { FeatureCollection } from '@/lib/geo/basemap';
import type { EvidenceState } from '@/lib/geo/evidence';
import { createClient } from '@/utils/supabase/client';

// MapLibre touches `window` at module scope, so it can never be server-rendered.
const OneMoveMap = dynamic(
  () => import('@/components/maps/OneMoveMap').then((m) => m.OneMoveMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-[#04070d]">
        <p className="text-xs text-slate-500">Initialising map engine…</p>
      </div>
    ),
  },
);

function collection(features: FeatureCollection['features']): FeatureCollection {
  return { type: 'FeatureCollection', features };
}

export default function OperatePage() {
  const [mission, setMission] = useState<MissionArtifact | null>(null);
  const [missionError, setMissionError] = useState<string | null>(null);
  const [context, setContext] = useState<LiveContext | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [facilityIds, setFacilityIds] = useState<string[]>([]);
  const [scene, setScene] = useState<OperateDemoScene>({ stage: 'opening' });

  // --- the simulated mission, from its versioned artifact -------------------

  useEffect(() => {
    let cancelled = false;
    fetch('/demo/mission-routes.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<MissionArtifact>;
      })
      .then((data) => {
        if (cancelled) return;
        // The artifact must say it is simulated. If it ever does not, something
        // other than the demo mission has been served here.
        if (data.evidence_class !== 'SIMULATED') {
          setMissionError(`mission artifact declares ${data.evidence_class}, expected SIMULATED`);
          return;
        }
        setMission(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setMissionError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    fetch('/demo/facilities.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: { facility_ids?: string[] }) => setFacilityIds(data.facility_ids ?? []))
      .catch(() => setFacilityIds([]));
  }, []);

  // The recording harness changes only the presentation stage. All numbers it
  // supplies are responses from the API calls made in the same test run.
  useEffect(() => {
    const target = window as unknown as {
      __omOperateDemo?: (next: Partial<OperateDemoScene> & { stage: OperateDemoScene['stage'] }) => void;
      __omOperateReady?: boolean;
    };
    target.__omOperateDemo = (next) => setScene((current) => ({ ...current, ...next }));
    target.__omOperateReady = true;
    return () => {
      delete target.__omOperateDemo;
      delete target.__omOperateReady;
    };
  }, []);

  // --- live context, from the API that reads the observation store ----------

  const loadContext = useCallback(async () => {
    const headers: Record<string, string> = {};
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (session) headers.Authorization = `Bearer ${session.access_token}`;
    } catch {
      // A recording may supply its verified bearer header at the browser-context
      // level. The endpoint still fails closed if neither source authenticates.
    }
    const workspaceId = process.env.NEXT_PUBLIC_DEMO_WORKSPACE_ID;
    if (workspaceId) headers['x-workspace-id'] = workspaceId;

    fetch('/api/v1/demo/live-context', { credentials: 'include', headers })
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => null);
          throw new Error(body?.error?.message ?? `HTTP ${r.status}`);
        }
        return r.json() as Promise<LiveContext>;
      })
      .then((data) => {
        setContext(data);
        setContextError(null);
      })
      .catch((err: unknown) => {
        // A failure to read context is shown as a failure. It must never fall
        // back to a cheerful empty panel, which would read as a calm network.
        setContext(null);
        setContextError(err instanceof Error ? err.message : String(err));
      });
  }, []);

  useEffect(() => {
    loadContext();
    // Freshness is only meaningful if it moves. Re-reading the store keeps the
    // displayed age honest without touching a provider.
    const timer = setInterval(loadContext, 60_000);
    return () => clearInterval(timer);
  }, [loadContext]);

  // --- map layers ------------------------------------------------------------

  const orderFeatures = useMemo(() => {
    if (!mission) return collection([]);
    return collection(
      mission.orders.flatMap((order) => [
        {
          type: 'Feature' as const,
          id: `${order.order_id}-p`,
          geometry: { type: 'Point', coordinates: order.pickup },
          properties: { orderId: order.order_id, kind: 'pickup', priority: order.priority },
        },
        {
          type: 'Feature' as const,
          id: `${order.order_id}-d`,
          geometry: { type: 'Point', coordinates: order.dropoff },
          properties: { orderId: order.order_id, kind: 'dropoff', priority: order.priority },
        },
      ]),
    );
  }, [mission]);

  const routeFeatures = useMemo(() => {
    if (!mission) return collection([]);
    return collection(
      mission.routes.map((route) => ({
        type: 'Feature' as const,
        id: route.route_id,
        geometry: { type: 'LineString', coordinates: route.geometry },
        properties: {
          orderId: route.order_id,
          routeId: route.route_id,
          distanceM: route.distance_m,
        },
      })),
    );
  }, [mission]);

  // Congestion per zone, straight from the observation store. A zone the store
  // has no reading for is absent from this map, and the renderer draws absence
  // as its own state rather than as free-flowing.
  const traffic = useMemo(() => {
    const byZone = new Map<string, { congestionRatio: number | null; evidence: EvidenceState }>();
    for (const zone of context?.zone_traffic ?? []) {
      byZone.set(zone.zone_id, {
        congestionRatio: zone.congestion_ratio,
        evidence: 'PROVIDER_ESTIMATED',
      });
    }
    return byZone;
  }, [context]);

  const trafficSource = context?.sources.find((s) => s.source === 'Traffic');

  const facilities = useMemo(
    () => collection(facilityIds.map((id) => {
      const [lat, lon] = cellToLatLng(id.replace(/^fac:/, ''));
      return {
        type: 'Feature' as const,
        id,
        geometry: { type: 'Point' as const, coordinates: [lon, lat] },
        properties: { facilityId: id },
      };
    })),
    [facilityIds],
  );

  const comparison = scene.optimization?.result_document.baseline_comparison;
  const disruptedFacility = comparison?.baseline_facility_ids?.[0] ?? facilityIds[0];
  const showDisruption = ['disruption', 'comparison', 'why', 'freeze', 'evidence', 'replay', 'closing'].includes(scene.stage);
  const showRecommendation = ['comparison', 'why', 'freeze', 'evidence', 'replay', 'closing'].includes(scene.stage);

  useEffect(() => {
    if (scene.stage === 'disruption') setSelectedOrderId(null);
  }, [scene.stage]);

  const disruption = useMemo(() => {
    if (!showDisruption || !disruptedFacility) return undefined;
    const cell = disruptedFacility.replace(/^fac:/, '');
    const ring = cellToBoundary(cell).map(([lat, lon]) => [lon, lat]);
    ring.push(ring[0]);
    return collection([{
      type: 'Feature' as const,
      id: `disruption-${cell}`,
      geometry: { type: 'Polygon' as const, coordinates: [ring] },
      properties: { scenarioId: 's3_congested_outage', evidenceClass: 'SIMULATED' },
    }]);
  }, [disruptedFacility, showDisruption]);

  const recommended = useMemo(() => {
    if (!showRecommendation) return undefined;
    const ids = scene.optimization?.opened_facilities ?? [];
    return collection(ids.map((id) => {
      const [lat, lon] = cellToLatLng(id.replace(/^fac:/, ''));
      return {
        type: 'Feature' as const,
        id: `recommended-${id}`,
        geometry: { type: 'Point' as const, coordinates: [lon, lat] },
        properties: { facilityId: id, evidenceClass: 'DERIVED' },
      };
    }));
  }, [scene.optimization, showRecommendation]);

  const baseline = useMemo(() => {
    if (!showRecommendation) return undefined;
    const ids = scene.optimization?.result_document.baseline_comparison?.baseline_facility_ids ?? [];
    return collection(ids.map((id) => {
      const [lat, lon] = cellToLatLng(id.replace(/^fac:/, ''));
      return {
        type: 'Feature' as const,
        id: `baseline-${id}`,
        geometry: { type: 'Point' as const, coordinates: [lon, lat] },
        properties: { facilityId: id, evidenceClass: 'SIMULATED' },
      };
    }));
  }, [scene.optimization, showRecommendation]);

  return (
    <div className="fixed inset-0 flex flex-col overflow-hidden bg-[#04070d] font-sans text-slate-100">
      <header className="z-20 flex shrink-0 items-center justify-between border-b border-slate-800/80 bg-[#070c16] px-6 py-2.5">
        <div className="flex items-baseline gap-3.5">
          <span className="text-[18px] font-semibold tracking-tight text-slate-50">OneMove</span>
          <span className="text-[12px] text-slate-500">Operate · Bengaluru pilot network</span>
        </div>
        <div className="flex items-center gap-5 text-[11.5px] text-slate-400">
          <span>
            94 zones · <span className="text-slate-300">H3 r8</span>
          </span>
          {mission && (
            <span className="font-mono text-[10px] text-slate-600">
              mission {mission.mission_version} · {mission.mission_fingerprint.slice(0, 8)}
            </span>
          )}
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div className="absolute inset-0" data-testid="map-stage">
          <OneMoveMap
            data={{ orders: orderFeatures, routes: routeFeatures, traffic, facilities, baseline, scenario: disruption, recommended }}
            selectedOrderId={selectedOrderId}
            onSelectOrder={setSelectedOrderId}
          />
        </div>

        <DecisionJourney scene={scene} />

        <aside className="pointer-events-none absolute right-4 top-4 bottom-4 z-10 flex w-[310px] flex-col gap-3">
          <LiveContextPanel
            context={context}
            error={contextError}
            className="pointer-events-auto shrink-0"
          />
          {missionError ? (
            <section
              data-testid="mission-error"
              className="pointer-events-auto rounded-xl border border-red-500/40 bg-[#0b1220]/92 p-4 text-[11.5px] text-red-300 backdrop-blur"
            >
              Delivery mission unavailable: {missionError}. No orders are drawn.
            </section>
          ) : (
            <OrderList
              mission={mission}
              selectedOrderId={selectedOrderId}
              onSelect={setSelectedOrderId}
              className="pointer-events-auto min-h-0 flex-1"
            />
          )}
        </aside>

        {/* One line, bottom-left, that a still frame can be judged against. */}
        <div className="pointer-events-none absolute bottom-4 left-4 z-10 max-w-[420px] rounded-lg border border-slate-700/50 bg-[#0b1220]/88 px-3 py-2 backdrop-blur">
          <p className="text-[11px] leading-snug text-slate-400">
            Geography and road network are{' '}
            <span className="text-sky-300">public geographic evidence</span>. Traffic is{' '}
            <span className="text-amber-300">provider-estimated</span>
            {trafficSource ? ` and ${trafficSource.freshness.toLowerCase()}` : ''}. The delivery
            orders are <span className="text-pink-300">simulated</span>.
          </p>
        </div>
      </div>
    </div>
  );
}
