import os
import sys
import time
import psycopg
import datetime
from services.collectors.db import attempt_claim_slot

def test_db_concurrency():
    db_url = os.environ.get("ZONEPILOT_DB_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    os.environ["ZONEPILOT_DB_URL"] = db_url
    os.environ["ZONEPILOT_ENV"] = "test"
    
    # 1. Apply Schema
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            schema_path = os.path.join("infrastructure", "zonepilot-data-template", "schema.sql")
            with open(schema_path, "r") as f:
                cur.execute(f.read())
                
            cur.execute("DELETE FROM zonepilot_ops.collection_runs;")

    # 2. Worker A Claims
    os.environ["WORKFLOW_RUN_ID"] = "worker-A"
    res_a = attempt_claim_slot("test_prov", "test_ds", "2026-08-09T00", "hash1")
    print(f"Worker A: {res_a}")
    assert res_a == "CLAIMED"

    # 3. Worker B Attempts Claim (ALREADY_RUNNING)
    os.environ["WORKFLOW_RUN_ID"] = "worker-B"
    res_b = attempt_claim_slot("test_prov", "test_ds", "2026-08-09T00", "hash1")
    print(f"Worker B: {res_b}")
    assert res_b == "ALREADY_RUNNING"

    # 4. Worker A Completes
    from services.collectors.db import mark_slot_completed
    mark_slot_completed("test_prov", "test_ds", "2026-08-09T00", "hash1", "SUCCESS", {})
    
    # 5. Worker C Attempts Claim (ALREADY_COMPLETE)
    os.environ["WORKFLOW_RUN_ID"] = "worker-C"
    res_c = attempt_claim_slot("test_prov", "test_ds", "2026-08-09T00", "hash1")
    print(f"Worker C: {res_c}")
    assert res_c == "ALREADY_COMPLETE"

    # 6. Forced Expired Lease
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Manually insert a RUNNING slot with expired lease
            cur.execute("""
                INSERT INTO zonepilot_ops.collection_runs 
                (provider, dataset, logical_interval, query_hash, status, runner_id, claimed_at, lease_expires_at)
                VALUES ('test_prov', 'test_ds', '2026-08-10T00', 'hash2', 'RUNNING', 'worker-old', %s, %s)
            """, (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2), 
                  datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)))

    # 7. Worker D Attempts Claim (RECOVERED_EXPIRED_LEASE)
    os.environ["WORKFLOW_RUN_ID"] = "worker-D"
    res_d = attempt_claim_slot("test_prov", "test_ds", "2026-08-10T00", "hash2")
    print(f"Worker D: {res_d}")
    assert res_d == "RECOVERED_EXPIRED_LEASE"

    # 8. Verify row count
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM zonepilot_ops.collection_runs")
            count = cur.fetchone()[0]
            print(f"Total Rows: {count}")
            assert count == 2
            
            cur.execute("SELECT runner_id FROM zonepilot_ops.collection_runs WHERE logical_interval = '2026-08-10T00'")
            runner = cur.fetchone()[0]
            assert runner == "worker-D"

if __name__ == "__main__":
    test_db_concurrency()
    print("Concurrency proof successful.")
