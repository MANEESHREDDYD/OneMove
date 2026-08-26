/**
 * Client-side geographic projection helpers.
 *
 * Everything the map draws must land on its true coordinate. These functions are
 * pure so the coordinate claim can be tested directly, rather than inferred from
 * a screenshot.
 *
 * Convention throughout this module: a position is [lon, lat] — x before y — to
 * match GeoJSON and the baked basemap artifact. Leaflet's [lat, lng] order is
 * converted at the Leaflet boundary, never here.
 */

export type LonLat = [number, number];

export type BBox = {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
};

export const EARTH_RADIUS_M = 6_371_008.8;

/**
 * Bengaluru pilot envelope. Wide enough that a legitimate re-cut of the extract
 * still passes, tight enough that any other city on earth fails. Kept in sync
 * with tests/geo/test_pilot_roads_lineage.py, which encodes the rule that
 * geography is verified by COORDINATES and never by a filename.
 */
export const BENGALURU_BOUNDS: BBox = {
  min_lat: 12.7,
  max_lat: 13.2,
  min_lon: 77.3,
  max_lon: 77.9,
};

export function isWithin(bounds: BBox, [lon, lat]: LonLat): boolean {
  return (
    Number.isFinite(lon) &&
    Number.isFinite(lat) &&
    lat >= bounds.min_lat &&
    lat <= bounds.max_lat &&
    lon >= bounds.min_lon &&
    lon <= bounds.max_lon
  );
}

/** Great-circle distance in metres. */
export function haversineMeters(a: LonLat, b: LonLat): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const lat1 = toRad(a[1]);
  const lat2 = toRad(b[1]);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type Projector = (lon: number, lat: number) => [number, number];

/**
 * Linear (plate carrée) mapping from a bbox onto a width x height viewport.
 *
 * This is only faithful — hexagons keep their shape rather than shearing into
 * lozenges — when the bbox aspect ratio equals the viewport aspect ratio in
 * PROJECTED units, i.e. with longitude scaled by cos(latitude). Callers that
 * bake a raster against the same bbox therefore share one mapping exactly, which
 * is what lets the SVG overlay sit on the raster instead of near it.
 *
 * `projectedAspectRatio` below is what a test asserts against; nothing here
 * silently corrects a mismatched bbox, because a silent correction would move
 * every feature off its true position by an amount nobody could see.
 */
export function makeLinearProjector(
  bbox: BBox,
  width: number,
  height: number,
): Projector {
  const lonSpan = bbox.max_lon - bbox.min_lon;
  const latSpan = bbox.max_lat - bbox.min_lat;
  return (lon, lat) => [
    ((lon - bbox.min_lon) / lonSpan) * width,
    ((bbox.max_lat - lat) / latSpan) * height,
  ];
}

/** Width:height of the bbox in cos(lat)-corrected degrees. */
export function projectedAspectRatio(bbox: BBox): number {
  const midLat = (bbox.min_lat + bbox.max_lat) / 2;
  const lonSpan =
    (bbox.max_lon - bbox.min_lon) * Math.cos((midLat * Math.PI) / 180);
  const latSpan = bbox.max_lat - bbox.min_lat;
  return lonSpan / latSpan;
}

/**
 * Equal-area-ish fit of a set of rings into a padded viewport, correcting
 * longitude for latitude so cells keep their shape. Used where there is no baked
 * raster to agree with and the extent is whatever the data happens to cover.
 */
export function makeFittedProjector(
  points: LonLat[],
  width: number,
  height: number,
  pad = 28,
): { project: Projector; bbox: BBox } | null {
  if (points.length === 0) return null;

  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of points) {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  if (!Number.isFinite(minLon) || !Number.isFinite(minLat)) return null;

  const bbox: BBox = {
    min_lat: minLat,
    max_lat: maxLat,
    min_lon: minLon,
    max_lon: maxLon,
  };

  const lonScale = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const effLonSpan = (maxLon - minLon) * lonScale || 1;
  const latSpan = maxLat - minLat || 1;
  const scale = Math.min(
    (width - pad * 2) / effLonSpan,
    (height - pad * 2) / latSpan,
  );
  const offX = (width - effLonSpan * scale) / 2;
  const offY = (height - latSpan * scale) / 2;

  return {
    bbox,
    project: (lon, lat) => [
      offX + (lon - minLon) * lonScale * scale,
      // Screen y grows downward; latitude grows northward.
      offY + (maxLat - lat) * scale,
    ],
  };
}

/**
 * Ray-casting point-in-polygon on a closed or open ring of [lon, lat].
 *
 * Used to prove a facility marker is drawn INSIDE the H3 cell the solver chose,
 * not merely near it — the difference between "this depot serves that cell" and
 * a decorative dot that happens to be close.
 */
export function pointInRing(point: LonLat, ring: LonLat[]): boolean {
  if (ring.length < 3) return false;
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersects =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

/** Arithmetic mean of a ring's vertices — adequate for a small H3 cell. */
export function ringCentroid(ring: LonLat[]): LonLat | null {
  if (ring.length === 0) return null;
  let sx = 0;
  let sy = 0;
  for (const [lon, lat] of ring) {
    sx += lon;
    sy += lat;
  }
  return [sx / ring.length, sy / ring.length];
}

/**
 * Position along a polyline at fraction `t` of its total length, measured in
 * whatever units the points are in. Walking by arc length keeps a moving marker
 * on the road geometry instead of sliding along a straight chord.
 */
export function pointAlongPolyline(
  points: [number, number][],
  t: number,
): [number, number] | null {
  if (points.length === 0) return null;
  if (points.length === 1) return points[0];

  const segs: number[] = [];
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    const d = Math.hypot(
      points[i][0] - points[i - 1][0],
      points[i][1] - points[i - 1][1],
    );
    segs.push(d);
    total += d;
  }
  if (total === 0) return points[0];

  let want = Math.max(0, Math.min(1, t)) * total;
  for (let i = 0; i < segs.length; i++) {
    if (want <= segs[i] || i === segs.length - 1) {
      const f = segs[i] === 0 ? 0 : Math.min(1, want / segs[i]);
      return [
        points[i][0] + (points[i + 1][0] - points[i][0]) * f,
        points[i][1] + (points[i + 1][1] - points[i][1]) * f,
      ];
    }
    want -= segs[i];
  }
  return points[points.length - 1];
}

/** A coordinate pair is usable only if both halves are real finite numbers. */
export function isValidLatLng(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number' &&
    Number.isFinite(value[0]) &&
    Number.isFinite(value[1]) &&
    Math.abs(value[0]) <= 90 &&
    Math.abs(value[1]) <= 180
  );
}
