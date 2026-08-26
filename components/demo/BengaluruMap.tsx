'use client';

import React, { useEffect, useState } from 'react';
import {
  makeLinearProjector,
  pointAlongPolyline,
  pointInRing,
  type BBox,
  type LonLat,
} from '@/lib/geo/projection';
import {
  evidenceState,
  requiresSyntheticWarning,
  EVIDENCE_TONE,
  evidenceCaption,
  UNAVAILABLE,
  type EvidenceState,
} from '@/lib/geo/evidence';
import { MapAttribution, type MapSource } from '@/components/maps/MapAttribution';

/**
 * The geographic stage for the Bengaluru pilot.
 *
 * WHAT IS ACTUALLY DRAWN, so nobody has to guess from the pixels:
 *
 *   1. roads   - a raster PNG baked from the pilot OpenStreetMap extract. It is
 *                NOT a slippy-map tile layer; there is no tile server in this
 *                component and no zoom or pan. It is a single pre-rendered image
 *                of real OSM road geometry, aligned to `bbox`.
 *   2. traffic - a raster PNG baked from TomTom Traffic Flow tiles captured at a
 *                fixed instant. PROVIDER_ESTIMATED, never OBSERVED, and never
 *                live: it is a still frame with a capture timestamp.
 *   3. overlay - live SVG drawn from bengaluru-basemap.json: the 94 H3 r8 cells
 *                at their true `h3.cellToLatLng` boundaries, plus facilities at
 *                their cells' true centroids.
 *
 * All three share ONE linear projection derived from `bbox`, which is why the
 * overlay lands on the roads instead of near them. The rasters are baked rather
 * than drawn client-side because 11k polylines re-parsed in the browser is the
 * kind of thing that paints blank on one run in ten.
 *
 * Every degraded state here is VISIBLE. A failed fetch, a missing raster and a
 * simulated scenario each say so on the map surface. The previous version
 * returned a bare dark rectangle when the basemap fetch rejected, which is
 * indistinguishable from a map of an empty city.
 */

const VW = 1600;
const VH = 900;

export type Zone = {
  h3: string;
  /** Cell boundary as [lon, lat] pairs. */
  b: LonLat[];
  /** Cell centroid as [lon, lat]. */
  c: LonLat;
  road_km: number;
  intersections: number;
  pois: number;
  road_density: number;
};

export type BaseMap = {
  bbox: BBox;
  zones: Zone[];
  labels: { name: string; lat: number; lon: number }[];
  source?: string;
  evidence_class?: string;
};

export type MapMode = 'baseline' | 'scenario' | 'optimized';

export type Mission = {
  points: LonLat[];
  origin: { lat: number; lon: number };
  destination: { lat: number; lon: number };
};

/** Which raster layers actually arrived. */
export type LayerHealth = {
  roads: 'ok' | 'failed';
  traffic: 'ok' | 'failed';
};

export type MapProps = {
  mode: MapMode;
  showTraffic: boolean;
  /** Facility ids (fac:<h3>) offered to the solver. */
  candidates?: string[];
  /** Facility ids the solver actually opened. */
  selected?: string[];
  /** Dim everything, for the title card. */
  dim?: number;
  /** The simulated delivery mission's real route, drawn when present. */
  mission?: Mission | null;
  /** How far along that route the courier is, 0..1. Null hides the courier. */
  missionProgress?: number | null;
  /**
   * Evidence class of the traffic raster. Defaults to the class the capture
   * manifest records. Anything not in the closed vocabulary degrades to
   * UNAVAILABLE and the layer is labelled as such rather than assumed good.
   */
  trafficEvidence?: string;
  /** ISO timestamp the traffic frame was captured. */
  trafficCapturedAt?: string | null;
  onReady?: (zoneCount: number) => void;
  /** Fires whenever a raster layer fails, so the host can log or annotate. */
  onLayerFailure?: (layer: 'roads' | 'traffic') => void;
};

/** Recorded in public/demo/bengaluru-traffic.json alongside the raster. */
const TRAFFIC_DEFAULT_EVIDENCE = 'PROVIDER_ESTIMATED';

const IST_TIME = (iso?: string | null): string => {
  if (!iso) return UNAVAILABLE;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return UNAVAILABLE;
  return (
    new Date(t).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Kolkata',
    }) + ' IST'
  );
};

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; base: BaseMap }
  | { status: 'error'; reason: string };

function useBaseMap(): LoadState {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  useEffect(() => {
    let alive = true;
    fetch('/demo/bengaluru-basemap.json')
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as BaseMap;
      })
      .then((d) => {
        if (!alive) return;
        if (!d?.bbox || !Array.isArray(d.zones) || d.zones.length === 0) {
          setState({
            status: 'error',
            reason: 'basemap artifact contained no zones',
          });
          return;
        }
        setState({ status: 'ready', base: d });
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setState({
          status: 'error',
          reason: e instanceof Error ? e.message : 'request failed',
        });
      });
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

/** A visibly failed map. Never a blank panel, never a stale frame. */
export function MapUnavailable({ reason }: { reason: string }) {
  return (
    <div
      className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#120607] px-8 text-center"
      data-map-state="error"
      role="alert"
    >
      <div
        aria-hidden="true"
        className="h-11 w-11 rounded-full border-2 border-rose-400/70 text-center text-[26px] font-bold leading-[38px] text-rose-300"
      >
        !
      </div>
      <p className="text-[15px] font-semibold tracking-wide text-rose-200">
        BASE MAP UNAVAILABLE
      </p>
      <p className="max-w-[520px] text-[13px] leading-relaxed text-rose-200/70">
        The Bengaluru geographic artifact did not load ({reason}). No geography is
        being shown. Nothing on this surface should be read as the state of the
        network.
      </p>
    </div>
  );
}

function LayerFailureNotice({ layer, reason }: { layer: string; reason: string }) {
  return (
    <div
      role="alert"
      data-layer-failure={layer}
      className="pointer-events-none absolute left-1/2 top-5 z-20 -translate-x-1/2 rounded-lg border border-rose-400/50 bg-rose-950/90 px-4 py-2 text-center text-[12.5px] font-medium text-rose-100 shadow-xl backdrop-blur"
    >
      {reason}
    </div>
  );
}

/**
 * The pure drawing surface. Takes geography as a prop and holds no async state,
 * so a component test can render it and assert where each feature landed.
 */
export function BengaluruMapSurface({
  base,
  mode,
  showTraffic,
  candidates = [],
  selected = [],
  dim = 0,
  mission = null,
  missionProgress = null,
  trafficEvidence = TRAFFIC_DEFAULT_EVIDENCE,
  trafficCapturedAt = null,
  layerHealth = { roads: 'ok', traffic: 'ok' },
  onRasterError,
}: {
  base: BaseMap;
  layerHealth?: LayerHealth;
  onRasterError?: (layer: 'roads' | 'traffic') => void;
} & Omit<MapProps, 'onReady' | 'onLayerFailure'>) {
  const project = makeLinearProjector(base.bbox, VW, VH);

  // Commercial POI count is the optimizer's own demand proxy. Shading by it
  // means the map's texture is the same quantity the solver reasons about,
  // rather than a decorative gradient.
  const sortedPois = base.zones.map((z) => z.pois).sort((a, b) => a - b);
  const poiCeiling = sortedPois[Math.floor(sortedPois.length * 0.92)] || 1;

  const cellOf = (facilityId: string) => facilityId.replace(/^fac:/, '');
  const selectedCells = new Set(selected.map(cellOf));
  const candidateCells = new Set(candidates.map(cellOf));

  // Scenario state is a SIMULATED shock, never an observation. The traffic
  // raster is a third-party estimate captured at a fixed instant, never live.
  const scenarioState: EvidenceState = mode === 'scenario' ? 'SIMULATED' : UNAVAILABLE;
  const trafficState = evidenceState(trafficEvidence);
  const trafficUsable = showTraffic && layerHealth.traffic === 'ok';

  const sources: MapSource[] = ['osm'];
  if (trafficUsable) sources.push('tomtom');
  if (mission) sources.push('osrm');

  return (
    <div
      className="absolute inset-0 overflow-hidden bg-[#060a12]"
      data-map-state="ready"
      data-map-mode={mode}
      data-evidence-scenario={scenarioState}
      data-evidence-traffic={trafficState}
    >
      {layerHealth.roads === 'ok' ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src="/demo/bengaluru-roads.png"
          alt="Bengaluru road network rendered from the pilot OpenStreetMap extract"
          className="absolute inset-0 h-full w-full object-fill"
          data-layer="roads"
          onError={() => onRasterError?.('roads')}
        />
      ) : (
        // A failed basemap raster must not leave a plausible-looking dark field
        // behind it. The surface is struck through so it reads as broken.
        <div
          className="absolute inset-0"
          data-layer="roads"
          data-layer-state="failed"
          aria-hidden="true"
          style={{
            background:
              'repeating-linear-gradient(45deg, #1a0d10 0 14px, #120a0c 14px 28px)',
          }}
        />
      )}

      {trafficUsable && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src="/demo/bengaluru-traffic.png"
          alt={`Traffic flow captured ${IST_TIME(trafficCapturedAt)}, ${evidenceCaption(trafficState)}`}
          className="absolute inset-0 h-full w-full object-fill transition-opacity duration-700"
          style={{ opacity: 0.78 }}
          data-layer="traffic"
          onError={() => onRasterError?.('traffic')}
        />
      )}

      <svg
        viewBox={`0 0 ${VW} ${VH}`}
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
        data-layer="overlay"
        data-zone-count={base.zones.length}
      >
        <defs>
          <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="7" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/*
            Simulated state is marked by TEXTURE as well as hue. A viewer who
            cannot separate cyan from orange still sees that the surface has
            changed character, so a simulation cannot be mistaken for an
            observation on colour perception alone (WCAG 1.4.1).
          */}
          <pattern
            id="simulated-hatch"
            width="18"
            height="18"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="18" height="18" fill="none" />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="18"
              stroke="rgba(251, 146, 60, 0.5)"
              strokeWidth="3"
            />
          </pattern>
        </defs>

        {mode === 'scenario' && (
          <rect
            x="0"
            y="0"
            width={VW}
            height={VH}
            fill="url(#simulated-hatch)"
            data-overlay="simulated-hatch"
          />
        )}

        {base.zones.map((z) => {
          const pts = z.b.map(([lon, lat]) => project(lon, lat).join(',')).join(' ');
          const isSelected = selectedCells.has(z.h3);
          const t = Math.min(1, z.pois / poiCeiling);

          // In the scenario state the SIMULATED shock is uniform across the
          // network, so tinting selected cells differently would invent
          // per-zone impact the backend never derived. The whole surface
          // shifts instead, which is what actually happened.
          let fill = `rgba(34, 211, 238, ${0.05 + t * 0.2})`;
          let stroke = 'rgba(103, 232, 249, 0.34)';
          let width = 0.9;

          if (mode === 'scenario') {
            fill = `rgba(251, 146, 60, ${0.07 + t * 0.26})`;
            stroke = 'rgba(253, 186, 116, 0.42)';
          }
          if (mode === 'optimized') {
            fill = `rgba(34, 211, 238, ${0.04 + t * 0.14})`;
            stroke = 'rgba(103, 232, 249, 0.24)';
          }
          if (isSelected) {
            fill = 'rgba(52, 211, 153, 0.42)';
            stroke = 'rgba(110, 231, 183, 0.95)';
            width = 2.6;
          }

          return (
            <polygon
              key={z.h3}
              points={pts}
              fill={fill}
              stroke={stroke}
              strokeWidth={width}
              data-h3={z.h3}
              data-selected={isSelected ? 'true' : 'false'}
              style={{ transition: 'fill 900ms ease, stroke 900ms ease' }}
            />
          );
        })}

        {base.labels.slice(0, 9).map((l) => {
          const [x, y] = project(l.lon, l.lat);
          return (
            <text
              key={l.name}
              x={x}
              y={y}
              fill="rgba(203, 213, 225, 0.66)"
              fontSize="12.5"
              fontFamily="system-ui, sans-serif"
              stroke="#060a12"
              strokeWidth="3"
              paintOrder="stroke"
            >
              {l.name}
            </text>
          );
        })}

        {base.zones
          .filter((z) => candidateCells.has(z.h3) && !selectedCells.has(z.h3))
          .map((z) => {
            const [x, y] = project(z.c[0], z.c[1]);
            return (
              <g key={`cand-${z.h3}`} data-facility="candidate" data-facility-cell={z.h3}>
                <circle cx={x} cy={y} r="8.5" fill="none" stroke="rgba(148,163,184,0.85)" strokeWidth="2" />
                <circle cx={x} cy={y} r="2.5" fill="rgba(148,163,184,0.85)" />
              </g>
            );
          })}

        {base.zones
          .filter((z) => selectedCells.has(z.h3))
          .map((z) => {
            // Drawn at the cell's own centroid, so the marker is inside the cell
            // the solver opened rather than beside it. The invariant is asserted
            // directly in __tests__/geo-map.test.ts via point-in-polygon.
            const [x, y] = project(z.c[0], z.c[1]);
            const inside = pointInRing(z.c, z.b);
            return (
              <g
                key={`sel-${z.h3}`}
                data-facility="selected"
                data-facility-cell={z.h3}
                data-inside-cell={inside ? 'true' : 'false'}
                filter="url(#glow)"
              >
                <circle cx={x} cy={y} r="17" fill="rgba(52,211,153,0.20)" stroke="rgba(110,231,183,0.95)" strokeWidth="2.5" />
                <circle cx={x} cy={y} r="6.5" fill="#34d399" />
              </g>
            );
          })}

        {mission && (
          <g data-layer="mission">
            <polyline
              points={mission.points.map(([lon, lat]) => project(lon, lat).join(',')).join(' ')}
              fill="none"
              stroke="rgba(250, 204, 21, 0.30)"
              strokeWidth="9"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <polyline
              points={mission.points.map(([lon, lat]) => project(lon, lat).join(',')).join(' ')}
              fill="none"
              stroke="#facc15"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {[
              [mission.origin, '#facc15'] as const,
              [mission.destination, '#f97316'] as const,
            ].map(([pt, colour], i) => {
              const [x, y] = project(pt.lon, pt.lat);
              return (
                <g key={i}>
                  <circle cx={x} cy={y} r="10" fill="none" stroke={colour} strokeWidth="2.4" />
                  <circle cx={x} cy={y} r="3.4" fill={colour} />
                </g>
              );
            })}
            {missionProgress != null &&
              (() => {
                // Walk the real polyline by arc length so the courier tracks the
                // road geometry rather than sliding along a straight line.
                const projected = mission.points.map(([lon, lat]) => project(lon, lat));
                const at = pointAlongPolyline(projected, missionProgress);
                if (!at) return null;
                return (
                  <g data-mission="courier" filter="url(#glow)">
                    <circle cx={at[0]} cy={at[1]} r="15" fill="rgba(250, 204, 21, 0.22)" />
                    <circle cx={at[0]} cy={at[1]} r="6.5" fill="#fde047" stroke="#78350f" strokeWidth="1.6" />
                  </g>
                );
              })()}
          </g>
        )}
      </svg>

      {layerHealth.roads === 'failed' && (
        <LayerFailureNotice
          layer="roads"
          reason="ROAD BASEMAP UNAVAILABLE — the OpenStreetMap raster failed to load. Cell positions below are still true; the streets behind them are not being drawn."
        />
      )}
      {showTraffic && layerHealth.traffic === 'failed' && (
        <LayerFailureNotice
          layer="traffic"
          reason="TRAFFIC UNAVAILABLE — the provider raster failed to load. This is not free-flowing traffic; it is no traffic data at all."
        />
      )}

      {/* ---- state legend: what is real, what is not ------------------ */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-10 max-w-[420px] space-y-2">
        {mode === 'scenario' && (
          <div
            data-evidence-banner="SIMULATED"
            role="status"
            className={`pointer-events-auto inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-[12.5px] font-semibold tracking-wide ring-1 ${EVIDENCE_TONE.SIMULATED}`}
          >
            <span className="rounded-sm bg-orange-400/25 px-1.5 py-[1px] text-[11px]">
              SIMULATED
            </span>
            <span className="font-normal">
              Scenario shock — this did not happen. Not an observation.
            </span>
          </div>
        )}

        <div
          data-evidence-banner="TRAFFIC"
          className={`pointer-events-auto inline-flex flex-wrap items-center gap-2 rounded-md px-3 py-1.5 text-[12px] ring-1 ${
            showTraffic && layerHealth.traffic === 'ok'
              ? EVIDENCE_TONE[trafficState]
              : EVIDENCE_TONE.UNAVAILABLE
          }`}
        >
          <span className="font-semibold tracking-wide">
            {showTraffic
              ? layerHealth.traffic === 'ok'
                ? trafficState
                : UNAVAILABLE
              : 'TRAFFIC LAYER OFF'}
          </span>
          {showTraffic && layerHealth.traffic === 'ok' && (
            <span className="font-normal opacity-80">
              TomTom flow · captured {IST_TIME(trafficCapturedAt)} · not live
            </span>
          )}
          {showTraffic && layerHealth.traffic === 'failed' && (
            <span className="font-normal opacity-80">
              no traffic reading — not zero congestion
            </span>
          )}
        </div>

        <MapAttribution
          sources={sources}
          className="rounded-md bg-[#04070d]/80 px-2.5 py-1 backdrop-blur"
        />
      </div>

      {dim > 0 && (
        <div
          className="absolute inset-0 transition-opacity duration-700"
          style={{ background: '#04070d', opacity: dim }}
        />
      )}
    </div>
  );
}

export function BengaluruMap({
  onReady,
  onLayerFailure,
  ...surfaceProps
}: MapProps) {
  const state = useBaseMap();
  const [layerHealth, setLayerHealth] = useState<LayerHealth>({
    roads: 'ok',
    traffic: 'ok',
  });

  const zoneCount = state.status === 'ready' ? state.base.zones.length : 0;
  useEffect(() => {
    if (zoneCount > 0) onReady?.(zoneCount);
  }, [zoneCount, onReady]);

  if (state.status === 'loading') {
    return (
      <div
        className="absolute inset-0 flex items-center justify-center bg-[#060a12]"
        data-map-state="loading"
        role="status"
      >
        <p className="text-[12.5px] tracking-[0.22em] text-slate-400">
          LOADING BENGALURU GEOGRAPHY…
        </p>
      </div>
    );
  }

  if (state.status === 'error') {
    return <MapUnavailable reason={state.reason} />;
  }

  return (
    <BengaluruMapSurface
      {...surfaceProps}
      base={state.base}
      layerHealth={layerHealth}
      onRasterError={(layer) => {
        setLayerHealth((prev) =>
          prev[layer] === 'failed' ? prev : { ...prev, [layer]: 'failed' },
        );
        onLayerFailure?.(layer);
      }}
    />
  );
}
