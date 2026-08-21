'use client';

import React, { useEffect, useMemo, useState } from 'react';

/**
 * The geographic stage for the demo.
 *
 * Three layers share one linear projection:
 *   1. roads    - raster, pre-rendered from pilot_roads.osm.pbf
 *   2. traffic  - raster, live provider flow tiles captured before the run
 *   3. overlay  - live SVG: H3 cells, candidate + selected facilities
 *
 * The rasters are baked rather than drawn client-side because 11k polylines
 * re-parsed in the browser is exactly the kind of thing that paints blank on
 * one run in ten, and a blank map mid-recording cannot be recovered.
 *
 * The basemap bbox is exactly 16:9 in PROJECTED units (degrees of longitude
 * scaled by cos(lat)). That is what lets the rasters and the SVG share a single
 * linear mapping, and what keeps the hexagons their true shape instead of
 * stretching them into lozenges.
 */

const VW = 1600;
const VH = 900;

export type Zone = {
  h3: string;
  b: [number, number][];
  c: [number, number];
  road_km: number;
  intersections: number;
  pois: number;
  road_density: number;
};

type BaseMap = {
  bbox: { min_lat: number; max_lat: number; min_lon: number; max_lon: number };
  zones: Zone[];
  labels: { name: string; lat: number; lon: number }[];
};

export type MapMode = 'baseline' | 'scenario' | 'optimized';

export type Mission = {
  points: [number, number][];
  origin: { lat: number; lon: number };
  destination: { lat: number; lon: number };
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
  onReady?: (zoneCount: number) => void;
};

function useBaseMap(): BaseMap | null {
  const [data, setData] = useState<BaseMap | null>(null);
  useEffect(() => {
    let alive = true;
    fetch('/demo/bengaluru-basemap.json')
      .then((r) => r.json())
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, []);
  return data;
}

export function BengaluruMap({
  mode,
  showTraffic,
  candidates = [],
  selected = [],
  dim = 0,
  mission = null,
  missionProgress = null,
  onReady,
}: MapProps) {
  const base = useBaseMap();

  useEffect(() => {
    if (base) onReady?.(base.zones.length);
  }, [base, onReady]);

  const project = useMemo(() => {
    if (!base) return null;
    const { min_lat, max_lat, min_lon, max_lon } = base.bbox;
    return (lon: number, lat: number): [number, number] => [
      ((lon - min_lon) / (max_lon - min_lon)) * VW,
      ((max_lat - lat) / (max_lat - min_lat)) * VH,
    ];
  }, [base]);

  // Commercial POI count is the optimizer's own demand proxy. Shading by it
  // means the map's texture is the same quantity the solver reasons about,
  // rather than a decorative gradient.
  const poiScale = useMemo(() => {
    if (!base) return (n: number) => 0;
    const vals = base.zones.map((z) => z.pois).sort((a, b) => a - b);
    const hi = vals[Math.floor(vals.length * 0.92)] || 1;
    return (n: number) => Math.min(1, n / hi);
  }, [base]);

  if (!base || !project) {
    return <div className="absolute inset-0 bg-[#060a12]" data-map-state="loading" />;
  }

  const cellOf = (facilityId: string) => facilityId.replace(/^fac:/, '');
  const selectedCells = new Set(selected.map(cellOf));
  const candidateCells = new Set(candidates.map(cellOf));

  return (
    <div className="absolute inset-0 overflow-hidden bg-[#060a12]" data-map-state="ready">
      <img
        src="/demo/bengaluru-roads.png"
        alt="Bengaluru road network rendered from the pilot OpenStreetMap extract"
        className="absolute inset-0 h-full w-full object-fill"
        data-layer="roads"
      />

      <img
        src="/demo/bengaluru-traffic.png"
        alt="Live traffic flow"
        className="absolute inset-0 h-full w-full object-fill transition-opacity duration-700"
        style={{ opacity: showTraffic ? 0.78 : 0 }}
        data-layer="traffic"
      />

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
        </defs>

        {base.zones.map((z) => {
          const pts = z.b.map(([lon, lat]) => project(lon, lat).join(',')).join(' ');
          const isSelected = selectedCells.has(z.h3);
          const t = poiScale(z.pois);

          // In the scenario state the SIMULATED shock is uniform across the
          // network, so tinting selected cells differently would invent
          // per-zone impact the backend never derived. The whole surface
          // shifts instead, which is what actually happened.
          let fill = `rgba(34, 211, 238, ${0.05 + t * 0.20})`;
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
          .filter((z) => candidateCells.has(z.h3))
          .map((z) => {
            const [x, y] = project(z.c[0], z.c[1]);
            const isSelected = selectedCells.has(z.h3);
            if (isSelected) return null;
            return (
              <g key={`cand-${z.h3}`} data-facility="candidate">
                <circle cx={x} cy={y} r="8.5" fill="none" stroke="rgba(148,163,184,0.85)" strokeWidth="2" />
                <circle cx={x} cy={y} r="2.5" fill="rgba(148,163,184,0.85)" />
              </g>
            );
          })}

        {base.zones
          .filter((z) => selectedCells.has(z.h3))
          .map((z) => {
            const [x, y] = project(z.c[0], z.c[1]);
            return (
              <g key={`sel-${z.h3}`} data-facility="selected" filter="url(#glow)">
                <circle cx={x} cy={y} r="17" fill="rgba(52,211,153,0.20)" stroke="rgba(110,231,183,0.95)" strokeWidth="2.5" />
                <circle cx={x} cy={y} r="6.5" fill="#34d399" />
              </g>
            );
          })}
        {mission && project && (
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
            {missionProgress != null && (() => {
              // Walk the real polyline by arc length so the courier tracks the
              // road geometry rather than sliding along a straight line.
              const pts = mission.points.map(([lon, lat]) => project(lon, lat));
              let total = 0;
              const segs: number[] = [];
              for (let i = 1; i < pts.length; i++) {
                const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
                segs.push(d);
                total += d;
              }
              let want = Math.max(0, Math.min(1, missionProgress)) * total;
              let cx = pts[0][0];
              let cy = pts[0][1];
              for (let i = 0; i < segs.length; i++) {
                if (want <= segs[i] || i === segs.length - 1) {
                  const t = segs[i] === 0 ? 0 : want / segs[i];
                  cx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t;
                  cy = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t;
                  break;
                }
                want -= segs[i];
              }
              return (
                <g data-mission="courier" filter="url(#glow)">
                  <circle cx={cx} cy={cy} r="15" fill="rgba(250, 204, 21, 0.22)" />
                  <circle cx={cx} cy={cy} r="6.5" fill="#fde047" stroke="#78350f" strokeWidth="1.6" />
                </g>
              );
            })()}
          </g>
        )}
      </svg>

      {dim > 0 && (
        <div
          className="absolute inset-0 transition-opacity duration-700"
          style={{ background: '#04070d', opacity: dim }}
        />
      )}
    </div>
  );
}
