import datetime
import json
import os
import uuid

import psycopg
from psycopg.errors import UniqueViolation


def get_db_connection():
    """Get a connection to the Postgres database using ZONEPILOT_DB_URL"""
    db_url = os.environ.get("ZONEPILOT_DB_URL")
    env = os.environ.get("ZONEPILOT_ENV", "production")
    
    if not db_url:
        if env == "test":
            print("Notice: ZONEPILOT_DB_URL not found, but ZONEPILOT_ENV=test. Operating in test mock mode.")
            return None
        else:
            raise RuntimeError("ZONEPILOT_DB_URL is missing in non-test environment. Faiing closed.")
    
    return psycopg.connect(db_url, autocommit=False)

def attempt_claim_slot(provider: str, dataset: str, logical_interval: str, query_hash: str) -> str:
    """
    Attempt to claim the unique logical slot in the distributed database.
    Returns: 'CLAIMED', 'ALREADY_RUNNING', 'ALREADY_COMPLETE', 'RECOVERED_EXPIRED_LEASE'
    """
    conn = get_db_connection()
    if not conn:
        return 'CLAIMED'  # Mock

    workflow_id = os.environ.get("WORKFLOW_RUN_ID", str(uuid.uuid4()))
    now = datetime.datetime.now(datetime.timezone.utc)
    lease_expires = now + datetime.timedelta(minutes=30)

    try:
        with conn.cursor() as cur:
            # 1. Atomic Upsert/Claim attempt
            try:
                cur.execute("""
                    INSERT INTO zonepilot_ops.collection_runs 
                    (provider, dataset, logical_interval, query_hash, status, runner_id, claimed_at, lease_expires_at)
                    VALUES (%s, %s, %s, %s, 'RUNNING', %s, %s, %s)
                    ON CONFLICT (provider, dataset, logical_interval, query_hash) DO NOTHING
                    RETURNING id;
                """, (provider, dataset, logical_interval, query_hash, workflow_id, now, lease_expires))
                
                row = cur.fetchone()
                if row:
                    conn.commit()
                    return 'CLAIMED'
            except UniqueViolation:
                # Just in case DO NOTHING is not used
                conn.rollback()

            # 2. If it wasn't inserted, it already exists. We lock it to see its status.
            cur.execute("""
                SELECT status, lease_expires_at 
                FROM zonepilot_ops.collection_runs 
                WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                FOR UPDATE;
            """, (provider, dataset, logical_interval, query_hash))
            
            existing_row = cur.fetchone()
            if not existing_row:
                # Highly unlikely race where it was deleted right after failed insert
                conn.rollback()
                return 'CLAIMED' # We'll just say claimed and let the next attempt handle it or retry

            status, existing_lease_expires = existing_row
            
            if status == 'SUCCESS':
                conn.rollback()
                return 'ALREADY_COMPLETE'
            elif status == 'RUNNING':
                if existing_lease_expires and existing_lease_expires > now:
                    conn.rollback()
                    return 'ALREADY_RUNNING'
                else:
                    # Expired lease
                    cur.execute("""
                        UPDATE zonepilot_ops.collection_runs
                        SET status = 'RUNNING', runner_id = %s, claimed_at = %s, lease_expires_at = %s
                        WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                    """, (workflow_id, now, lease_expires, provider, dataset, logical_interval, query_hash))
                    conn.commit()
                    return 'RECOVERED_EXPIRED_LEASE'
            else:
                # FAILED, PARTIAL, etc. Recover and retry.
                cur.execute("""
                    UPDATE zonepilot_ops.collection_runs
                    SET status = 'RUNNING', runner_id = %s, claimed_at = %s, lease_expires_at = %s
                    WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                """, (workflow_id, now, lease_expires, provider, dataset, logical_interval, query_hash))
                conn.commit()
                return 'RECOVERED_EXPIRED_LEASE'

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def mark_slot_completed(provider: str, dataset: str, logical_interval: str, query_hash: str, status: str, metadata: dict):
    """Mark the claimed slot with its final outcome (SUCCESS, FAILED, PARTIAL, etc)."""
    conn = get_db_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE zonepilot_ops.collection_runs
                SET status = %s, result_metadata = %s, completed_at = %s
                WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
            """, (status, json.dumps(metadata), datetime.datetime.now(datetime.timezone.utc), provider, dataset, logical_interval, query_hash))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    pass

def record_run_start(run_id, provider, dataset, mode, logical_date):
    """Stub for backwards compatibility with collectors that don't use scheduler claims"""
    pass

def record_run_error(run_id, error_msg):
    """Stub for backwards compatibility"""
    pass

def record_run_complete(run_id, records_written, total_written, metadata):
    """Stub for backwards compatibility"""
    pass
