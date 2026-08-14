"use client";

import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection, Polygon } from "geojson";
import { circleMarker } from "leaflet";
import type { PathOptions } from "leaflet";

import type { MapLayer, ZoneSummary } from "../../lib/api/types";

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

function zoneCollection(zones: ZoneSummary[]): FeatureCollection<Polygon> {
  return {
    type: "FeatureCollection",
    features: zones.map((zone) => ({
      type: "Feature",
      properties: {
        zone_id: zone.zone_id,
        evidence_class: zone.evidence_class,
        source: zone.source,
        source_version: zone.source_version,
        observed_at: zone.observed_at,
        availability: "AVAILABLE",
      },
      geometry: {
        type: "Polygon",
        // API coordinates are [latitude, longitude]; GeoJSON is [longitude, latitude].
        coordinates: [[
          ...zone.boundary.map(([latitude, longitude]) => [longitude, latitude]),
          [zone.boundary[0][1], zone.boundary[0][0]],
        ]],
      },
    })),
  };
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
            const properties = feature.properties;
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
      <div className="grid gap-px border-t border-slate-300 bg-slate-300 sm:grid-cols-2 lg:grid-cols-3">
        <LayerStatus availability="AVAILABLE" label="Pilot boundary" source="ZonePilot pilot BBOX" />
        <LayerStatus availability="AVAILABLE" label="H3 R8 cells" source="Verified Gold Parquet" />
        <EvidenceLayerStatus label="Road geometries" layer={layers.find((item) => item.layer === "roads")} />
        <EvidenceLayerStatus label="Intersections" layer={layers.find((item) => item.layer === "intersections")} />
        <EvidenceLayerStatus label="POIs" layer={layers.find((item) => item.layer === "pois")} />
        <LayerStatus availability="UNAVAILABLE" label="Traffic" source="No zone-linked traffic artifact" />
      </div>
    </div>
  );
}

function EvidenceLayerStatus({ label, layer }: { label: string; layer?: MapLayer }) {
  const availability = layer?.state ?? "UNAVAILABLE";
  const count = layer
    ? `${layer.returned_feature_count.toLocaleString()} of ${layer.total_feature_count.toLocaleString()} features`
    : "No mounted artifact";
  const provenance = layer
    ? `${layer.source} · ${layer.source_version ?? "unversioned"} · ${layer.observed_at ?? "timestamp unavailable"} · ${layer.evidence_class}`
    : "Layer metadata unavailable";
  return (
    <LayerStatus
      availability={availability}
      label={label}
      source={`${count}. ${provenance}`}
    />
  );
}

function LayerStatus({
  availability,
  label,
  source,
}: {
  availability: "AVAILABLE" | "UNAVAILABLE";
  label: string;
  source: string;
}) {
  const available = availability === "AVAILABLE";
  return (
    <div className="bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">{label}</p>
        <span className={`rounded-full px-2 py-1 text-[0.65rem] font-bold ${available ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"}`}>
          {availability}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-500">{source}</p>
    </div>
  );
}
