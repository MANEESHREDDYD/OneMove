'use client';

import React, { useMemo } from 'react';

export type Zone = {
  zone_id: string;
  resolution: number;
  boundary: [number, number][];
  evidence_class?: string;
  source?: string;
  source_version?: string;
  artifact_hash?: string;
};

type Props = {
  zones: Zone[];
  /** Optional authentic facility zone ids. Never synthesise these. */
  facilityZoneIds?: string[];
  width?: number;
  height?: number;
};

/**
 * Renders the authentic H3 cell boundaries returned by /api/v1/zones.
 *
 * Deliberately an inline SVG projection rather than a tile-based map: it depends
 * on no external tile server, so it cannot render blank or half-loaded during a
 * recording, and every polygon drawn is real geometry from the Gold artifact.
 * Nothing here is generated or placed at a random coordinate.
 */
export function H3NetworkMap({ zones, facilityZoneIds = [], width = 900, height = 640 }: Props) {
  const projected = useMemo(() => {
    const pts = zones.flatMap((z) => z.boundary || []);
    if (pts.length === 0) return null;

    const lats = pts.map((p) => p[0]);
    const lngs = pts.map((p) => p[1]);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const pad = 28;
    const spanLng = maxLng - minLng || 1;
    const spanLat = maxLat - minLat || 1;

    // Equirectangular projection corrected for latitude so hexagons keep their
    // shape instead of shearing. At Bengaluru's latitude the correction is ~0.975.
    const latMid = (minLat + maxLat) / 2;
    const lngScale = Math.cos((latMid * Math.PI) / 180);
    const effLngSpan = spanLng * lngScale;

    const scale = Math.min((width - pad * 2) / effLngSpan, (height - pad * 2) / spanLat);
    const drawnW = effLngSpan * scale;
    const drawnH = spanLat * scale;
    const offX = (width - drawnW) / 2;
    const offY = (height - drawnH) / 2;

    const toXY = ([lat, lng]: [number, number]): [number, number] => [
      offX + (lng - minLng) * lngScale * scale,
      // Screen y grows downward; latitude grows northward.
      offY + (maxLat - lat) * scale,
    ];

    return zones
      .filter((z) => (z.boundary || []).length > 0)
      .map((z) => ({
        id: z.zone_id,
        isFacility: facilityZoneIds.includes(z.zone_id),
        points: z.boundary.map(toXY).map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' '),
      }));
  }, [zones, facilityZoneIds, width, height]);

  if (!projected) {
    return (
      <div
        className="flex items-center justify-center text-neutral-500 font-mono tracking-widest"
        style={{ width, height }}
      >
        NETWORK GEOMETRY UNAVAILABLE
      </div>
    );
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Bengaluru pilot network: ${projected.length} H3 cells rendered from public geographic evidence`}
    >
      <defs>
        <radialGradient id="onemove-glow" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.16" />
          <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width={width} height={height} fill="#07090d" />
      <rect width={width} height={height} fill="url(#onemove-glow)" />
      {projected.map((cell) => (
        <polygon
          key={cell.id}
          points={cell.points}
          fill={cell.isFacility ? 'rgba(56,189,248,0.30)' : 'rgba(56,189,248,0.07)'}
          stroke={cell.isFacility ? '#38bdf8' : 'rgba(56,189,248,0.42)'}
          strokeWidth={cell.isFacility ? 1.8 : 0.9}
        />
      ))}
    </svg>
  );
}
