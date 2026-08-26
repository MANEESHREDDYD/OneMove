'use client';

/**
 * The sixteen simulated orders, and what selecting one does.
 *
 * Two things this list has to get right. First, the orders are SIMULATED and
 * the label travels with them everywhere -- header, every row, and the detail
 * panel -- so no screenshot can be cropped into something that looks like real
 * customer demand.
 *
 * Second, the route metrics must not overstate themselves. Travel time here is
 * distance over a declared free-flow speed assumption, not an ETA, and the
 * panel says so in words rather than relying on the viewer to remember. The
 * `traffic_aware` flag comes from the artifact; if it ever flips to true, the
 * copy changes with it rather than being edited by hand.
 */

import React from 'react';

export type DemoOrder = {
  order_id: string;
  pickup: [number, number];
  dropoff: [number, number];
  pickup_h3: string;
  dropoff_h3: string;
  priority: string;
  shape: string;
  evidence_class: string;
};

export type DemoRoute = {
  route_id: string;
  order_id: string;
  geometry: [number, number][];
  distance_m: number;
  travel_time_seconds: number;
  travel_time_source: string;
  traffic_aware: boolean;
  snap_distance_pickup_m: number;
  snap_distance_dropoff_m: number;
};

export type MissionArtifact = {
  mission_version: string;
  mission_fingerprint: string;
  routes_fingerprint: string;
  routing_version: string;
  traffic_aware: boolean;
  evidence_class: string;
  orders: DemoOrder[];
  routes: DemoRoute[];
};

const SHAPE_LABEL: Record<string, string> = {
  SHORT_INTRA_CELL: 'short hop',
  CROSS_ZONE: 'cross-zone',
  SHARED_CORRIDOR: 'shared corridor',
  NEAR_CANDIDATE_FACILITY: 'near a candidate site',
  GEOGRAPHICALLY_INCONVENIENT: 'hardest to serve',
};

export function formatKm(metres: number): string {
  return `${(metres / 1000).toFixed(2)} km`;
}

export function formatMinutes(seconds: number): string {
  const minutes = seconds / 60;
  return minutes < 1 ? '<1 min' : `${minutes.toFixed(minutes < 10 ? 1 : 0)} min`;
}

export function OrderList({
  mission,
  selectedOrderId,
  onSelect,
  className = '',
}: {
  mission: MissionArtifact | null;
  selectedOrderId: string | null;
  onSelect: (orderId: string | null) => void;
  className?: string;
}) {
  const routeByOrder = new Map((mission?.routes ?? []).map((r) => [r.order_id, r]));
  const selected = selectedOrderId ? routeByOrder.get(selectedOrderId) : undefined;
  const selectedOrder = mission?.orders.find((o) => o.order_id === selectedOrderId);

  const totalKm = (mission?.routes ?? []).reduce((sum, r) => sum + r.distance_m, 0) / 1000;

  return (
    <section
      data-testid="order-list"
      className={`flex min-h-0 flex-col rounded-xl border border-slate-700/60 bg-[#0b1220]/92 backdrop-blur ${className}`}
    >
      <div className="shrink-0 border-b border-slate-800/70 p-4 pb-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            Delivery mission
          </h2>
          {/* The class sits in the header, not only on the rows, so a cropped
              screenshot of this panel still carries it. */}
          <span className="rounded border border-pink-500/40 bg-pink-500/10 px-1.5 py-px text-[10px] font-semibold tracking-wide text-pink-300">
            SIMULATED
          </span>
        </div>
        {mission && (
          <p className="mt-1.5 text-[11px] leading-snug text-slate-400">
            {mission.orders.length} orders · {totalKm.toFixed(1)} km routed on real Bengaluru roads.
            No customer, merchant or rider exists.
          </p>
        )}
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto p-1.5" data-testid="order-rows">
        {(mission?.orders ?? []).map((order) => {
          const route = routeByOrder.get(order.order_id);
          const active = order.order_id === selectedOrderId;
          return (
            <li key={order.order_id}>
              <button
                type="button"
                data-order-id={order.order_id}
                data-selected={active}
                onClick={() => onSelect(active ? null : order.order_id)}
                className={`w-full rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                  active ? 'bg-sky-500/15 ring-1 ring-sky-400/50' : 'hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[12px] text-slate-100">{order.order_id}</span>
                  <span className="text-[11px] text-slate-400">
                    {route ? formatKm(route.distance_m) : '—'}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-slate-500">
                  <span>{SHAPE_LABEL[order.shape] ?? order.shape.toLowerCase()}</span>
                  {order.priority === 'HIGH' && (
                    <span className="rounded bg-amber-500/15 px-1 text-amber-300">HIGH</span>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {selected && selectedOrder && (
        <div
          data-testid="order-detail"
          className="shrink-0 border-t border-slate-800/70 bg-slate-900/40 p-3.5 text-[11px]"
        >
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="font-mono text-[12.5px] text-sky-300">{selectedOrder.order_id}</span>
            <span className="text-[10px] text-slate-500">{selected.route_id}</span>
          </div>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400">
            <dt>Route distance</dt>
            <dd className="text-right text-slate-200">{formatKm(selected.distance_m)}</dd>
            <dt>Travel time</dt>
            <dd className="text-right text-slate-200">{formatMinutes(selected.travel_time_seconds)}</dd>
            <dt>Road vertices</dt>
            <dd className="text-right text-slate-200">{selected.geometry.length}</dd>
            <dt>Evidence</dt>
            <dd className="text-right text-pink-300">{selectedOrder.evidence_class}</dd>
          </dl>
          {/* The honesty line. It is derived from the flag, so it cannot drift
              out of step with what the routing actually did. */}
          <p className="mt-2 leading-snug text-slate-500">
            {selected.traffic_aware
              ? 'Travel time incorporates current traffic.'
              : 'Free-flow estimate from road class, not traffic-aware. Not an ETA.'}
          </p>
          {selected.snap_distance_dropoff_m > 250 && (
            <p className="mt-1 leading-snug text-amber-300/80">
              Dropoff sits {selected.snap_distance_dropoff_m} m from the routable network; the
              extract is clipped at its boundary here.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
