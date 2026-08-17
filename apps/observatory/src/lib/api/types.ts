import type { FeatureCollection } from "geojson";

export type ProviderState = "FRESH" | "DEGRADED" | "STALE" | "UNAVAILABLE";
export type DatasetAvailability = "AVAILABLE" | "EMPTY" | "FAILED" | "UNAVAILABLE";

/** Canonical taxonomy. Mirrors services.temporal.contracts.EvidenceClass. */
export type EvidenceClass =
  | "OBSERVED"
  | "PUBLIC_OFFICIAL"
  | "PUBLIC_GEOGRAPHIC"
  | "PROVIDER_ESTIMATED"
  | "DERIVED"
  | "SIMULATED"
  | "ASSUMPTION"
  | "STAGING_DO_NOT_USE"
  | "TEST_ONLY";

export interface Provenance {
  /** Null when there is no observation to classify. Availability lives in `state`. */
  evidence_class: EvidenceClass | null;
  source: string;
  source_version: string | null;
  observed_at: string | null;
  artifact_hash: string | null;
}

export interface ZoneSummary extends Provenance {
  zone_id: string;
  resolution: number;
  boundary: Array<[number, number]>;
}

export interface DatasetRecord extends Provenance {
  dataset_id: string;
  provider: string;
  version: string;
  schema_version: string | null;
  availability: DatasetAvailability;
  record_count: number | null;
  run_id: string | null;
}

export interface ProviderHealth {
  provider: string;
  state: ProviderState;
  last_successful_collection: string | null;
  expected_freshness_seconds: number;
  observed_freshness_seconds: number | null;
  dq_result: "PASS" | "FAIL" | "UNKNOWN";
  latest_run_status: string | null;
  dataset_ids: string[];
}

export interface ZoneListResponse {
  data: ZoneSummary[];
}

export interface DatasetListResponse {
  data: DatasetRecord[];
}

export interface DataHealthResponse {
  data: ProviderHealth[];
  evaluated_at: string;
}

export interface MapLayer extends Provenance {
  layer: "roads" | "intersections" | "pois";
  state: "AVAILABLE" | "UNAVAILABLE";
  complete: boolean;
  total_feature_count: number;
  returned_feature_count: number;
  selection_policy: string;
  geojson: FeatureCollection;
}

export interface MapLayerListResponse {
  data: MapLayer[];
}
