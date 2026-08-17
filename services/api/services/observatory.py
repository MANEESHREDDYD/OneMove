import os
from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import h3

from services.api.contracts.observatory import (
    DataHealthResponse,
    DatasetAvailability,
    DatasetListResponse,
    DatasetRecord,
    DQResult,
    EvidenceClass,
    EvidenceRecord,
    EvidenceResponse,
    FieldEvidence,
    MapLayer,
    MapLayerListResponse,
    NetworkMetrics,
    NetworkSnapshot,
    NetworkSnapshotListResponse,
    NetworkSnapshotResponse,
    ProviderHealth,
    ProviderState,
    UnavailableLayer,
    ZoneListResponse,
    ZoneState,
    ZoneStateResponse,
    ZoneStaticState,
    ZoneSummary,
)
from services.api.repositories.artifact_catalog import (
    ArtifactCatalogRepository,
    ArtifactCorrupt,
    ArtifactNotReady,
)

# Every value here must be a member of the canonical taxonomy in
# services/temporal/contracts.py. Open-Meteo and ONDC are public official data
# sources, so they classify as PUBLIC_OFFICIAL.
PROVIDER_EVIDENCE_CLASS: dict[str, EvidenceClass] = {
    "openmeteo": EvidenceClass.PUBLIC_OFFICIAL,
    "osm": EvidenceClass.PUBLIC_GEOGRAPHIC,
    "osrm": EvidenceClass.DERIVED,
    "tomtom": EvidenceClass.PROVIDER_ESTIMATED,
    "ondc": EvidenceClass.PUBLIC_OFFICIAL,
}

DEFAULT_FRESHNESS_SECONDS = {
    "openmeteo": 6 * 60 * 60,
    "osm": 7 * 24 * 60 * 60,
    "osrm": 30 * 24 * 60 * 60,
    "tomtom": 15 * 60,
    "ondc": 24 * 60 * 60,
}

DISPLAY_ROAD_CLASSES = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
}
MAX_MAP_ROADS = 3_000
MAX_MAP_INTERSECTIONS = 1_500
MAX_MAP_POIS = 1_500


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _required_str(data: dict[str, Any], key: str, artifact: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ArtifactCorrupt(f"{artifact} is missing required field {key}")
    return value


def _required_int(data: dict[str, Any], key: str, artifact: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactCorrupt(f"{artifact} is missing required integer field {key}")
    return value


class ObservatoryService:
    def __init__(
        self,
        repository: ArtifactCatalogRepository,
        now: Callable[[], datetime] | None = None,
    ):
        self.repository = repository
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._map_layers_cache: MapLayerListResponse | None = None

    def _gold_provenance(self) -> dict[str, Any]:
        manifest = self.repository.gold_manifest()
        expected_hash = _required_str(manifest, "parquet_sha256", "Gold manifest")
        actual_hash = self.repository.gold_artifact_hash()
        if actual_hash != expected_hash:
            raise ArtifactCorrupt("Gold network artifact hash does not match its manifest")
        return {
            "evidence_class": EvidenceClass.PUBLIC_GEOGRAPHIC,
            "source": _required_str(manifest, "osm_source", "Gold manifest"),
            "source_version": str(manifest.get("graph_version")) if manifest.get("graph_version") is not None else None,
            "observed_at": _parse_timestamp(manifest.get("generated_at")),
            "artifact_hash": actual_hash,
        }

    def list_zones(self) -> ZoneListResponse:
        provenance = self._gold_provenance()
        zones = []
        for row in self.repository.gold_rows():
            zone_id = _required_str(row, "h3_index", "Gold network row")
            resolution = _required_int(row, "h3_resolution", "Gold network row")
            zones.append(
                ZoneSummary(
                    zone_id=zone_id,
                    resolution=resolution,
                    boundary=[(float(lat), float(lng)) for lat, lng in h3.cell_to_boundary(zone_id)],
                    **provenance,
                )
            )
        return ZoneListResponse(data=zones)

    def get_zone_state(self, zone_id: str) -> ZoneStateResponse:
        if not h3.is_valid_cell(zone_id):
            raise ValueError("Zone ID must be a valid H3 cell identifier")
        row = self.repository.gold_row(zone_id)
        provenance = self._gold_provenance()

        def field(name: str, unit: str | None = None) -> FieldEvidence:
            value = row.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                raise ArtifactCorrupt(f"Gold network row has invalid field {name}")
            return FieldEvidence(value=value, unit=unit, **provenance)

        resolution = _required_int(row, "h3_resolution", "Gold network row")
        state = ZoneState(
            zone_id=zone_id,
            resolution=resolution,
            boundary=[(float(lat), float(lng)) for lat, lng in h3.cell_to_boundary(zone_id)],
            static=ZoneStaticState(
                cell_area_km2=field("cell_area_km2", "km2"),
                road_length_km=field("road_length_km", "km"),
                intersection_count=field("intersection_count", "count"),
                restaurant_count=field("restaurant_count", "count"),
                grocery_count=field("grocery_count", "count"),
                commercial_poi_count=field("commercial_poi_count", "count"),
                road_density_km_per_sqkm=field("road_density_km_per_sqkm", "km/km2"),
                intersection_density_per_sqkm=field("intersection_density_per_sqkm", "count/km2"),
            ),
            unavailable_dynamic_layers=[
                UnavailableLayer(
                    layer="traffic",
                    reason="No traffic observation in the mounted artifacts is spatially joined to this H3 cell.",
                ),
                UnavailableLayer(
                    layer="weather",
                    reason="No weather observation in the mounted artifacts is spatially joined to this H3 cell.",
                ),
            ],
            **provenance,
        )
        return ZoneStateResponse(data=state)

    def _run_datasets(self) -> list[DatasetRecord]:
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for manifest in self.repository.daily_manifests():
            runs = manifest.get("runs", [])
            if not isinstance(runs, list):
                raise ArtifactCorrupt("Daily manifest runs field must be a list")
            for run in runs:
                if not isinstance(run, dict):
                    raise ArtifactCorrupt("Daily manifest contains a non-object run")
                provider = run.get("provider")
                dataset = run.get("dataset")
                if not isinstance(provider, str) or not isinstance(dataset, str):
                    raise ArtifactCorrupt("Daily manifest run is missing provider or dataset")
                key = (provider, dataset)
                candidate_time = _parse_timestamp(run.get("completed_at") or run.get("started_at"))
                current_time = _parse_timestamp(
                    latest.get(key, {}).get("completed_at") or latest.get(key, {}).get("started_at")
                )
                if key not in latest or (candidate_time and (not current_time or candidate_time >= current_time)):
                    latest[key] = run

        datasets: list[DatasetRecord] = []
        for (provider, dataset), run in sorted(latest.items()):
            status = str(run.get("status", "UNKNOWN")).upper()
            records = run.get("records_written", run.get("records_received"))
            record_count = records if isinstance(records, int) and not isinstance(records, bool) else None
            if status not in {"COMPLETED", "SUCCESS"}:
                availability = DatasetAvailability.FAILED
            elif record_count == 0:
                availability = DatasetAvailability.EMPTY
            else:
                availability = DatasetAvailability.AVAILABLE
            run_id = str(run.get("run_id")) if run.get("run_id") is not None else None
            version = str(run.get("raw_hash") or run_id or "unversioned")
            datasets.append(
                DatasetRecord(
                    dataset_id=f"{provider}:{dataset}",
                    provider=provider,
                    version=version,
                    # Collection runs carry no schema identity in
                    # zonepilot_ops.collection_runs, so there is nothing
                    # truthful to report here.
                    schema_version=None,
                    availability=availability,
                    record_count=record_count,
                    run_id=run_id,
                    evidence_class=PROVIDER_EVIDENCE_CLASS.get(provider, EvidenceClass.OBSERVED),
                    source=provider,
                    source_version=str(run.get("source_version")) if run.get("source_version") is not None else None,
                    observed_at=_parse_timestamp(run.get("completed_at") or run.get("started_at")),
                    artifact_hash=str(run.get("raw_hash")) if run.get("raw_hash") else None,
                )
            )
        return datasets

    def list_datasets(self) -> DatasetListResponse:
        manifest = self.repository.gold_manifest()
        provenance = self._gold_provenance()
        gold = DatasetRecord(
            dataset_id=_required_str(manifest, "dataset_id", "Gold manifest"),
            provider="osm",
            version=_required_str(manifest, "parquet_sha256", "Gold manifest"),
            # The Gold manifest's own `schema_version` is the schema identity
            # (see services/collectors/gold.py). `graph_version` identifies the
            # road graph the rows were derived from, not the row schema, and is
            # reported separately as NetworkSnapshot.graph_version.
            schema_version=(
                str(manifest.get("schema_version")) if manifest.get("schema_version") is not None else None
            ),
            availability=DatasetAvailability.AVAILABLE,
            record_count=_required_int(manifest, "rows", "Gold manifest"),
            evidence_class=provenance["evidence_class"],
            source=provenance["source"],
            source_version=provenance["source_version"],
            observed_at=provenance["observed_at"],
            artifact_hash=provenance["artifact_hash"],
        )
        return DatasetListResponse(data=[gold, *self._run_datasets()])

    def _network_snapshot(self) -> NetworkSnapshot | None:
        osrm = self.repository.osrm_manifest()
        gold = self.repository.gold_manifest()
        if osrm is None or not self.repository.network_artifact_available():
            return None
        graph_metrics = gold.get("graph_metrics")
        if not isinstance(graph_metrics, dict):
            raise ArtifactCorrupt("Gold manifest graph_metrics must be an object")
        graph_hash = _required_str(osrm, "graph_bundle_sha256", "OSRM manifest")
        return NetworkSnapshot(
            snapshot_id=graph_hash,
            graph_version=str(gold.get("graph_version", "unversioned")),
            h3_resolution=_required_int(gold, "h3_resolution", "Gold manifest"),
            metrics=NetworkMetrics(
                graph_vertices=_required_int(graph_metrics, "graph_vertices", "Gold graph metrics"),
                graph_directed_edges=_required_int(graph_metrics, "graph_directed_edges", "Gold graph metrics"),
                intersections=_required_int(graph_metrics, "intersections", "Gold graph metrics"),
                connected_components=_required_int(graph_metrics, "connected_components", "Gold graph metrics"),
                largest_component_vertices=_required_int(
                    graph_metrics, "largest_component_vertices", "Gold graph metrics"
                ),
            ),
            evidence_class=EvidenceClass.DERIVED,
            source="OSRM",
            source_version=str(osrm.get("OSRM_image_digest")) if osrm.get("OSRM_image_digest") else None,
            observed_at=_parse_timestamp(osrm.get("generated_at")),
            artifact_hash=graph_hash,
        )

    def list_network_snapshots(self) -> NetworkSnapshotListResponse:
        snapshot = self._network_snapshot()
        return NetworkSnapshotListResponse(data=[snapshot] if snapshot else [])

    def get_network_snapshot(self, snapshot_id: str) -> NetworkSnapshotResponse:
        snapshot = self._network_snapshot()
        if snapshot is None or snapshot.snapshot_id != snapshot_id:
            raise LookupError(f"Network snapshot {snapshot_id} is not available")
        return NetworkSnapshotResponse(data=snapshot)

    @staticmethod
    def _bounded(features: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        if len(features) <= limit:
            return features
        # Preserve coverage across the source's deterministic ordering instead
        # of returning only the first geographic cluster.
        return [features[(index * len(features)) // limit] for index in range(limit)]

    def map_layers(self) -> MapLayerListResponse:
        if self._map_layers_cache is not None:
            return self._map_layers_cache
        osm = self.repository.osm_manifest()
        gold = self.repository.gold_manifest()
        observed_at = _parse_timestamp((osm or {}).get("retrieved_at") or (osm or {}).get("timestamp"))
        source_version = (
            str((osm or {}).get("source_version"))
            if (osm or {}).get("source_version") is not None
            else None
        )
        layers: list[MapLayer] = []

        def unavailable(layer: str, source: str) -> MapLayer:
            return MapLayer(
                layer=layer,
                state="UNAVAILABLE",
                complete=False,
                total_feature_count=0,
                returned_feature_count=0,
                selection_policy="Artifact is not mounted.",
                geojson={"type": "FeatureCollection", "features": []},
                # No mounted artifact means no observation, so there is no
                # evidence to classify. Availability lives in `state`.
                evidence_class=None,
                source=source,
                source_version=source_version,
                observed_at=observed_at,
                artifact_hash=None,
            )

        try:
            all_roads = self.repository.geojson_features("raw/osm/pilot_roads.geojson")
            road_features = [
                feature
                for feature in all_roads
                if isinstance(feature.get("geometry"), dict)
                and feature["geometry"].get("type") in {"LineString", "MultiLineString"}
                and isinstance(feature.get("properties"), dict)
                and feature["properties"].get("highway") in DISPLAY_ROAD_CLASSES
            ]
            displayed_roads = self._bounded(road_features, MAX_MAP_ROADS)
            road_hash = self.repository.artifact_hash("raw/osm/pilot_roads.geojson")
            layers.append(
                MapLayer(
                    layer="roads",
                    state="AVAILABLE",
                    complete=len(displayed_roads) == len(road_features),
                    total_feature_count=len(road_features),
                    returned_feature_count=len(displayed_roads),
                    selection_policy="All major-class OSM road features, evenly sampled only above 3000.",
                    geojson={"type": "FeatureCollection", "features": displayed_roads},
                    evidence_class=EvidenceClass.PUBLIC_GEOGRAPHIC,
                    source="pilot_roads.geojson",
                    source_version=source_version,
                    observed_at=observed_at,
                    artifact_hash=road_hash,
                )
            )

            neighbors: dict[tuple[float, float], set[tuple[float, float]]] = {}
            for feature in all_roads:
                geometry = feature.get("geometry")
                if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
                    continue
                coordinates = geometry.get("coordinates")
                if not isinstance(coordinates, list):
                    continue
                points = [
                    (float(point[0]), float(point[1]))
                    for point in coordinates
                    if isinstance(point, list)
                    and len(point) >= 2
                    and isinstance(point[0], (int, float))
                    and isinstance(point[1], (int, float))
                ]
                for start, end in zip(points, points[1:], strict=False):
                    neighbors.setdefault(start, set()).add(end)
                    neighbors.setdefault(end, set()).add(start)
            intersection_points = sorted(point for point, adjacent in neighbors.items() if len(adjacent) >= 3)
            displayed_intersections = self._bounded(intersection_points, MAX_MAP_INTERSECTIONS)
            intersection_features = [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": list(point)},
                    "properties": {},
                }
                for point in displayed_intersections
            ]
            topology_hash = gold.get("graph_topology_sha256")
            layers.append(
                MapLayer(
                    layer="intersections",
                    state="AVAILABLE",
                    complete=len(displayed_intersections) == len(intersection_points),
                    total_feature_count=len(intersection_points),
                    returned_feature_count=len(displayed_intersections),
                    selection_policy="Canonical degree >= 3 intersections, evenly sampled only above 1500.",
                    geojson={"type": "FeatureCollection", "features": intersection_features},
                    evidence_class=EvidenceClass.DERIVED,
                    source="canonical OSM graph",
                    source_version=str(gold.get("graph_version")) if gold.get("graph_version") else None,
                    observed_at=_parse_timestamp(gold.get("generated_at")),
                    artifact_hash=str(topology_hash) if topology_hash else road_hash,
                )
            )
        except ArtifactNotReady:
            layers.extend(
                [
                    unavailable("roads", "pilot_roads.geojson"),
                    unavailable("intersections", "canonical OSM graph"),
                ]
            )

        try:
            all_pois = self.repository.geojson_features("raw/osm/silver_pois.geojson")
            commercial_pois = []
            for feature in all_pois:
                properties = feature.get("properties")
                if not isinstance(properties, dict):
                    continue
                amenity = str(properties.get("amenity", "")).lower()
                shop = str(properties.get("shop", "")).lower()
                if amenity in {"restaurant", "fast_food", "cafe"} or shop not in {"", "none"}:
                    commercial_pois.append(feature)
            displayed_pois = self._bounded(commercial_pois, MAX_MAP_POIS)
            layers.append(
                MapLayer(
                    layer="pois",
                    state="AVAILABLE",
                    complete=len(displayed_pois) == len(commercial_pois),
                    total_feature_count=len(commercial_pois),
                    returned_feature_count=len(displayed_pois),
                    selection_policy="Commercial OSM POIs, evenly sampled only above 1500.",
                    geojson={"type": "FeatureCollection", "features": displayed_pois},
                    evidence_class=EvidenceClass.PUBLIC_GEOGRAPHIC,
                    source="silver_pois.geojson",
                    source_version=source_version,
                    observed_at=observed_at,
                    artifact_hash=self.repository.artifact_hash("raw/osm/silver_pois.geojson"),
                )
            )
        except ArtifactNotReady:
            layers.append(unavailable("pois", "silver_pois.geojson"))

        self._map_layers_cache = MapLayerListResponse(data=layers)
        return self._map_layers_cache

    def _freshness_seconds(self, provider: str) -> int:
        env_name = f"ZONEPILOT_FRESHNESS_{provider.upper().replace('-', '_')}_SECONDS"
        value = os.environ.get(env_name)
        if value is None:
            return DEFAULT_FRESHNESS_SECONDS.get(provider, 24 * 60 * 60)
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{env_name} must be an integer") from exc
        if parsed <= 0:
            raise ValueError(f"{env_name} must be greater than zero")
        return parsed

    def data_health(self) -> DataHealthResponse:
        evaluated_at = self.now().astimezone(timezone.utc)
        runs_by_provider: dict[str, list[dict[str, Any]]] = {}
        for manifest in self.repository.daily_manifests():
            runs = manifest.get("runs", [])
            if not isinstance(runs, list):
                raise ArtifactCorrupt("Daily manifest runs field must be a list")
            for run in runs:
                if not isinstance(run, dict) or not isinstance(run.get("provider"), str):
                    raise ArtifactCorrupt("Daily manifest contains a run without a provider")
                runs_by_provider.setdefault(run["provider"], []).append(run)

        if self.repository.osm_manifest() is not None:
            runs_by_provider.setdefault("osm", [])
        if self.repository.osrm_manifest() is not None:
            runs_by_provider.setdefault("osrm", [])

        health: list[ProviderHealth] = []
        for provider, runs in sorted(runs_by_provider.items()):
            expected = self._freshness_seconds(provider)
            latest_run = max(
                runs,
                key=lambda run: _parse_timestamp(run.get("completed_at") or run.get("started_at"))
                or datetime.min.replace(tzinfo=timezone.utc),
                default=None,
            )
            successes = [
                run
                for run in runs
                if str(run.get("status", "")).upper() in {"COMPLETED", "SUCCESS"}
                and _parse_timestamp(run.get("completed_at") or run.get("started_at")) is not None
            ]
            last_success = max(
                (_parse_timestamp(run.get("completed_at") or run.get("started_at")) for run in successes),
                default=None,
            )

            if provider == "osm" and last_success is None:
                osm = self.repository.osm_manifest()
                last_success = _parse_timestamp(osm.get("timestamp")) if osm else None
            if provider == "osrm" and last_success is None:
                osrm = self.repository.osrm_manifest()
                last_success = _parse_timestamp(osrm.get("generated_at")) if osrm else None

            age = max(0, int((evaluated_at - last_success).total_seconds())) if last_success else None
            latest_status = str(latest_run.get("status")) if latest_run else ("COMPLETED" if last_success else None)
            latest_failed = latest_status is not None and latest_status.upper() not in {"COMPLETED", "SUCCESS"}
            missing_intervals = latest_run.get("missing_intervals") if latest_run else None
            latest_success_run = max(
                successes,
                key=lambda run: _parse_timestamp(run.get("completed_at") or run.get("started_at"))
                or datetime.min.replace(tzinfo=timezone.utc),
                default=None,
            )
            latest_success_records = (
                latest_success_run.get("records_written", latest_success_run.get("records_received"))
                if latest_success_run
                else None
            )
            if isinstance(missing_intervals, int) and missing_intervals > 0:
                dq_result = DQResult.FAIL
            elif latest_success_records == 0 and provider not in {"osm", "osrm"}:
                dq_result = DQResult.UNKNOWN
            elif last_success:
                dq_result = DQResult.PASS
            else:
                dq_result = DQResult.UNKNOWN

            if last_success is None:
                state = ProviderState.UNAVAILABLE
            elif age is not None and age > expected * 2:
                state = ProviderState.STALE
            elif latest_failed or (age is not None and age > expected):
                state = ProviderState.DEGRADED
            else:
                state = ProviderState.FRESH

            dataset_ids = sorted(
                {
                    f"{provider}:{run['dataset']}"
                    for run in runs
                    if isinstance(run.get("dataset"), str)
                }
            )
            if provider == "osm":
                dataset_ids.append("gold_network_bengaluru")
            if provider == "osrm":
                dataset_ids.append("osrm:network_snapshot")

            health.append(
                ProviderHealth(
                    provider=provider,
                    state=state,
                    last_successful_collection=last_success,
                    expected_freshness_seconds=expected,
                    observed_freshness_seconds=age,
                    dq_result=dq_result,
                    latest_run_status=latest_status,
                    dataset_ids=sorted(set(dataset_ids)),
                )
            )
        return DataHealthResponse(data=health, evaluated_at=evaluated_at)

    def get_evidence(self, entity_type: str, entity_id: str) -> EvidenceResponse:
        if entity_type == "dataset":
            dataset = next((item for item in self.list_datasets().data if item.dataset_id == entity_id), None)
            if dataset is None:
                raise LookupError(f"Dataset evidence {entity_id} is not available")
            record = EvidenceRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                evidence_class=dataset.evidence_class,
                source=dataset.source,
                source_version=dataset.source_version,
                observed_at=dataset.observed_at,
                artifact_hash=dataset.artifact_hash,
                metadata={
                    "version": dataset.version,
                    "availability": dataset.availability.value,
                    "record_count": dataset.record_count,
                    "run_id": dataset.run_id,
                },
            )
        elif entity_type == "zone":
            zone = self.get_zone_state(entity_id).data
            record = EvidenceRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                evidence_class=zone.evidence_class,
                source=zone.source,
                source_version=zone.source_version,
                observed_at=zone.observed_at,
                artifact_hash=zone.artifact_hash,
                metadata={
                    "h3_resolution": zone.resolution,
                    "road_length_km": zone.static.road_length_km.value,
                    "intersection_count": zone.static.intersection_count.value,
                },
            )
        elif entity_type == "network":
            snapshot = self.get_network_snapshot(entity_id).data
            record = EvidenceRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                evidence_class=snapshot.evidence_class,
                source=snapshot.source,
                source_version=snapshot.source_version,
                observed_at=snapshot.observed_at,
                artifact_hash=snapshot.artifact_hash,
                metadata={
                    "graph_version": snapshot.graph_version,
                    "h3_resolution": snapshot.h3_resolution,
                    "graph_vertices": snapshot.metrics.graph_vertices,
                    "graph_directed_edges": snapshot.metrics.graph_directed_edges,
                },
            )
        else:
            raise ValueError("entity_type must be one of: dataset, network, zone")
        return EvidenceResponse(data=record)


@lru_cache(maxsize=1)
def get_observatory_service() -> ObservatoryService:
    return ObservatoryService(ArtifactCatalogRepository.from_environment())
