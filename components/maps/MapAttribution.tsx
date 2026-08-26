import React from 'react';

/**
 * Visible attribution for map data and tiles.
 *
 * Attribution is a licence condition, not decoration. OpenStreetMap's ODbL and
 * TomTom's terms both require the credit to be visible in the interface that
 * displays the derived geometry or tiles — a credit that lives only in an `alt`
 * attribute, a source comment, or docs/data/DATA_LICENSES.md does not discharge
 * it. Every surface that draws OSM-derived geometry renders this.
 *
 * Server-renderable on purpose: it carries no state, so a component test can
 * assert the required strings are actually in the markup.
 */

export type MapSource =
  /** Geometry derived from the OpenStreetMap extract (ODbL 1.0). */
  | 'osm'
  /** Raster basemap tiles served by CARTO, themselves OSM-derived. */
  | 'carto'
  /** TomTom Traffic Flow (relative0 tiles / flowSegmentData). */
  | 'tomtom'
  /** Routes computed by OSRM over the OSM road network (BSD-2-Clause). */
  | 'osrm';

const CREDITS: Record<MapSource, { text: string; href: string; label: string }> = {
  osm: {
    text: '© OpenStreetMap contributors',
    href: 'https://www.openstreetmap.org/copyright',
    label: 'OpenStreetMap copyright and licence',
  },
  carto: {
    text: '© CARTO',
    href: 'https://carto.com/attributions',
    label: 'CARTO basemap attributions',
  },
  tomtom: {
    text: 'Traffic © TomTom',
    href: 'https://www.tomtom.com/products/traffic-apis/',
    label: 'TomTom traffic data attribution',
  },
  osrm: {
    text: 'Routing by OSRM',
    href: 'https://project-osrm.org/',
    label: 'Project OSRM',
  },
};

/** The plain-text credit line, for tests and for non-DOM consumers. */
export function attributionText(sources: MapSource[]): string {
  return sources.map((s) => CREDITS[s].text).join(' · ');
}

export function MapAttribution({
  sources,
  className = '',
}: {
  sources: MapSource[];
  className?: string;
}) {
  if (sources.length === 0) return null;
  return (
    <div
      data-map-attribution="true"
      className={`pointer-events-auto flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] leading-tight text-slate-300 ${className}`}
    >
      {sources.map((source, i) => {
        const credit = CREDITS[source];
        return (
          <React.Fragment key={source}>
            {i > 0 && (
              <span aria-hidden="true" className="text-slate-500">
                ·
              </span>
            )}
            <a
              href={credit.href}
              target="_blank"
              rel="noreferrer noopener"
              aria-label={credit.label}
              className="underline decoration-slate-500 underline-offset-2 hover:text-slate-100"
            >
              {credit.text}
            </a>
          </React.Fragment>
        );
      })}
    </div>
  );
}
