import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List


def get_data_root() -> str:
    root = os.environ.get("ZONEPILOT_DATA_ROOT")
    if not root:
        raise ValueError("ZONEPILOT_DATA_ROOT is required")
    return root


def ensure_directories():
    """Ensure the primary directory structure exists."""
    root = get_data_root()
    dirs = [
        "private/official/raw",
        "private/official/bronze",
        "private/official/silver",
        "private/official/manifests",
        "private/official/checkpoints",
        "private/official/quarantine",
        "private/staging",
        "private/test",
    ]
    for d in dirs:
        os.makedirs(os.path.join(root, d), exist_ok=True)


def get_partition_path(layer: str, provider: str, dataset: str, dt: datetime, run_id: str) -> str:
    """
    Constructs the partition path: layer/provider/dataset/YYYY/MM/DD/run_id
    """
    root = get_data_root()
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")

    path = os.path.join(root, "private", "official", layer, provider, dataset, year, month, day, run_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_raw_data(provider: str, dataset: str, dt: datetime, run_id: str, data: Any, filename: str) -> str:
    """Save raw immutable data and return its SHA-256 hash."""
    path = get_partition_path("raw", provider, dataset, dt, run_id)
    filepath = os.path.join(path, filename)

    # Do not overwrite existing raw files. Raw is immutable.
    if os.path.exists(filepath):
        raise FileExistsError(f"Raw data file already exists: {filepath}")

    content_bytes = json.dumps(data, indent=2).encode("utf-8")
    with open(filepath, "wb") as f:
        f.write(content_bytes)

    return hashlib.sha256(content_bytes).hexdigest()


def save_bronze_data(
    provider: str, dataset: str, dt: datetime, run_id: str, data: List[Dict[str, Any]], filename: str
) -> None:
    """Save normalized bronze data (typically JSONL format)."""
    path = get_partition_path("bronze", provider, dataset, dt, run_id)
    filepath = os.path.join(path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")


def save_silver_data(
    provider: str, dataset: str, dt: datetime, run_id: str, data: List[Dict[str, Any]], filename: str
) -> None:
    """Save canonical silver data (typically JSONL format)."""
    path = get_partition_path("silver", provider, dataset, dt, run_id)
    filepath = os.path.join(path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")
