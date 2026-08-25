/**
 * The pilot basemap, turned into GeoJSON a map engine can render.
 *
 * `public/demo/bengaluru-basemap.json` is a compact artifact baked from
 * `pilot_roads.osm.pbf` (sha256 461584ea03d2...), the same extract
 * tests/geo/test_pilot_roads_lineage.py verifies by coordinate. It holds 11,174
 * real road geometries, 14 named places and the boundaries of all 94 H3
 * resolution-8 cells of the pilot network. Its evidence class is
 * PUBLIC_GEOGRAPHIC and it is stated in the file itself.
 *
 * WHY THIS AND NOT A TILE SERVER. The provider licence review
 * (docs/data/DATA_LICENSES.md) found that the OSMF and CARTO tile CDNs are not
 * acceptable as a commercial product's basemap at scale, and that TomTom raster
 * tiles require a Copyrights API caption this product does not generate. Serving
 * our own geometry from our own extract sidesteps both: the only obligation left
 * is ODbL attribution, which components/maps/MapAttribution.tsx renders.
 *
 * It also means the map has no external dependency at render time. A tile CDN
 * outage cannot blank the flagship surface.
 */

export type RoadClass = 0 | 1 | 2 | 3 | 4;

/**
 * Road importance, most significant first. The numbers are the artifact's own
 * `t` field; the names are how they are drawn. Class 4 is the long tail of
 * residential and service ways -- 8,708 of the 11,174 -- and is drawn thinnest
 * and revealed last, or the arterials disappear into it.
 */
export const ROAD_CLASS_NAMES: Record<RoadClass, string> = {
  0: 'motorway',
  1: 'trunk',
  2: 'primary',
  3: 'secondary',
  4: 'local',
};

export type RawBasemap = {
  source: string;
  source_sha256_prefix: string;
  evidence_class: string;
  bbox: { min_lat: number; max_lat: number; min_lon: number; max_lon: number };
  roads: { t: RoadClass; p: [number, number][] }[];
  labels: { name: string; lon: number; lat: number }[];
  zones: {
    h3: string;
    b: [number, number][];
    c: [number, number];
    road_km: number;
    intersections: number;
    pois: number;
    road_density: number;
  }[];
};

export type FeatureCollection = {
  type: 'FeatureCollection';
  features: {
    type: 'Feature';
    id?: string | number;
    geometry: { type: string; coordinates: unknown };
    properties: Record<string, unknown>;
  }[];
};

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };

export function emptyCollection(): FeatureCollection {
  return { type: 'FeatureCollection', features: [] };
}

/**
 * Roads as LineStrings, keeping the class so the renderer can weight them.
 *
 * Coordinates stay in the artifact's [lon, lat] order, which is what GeoJSON
 * requires. Silently flipping them would put Bengaluru in the Indian Ocean, and
 * the resulting map would still render -- just of nowhere.
 */
export function roadsToGeoJSON(basemap: RawBasemap): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: basemap.roads.map((road, i) => ({
      type: 'Feature' as const,
      id: i,
      geometry: { type: 'LineString', coordinates: road.p },
      properties: { roadClass: road.t, roadClassName: ROAD_CLASS_NAMES[road.t] ?? 'local' },
    })),
  };
}

/**
 * The 94 pilot cells as closed polygons.
 *
 * The artifact stores each boundary open (the last vertex is not a repeat of
 * the first). GeoJSON requires a closed ring, so the first coordinate is
 * appended. Without it MapLibre renders a hairline gap on every cell.
 */
export function zonesToGeoJSON(
  basemap: RawBasemap,
  attributes: Map<string, Record<string, unknown>> = new Map(),
): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: basemap.zones.map((zone) => {
      const ring = [...zone.b, zone.b[0]];
      return {
        type: 'Feature' as const,
        id: zone.h3,
        geometry: { type: 'Polygon', coordinates: [ring] },
        properties: {
          h3: zone.h3,
          centroidLon: zone.c[0],
          centroidLat: zone.c[1],
          roadKm: zone.road_km,
          intersections: zone.intersections,
          pois: zone.pois,
          roadDensity: zone.road_density,
          ...(attributes.get(zone.h3) ?? {}),
        },
      };
    }),
  };
}

export function labelsToGeoJSON(basemap: RawBasemap): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: basemap.labels.map((label, i) => ({
      type: 'Feature' as const,
      id: i,
      geometry: { type: 'Point', coordinates: [label.lon, label.lat] },
      properties: { name: label.name },
    })),
  };
}

/** The extract's own bounds, as MapLibre wants them: [[w, s], [e, n]]. */
export function boundsOf(basemap: RawBasemap): [[number, number], [number, number]] {
  const { min_lat, max_lat, min_lon, max_lon } = basemap.bbox;
  return [
    [min_lon, min_lat],
    [max_lon, max_lat],
  ];
}

/**
 * Reject an artifact that is not the pilot extract.
 *
 * A road extract named for Bengaluru was once byte-identical to an Andorra
 * extract, and twelve of twenty-two routing-graph parts had the same defect. The
 * lesson stuck: geography is checked by coordinates, never by a filename. If a
 * swapped artifact ever reaches the browser, the map must refuse to draw rather
 * than render another city under Bengaluru's name.
 */
export const PILOT_ENVELOPE = { minLat: 12.7, maxLat: 13.2, minLon: 77.3, maxLon: 77.9 };

export function validateBasemap(basemap: RawBasemap): string[] {
  const problems: string[] = [];

  if (basemap.evidence_class !== 'PUBLIC_GEOGRAPHIC') {
    problems.push(`basemap evidence class is ${basemap.evidence_class}, expected PUBLIC_GEOGRAPHIC`);
  }
  if (!basemap.zones?.length) problems.push('basemap contains no zones');
  if (!basemap.roads?.length) problems.push('basemap contains no roads');
  if (basemap.zones && basemap.zones.length !== 94) {
    problems.push(`basemap has ${basemap.zones.length} zones, expected the 94 pilot cells`);
  }

  const { min_lat, max_lat, min_lon, max_lon } = basemap.bbox ?? {};
  const inside =
    min_lat >= PILOT_ENVELOPE.minLat &&
    max_lat <= PILOT_ENVELOPE.maxLat &&
    min_lon >= PILOT_ENVELOPE.minLon &&
    max_lon <= PILOT_ENVELOPE.maxLon;
  if (!inside) {
    problems.push(
      `basemap bounds ${min_lat}..${max_lat} / ${min_lon}..${max_lon} are outside the Bengaluru pilot envelope`,
    );
  }

  return problems;
}

export { EMPTY };
