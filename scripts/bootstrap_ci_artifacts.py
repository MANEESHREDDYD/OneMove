"""Bootstrap data_root artifact supply chain for CI and local test execution."""

from __future__ import annotations

import base64
import hashlib
import os
import shutil
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    target_data_root = Path(os.environ.get("ZONEPILOT_DATA_ROOT", root / "data_root"))

    gold_src = root / "data" / "private" / "official" / "gold"
    manifests_src = root / "data" / "private" / "official" / "manifests"
    raw_osrm_src = root / "data" / "private" / "official" / "raw" / "osrm"

    gold_dst = target_data_root / "private" / "official" / "gold"
    manifests_dst = target_data_root / "private" / "official" / "manifests"
    raw_osrm_dst = target_data_root / "private" / "official" / "raw" / "osrm"

    gold_dst.mkdir(parents=True, exist_ok=True)
    manifests_dst.mkdir(parents=True, exist_ok=True)
    raw_osrm_dst.mkdir(parents=True, exist_ok=True)

    # 1. Copy JSON manifests and matrices from data/
    for src_dir, dst_dir in [
        (gold_src, gold_dst),
        (manifests_src, manifests_dst),
        (raw_osrm_src, raw_osrm_dst),
    ]:
        if src_dir.exists():
            for item in src_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst_dir / item.name)

    # 2. Restore gold_network_h3_8.parquet from authentic b64 payload if not present
    gold_parquet_dst = gold_dst / "gold_network_h3_8.parquet"
    gold_parquet_src = gold_src / "gold_network_h3_8.parquet"
    b64_file = gold_src / "gold_network_h3_8.b64"

    if b64_file.exists():
        raw_bytes = base64.b64decode(b64_file.read_text(encoding="utf-8").strip())
        sha = hashlib.sha256(raw_bytes).hexdigest()
        assert sha == "7d8973d37a73d86000b066a2e955ea7421d3fa4a878d3538a8114b6a5221747e", f"Corrupt gold parquet: {sha}"
        gold_parquet_dst.write_bytes(raw_bytes)
        if not gold_parquet_src.exists():
            gold_parquet_src.write_bytes(raw_bytes)
        print(f"Restored authentic gold_network_h3_8.parquet (SHA: {sha})")

    print(f"Successfully bootstrapped data_root artifacts at {target_data_root}")
    return 0


if __name__ == "__main__":
    main()
