from __future__ import annotations

import os
import re
from math import isfinite
from typing import Any, Mapping

from services.api.contracts.release_identity import (
    GoldReleaseIdentity,
    GraphReleaseIdentity,
    ReleaseIdentity,
    ReleaseIdentityResponse,
)
from services.api.repositories.artifact_catalog import (
    ArtifactCatalogError,
    ArtifactCatalogRepository,
)

FULL_SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
SEMANTIC_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?")
SAFE_IDENTITY = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,127}")
PLACEHOLDER_VALUES = frozenset(
    {
        "change-me",
        "changeme",
        "dev",
        "development",
        "latest",
        "local",
        "n/a",
        "na",
        "none",
        "null",
        "placeholder",
        "todo",
        "unknown",
        "unset",
    }
)


class ReleaseIdentityUnavailable(RuntimeError):
    """Raised when the release cannot prove one complete immutable identity."""


def _configured_value(environ: Mapping[str, str], name: str, pattern: re.Pattern[str]) -> str:
    value = environ.get(name, "").strip()
    if not value or value.lower() in PLACEHOLDER_VALUES or pattern.fullmatch(value) is None:
        raise ReleaseIdentityUnavailable(f"{name} is not a valid immutable release value")
    return value


def _manifest_value(manifest: dict[str, Any], name: str, pattern: re.Pattern[str], artifact: str) -> str:
    value = manifest.get(name)
    if (
        not isinstance(value, str)
        or value.lower() in PLACEHOLDER_VALUES
        or pattern.fullmatch(value) is None
        or ".." in value
    ):
        raise ReleaseIdentityUnavailable(f"{artifact} identity is incomplete")
    return value


def _positive_int(manifest: dict[str, Any], name: str, artifact: str) -> int:
    value = manifest.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ReleaseIdentityUnavailable(f"{artifact} identity is incomplete")
    return value


def _zero_int(manifest: dict[str, Any], name: str, artifact: str) -> int:
    value = manifest.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise ReleaseIdentityUnavailable(f"{artifact} identity is incomplete")
    return value


def _positive_number(manifest: dict[str, Any], name: str, artifact: str) -> float:
    value = manifest.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
        raise ReleaseIdentityUnavailable(f"{artifact} identity is incomplete")
    return float(value)


class ReleaseIdentityService:
    def __init__(
        self,
        repository: ArtifactCatalogRepository,
        environ: Mapping[str, str] | None = None,
    ):
        self.repository = repository
        self.environ = os.environ if environ is None else environ

    def get_release_identity(self) -> ReleaseIdentityResponse:
        app_version = _configured_value(self.environ, "ZONEPILOT_APP_VERSION", SEMANTIC_VERSION)
        git_sha = _configured_value(self.environ, "ZONEPILOT_GIT_SHA", FULL_SHA)
        schema_version = _configured_value(self.environ, "ZONEPILOT_SCHEMA_VERSION", SEMANTIC_VERSION)

        try:
            gold_manifest = self.repository.gold_manifest()
            osrm_manifest = self.repository.osrm_manifest()
            osrm_build_manifest = self.repository.osrm_build_manifest()
            if osrm_manifest is None or osrm_build_manifest is None:
                raise ReleaseIdentityUnavailable("Graph identity is unavailable")
            actual_gold_sha = self.repository.gold_artifact_hash()
            actual_graph_sha = self.repository.osrm_graph_bundle_hash()
        except ReleaseIdentityUnavailable:
            raise
        except ArtifactCatalogError as exc:
            raise ReleaseIdentityUnavailable("Artifact identity could not be verified") from exc

        gold_code_sha = _manifest_value(gold_manifest, "code_sha", FULL_SHA, "Gold")
        gold_schema_version = _manifest_value(
            gold_manifest,
            "schema_version",
            SEMANTIC_VERSION,
            "Gold",
        )
        expected_gold_sha = _manifest_value(gold_manifest, "parquet_sha256", SHA256, "Gold")
        if gold_schema_version != schema_version:
            raise ReleaseIdentityUnavailable("Gold identity does not match the deployed release")
        if gold_manifest.get("dq_status") != "PASS" or expected_gold_sha != actual_gold_sha:
            raise ReleaseIdentityUnavailable("Gold artifact could not be verified")
        gold_inputs = gold_manifest.get("input_hashes")
        if not isinstance(gold_inputs, dict):
            raise ReleaseIdentityUnavailable("Gold identity is incomplete")
        gold_pbf_sha = _manifest_value(gold_inputs, "roads_pbf_sha256", SHA256, "Gold")

        graph_build_code_sha = _manifest_value(osrm_build_manifest, "code_sha", FULL_SHA, "Graph")
        graph_smoke_code_sha = _manifest_value(osrm_manifest, "code_sha", FULL_SHA, "Graph")
        expected_build_graph_sha = _manifest_value(
            osrm_build_manifest,
            "graph_bundle_sha256",
            SHA256,
            "Graph",
        )
        expected_graph_sha = _manifest_value(
            osrm_manifest,
            "graph_bundle_sha256",
            SHA256,
            "Graph",
        )
        build_pbf_sha = _manifest_value(osrm_build_manifest, "input_pbf_sha256", SHA256, "Graph")
        smoke_pbf_sha = _manifest_value(osrm_manifest, "PBF_sha", SHA256, "Graph")
        if (
            expected_build_graph_sha != actual_graph_sha
            or expected_graph_sha != actual_graph_sha
            or build_pbf_sha != smoke_pbf_sha
            or build_pbf_sha != gold_pbf_sha
        ):
            raise ReleaseIdentityUnavailable("Graph artifact could not be verified")
        if osrm_build_manifest.get("dq_status") != "PASS" or osrm_manifest.get("dq_status") != "PASS":
            raise ReleaseIdentityUnavailable("Graph evidence did not pass data quality checks")
        _positive_number(osrm_manifest, "distance_m", "Graph")
        _positive_number(osrm_manifest, "duration_s", "Graph")
        _positive_int(osrm_manifest, "finite_cells", "Graph")
        _zero_int(osrm_manifest, "null_cells", "Graph")

        identity = ReleaseIdentity(
            app_version=app_version,
            git_sha=git_sha,
            schema_version=schema_version,
            gold=GoldReleaseIdentity(
                dataset_id=_manifest_value(gold_manifest, "dataset_id", SAFE_IDENTITY, "Gold"),
                dataset_version=_manifest_value(
                    gold_manifest,
                    "dataset_version",
                    SAFE_IDENTITY,
                    "Gold",
                ),
                schema_version=gold_schema_version,
                artifact_sha256=actual_gold_sha,
                record_count=_positive_int(gold_manifest, "rows", "Gold"),
            ),
            graph=GraphReleaseIdentity(
                graph_version=_manifest_value(
                    gold_manifest,
                    "graph_version",
                    SAFE_IDENTITY,
                    "Graph",
                ),
                topology_sha256=_manifest_value(
                    gold_manifest,
                    "graph_topology_sha256",
                    SHA256,
                    "Graph",
                ),
                bundle_sha256=actual_graph_sha,
            ),
        )
        return ReleaseIdentityResponse(data=identity)


def get_release_identity_service() -> ReleaseIdentityService:
    return ReleaseIdentityService(ArtifactCatalogRepository.from_environment())
