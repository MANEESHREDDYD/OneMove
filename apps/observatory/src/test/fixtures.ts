/**
 * Fixtures shaped from `src/lib/api/types.ts`. They are typed, not cast, so a
 * contract change in the API types breaks these builders at compile time rather
 * than silently letting tests assert against a shape the API no longer returns.
 */
import type {
  DataHealthResponse,
  DatasetRecord,
  MapLayer,
  MapLayerListResponse,
  ProviderHealth,
  ProviderState,
  ReleaseIdentity,
  ReleaseIdentityResponse,
  ZoneListResponse,
  ZoneSummary,
} from "../lib/api/types";

export function providerHealth(overrides: Partial<ProviderHealth> = {}): ProviderHealth {
  return {
    provider: "open-meteo",
    state: "FRESH",
    last_successful_collection: "2026-08-17T09:00:00Z",
    expected_freshness_seconds: 3600,
    observed_freshness_seconds: 120,
    dq_result: "PASS",
    latest_run_status: "SUCCEEDED",
    dataset_ids: ["weather_hourly"],
    ...overrides,
  };
}

/** One provider per canonical state, for exhaustive state-rendering tests. */
export function providersInEveryState(): ProviderHealth[] {
  const states: ProviderState[] = ["FRESH", "DEGRADED", "STALE", "UNAVAILABLE"];
  return states.map((state) =>
    providerHealth({
      provider: `provider-${state.toLowerCase()}`,
      state,
      dq_result: state === "FRESH" ? "PASS" : state === "UNAVAILABLE" ? "UNKNOWN" : "FAIL",
      last_successful_collection: state === "UNAVAILABLE" ? null : "2026-08-17T09:00:00Z",
      latest_run_status: state === "UNAVAILABLE" ? null : "SUCCEEDED",
    }),
  );
}

export function dataHealthResponse(overrides: Partial<DataHealthResponse> = {}): DataHealthResponse {
  return {
    data: providersInEveryState(),
    evaluated_at: "2026-08-17T09:05:00Z",
    ...overrides,
  };
}

export function zoneSummary(overrides: Partial<ZoneSummary> = {}): ZoneSummary {
  return {
    zone_id: "8861086b0dfffff",
    resolution: 8,
    boundary: [
      [12.94, 77.61],
      [12.95, 77.62],
      [12.93, 77.63],
    ],
    evidence_class: "PUBLIC_GEOGRAPHIC",
    source: "gold_network_parquet",
    source_version: "2026.08.1",
    observed_at: "2026-08-17T08:00:00Z",
    artifact_hash: "sha256:abc123",
    ...overrides,
  };
}

export function zoneListResponse(zones: ZoneSummary[] = [zoneSummary()]): ZoneListResponse {
  return { data: zones };
}

export function datasetRecord(overrides: Partial<DatasetRecord> = {}): DatasetRecord {
  return {
    dataset_id: "weather_hourly",
    provider: "open-meteo",
    version: "2026.08.1",
    schema_version: "1.0.0",
    availability: "AVAILABLE",
    record_count: 1024,
    run_id: "run-1",
    evidence_class: "OBSERVED",
    source: "open-meteo",
    source_version: "v1",
    observed_at: "2026-08-17T09:00:00Z",
    artifact_hash: "sha256:def456",
    ...overrides,
  };
}

/** An AVAILABLE layer: it has an observation, so it has an evidence class. */
export function availableMapLayer(overrides: Partial<MapLayer> = {}): MapLayer {
  return {
    layer: "roads",
    state: "AVAILABLE",
    complete: true,
    total_feature_count: 12500,
    returned_feature_count: 12500,
    selection_policy: "ALL",
    geojson: { type: "FeatureCollection", features: [] },
    evidence_class: "PUBLIC_GEOGRAPHIC",
    source: "openstreetmap",
    source_version: "2026-08-01",
    observed_at: "2026-08-17T07:00:00Z",
    artifact_hash: "sha256:ghi789",
    ...overrides,
  };
}

/**
 * An UNAVAILABLE layer. Per the canonical contract there is no observation to
 * classify, so every provenance field including `evidence_class` is null. This
 * is the shape that regressed into rendering the literal string "null".
 */
export function unavailableMapLayer(overrides: Partial<MapLayer> = {}): MapLayer {
  return {
    layer: "pois",
    state: "UNAVAILABLE",
    complete: false,
    total_feature_count: 0,
    returned_feature_count: 0,
    selection_policy: "NONE",
    geojson: { type: "FeatureCollection", features: [] },
    evidence_class: null,
    source: "openstreetmap",
    source_version: null,
    observed_at: null,
    artifact_hash: null,
    ...overrides,
  };
}

export function mapLayerListResponse(layers: MapLayer[] = [availableMapLayer()]): MapLayerListResponse {
  return { data: layers };
}

export function releaseIdentity(overrides: Partial<ReleaseIdentity> = {}): ReleaseIdentity {
  return {
    app_version: "1.5.1",
    git_sha: "666ade66f965df76097c557cdf419501b683db75",
    schema_version: "1.0.0",
    gold: {
      dataset_id: "gold_network",
      dataset_version: "2026.08.1",
      schema_version: "1.0.0",
      artifact_sha256: "a".repeat(64),
      record_count: 4096,
    },
    graph: {
      graph_version: "2026.08.1",
      topology_sha256: "b".repeat(64),
      bundle_sha256: "c".repeat(64),
    },
    ...overrides,
  };
}

export function releaseIdentityResponse(
  overrides: Partial<ReleaseIdentity> = {},
): ReleaseIdentityResponse {
  return { data: releaseIdentity(overrides) };
}
