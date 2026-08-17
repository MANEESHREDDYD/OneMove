import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


class ArtifactCatalogError(RuntimeError):
    pass


class ArtifactNotReady(ArtifactCatalogError):
    pass


class ArtifactNotFound(ArtifactCatalogError):
    pass


class ArtifactCorrupt(ArtifactCatalogError):
    pass


class ArtifactCatalogRepository:
    """Read-only access to locally mounted, immutable ZonePilot artifacts."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._gold_rows_cache: tuple[int, list[dict[str, Any]]] | None = None
        self._geojson_cache: dict[str, tuple[int, list[dict[str, Any]]]] = {}

    @classmethod
    def from_environment(cls) -> "ArtifactCatalogRepository":
        configured_root = os.environ.get("ZONEPILOT_DATA_ROOT")
        if configured_root:
            configured = Path(configured_root)
            official = configured / "private" / "official"
            return cls(official if official.is_dir() else configured)
        repository_root = Path(__file__).resolve().parents[3]
        return cls(repository_root / "data_root" / "private" / "official")

    def _path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if self.root not in path.parents and path != self.root:
            raise ArtifactCatalogError("Artifact path escaped the configured data root")
        return path

    def _read_json(self, relative_path: str, *, required: bool = True) -> dict[str, Any] | None:
        path = self._path(relative_path)
        if not path.is_file():
            if required:
                raise ArtifactNotReady(f"Required artifact manifest is missing: {relative_path}")
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactCorrupt(f"Artifact manifest is unreadable: {relative_path}") from exc
        if not isinstance(data, dict):
            raise ArtifactCorrupt(f"Artifact manifest must contain a JSON object: {relative_path}")
        return data

    def gold_manifest(self) -> dict[str, Any]:
        manifest = self._read_json("manifests/gold_manifest.json")
        assert manifest is not None
        return manifest

    def osm_manifest(self) -> dict[str, Any] | None:
        return self._read_json("raw/osm/manifest.json", required=False)

    def osrm_manifest(self) -> dict[str, Any] | None:
        return self._read_json("manifests/osrm_smoke_manifest.json", required=False)

    def osrm_build_manifest(self) -> dict[str, Any] | None:
        return self._read_json("raw/osrm/benchmark.json", required=False)

    def daily_manifests(self) -> list[dict[str, Any]]:
        manifests_dir = self._path("manifests")
        if not manifests_dir.is_dir():
            return []
        manifests: list[dict[str, Any]] = []
        for path in sorted(manifests_dir.glob("OFFICIAL_DAILY_MANIFEST_*.json")):
            relative_path = path.relative_to(self.root).as_posix()
            manifest = self._read_json(relative_path)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    def gold_artifact_path(self) -> Path:
        return self._path("gold/gold_network_h3_8.parquet")

    def gold_artifact_hash(self) -> str:
        path = self.gold_artifact_path()
        if not path.is_file():
            raise ArtifactNotReady("Gold network artifact is not mounted")
        digest = hashlib.sha256()
        try:
            with path.open("rb") as artifact:
                for block in iter(lambda: artifact.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError as exc:
            raise ArtifactNotReady("Gold network artifact cannot be read") from exc
        return digest.hexdigest()

    def gold_rows(self) -> list[dict[str, Any]]:
        path = self.gold_artifact_path()
        if not path.is_file():
            raise ArtifactNotReady("Gold network artifact is not mounted")
        modified_ns = path.stat().st_mtime_ns
        if self._gold_rows_cache and self._gold_rows_cache[0] == modified_ns:
            return self._gold_rows_cache[1]
        try:
            rows = pq.read_table(path).to_pylist()
        except Exception as exc:
            raise ArtifactCorrupt("Gold network Parquet is unreadable") from exc
        if not all(isinstance(row, dict) and isinstance(row.get("h3_index"), str) for row in rows):
            raise ArtifactCorrupt("Gold network Parquet does not satisfy the H3 row contract")
        self._gold_rows_cache = (modified_ns, rows)
        return rows

    def gold_row(self, zone_id: str) -> dict[str, Any]:
        for row in self.gold_rows():
            if row["h3_index"] == zone_id:
                return row
        raise ArtifactNotFound(f"Zone {zone_id} is not present in the Gold network dataset")

    def network_artifact_available(self) -> bool:
        return self._path("raw/osrm/pilot_roads.osrm").is_file()

    def osrm_graph_bundle_hash(self) -> str:
        """Hash OSRM file names and bytes using the release evidence contract."""

        osrm_dir = self._path("raw/osrm")
        try:
            graph_files = [path for path in osrm_dir.glob("pilot_roads.osrm*") if path.is_file()]
            if not graph_files:
                raise ArtifactNotReady("OSRM graph bundle is not mounted")
            digest = hashlib.sha256()
            for path in sorted(graph_files, key=lambda item: item.relative_to(osrm_dir).as_posix()):
                relative_name = path.relative_to(osrm_dir).as_posix().encode("utf-8")
                digest.update(relative_name)
                digest.update(b"\0")
                with path.open("rb") as artifact:
                    for block in iter(lambda: artifact.read(1024 * 1024), b""):
                        digest.update(block)
                digest.update(b"\0")
        except OSError as exc:
            raise ArtifactNotReady("OSRM graph bundle cannot be read") from exc
        return digest.hexdigest()

    def geojson_features(self, relative_path: str) -> list[dict[str, Any]]:
        path = self._path(relative_path)
        if not path.is_file():
            raise ArtifactNotReady(f"Required map artifact is missing: {relative_path}")
        modified_ns = path.stat().st_mtime_ns
        cached = self._geojson_cache.get(relative_path)
        if cached and cached[0] == modified_ns:
            return cached[1]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactCorrupt(f"Map artifact is unreadable: {relative_path}") from exc
        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list) or not all(isinstance(feature, dict) for feature in features):
            raise ArtifactCorrupt(f"Map artifact is not a GeoJSON FeatureCollection: {relative_path}")
        self._geojson_cache[relative_path] = (modified_ns, features)
        return features

    def artifact_hash(self, relative_path: str) -> str:
        path = self._path(relative_path)
        if not path.is_file():
            raise ArtifactNotReady(f"Required artifact is missing: {relative_path}")
        digest = hashlib.sha256()
        try:
            with path.open("rb") as artifact:
                for block in iter(lambda: artifact.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError as exc:
            raise ArtifactNotReady(f"Artifact cannot be read: {relative_path}") from exc
        return digest.hexdigest()
