'use client';

/**
 * The flagship map. A real WebGL map engine, not a picture of one.
 *
 * What this replaces: two baked raster PNGs with an SVG overlay. Those were
 * coordinate-correct, which was the hard part, but they could not pan, zoom,
 * select, or reveal detail -- and a still image of a city is not a map.
 *
 * WHY MAPLIBRE WITH LOCAL GEOJSON AND NO TILE SERVER.
 * The provider licence review found the OSMF and CARTO tile CDNs unacceptable as
 * a commercial product's basemap at scale, and TomTom raster tiles require a
 * Copyrights API caption this product does not generate. Serving our own
 * geometry, from our own OpenStreetMap extract, sidesteps both. The only
 * obligation left is ODbL attribution, which is rendered. It also removes the
 * last render-time external dependency: no CDN outage can blank this surface.
 *
 * The trade is honest and worth stating: outside the pilot extract's bounding
 * box there is no map, because we hold no data there. The surface says so rather
 * than fading into an empty grey plane that looks like the sea.
 *
 * EVERY LAYER DECLARES WHAT IT IS. Geography is PUBLIC_GEOGRAPHIC, live traffic
 * is PROVIDER_ESTIMATED, the delivery mission is SIMULATED, optimizer output is
 * DERIVED. The legend shows the class beside the layer, so a viewer never has to
 * infer which parts of the picture are real.
 */

import * as maplibregl from 'maplibre-gl';
import type { Map as MapLibreMap } from 'maplibre-gl';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { MapAttribution, type MapSource } from '@/components/maps/MapAttribution';
import {
  type FeatureCollection,
  type RawBasemap,
  boundsOf,
  emptyCollection,
  labelsToGeoJSON,
  roadsToGeoJSON,
  validateBasemap,
  zonesToGeoJSON,
} from '@/lib/geo/basemap';
import { type EvidenceState, UNAVAILABLE } from '@/lib/geo/evidence';

import 'maplibre-gl/dist/maplibre-gl.css';

export type LayerId =
  | 'roads'
  | 'zones'
  | 'facilities'
  | 'traffic'
  | 'orders'
  | 'routes'
  | 'scenario'
  | 'recommended';

type LayerSpec = {
  id: LayerId;
  label: string;
  evidence: EvidenceState;
  defaultOn: boolean;
};

/**
 * The legend and the layer control are the same list, deliberately. Two lists
 * drift, and a legend that disagrees with what is drawn is worse than none.
 */
export const LAYERS: LayerSpec[] = [
  { id: 'roads', label: 'Road network', evidence: 'PUBLIC_GEOGRAPHIC', defaultOn: true },
  { id: 'zones', label: '94 H3 service zones', evidence: 'PUBLIC_GEOGRAPHIC', defaultOn: true },
  { id: 'facilities', label: 'Candidate facilities', evidence: 'ASSUMPTION', defaultOn: true },
  { id: 'traffic', label: 'Current traffic', evidence: 'PROVIDER_ESTIMATED', defaultOn: true },
  { id: 'orders', label: 'Delivery orders', evidence: 'SIMULATED', defaultOn: true },
  { id: 'routes', label: 'Delivery routes', evidence: 'SIMULATED', defaultOn: true },
  { id: 'scenario', label: 'Disruption scenario', evidence: 'SIMULATED', defaultOn: false },
  { id: 'recommended', label: 'Recommended facilities', evidence: 'DERIVED', defaultOn: false },
];

export type MapData = {
  /** Live traffic per zone, keyed by H3 index. Absent means UNAVAILABLE, not free-flowing. */
  traffic?: Map<string, { congestionRatio: number | null; evidence: EvidenceState }>;
  facilities?: FeatureCollection;
  orders?: FeatureCollection;
  routes?: FeatureCollection;
  scenario?: FeatureCollection;
  recommended?: FeatureCollection;
};

type LoadState =
  | { status: 'loading' }
  | { status: 'failed'; reason: string }
  | { status: 'ready'; basemap: RawBasemap };

const ROAD_WIDTH: maplibregl.DataDrivenPropertyValueSpecification<number> = [
  'interpolate',
  ['linear'],
  ['zoom'],
  10,
  ['match', ['get', 'roadClass'], 0, 1.6, 1, 1.3, 2, 1.0, 3, 0.6, 0.25],
  14,
  ['match', ['get', 'roadClass'], 0, 5.0, 1, 4.0, 2, 3.0, 3, 2.0, 0.9],
  17,
  ['match', ['get', 'roadClass'], 0, 12.0, 1, 10.0, 2, 8.0, 3, 5.0, 2.5],
];

/**
 * Congestion colour. `null` is NOT on this ramp: a zone with no reading is drawn
 * in the explicit unavailable hatch colour rather than the free-flowing end,
 * because "we do not know" must never look like "it is clear".
 */
const CONGESTION_COLOR: maplibregl.DataDrivenPropertyValueSpecification<string> = [
  'case',
  ['==', ['get', 'congestionRatio'], null],
  '#3f3f46',
  [
    'interpolate',
    ['linear'],
    ['get', 'congestionRatio'],
    1.0,
    '#16a34a',
    1.25,
    '#eab308',
    1.6,
    '#f97316',
    2.2,
    '#dc2626',
  ],
];

export function OneMoveMap({
  data = {},
  selectedOrderId = null,
  onSelectOrder,
  onSelectZone,
  className = '',
}: {
  data?: MapData;
  selectedOrderId?: string | null;
  onSelectOrder?: (orderId: string | null) => void;
  onSelectZone?: (h3: string | null) => void;
  className?: string;
}) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [load, setLoad] = useState<LoadState>({ status: 'loading' });
  const [styleReady, setStyleReady] = useState(false);
  const [visible, setVisible] = useState<Record<LayerId, boolean>>(
    () => Object.fromEntries(LAYERS.map((l) => [l.id, l.defaultOn])) as Record<LayerId, boolean>,
  );
  const [hovered, setHovered] = useState<string | null>(null);

  // --- load the basemap artifact --------------------------------------------

  useEffect(() => {
    let cancelled = false;
    fetch('/demo/bengaluru-basemap.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<RawBasemap>;
      })
      .then((basemap) => {
        if (cancelled) return;
        // Refuse to draw geography that does not prove it is Bengaluru. An
        // Andorra extract once shipped under a Bengaluru filename.
        const problems = validateBasemap(basemap);
        if (problems.length) {
          setLoad({ status: 'failed', reason: problems.join('; ') });
          return;
        }
        setLoad({ status: 'ready', basemap });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLoad({ status: 'failed', reason: err instanceof Error ? err.message : String(err) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const zoneCollection = useMemo(() => {
    if (load.status !== 'ready') return emptyCollection();
    const attributes = new Map<string, Record<string, unknown>>();
    for (const zone of load.basemap.zones) {
      const reading = data.traffic?.get(zone.h3);
      attributes.set(zone.h3, {
        // Explicitly null, never 0. Null takes the unavailable colour branch.
        congestionRatio: reading?.congestionRatio ?? null,
        trafficEvidence: reading?.evidence ?? UNAVAILABLE,
      });
    }
    return zonesToGeoJSON(load.basemap, attributes);
  }, [load, data.traffic]);

  // --- create the map --------------------------------------------------------

  useEffect(() => {
    if (load.status !== 'ready' || !container.current || map.current) return;

    const instance = new maplibregl.Map({
      container: container.current,
      // A style with no external sources at all: our own background, and the
      // GeoJSON we add below. No tile server is contacted, ever.
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0b0f14' } }],
        glyphs: undefined,
      },
      bounds: boundsOf(load.basemap),
      fitBoundsOptions: { padding: 32 },
      attributionControl: false,
      // Keep the viewer inside the extract. Panning beyond it shows nothing,
      // because we hold no data there.
      maxBounds: [
        [load.basemap.bbox.min_lon - 0.08, load.basemap.bbox.min_lat - 0.08],
        [load.basemap.bbox.max_lon + 0.08, load.basemap.bbox.max_lat + 0.08],
      ],
      minZoom: 9,
      maxZoom: 18,
    });

    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    instance.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
    instance.dragRotate.disable();
    instance.touchZoomRotate.disableRotation();

    instance.on('load', () => {
      instance.addSource('roads', { type: 'geojson', data: roadsToGeoJSON(load.basemap) as never });
      instance.addSource('zones', { type: 'geojson', data: emptyCollection() as never });
      instance.addSource('labels', { type: 'geojson', data: labelsToGeoJSON(load.basemap) as never });
      for (const id of ['facilities', 'orders', 'routes', 'scenario', 'recommended'] as const) {
        instance.addSource(id, { type: 'geojson', data: emptyCollection() as never });
      }

      // Zone fill sits UNDER the roads: the arterials are the thing a reader
      // orients by, and a translucent congestion wash over them muddies both.
      instance.addLayer({
        id: 'zones-fill',
        type: 'fill',
        source: 'zones',
        paint: { 'fill-color': CONGESTION_COLOR, 'fill-opacity': 0.28 },
      });
      instance.addLayer({
        id: 'zones-outline',
        type: 'line',
        source: 'zones',
        paint: { 'line-color': '#64748b', 'line-width': 0.6, 'line-opacity': 0.5 },
      });
      instance.addLayer({
        id: 'zones-hover',
        type: 'line',
        source: 'zones',
        paint: { 'line-color': '#e2e8f0', 'line-width': 2 },
        filter: ['==', ['get', 'h3'], ''],
      });

      instance.addLayer({
        id: 'roads-line',
        type: 'line',
        source: 'roads',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': [
            'match',
            ['get', 'roadClass'],
            0, '#e2e8f0',
            1, '#cbd5e1',
            2, '#94a3b8',
            3, '#64748b',
            '#475569',
          ],
          'line-width': ROAD_WIDTH,
          // The 8,708 local ways would smother the arterials at low zoom, so
          // they fade in only once the viewer is close enough to want them.
          'line-opacity': [
            'case',
            ['==', ['get', 'roadClass'], 4],
            ['interpolate', ['linear'], ['zoom'], 11, 0, 13.5, 0.55],
            0.9,
          ],
        },
      });

      instance.addLayer({
        id: 'routes-line',
        type: 'line',
        source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': ['case', ['get', 'selected'], '#38bdf8', '#0ea5e9'],
          'line-width': ['case', ['get', 'selected'], 4.5, 2],
          // Unrelated routes dim rather than disappear, so the selected one
          // reads in context instead of floating alone.
          'line-opacity': ['case', ['get', 'selected'], 0.95, 0.22],
        },
      });

      instance.addLayer({
        id: 'scenario-fill',
        type: 'fill',
        source: 'scenario',
        paint: { 'fill-color': '#a855f7', 'fill-opacity': 0.3 },
      });

      instance.addLayer({
        id: 'facilities-point',
        type: 'circle',
        source: 'facilities',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 4, 15, 9],
          'circle-color': '#f8fafc',
          'circle-stroke-color': '#0f172a',
          'circle-stroke-width': 1.5,
        },
      });

      instance.addLayer({
        id: 'recommended-point',
        type: 'circle',
        source: 'recommended',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 7, 15, 14],
          'circle-color': '#22c55e',
          'circle-stroke-color': '#052e16',
          'circle-stroke-width': 2,
        },
      });

      instance.addLayer({
        id: 'orders-point',
        type: 'circle',
        source: 'orders',
        paint: {
          'circle-radius': [
            'case',
            ['get', 'selected'],
            8,
            ['interpolate', ['linear'], ['zoom'], 10, 3.5, 15, 6.5],
          ],
          // Pickup and dropoff must be distinguishable at a glance, or a
          // sixteen-order map is just confetti.
          'circle-color': ['case', ['==', ['get', 'kind'], 'pickup'], '#fbbf24', '#f472b6'],
          'circle-stroke-color': ['case', ['get', 'selected'], '#ffffff', '#0f172a'],
          'circle-stroke-width': ['case', ['get', 'selected'], 2.5, 1],
          'circle-opacity': ['case', ['get', 'dimmed'], 0.25, 1],
        },
      });

      setStyleReady(true);
    });

    instance.on('error', (event) => {
      // A style or source failure must be visible, never a silently empty frame.
      setLoad({ status: 'failed', reason: event.error?.message ?? 'map engine error' });
    });

    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
      setStyleReady(false);
    };
  }, [load]);

  // --- interaction -----------------------------------------------------------

  useEffect(() => {
    const instance = map.current;
    if (!instance || !styleReady) return;

    const onZoneMove = (e: maplibregl.MapLayerMouseEvent) => {
      const h3 = e.features?.[0]?.properties?.h3 as string | undefined;
      setHovered(h3 ?? null);
      instance.getCanvas().style.cursor = h3 ? 'pointer' : '';
    };
    const onZoneLeave = () => {
      setHovered(null);
      instance.getCanvas().style.cursor = '';
    };
    const onZoneClick = (e: maplibregl.MapLayerMouseEvent) => {
      onSelectZone?.((e.features?.[0]?.properties?.h3 as string) ?? null);
    };
    const onOrderClick = (e: maplibregl.MapLayerMouseEvent) => {
      const orderId = e.features?.[0]?.properties?.orderId as string | undefined;
      if (orderId) {
        onSelectOrder?.(orderId);
        e.preventDefault();
      }
    };
    const onBackgroundClick = () => onSelectOrder?.(null);

    instance.on('mousemove', 'zones-fill', onZoneMove);
    instance.on('mouseleave', 'zones-fill', onZoneLeave);
    instance.on('click', 'zones-fill', onZoneClick);
    instance.on('click', 'orders-point', onOrderClick);
    instance.on('click', onBackgroundClick);

    return () => {
      instance.off('mousemove', 'zones-fill', onZoneMove);
      instance.off('mouseleave', 'zones-fill', onZoneLeave);
      instance.off('click', 'zones-fill', onZoneClick);
      instance.off('click', 'orders-point', onOrderClick);
      instance.off('click', onBackgroundClick);
    };
  }, [styleReady, onSelectOrder, onSelectZone]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !styleReady) return;
    instance.setFilter('zones-hover', ['==', ['get', 'h3'], hovered ?? '']);
  }, [hovered, styleReady]);

  // --- data in ---------------------------------------------------------------

  const setSource = useCallback(
    (id: string, collection: FeatureCollection | undefined) => {
      const instance = map.current;
      if (!instance || !styleReady) return;
      const source = instance.getSource(id) as maplibregl.GeoJSONSource | undefined;
      source?.setData((collection ?? emptyCollection()) as never);
    },
    [styleReady],
  );

  useEffect(() => setSource('zones', zoneCollection), [setSource, zoneCollection]);
  useEffect(() => setSource('facilities', data.facilities), [setSource, data.facilities]);
  useEffect(() => setSource('scenario', data.scenario), [setSource, data.scenario]);
  useEffect(() => setSource('recommended', data.recommended), [setSource, data.recommended]);

  // Selection is applied to the data rather than to a filter, so a selected
  // order can be emphasised while the rest stay drawn but dimmed.
  useEffect(() => {
    const mark = (collection: FeatureCollection | undefined) => {
      if (!collection) return undefined;
      return {
        ...collection,
        features: collection.features.map((f) => ({
          ...f,
          properties: {
            ...f.properties,
            selected: selectedOrderId != null && f.properties.orderId === selectedOrderId,
            dimmed: selectedOrderId != null && f.properties.orderId !== selectedOrderId,
          },
        })),
      };
    };
    setSource('orders', mark(data.orders));
    setSource('routes', mark(data.routes));
  }, [setSource, data.orders, data.routes, selectedOrderId]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !styleReady) return;
    for (const [layerId, mapLayers] of Object.entries(LAYER_TO_MAPLIBRE)) {
      const on = visible[layerId as LayerId];
      for (const name of mapLayers) {
        if (instance.getLayer(name)) {
          instance.setLayoutProperty(name, 'visibility', on ? 'visible' : 'none');
        }
      }
    }
  }, [visible, styleReady]);

  const fitToNetwork = useCallback(() => {
    if (load.status === 'ready') {
      map.current?.fitBounds(boundsOf(load.basemap), { padding: 32, duration: 600 });
    }
  }, [load]);

  // --- render ----------------------------------------------------------------

  const sources: MapSource[] = ['osm'];
  if (data.traffic && data.traffic.size > 0) sources.push('tomtom');
  if (data.routes && data.routes.features.length > 0) sources.push('osrm');

  if (load.status === 'failed') {
    return (
      <div
        data-map-state="failed"
        className={`flex h-full w-full flex-col items-center justify-center gap-2 bg-slate-950 p-6 text-center ${className}`}
      >
        <p className="text-sm font-semibold text-red-400">Map unavailable</p>
        <p className="max-w-md text-xs text-slate-400">{load.reason}</p>
        <p className="max-w-md text-xs text-slate-500">
          The geographic evidence could not be loaded or did not validate. No substitute is drawn.
        </p>
      </div>
    );
  }

  return (
    <div className={`relative h-full w-full ${className}`} data-map-state={load.status}>
      <div ref={container} className="h-full w-full" data-testid="onemove-map" />

      {load.status === 'loading' && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80">
          <p className="text-xs text-slate-400">Loading Bengaluru geographic evidence…</p>
        </div>
      )}

      <div className="pointer-events-none absolute left-3 top-3 flex flex-col gap-2">
        <div className="pointer-events-auto rounded-md border border-slate-700/70 bg-slate-950/85 p-2 backdrop-blur">
          <div className="mb-1.5 flex items-center justify-between gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Layers</span>
            <button
              type="button"
              onClick={fitToNetwork}
              className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] text-slate-300 hover:bg-slate-800"
            >
              Fit network
            </button>
          </div>
          <ul className="space-y-1">
            {LAYERS.map((layer) => (
              <li key={layer.id}>
                <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-300">
                  <input
                    type="checkbox"
                    checked={visible[layer.id]}
                    onChange={(e) => setVisible((v) => ({ ...v, [layer.id]: e.target.checked }))}
                    className="h-3 w-3 accent-sky-500"
                  />
                  <span className="flex-1">{layer.label}</span>
                  <span className="rounded bg-slate-800 px-1 py-px text-[9px] uppercase tracking-wide text-slate-400">
                    {layer.evidence}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-3 right-3 flex flex-col items-end gap-1.5">
        <div className="pointer-events-auto rounded-md border border-slate-700/70 bg-slate-950/85 px-2 py-1.5 backdrop-blur">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Congestion</p>
          <div className="flex items-center gap-1 text-[10px] text-slate-300">
            <span className="h-2 w-6 rounded-sm bg-[#16a34a]" />
            <span>free</span>
            <span className="h-2 w-6 rounded-sm bg-[#eab308]" />
            <span className="h-2 w-6 rounded-sm bg-[#f97316]" />
            <span className="h-2 w-6 rounded-sm bg-[#dc2626]" />
            <span>heavy</span>
            <span className="ml-2 h-2 w-6 rounded-sm bg-[#3f3f46]" />
            <span>unavailable</span>
          </div>
        </div>
        <MapAttribution sources={sources} className="pointer-events-auto rounded bg-slate-950/85 px-2 py-1" />
      </div>
    </div>
  );
}

const LAYER_TO_MAPLIBRE: Record<LayerId, string[]> = {
  roads: ['roads-line'],
  zones: ['zones-outline', 'zones-hover'],
  facilities: ['facilities-point'],
  traffic: ['zones-fill'],
  orders: ['orders-point'],
  routes: ['routes-line'],
  scenario: ['scenario-fill'],
  recommended: ['recommended-point'],
};
