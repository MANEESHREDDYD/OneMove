import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List


def check_no_staging_contamination(records: List[Dict[str, Any]]) -> bool:
    """Ensure no faker/demo/test data is present using metadata first."""
    forbidden_terms = ["faker", "demo", "test", "synthetic", "mock"]
    forbidden_classes = ["TEST_ONLY", "STAGING_DO_NOT_USE", "DEMO_SYNTHETIC"]

    for record in records:
        ev_class = record.get("evidence_class")
        if ev_class in forbidden_classes:
            return False

        text = json.dumps(record).lower()
        # secondary check
        for term in forbidden_terms:
            if term in text:
                return False

    return True


def to_ts(ts_str):
    if not ts_str:
        return None
    try:
        # Handle "Z" or timezone-aware ISO formats
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str).timestamp()
    except Exception:
        return None


def check_lifecycle_ordering(record: Dict[str, Any]) -> bool:
    """Ensure ordered <= accepted <= ready <= picked_up <= delivered."""
    ordered = to_ts(record.get("ordered_at"))
    accepted = to_ts(record.get("accepted_at"))
    ready = to_ts(record.get("ready_at"))
    pickup = to_ts(record.get("pickup_at"))
    delivered = to_ts(record.get("delivered_at"))

    # We only assert if BOTH adjacent timestamps exist
    if ordered and accepted and ordered > accepted:
        return False
    if accepted and ready and accepted > ready:
        return False
    if ready and pickup and ready > pickup:
        return False
    if pickup and delivered and pickup > delivered:
        return False

    return True


def check_temporal_semantics(records: List[Dict[str, Any]], decision_time_ts: float) -> bool:
    """
    Ensure no temporal leakage.
    information_available_at <= decision_time
    valid_at may be in the future.
    """
    for record in records:
        info_at = to_ts(record.get("information_available_at")) or to_ts(record.get("retrieved_at"))
        if info_at and info_at > decision_time_ts:
            return False

        # We explicitly allow valid_at > decision_time_ts
    return True


def check_invalid_coordinates(records: List[Dict[str, Any]]) -> bool:
    """Ensure latitudes and longitudes are globally valid. Tag if outside Bengaluru/Pilot."""
    for record in records:
        lat = record.get("lat") or record.get("latitude")
        lon = record.get("lon") or record.get("longitude")

        if lat is not None and lon is not None:
            if not (-90.0 <= float(lat) <= 90.0):
                return False
            if not (-180.0 <= float(lon) <= 180.0):
                return False

            record["in_bengaluru"] = (12.0 <= float(lat) <= 13.5) and (77.0 <= float(lon) <= 78.5)
            record["in_pilot_bbox"] = (12.90 <= float(lat) <= 12.98) and (77.58 <= float(lon) <= 77.65)

    return True


def check_impossible_speed(records: List[Dict[str, Any]]) -> bool:
    """Flag speeds over 120km/h for hyperlocal delivery or negative speeds."""
    for record in records:
        speed = record.get("current_speed_kph") or record.get("speed")
        if speed is not None:
            if float(speed) < 0 or float(speed) > 120:
                return False
    return True


def check_duplicates(records: List[Dict[str, Any]], primary_key: str) -> bool:
    """Ensure uniqueness of records based on a primary key."""
    seen = set()
    for record in records:
        val = record.get(primary_key)
        if val:
            if val in seen:
                return False
            seen.add(val)
    return True


def check_hash_mismatch(record: Dict[str, Any], payload: str, stored_hash: str) -> bool:
    """Verify cryptographic integrity of Raw records."""
    computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return computed_hash == stored_hash


def run_dq_checks(silver_records: List[Dict[str, Any]]) -> bool:
    """Run all automated Data Quality checks for Silver tier."""
    if not silver_records:
        return True

    if not check_no_staging_contamination(silver_records):
        print("DQ FAILED: Staging/Synthetic data detected in official records.")
        return False

    now_ts = datetime.now(timezone.utc).timestamp()
    if not check_temporal_semantics(silver_records, now_ts):
        print("DQ FAILED: Temporal leakage detected (information_available_at > decision_time).")
        return False

    if not check_invalid_coordinates(silver_records):
        print("DQ FAILED: Invalid or out-of-bounds coordinates detected.")
        return False

    if not check_impossible_speed(silver_records):
        print("DQ FAILED: Impossible speed detected.")
        return False

    for r in silver_records:
        if not check_lifecycle_ordering(r):
            print(f"DQ FAILED: Lifecycle ordering violation in record {r.get('order_id_hash', 'Unknown')}.")
            return False

    return True
