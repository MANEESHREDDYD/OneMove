"use client";

import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection, Polygon, Position } from "geojson";
import { circleMarker } from "leaflet";
import type { PathOptions } from "leaflet";

import type { MapLayer, ZoneSummary } from "../../lib/api/types";
import { MapLayerSummary } from "./layer-summary";

interface NetworkMapProps {
  layers: MapLayer[];
  zones: ZoneSummary[];
}

const PILOT_BOUNDARY: Feature<Polygon> = {
  type: "Feature",
  properties: { layer: "pilot-boundary" },
  geometry: {
    type: "Polygon",
    coordinates: [[
      [77.58, 12.90],
      [77.65, 12.90],
      [77.65, 12.98],
      [77.58, 12.98],
      [77.58, 12.90],
    ]],
  },
};

const pilotStyle: PathOptions = {
  color: "#0f172a",
  dashArray: "8 6",
  fillOpacity: 0,
  weight: 2,
};

const cellStyle: PathOptions = {
  color: "#1d4ed8",
  fillColor: "#60a5fa",
  fillOpacity: 0.18,
  weight: 1,
};

/**
 * A GeoJSON linear ring needs at least three distinct vertices plus an explicit
 * closing vertex. A zone whose boundary is empty or degenerate cannot be drawn,
 * so it is dropped rather than emitting invalid geometry (or dereferencing a
 * missing first vertex, which previously threw).
 */
function zoneRing(zone: ZoneSummary): Position[] | null {
  const first = zone.boundary[0];
  if (!first || zone.boundary.length < 3) return null;
  // API coordinates are [latitude, longitude]; GeoJSON is [longitude, latitude].
  const ring: Position[] = zone.boundary.map(([latitude, longitude]) => [longitude, latitude]);
  ring.push([first[1], first[0]]);
  return ring;
}

export function zoneCollection(zones: ZoneSummary[]): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = [];
  for (const zone of zones) {
    const ring = zoneRing(zone);
    if (!ring) continue;
    features.push({
      type: "Feature",
      properties: {
        zone_id: zone.zone_id,
        evidence_class: zone.evidence_class,
        source: zone.source,
        source_version: zone.source_version,
        observed_at: zone.observed_at,
        availability: "AVAILABLE",
      },
      geometry: { type: "Polygon", coordinates: [ring] },
    });
  }
  return { type: "FeatureCollection", features };
}

function escapeHtml(value: unknown): string {
  return String(value ?? "not declared").replace(
    /[&<>"']/g,
    (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    })[character] ?? character,
  );
}

export default function NetworkMap({ layers, zones }: NetworkMapProps) {
  const roads = layers.find((layer) => layer.layer === "roads" && layer.state === "AVAILABLE");
  const intersections = layers.find((layer) => layer.layer === "intersections" && layer.state === "AVAILABLE");
  const pois = layers.find((layer) => layer.layer === "pois" && layer.state === "AVAILABLE");

  return (
    <div className="overflow-hidden rounded-xl border border-slate-300 bg-slate-200 shadow-sm">
      <MapContainer
        aria-label="Verified ZonePilot H3 network map"
        center={[12.94, 77.615]}
        className="h-[32rem] w-full"
        maxZoom={18}
        minZoom={10}
        scrollWheelZoom
        zoom={13}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          maxZoom={19}
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON data={PILOT_BOUNDARY} style={pilotStyle} />
        {roads && (
          <GeoJSON
            data={roads.geojson}
            style={{ color: "#475569", opacity: 0.7, weight: 1.5 }}
          />
        )}
        {intersections && (
          <GeoJSON
            data={intersections.geojson}
            pointToLayer={(_feature, latlng) => circleMarker(latlng, {
              color: "#7c3aed",
              fillColor: "#a78bfa",
              fillOpacity: 0.8,
              radius: 2.5,
              weight: 1,
            })}
          />
        )}
        {pois && (
          <GeoJSON
            data={pois.geojson}
            pointToLayer={(_feature, latlng) => circleMarker(latlng, {
              color: "#b45309",
              fillColor: "#f59e0b",
              fillOpacity: 0.75,
              radius: 3,
              weight: 1,
            })}
          />
        )}
        <GeoJSON
          data={zoneCollection(zones)}
          onEachFeature={(feature, layer) => {
            // GeoJSON `properties` is nullable by specification.
            const properties = feature.properties ?? {};
            layer.bindPopup(
              `<strong>${escapeHtml(properties.zone_id)}</strong><br>` +
              `Source: ${escapeHtml(properties.source)}<br>` +
              `Version: ${escapeHtml(properties.source_version)}<br>` +
              `Observed: ${escapeHtml(properties.observed_at)}<br>` +
              `Evidence: ${escapeHtml(properties.evidence_class)}<br>` +
              `Availability: ${escapeHtml(properties.availability)}`,
            );
          }}
          style={cellStyle}
        />
      </MapContainer>
      <MapLayerSummary layers={layers} zones={zones} />
    </div>
  );
}
