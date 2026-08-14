import datetime
import multiprocessing
import os

import psycopg
import pytest

from services.collectors.db import attempt_claim_slot


def _worker_task(worker_id, barrier, queue, provider, dataset, interval, query_hash, db_url):
    os.environ["WORKFLOW_RUN_ID"] = worker_id
    os.environ["ZONEPILOT_DB_URL"] = db_url
    os.environ["ZONEPILOT_ENV"] = "test"
    # Wait for all processes to be ready
    barrier.wait()
    # Attempt claim
    try:
        res = attempt_claim_slot(provider, dataset, interval, query_hash)
        queue.put((worker_id, res))
    except Exception as e:
        queue.put((worker_id, f"ERROR:{str(e)}"))

def test_db_concurrency():
    env = os.environ.get("ZONEPILOT_ENV", "production")
    if env != "test":
        pytest.skip("Test environment not set. Skipping destructive DB test.")
    
    allow_reset = os.environ.get("ZONEPILOT_ALLOW_DB_TEST_RESET")
    if allow_reset != "1":
        pytest.skip("ZONEPILOT_ALLOW_DB_TEST_RESET=1 not set. Skipping DB test.")

    db_url = os.environ.get("ZONEPILOT_DB_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    os.environ["ZONEPILOT_DB_URL"] = db_url
    os.environ["ZONEPILOT_ENV"] = "test"
    
    # Check if DB seems to be production
    if "prod" in db_url.lower():
        pytest.fail("Database URL appears to be production. Aborting test setup.")

    # 1. Apply Schema and Clear
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            schema_path = os.path.join("infrastructure", "zonepilot-data-template", "schema.sql")
            with open(schema_path, "r") as f:
                try:
                    cur.execute(f.read())
                except psycopg.errors.DuplicateObject:
                    pass
            cur.execute("DELETE FROM zonepilot_ops.collection_runs;")

    # 2. Race Stress Test (20 iterations)
    iterations = 20
    workers_per_iter = 4
    
    ctx = multiprocessing.get_context("spawn")

    for i in range(iterations):
        interval = f"2026-08-09T{i:02d}"
        query_hash = f"hash_{i}"
        
        barrier = ctx.Barrier(workers_per_iter)
        queue = ctx.Queue()
        
        processes = []
        for w in range(workers_per_iter):
            worker_id = f"worker-{w}"
            p = ctx.Process(target=_worker_task, args=(worker_id, barrier, queue, "test_prov", "test_ds", interval, query_hash, db_url))
            p.start()
            processes.append(p)
            
        for p in processes:
            p.join(timeout=5)
            
        results = []
        while not queue.empty():
            results.append(queue.get())
            
        assert len(results) == workers_per_iter, f"Expected {workers_per_iter} results, got {len(results)}"
        
        claimed_count = sum(1 for _, res in results if res == "CLAIMED")
        running_count = sum(1 for _, res in results if res == "ALREADY_RUNNING")
        errors = [res for _, res in results if "ERROR:" in res]
        
        assert not errors, f"DB Error occurred: {errors}"
        assert claimed_count == 1, f"Iteration {i}: Expected exactly 1 CLAIMED, got {claimed_count}"
        assert running_count == workers_per_iter - 1, f"Iteration {i}: Expected {workers_per_iter - 1} ALREADY_RUNNING, got {running_count}"
        
        # Verify exactly one logical row
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM zonepilot_ops.collection_runs WHERE logical_interval = %s", (interval,))
                count = cur.fetchone()[0]
                assert count == 1, f"Iteration {i}: Expected 1 canonical row, found {count}"
                
    # 3. Lease Recovery
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO zonepilot_ops.collection_runs 
                (provider, dataset, logical_interval, query_hash, status, runner_id, claimed_at, lease_expires_at)
                VALUES ('test_prov', 'test_ds', '2026-08-10T00', 'hash_lease', 'RUNNING', 'worker-old', %s, %s)
            """, (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2), 
                  datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)))

    os.environ["WORKFLOW_RUN_ID"] = "worker-recover"
    res_d = attempt_claim_slot("test_prov", "test_ds", "2026-08-10T00", "hash_lease")
    assert res_d == "RECOVERED_EXPIRED_LEASE"
    
    # Verify row count wasn't duplicated
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM zonepilot_ops.collection_runs WHERE logical_interval = '2026-08-10T00'")
            count = cur.fetchone()[0]
            assert count == 1
            
            cur.execute("SELECT runner_id FROM zonepilot_ops.collection_runs WHERE logical_interval = '2026-08-10T00'")
            runner = cur.fetchone()[0]
            assert runner == "worker-recover"

if __name__ == "__main__":
    test_db_concurrency()
