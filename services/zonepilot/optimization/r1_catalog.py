"""Read-only access to the R1 artifacts on disk.

``r1_network`` declares :class:`~services.zonepilot.optimization.r1_network.ArtifactCatalog`
as a Protocol so the optimizer never hard-codes a storage layout. This module is
the one concrete implementation over the R1 data root.

Every accessor either returns a real, verified artifact or raises. There is no
default, no placeholder, and no synthesised row: a missing manifest must stop a
run rather than let it proceed on invented lineage.

The integrity check on the Gold Parquet is deliberate. The Gold manifest records
``parquet_sha256``; if the file on disk no longer hashes to it, the zone set has
drifted from the artifact the manifest describes and any result built on it
would carry a false ``dataset_version``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from services.zonepilot.optimization.r1_network import R1NetworkUnavailable

GOLD_PARQUET_RELATIVE = Path("private/official/gold/gold_network_h3_8.parquet")
GOLD_MANIFEST_RELATIVE = Path("private/official/manifests/gold_manifest.json")
OSRM_BUILD_MANIFEST_RELATIVE = Path("private/official/raw/osrm/benchmark.json")


def default_data_root() -> Path:
    """Resolve the R1 data root, honouring the pipeline's own env var."""

    return Path(os.environ.get("ZONEPILOT_DATA_ROOT", Path.cwd() / "data_root"))


def _read_json(path: Path, description: str) -> dict[str, Any]:
    if not path.is_file():
        raise R1NetworkUnavailable(f"{description} is missing at {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise R1NetworkUnavailable(f"{description} could not be read: {exc}") from exc
    if not isinstance(payload, dict):
        raise R1NetworkUnavailable(f"{description} is not a JSON object")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileSystemArtifactCatalog:
    """The R1 Gold + OSRM artifacts, read from a data root on disk."""

    def __init__(self, data_root: Path | None = None, *, verify_gold_hash: bool = True) -> None:
        self.data_root = Path(data_root) if data_root is not None else default_data_root()
        self.verify_gold_hash = verify_gold_hash
        self._gold_rows: list[dict[str, Any]] | None = None
        self._gold_manifest: dict[str, Any] | None = None
        self._osrm_build_manifest: dict[str, Any] | None = None

    @property
    def gold_parquet_path(self) -> Path:
        return self.data_root / GOLD_PARQUET_RELATIVE

    def gold_manifest(self) -> dict[str, Any]:
        if self._gold_manifest is None:
            self._gold_manifest = _read_json(self.data_root / GOLD_MANIFEST_RELATIVE, "Gold manifest")
        return self._gold_manifest

    def osrm_build_manifest(self) -> dict[str, Any] | None:
        if self._osrm_build_manifest is None:
            self._osrm_build_manifest = _read_json(
                self.data_root / OSRM_BUILD_MANIFEST_RELATIVE, "OSRM build manifest"
            )
        return self._osrm_build_manifest

    def osrm_graph_bundle_hash(self) -> str:
        manifest = self.osrm_build_manifest() or {}
        bundle_hash = manifest.get("graph_bundle_sha256")
        if not isinstance(bundle_hash, str) or not bundle_hash.strip():
            raise R1NetworkUnavailable("OSRM build manifest does not declare a graph_bundle_sha256")
        return bundle_hash.strip()

    def gold_rows(self) -> list[dict[str, Any]]:
        if self._gold_rows is not None:
            return self._gold_rows

        path = self.gold_parquet_path
        if not path.is_file():
            raise R1NetworkUnavailable(f"Gold network Parquet is missing at {path}")

        if self.verify_gold_hash:
            manifest = self.gold_manifest()
            expected = manifest.get("parquet_sha256")
            if isinstance(expected, str) and expected.strip():
                actual = _sha256_file(path)
                if actual != expected.strip():
                    raise R1NetworkUnavailable(
                        "Gold Parquet does not match the parquet_sha256 recorded in its manifest; "
                        "the zone set has drifted from its declared dataset_version"
                    )

        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - environment guard
            raise R1NetworkUnavailable("pandas is required to read the Gold Parquet artifact") from exc

        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            raise R1NetworkUnavailable(f"Gold network Parquet could not be read: {exc}") from exc

        if "h3_index" not in frame.columns:
            raise R1NetworkUnavailable("Gold network Parquet does not contain an h3_index column")

        rows = frame.to_dict(orient="records")
        # Normalise numpy scalars to plain Python so downstream integer coercion
        # and JSON lineage stay free of numpy types.
        self._gold_rows = [{key: _plain(value) for key, value in row.items()} for row in rows]
        return self._gold_rows


def _plain(value: Any) -> Any:
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (AttributeError, ValueError):  # pragma: no cover - defensive
            return value
    return value
