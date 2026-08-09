import os
import json
import uuid
import datetime
import psycopg

def get_db_connection():
    """Get a connection to the Postgres database using ZONEPILOT_DB_URL"""
    db_url = os.environ.get("ZONEPILOT_DB_URL")
    if not db_url:
        print("Warning: ZONEPILOT_DB_URL not found, using mocked local ledger for testing.")
        return None
    
    # Use autocommit=False to manage transactions explicitly
    return psycopg.connect(db_url, autocommit=False)

def attempt_claim_slot(provider: str, dataset: str, logical_interval: str, query_hash: str) -> bool:
    """
    Attempt to claim the unique logical slot in the distributed database.
    Returns True if successfully claimed, False if ALREADY_RUNNING or SUCCESS.
    """
    conn = get_db_connection()
    if not conn:
        # Fallback to local memory mock
        return True

    try:
        with conn.cursor() as cur:
            # Check if it exists and what the status is
            cur.execute("""
                SELECT status, lease_expires_at 
                FROM zonepilot_ops.collection_runs 
                WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                FOR UPDATE SKIP LOCKED;
            """, (provider, dataset, logical_interval, query_hash))
            
            row = cur.fetchone()
            
            workflow_id = os.environ.get("WORKFLOW_RUN_ID", "local")
            now = datetime.datetime.now(datetime.timezone.utc)
            lease_expires = now + datetime.timedelta(minutes=30)
            
            if row is None:
                # Does not exist, insert and claim
                cur.execute("""
                    INSERT INTO zonepilot_ops.collection_runs 
                    (provider, dataset, logical_interval, query_hash, status, runner_id, claimed_at, lease_expires_at)
                    VALUES (%s, %s, %s, %s, 'RUNNING', %s, %s, %s)
                """, (provider, dataset, logical_interval, query_hash, workflow_id, now, lease_expires))
                conn.commit()
                return True
            else:
                status, existing_lease_expires = row
                if status == 'SUCCESS':
                    conn.rollback()
                    return False # Already complete
                elif status == 'RUNNING':
                    if existing_lease_expires and existing_lease_expires > now:
                        conn.rollback()
                        return False # Another live worker owns it
                    else:
                        # Lease expired, claim recovery
                        cur.execute("""
                            UPDATE zonepilot_ops.collection_runs
                            SET status = 'RUNNING', runner_id = %s, claimed_at = %s, lease_expires_at = %s
                            WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                        """, (workflow_id, now, lease_expires, provider, dataset, logical_interval, query_hash))
                        conn.commit()
                        return True
                else:
                    # FAILED, PARTIAL, etc. Claim recovery
                    cur.execute("""
                        UPDATE zonepilot_ops.collection_runs
                        SET status = 'RUNNING', runner_id = %s, claimed_at = %s, lease_expires_at = %s
                        WHERE provider = %s AND dataset = %s AND logical_interval = %s AND query_hash = %s
                    """, (workflow_id, now, lease_expires, provider, dataset, logical_interval, query_hash))
                    conn.commit()
                    return True

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
