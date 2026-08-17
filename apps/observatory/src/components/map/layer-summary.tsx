"use client";

import type { MapLayer, ZoneSummary } from "../../lib/api/types";

/**
 * The Leaflet canvas is opaque to assistive technology, so this module renders
 * the map's evidence as text. It deliberately imports no Leaflet code: it is the
 * text alternative, and it must render even when the map itself cannot.
 */

export type LayerAvailability = "AVAILABLE" | "UNAVAILABLE";

export interface LayerDescription {
  label: string;
  availability: LayerAvailability;
  /** Human-readable feature count, or an explicit statement that there is none. */
  features: string;
  /** Provenance sentence. Never contains a stringified null. */
  provenance: string;
}

function formatCount(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString() : "an unreported number of";
}

/**
 * Describes one evidence-backed map layer.
 *
 * An UNAVAILABLE layer has no observation behind it, so `evidence_class` is
 * null by contract. Interpolating it directly would surface the literal string
 * "null" to the reader, so the null case is spelled out in words instead.
 */
export function describeLayer(label: string, layer: MapLayer | undefined): LayerDescription {
  if (!layer) {
    return {
      label,
      availability: "UNAVAILABLE",
      features: "No mounted artifact",
      provenance: "Layer metadata unavailable",
    };
  }

  const evidence =
    layer.state === "AVAILABLE" && layer.evidence_class
      ? layer.evidence_class
      : "no evidence class";

  return {
    label,
    availability: layer.state,
    features: `${formatCount(layer.returned_feature_count)} of ${formatCount(layer.total_feature_count)} features`,
    provenance: [
      layer.source,
      layer.source_version ?? "unversioned",
      layer.observed_at ?? "timestamp unavailable",
      evidence,
    ].join(" · "),
  };
}

/** Layers ZonePilot draws from its own configuration rather than from the API. */
function staticDescriptions(zones: ZoneSummary[]): LayerDescription[] {
  return [
    {
      label: "Pilot boundary",
      availability: "AVAILABLE",
      features: "1 boundary polygon",
      provenance: "ZonePilot pilot BBOX",
    },
    {
      label: "H3 R8 cells",
      availability: zones.length > 0 ? "AVAILABLE" : "UNAVAILABLE",
      features: zones.length > 0 ? `${zones.length.toLocaleString()} cells` : "No mounted cells",
      provenance: "Verified Gold Parquet",
    },
  ];
}

export function describeLayers(layers: MapLayer[], zones: ZoneSummary[]): LayerDescription[] {
  const find = (name: MapLayer["layer"]) => layers.find((item) => item.layer === name);
  return [
    ...staticDescriptions(zones),
    describeLayer("Road geometries", find("roads")),
    describeLayer("Intersections", find("intersections")),
    describeLayer("POIs", find("pois")),
    {
      label: "Traffic",
      availability: "UNAVAILABLE",
      features: "No zone-linked traffic artifact",
      provenance: "No mounted traffic artifact is spatially joined to these cells",
    },
  ];
}

function AvailabilityBadge({ availability }: { availability: LayerAvailability }) {
  const available = availability === "AVAILABLE";
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-1 text-[0.65rem] font-bold ${
        available ? "bg-emerald-100 text-emerald-900" : "bg-slate-200 text-slate-800"
      }`}
    >
      {availability}
    </span>
  );
}

/**
 * The accessible equivalent of the map. Rendered as a real table so screen
 * reader users get row/column semantics and can review every layer's
 * availability, feature counts, and provenance without seeing the canvas.
 */
export function MapLayerSummary({ layers, zones }: { layers: MapLayer[]; zones: ZoneSummary[] }) {
  const descriptions = describeLayers(layers, zones);
  const availableCount = descriptions.filter((item) => item.availability === "AVAILABLE").length;

  return (
    <div className="overflow-x-auto border-t border-slate-300">
      <table className="w-full min-w-[36rem] border-collapse text-left">
        <caption className="px-4 pb-3 pt-4 text-left text-sm text-slate-600">
          Text alternative for the evidence map: {availableCount} of {descriptions.length} layers are
          available. Each row states one layer&apos;s availability, feature count, and provenance.
        </caption>
        <thead>
          <tr className="border-b border-slate-300 bg-slate-50">
            <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
              Layer
            </th>
            <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
              Availability
            </th>
            <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
              Features
            </th>
            <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
              Provenance
            </th>
          </tr>
        </thead>
        <tbody>
          {descriptions.map((description) => (
            <tr className="border-b border-slate-200 last:border-0 bg-white" key={description.label}>
              <th className="px-4 py-3 text-sm font-semibold" scope="row">
                {description.label}
              </th>
              <td className="px-4 py-3">
                <AvailabilityBadge availability={description.availability} />
              </td>
              <td className="px-4 py-3 text-sm text-slate-700">{description.features}</td>
              <td className="px-4 py-3 text-xs leading-5 text-slate-600">{description.provenance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
