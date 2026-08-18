import json
import os
from datetime import datetime

import pytz

from services.collectors.db import get_db_connection
from services.collectors.storage import get_data_root


def generate_daily_manifest(logical_date: str):
    """
    Generates OFFICIAL_DAILY_MANIFEST_YYYY-MM-DD.
    Gathers all completed collection_runs for the logical_date.
    """
    root = get_data_root()
    manifest_dir = os.path.join(root, "private", "official", "manifests")
    os.makedirs(manifest_dir, exist_ok=True)

    manifest_filepath = os.path.join(manifest_dir, f"OFFICIAL_DAILY_MANIFEST_{logical_date}.json")

    manifest = {
        "logical_date": logical_date,
        "generated_at": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "runs": [],
    }

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM collection_runs 
            WHERE logical_date = ?
            ORDER BY started_at ASC
        """,
            (logical_date,),
        )
        runs = cursor.fetchall()

        for row in runs:
            manifest["runs"].append(dict(row))

    with open(manifest_filepath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated manifest: {manifest_filepath}")
    return manifest_filepath


if __name__ == "__main__":
    today = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")
    generate_daily_manifest(today)
