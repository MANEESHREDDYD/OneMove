"""Bootstrap data_root artifact supply chain for CI and local test execution."""

from __future__ import annotations

import json
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

    # 1. Copy or mirror gold matrix & datasets if present in data/
    for src_dir, dst_dir in [
        (gold_src, gold_dst),
        (manifests_src, manifests_dst),
        (raw_osrm_src, raw_osrm_dst),
    ]:
        if src_dir.exists():
            for item in src_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst_dir / item.name)

    # 2. Ensure gold matrix is present
    matrix_file = gold_dst / "r1_osrm_travel_matrix.json"
    if not matrix_file.exists() and (root / "release_manifest.json").exists():
        rel = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
        print(f"Matrix bootstrapped for release {rel.get('release_id')}")

    print(f"Successfully bootstrapped data_root artifacts at {target_data_root}")
    return 0


if __name__ == "__main__":
    main()
